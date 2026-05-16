"""extraction_node.py — Node 2"""
import json, logging
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

SYSTEM = """Extract health entities from the patient message. Return ONLY valid JSON:
{"symptoms": [], "body_parts": [], "duration": [], "severity": [], "medications": [], "emotional_context": []}"""

@traceable(name="extraction_node", tags=["nlp"])
def extraction_node(state: PatientState) -> dict:
    if state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "extraction"}
    raw = state.get("raw_input", "")
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )
        text = resp.content[0].text.strip().replace("```json","").replace("```","")
        extraction = json.loads(text[text.find("{"):text.rfind("}")+1])
        return {"extraction": extraction, "current_node": "extraction", "error": None}
    except Exception as e:
        return {"extraction": {}, "current_node": "extraction", "error": f"Extraction failed: {e}"}
