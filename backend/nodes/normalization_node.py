"""normalization_node.py - Node 3 - Clinical differential with red flag detection"""
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

SYSTEM = """You are a clinical terminology mapper for a patient education tool.
Return ONLY valid JSON:
{
  "term_mappings": [{"patient_said": "exact words", "doctors_call_it": "clinical term", "simple_meaning": "one plain sentence"}],
  "primary_condition": "most likely clinical condition",
  "plain_condition_name": "everyday name",
  "plain_reason": "2 sentences why this fits",
  "alternate_conditions": ["3-5 other possibilities"],
  "red_flags": [{"symptom": "symptom", "concern": "serious condition", "action": "what to do"}],
  "urgency": "emergency_now or see_doctor_today or see_doctor_soon or monitor",
  "urgency_reason": "plain language explanation",
  "confidence": "high or medium or low",
  "confidence_note": "honest plain language about limitations"
}"""


@traceable(name="normalization_node", tags=["clinical"])
def normalization_node(state: PatientState) -> dict:
    if state.get("error") or state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "normalization"}

    raw = state.get("raw_input", "")
    extraction = state.get("extraction", {})
    if not raw:
        return {"normalization": {}, "current_node": "normalization", "error": None}

    logger.info("normalization_node running")
    try:
        prompt = (
            f"Patient said: {raw}\n\n"
            f"Extracted entities: {json.dumps(extraction)}\n\n"
            f"Map to clinical terms and provide full differential."
        )
        resp = get_client().messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1200,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        text = ""
        for block in resp.content:
            if hasattr(block, "text") and block.text:
                text = block.text
                break

        text = text.strip().replace("```json", "").replace("```", "")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            return {"normalization": {}, "current_node": "normalization", "error": None}

        norm = json.loads(text[start:end])
        logger.info(f"normalization_node: {norm.get('primary_condition')} | urgency: {norm.get('urgency')}")
        return {"normalization": norm, "current_node": "normalization", "error": None}

    except Exception as e:
        logger.error(f"normalization_node error: {e}")
        return {"normalization": {}, "current_node": "normalization", "error": None}
