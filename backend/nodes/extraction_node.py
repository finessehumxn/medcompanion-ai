"""extraction_node.py — Node 2"""
import json, logging
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = None

def get_client():
    global client
    if client is None:
        client = anthropic.Anthropic()
    return client

try:
    from langsmith import traceable
except ImportError:
    def traceable(**kw):
        def decorator(fn): return fn
        return decorator

SYSTEM = """Extract health entities from the patient message. The message may be about the patient OR a family member.

Return ONLY valid JSON:
{
  "symptoms": ["symptoms, conditions, or diagnoses mentioned"],
  "body_parts": ["body areas mentioned"],
  "duration": ["time expressions like 'for 3 days'"],
  "severity": ["severity words like 'severe', 'mild'"],
  "medications": ["medications mentioned"],
  "emotional_context": ["emotions like scared, worried, confused"],
  "context_type": "self or caregiver or inquiry",
  "conditions_mentioned": ["specific medical conditions named"]
}
Use empty lists [] for fields with nothing. Return ONLY the JSON object."""


@traceable(name="extraction_node", tags=["nlp"])
def extraction_node(state: PatientState) -> dict:
    if state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "extraction"}
    raw = state.get("raw_input", "")
    if not raw:
        return {"extraction": {}, "current_node": "extraction", "error": "No input"}

    logger.info(f"extraction_node: {raw[:60]}")
    try:
        from ._fast import fast_create
        resp = fast_create(
            get_client(),
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )

        # Safe content extraction - handle tool use blocks
        text = ""
        for block in resp.content:
            if hasattr(block, "text") and block.text:
                text = block.text
                break

        if not text:
            logger.warning("extraction_node: no text block in response")
            return {"extraction": {}, "current_node": "extraction", "error": None}

        text = text.strip().replace("```json", "").replace("```", "")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            logger.warning(f"extraction_node: no JSON found in: {text[:100]}")
            return {"extraction": {}, "current_node": "extraction", "error": None}

        extraction = json.loads(text[start:end])

        # Merge conditions into symptoms if symptoms empty
        if not extraction.get("symptoms") and extraction.get("conditions_mentioned"):
            extraction["symptoms"] = extraction["conditions_mentioned"]

        logger.info(f"extraction_node done: {len(extraction.get('symptoms', []))} items")
        return {"extraction": extraction, "current_node": "extraction", "error": None}

    except Exception as e:
        logger.error(f"extraction_node error: {e}")
        # Return empty extraction instead of crashing - let pipeline continue
        return {"extraction": {}, "current_node": "extraction", "error": None}



