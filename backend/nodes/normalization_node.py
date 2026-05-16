"""normalization_node.py — Node 3"""
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

SYSTEM = """Map patient language to clinical terminology. Return ONLY valid JSON:
{"term_mappings": [{"patient_said": "", "doctors_call_it": "", "simple_meaning": ""}], "primary_condition": "", "plain_condition_name": "", "plain_reason": "", "alternate_conditions": [], "confidence": "high"}"""

@traceable(name="normalization_node", tags=["clinical"])
def normalization_node(state: PatientState) -> dict:
    if state.get("error") or state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "normalization"}
    raw = state.get("raw_input", "")
    extraction = state.get("extraction", {})
    try:
        prompt = f"Patient said: {raw}\n\nExtracted: {json.dumps(extraction)}"
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip().replace("```json","").replace("```","")
        norm = json.loads(text[text.find("{"):text.rfind("}")+1])
        return {"normalization": norm, "current_node": "normalization", "error": None}
    except Exception as e:
        return {"normalization": {}, "current_node": "normalization", "error": f"Normalization failed: {e}"}
