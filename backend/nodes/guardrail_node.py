"""guardrail_node.py � Node 1"""
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

SYSTEM = """You are a safety classifier for a patient health information tool.
Classify the input into exactly one category:
- pass: health-related question appropriate to answer
- emergency: life-threatening symptoms requiring immediate 911 response
- crisis: mental health crisis or suicidal ideation requiring 988 referral
- off_topic: completely unrelated to health
- invalid: gibberish or too vague
Respond ONLY with valid JSON: {"status": "<category>", "message": "<warm human message if blocked, else empty string>"}"""

@traceable(name="guardrail_node", tags=["safety"])
def guardrail_node(state: PatientState) -> dict:
    raw = state.get("raw_input", "").strip()
    if not raw:
        return {"guardrail_status": "invalid", "guardrail_message": "Please share what's on your mind.", "current_node": "guardrail"}
    # Medication-interaction mode: a bare list of meds/foods is a valid health
    # question here, so tell the classifier not to treat it as "too vague".
    system = SYSTEM
    user_content = raw
    if (state.get("intent") or "").lower() in ("medication", "pharmacist"):
        system = SYSTEM + (
            "\n\nCONTEXT: The user is using a medication-interaction checker. "
            "A list of medications, foods, or drinks (even without a full sentence) "
            "is a valid health question — classify it as 'pass' unless it is an "
            "emergency, crisis, gibberish, or clearly unrelated to health."
        )
        user_content = f"Medication/interaction check: {raw}"
    try:
        resp = get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_content}]
        )
        result = json.loads(resp.content[0].text.strip())
        return {"guardrail_status": result.get("status", "pass"), "guardrail_message": result.get("message", ""), "current_node": "guardrail", "error": None}
    except Exception as e:
        logger.error(f"guardrail_node error: {e}")
        return {"guardrail_status": "pass", "current_node": "guardrail", "error": None}



