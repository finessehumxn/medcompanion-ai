"""briefing_node.py — Node 5"""
import json, re, logging
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

try:
    from langsmith import traceable
except ImportError:
    def traceable(**kw):
        def decorator(fn): return fn
        return decorator

SYSTEM_PROMPT = """You are a warm, patient-friendly medical information specialist.

Generate a complete health briefing as a SINGLE valid JSON object.

ABSOLUTE JSON RULES — failure to follow these will break the system:
- Return ONLY the JSON object. Zero text before or after it.
- Use ONLY double quotes for ALL strings. Never use single quotes.
- No apostrophes anywhere — write "does not" instead of "doesn't", "it is" instead of "it's"
- No citation markers [1] [2] anywhere in any field
- No markdown, no asterisks, no headers inside any field
- No trailing commas after the last item in any array or object
- Every string value must be on ONE line — no line breaks inside string values
- Spell out ALL acronyms on first use

JSON structure — every field is required:
{
  "condition_name": "Full clinical name",
  "plain_name": "Everyday plain name",
  "opening": "2-3 warm sentences. No apostrophes.",
  "standard_of_care": {
    "plain_summary": "2-3 sentences about treatment. No apostrophes.",
    "treatments": [
      {
        "name": "Treatment name",
        "phase": "First-line treatment",
        "plain_description": "What this is and how it helps. No apostrophes.",
        "what_this_means_for_you": "One personalizing sentence. No apostrophes."
      }
    ]
  },
  "emerging": [
    {
      "name": "Emerging treatment name",
      "phase": "Phase 2 trial",
      "plain_description": "What researchers are testing. No apostrophes."
    }
  ],
  "holistic": {
    "intro": "Brief intro to complementary approaches. No apostrophes.",
    "options": [
      {
        "name": "Approach name",
        "type": "Lifestyle",
        "plain_description": "What it is and how it may help. No apostrophes.",
        "note": "Any caution. No apostrophes."
      }
    ],
    "reminder": "Always discuss with your doctor before starting anything new."
  },
  "companies": [
    {
      "name": "Organization name",
      "type": "Research",
      "focus": "What they do for this condition."
    }
  ],
  "sources": [
    {
      "title": "Source title",
      "url": "https://actual-url.org"
    }
  ],
  "closing": "1-2 warm closing sentences. No apostrophes."
}"""


def repair_json(text: str) -> str:
    """Aggressively repair common JSON issues from LLM output."""
    # Remove code fences
    text = text.replace("```json", "").replace("```", "").strip()

    # Extract JSON object
    s = text.find("{")
    e = text.rfind("}")
    if s == -1:
        raise ValueError(f"No JSON object found. Preview: {text[:200]}")
    text = text[s:e+1]

    # Remove control characters (except \n \t which are valid in JSON)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Fix trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Fix unescaped newlines inside strings
    # Find strings and replace literal newlines inside them
    def fix_newlines_in_strings(m):
        return m.group(0).replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_newlines_in_strings, text, flags=re.DOTALL)

    # Fix single-quoted strings — convert to double-quoted
    # Only do this if the text uses single quotes as string delimiters
    if text.count('"') < text.count("'") // 2:
        text = text.replace("'", '"')

    return text


@traceable(name="briefing_node", tags=["briefing", "pipeline"])
def briefing_node(state: PatientState) -> dict:
    if state.get("error"):
        return {"current_node": "briefing"}

    # Condition from multiple fallbacks
    condition = (state.get("final_condition") or "").strip()
    if not condition:
        norm = state.get("normalization", {})
        condition = (norm.get("primary_condition") or norm.get("plain_condition_name") or "").strip()
    if not condition:
        condition = state.get("raw_input", "").strip()[:150]

    if not condition:
        return {"briefing": None, "current_node": "briefing",
                "error": "No condition name available."}

    logger.info(f"briefing_node: {condition}")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    f"Generate a complete patient-friendly health briefing for: {condition}\n\n"
                    f"Use web search. Prioritize NIH, Mayo Clinic, FDA, PubMed, OpenEvidence.\n"
                    f"If multiple conditions are mentioned, cover their relationship.\n"
                    f"Include at least 2-3 items in every array.\n\n"
                    f"CRITICAL: Return ONLY valid JSON. "
                    f"NO apostrophes in any text field — use full words instead. "
                    f"NO citation markers. NO line breaks inside string values."
                )
            }]
        )

        # Collect all text blocks
        texts = ""
        for block in response.content:
            if hasattr(block, "text") and block.text:
                texts += block.text

        # Remove citation tags
        texts = re.sub(r'<cite[^>]*>.*?</cite>', '', texts, flags=re.DOTALL)
        texts = re.sub(r'</?cite[^>]*>', '', texts)
        texts = re.sub(r'\[\d+\]', '', texts)

        # Try parsing with progressive repair
        json_str = repair_json(texts)

        try:
            briefing = json.loads(json_str)
        except json.JSONDecodeError as e1:
            logger.warning(f"Parse attempt 1 failed: {e1}")
            # More aggressive: escape problematic characters
            # Find the position of the error and fix around it
            err_pos = e1.pos if hasattr(e1, 'pos') else 0
            logger.warning(f"Error near: {repr(json_str[max(0,err_pos-30):err_pos+30])}")

            # Try replacing smart quotes
            json_str2 = json_str.replace('\u2018', '').replace('\u2019', '').replace('\u201c', '"').replace('\u201d', '"')
            # Remove any remaining problematic chars near the error
            json_str2 = re.sub(r"(?<=: \")([^\"]*)'([^\"]*?)(?=\")", r'\1\2', json_str2)

            try:
                briefing = json.loads(json_str2)
            except json.JSONDecodeError as e2:
                logger.error(f"Parse attempt 2 failed: {e2}")
                raise ValueError(f"JSON parsing failed: {e2}")

        logger.info(f"briefing_node complete: {condition}")
        return {"briefing": briefing, "current_node": "briefing", "error": None}

    except Exception as exc:
        logger.error(f"briefing_node error: {exc}")
        return {"briefing": None, "current_node": "briefing", "error": f"Briefing failed: {exc}"}
