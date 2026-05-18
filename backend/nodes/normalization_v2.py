"""normalization_node.py — Node 3 — Clinical differential with red flag detection"""
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

Your job is NOT to diagnose. Your job is to:
1. Map patient language to medical terms
2. ALWAYS identify the full differential — what else this could be
3. ALWAYS flag red flag symptoms that need urgent evaluation regardless of the most likely cause
4. NEVER anchor on one diagnosis and ignore serious alternatives

CRITICAL SAFETY RULE:
If a patient describes chest pain, chest pressure, or chest tightness — you MUST flag cardiac causes regardless of anxiety history.
If a patient describes sudden severe headache — you MUST flag intracranial causes.
If a patient describes unilateral weakness or speech changes — you MUST flag stroke.
The presence of a common diagnosis (anxiety, diabetes) does NOT rule out a dangerous one.

Return ONLY valid JSON:
{
  "term_mappings": [
    {
      "patient_said": "exact words",
      "doctors_call_it": "clinical term spelled out",
      "simple_meaning": "one plain sentence"
    }
  ],
  "primary_condition": "most likely clinical condition",
  "plain_condition_name": "everyday name",
  "plain_reason": "2 warm sentences why this fits — but acknowledge uncertainty",
  "alternate_conditions": ["at least 3-5 other possibilities, ranked by clinical importance not likelihood"],
  "red_flags": [
    {
      "symptom": "the specific symptom",
      "concern": "what serious condition this could indicate",
      "action": "what the patient should do — seek care now / see doctor soon / monitor"
    }
  ],
  "urgency": "emergency_now or see_doctor_today or see_doctor_soon or monitor",
  "urgency_reason": "plain language explanation of why this urgency level",
  "confidence": "high or medium or low",
  "confidence_note": "honest plain language about what we cannot determine without examination"
}

Red flags that ALWAYS require flagging regardless of context:
- Chest pain, chest pressure, chest tightness → rule out cardiac
- Sudden severe headache → rule out intracranial
- One-sided weakness, facial droop, speech difficulty → rule out stroke
- Shortness of breath at rest → rule out pulmonary embolism, cardiac
- Coughing blood → rule out serious pulmonary
- Unexplained weight loss + fatigue → rule out malignancy
- High fever + stiff neck → rule out meningitis
- Severe abdominal pain → rule out surgical emergency"""


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
            f"Map to clinical terms. Identify ALL red flag symptoms. "
            f"Provide a full differential — do not anchor on one diagnosis. "
            f"If chest pain, cardiac causes MUST appear in the differential and red_flags."
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
        logger.info(f"normalization_node: {norm.get('primary_condition')} | urgency: {norm.get('urgency')} | red_flags: {len(norm.get('red_flags', []))}")
        return {"normalization": norm, "current_node": "normalization", "error": None}

    except Exception as e:
        logger.error(f"normalization_node error: {e}")
        return {"normalization": {}, "current_node": "normalization", "error": None}



