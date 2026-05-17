"""briefing_node.py — Node 5 — Final stable version"""
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


def clean_for_json(text: str) -> str:
    """Remove characters that break JSON parsing."""
    if not text:
        return ""
    # Replace curly apostrophes and quotes
    text = text.replace('\u2018', '').replace('\u2019', '').replace('\u201c', '"').replace('\u201d', '"')
    # Replace straight apostrophes in contractions
    text = re.sub(r"(\w)'(\w)", r"\1\2", text)  # don't -> dont, it's -> its
    # Remove remaining apostrophes
    text = text.replace("'", "")
    # Remove newlines and tabs inside what will be string values
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # Collapse multiple spaces
    text = re.sub(r' +', ' ', text).strip()
    return text


def safe_json_loads(text: str) -> dict:
    """Try multiple strategies to parse JSON from LLM output."""
    # Clean code fences
    text = text.replace("```json", "").replace("```", "").strip()

    # Extract JSON object
    s = text.find("{")
    e = text.rfind("}")
    if s == -1:
        raise ValueError("No JSON object in response")

    json_str = text[s:e+1]

    # Strategy 1: direct parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Strategy 2: fix trailing commas
    cleaned = re.sub(r',(\s*[}\]])', r'\1', json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: remove all apostrophes and fix newlines in strings
    def fix_string_values(m):
        val = m.group(0)
        val = re.sub(r"(?<=\w)'(?=\w)", '', val)  # contractions
        val = val.replace("'", "")
        val = val.replace('\n', ' ').replace('\r', ' ')
        return val

    cleaned2 = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_values, cleaned, flags=re.DOTALL)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError:
        pass

    # Strategy 4: remove ALL non-ASCII and control characters
    cleaned3 = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned2)
    cleaned3 = re.sub(r',(\s*[}\]])', r'\1', cleaned3)
    try:
        return json.loads(cleaned3)
    except json.JSONDecodeError as e:
        raise ValueError(f"All JSON repair strategies failed. Last error: {e}")


SYSTEM_PROMPT = """You are a medical information specialist generating patient-friendly health briefings.

CRITICAL: Return a single valid JSON object. Follow these rules exactly:
- NO apostrophes anywhere. Write "does not" not "doesn't". Write "it is" not "it's".
- NO line breaks inside string values. Each value must be on one continuous line.
- NO citation markers like [1] or [2].
- NO markdown inside values.
- Use double quotes for all strings.
- Include at least 2 items in every array.

Return this exact structure:
{
  "condition_name": "clinical name here",
  "plain_name": "everyday name here",
  "opening": "warm 2-3 sentence opening without apostrophes",
  "standard_of_care": {
    "plain_summary": "how doctors treat this without apostrophes",
    "treatments": [
      {"name": "name", "phase": "First-line", "plain_description": "description without apostrophes", "what_this_means_for_you": "one sentence without apostrophes"}
    ]
  },
  "emerging": [
    {"name": "name", "phase": "phase", "plain_description": "description without apostrophes"}
  ],
  "holistic": {
    "intro": "intro without apostrophes",
    "options": [
      {"name": "name", "type": "type", "plain_description": "description without apostrophes", "note": "note without apostrophes"}
    ],
    "reminder": "reminder without apostrophes"
  },
  "companies": [
    {"name": "org name", "type": "type", "focus": "focus without apostrophes"}
  ],
  "sources": [
    {"title": "title", "url": "https://url.org"}
  ],
  "closing": "warm closing without apostrophes"
}"""


@traceable(name="briefing_node", tags=["briefing", "pipeline"])
def briefing_node(state: PatientState) -> dict:
    if state.get("error"):
        return {"current_node": "briefing"}

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
                    f"Generate a complete patient briefing for: {condition}\n\n"
                    f"Search for current information. Use NIH, Mayo Clinic, FDA, PubMed, OpenEvidence.\n"
                    f"If multiple conditions mentioned, cover their relationship.\n\n"
                    f"CRITICAL RULES:\n"
                    f"1. NO apostrophes in any text. Use full words only.\n"
                    f"2. NO line breaks inside string values.\n"
                    f"3. NO citation markers.\n"
                    f"4. At least 2 items in every array.\n"
                    f"5. Return ONLY the JSON object."
                )
            }]
        )

        texts = ""
        for block in response.content:
            if hasattr(block, "text") and block.text:
                texts += block.text

        # Remove citation tags
        texts = re.sub(r'<cite[^>]*>.*?</cite>', '', texts, flags=re.DOTALL)
        texts = re.sub(r'</?cite[^>]*>', '', texts)
        texts = re.sub(r'\[\d+\]', '', texts)

        briefing = safe_json_loads(texts)

        logger.info(f"briefing_node complete: {condition}")
        return {"briefing": briefing, "current_node": "briefing", "error": None}

    except Exception as exc:
        logger.error(f"briefing_node error: {exc}")
        return {"briefing": None, "current_node": "briefing",
                "error": f"Briefing failed: {exc}"}
