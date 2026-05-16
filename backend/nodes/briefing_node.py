"""briefing_node.py — Node 5 — Web Search Briefing Generator"""
import json
import re
import logging
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

CRITICAL RULES:
- Return ONLY the JSON object. No text before or after it.
- No citation markers like [1] [2] anywhere in text fields
- No markdown formatting inside JSON values
- Spell out ALL acronyms on first use
- Use double quotes for all JSON strings
- Escape any apostrophes in text as \\u0027 or avoid them entirely
- Keep all text fields warm, plain, and human

JSON structure:
{
  "condition_name": "Full clinical name",
  "plain_name": "Plain everyday name",
  "opening": "2-3 warm sentences validating what the patient is experiencing",
  "standard_of_care": {
    "plain_summary": "2-3 sentences about how doctors generally treat this",
    "treatments": [
      {
        "name": "Treatment name",
        "phase": "First-line treatment",
        "plain_description": "1-2 plain sentences about this treatment",
        "what_this_means_for_you": "1 sentence personalizing this"
      }
    ]
  },
  "emerging": [
    {
      "name": "Emerging treatment name",
      "phase": "Phase 2 trial",
      "plain_description": "What researchers are testing and why it matters"
    }
  ],
  "holistic": {
    "intro": "1-2 sentences about complementary approaches",
    "options": [
      {
        "name": "Option name",
        "type": "Lifestyle / Supplement / Mind-Body",
        "plain_description": "What it is and how it may help",
        "note": "Any important caution or note"
      }
    ],
    "reminder": "Always discuss supplements or alternative approaches with your doctor"
  },
  "companies": [
    {
      "name": "Organization name",
      "type": "Research / Nonprofit / Hospital",
      "focus": "What they do for this condition"
    }
  ],
  "sources": [
    {
      "title": "Source title",
      "url": "https://actual-url.org"
    }
  ],
  "closing": "1-2 warm closing sentences encouraging the patient"
}"""


@traceable(name="briefing_node", tags=["briefing", "pipeline"])
def briefing_node(state: PatientState) -> dict:
    if state.get("error"):
        return {"current_node": "briefing"}

    condition = (state.get("final_condition") or "").strip()
    if not condition:
        # Try to get from normalization
        norm = state.get("normalization", {})
        condition = (norm.get("primary_condition") or norm.get("plain_condition_name") or "").strip()

    if not condition:
        logger.error("briefing_node: no condition name found in state")
        return {
            "briefing": None,
            "current_node": "briefing",
            "error": "No condition name available to generate a briefing.",
        }

    logger.info(f"briefing_node generating for: {condition}")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    f"Generate a complete, warm, patient-friendly briefing for: {condition}.\n"
                    f"Use web search for current standard of care, emerging treatments, "
                    f"holistic options, and key organisations.\n"
                    f"CRITICAL: Return ONLY a valid JSON object. "
                    f"No apostrophes in text — use alternative wording. "
                    f"No citation markers. No markdown. Just the JSON."
                )
            }]
        )

        # Collect all text blocks
        texts = " ".join(b.text for b in response.content if hasattr(b, "text") and b.text)

        # Clean up
        texts = re.sub(r'<cite[^>]*>.*?</cite>', '', texts, flags=re.DOTALL)
        texts = re.sub(r'<cite[^>]*>', '', texts)
        texts = re.sub(r'</cite>', '', texts)
        texts = re.sub(r'\[\d+\]', '', texts)
        texts = texts.replace("```json", "").replace("```", "").strip()

        # Extract JSON
        s = texts.find("{")
        e = texts.rfind("}")
        if s == -1:
            raise ValueError("No JSON object found in briefing response.")

        json_str = texts[s:e+1]

        # Try to parse — if fails, do aggressive cleanup
        try:
            briefing = json.loads(json_str)
        except json.JSONDecodeError as je:
            logger.warning(f"First parse failed ({je}), attempting cleanup")
            # Remove control characters
            json_str = re.sub(r'[\x00-\x1f\x7f]', ' ', json_str)
            # Fix common issues: trailing commas before }]
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            briefing = json.loads(json_str)

        logger.info(f"briefing_node complete for: {condition}")
        return {
            "briefing": briefing,
            "current_node": "briefing",
            "error": None,
        }

    except Exception as exc:
        logger.error(f"briefing_node error: {exc}")
        return {
            "briefing": None,
            "current_node": "briefing",
            "error": f"Briefing failed: {exc}",
        }
