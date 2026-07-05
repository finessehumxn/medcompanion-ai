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
    has_image = bool(state.get("image_data"))
    # An attached photo (lab result / document) IS the content — so empty or thin
    # text is fine when an image is present. Only reject truly-empty requests.
    if not raw and not has_image:
        return {"guardrail_status": "invalid", "guardrail_message": "Please share what's on your mind.", "current_node": "guardrail"}
    # Medication-interaction mode: a bare list of meds/foods is a valid health
    # question here, so tell the classifier not to treat it as "too vague".
    system = SYSTEM
    user_content = raw or "Please explain the attached image."
    if (state.get("intent") or "").lower() in ("medication", "pharmacist"):
        system = SYSTEM + (
            "\n\nCONTEXT: The user is using a medication-interaction checker. "
            "A list of medications, foods, or drinks (even without a full sentence) "
            "is a valid health question — classify it as 'pass' unless it is an "
            "emergency, crisis, gibberish, or clearly unrelated to health."
        )
        user_content = f"Medication/interaction check: {raw}"
    if has_image:
        system = system + (
            "\n\nCONTEXT: The user has ATTACHED AN IMAGE (a photo of a lab result, "
            "prescription, or medical document) along with their text. The image IS "
            "the content to explain, so brief or vague text such as 'explain this' or "
            "'what does this mean' is a valid 'pass' — do NOT classify it as invalid "
            "or off_topic just because the text is short. Only use emergency or crisis "
            "for a genuine safety issue in the text."
        )
    try:
        resp = get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_content}]
        )
        result = json.loads(resp.content[0].text.strip())
        status = result.get("status", "pass")
        # Safety net: never let an attached image get bounced as vague/unrelated.
        # Emergency/crisis still take priority (real safety), but invalid/off_topic
        # on an image-bearing request becomes a pass so the photo gets analyzed.
        if has_image and status in ("invalid", "off_topic"):
            status = "pass"
        message = "" if status == "pass" else result.get("message", "")
        return {"guardrail_status": status, "guardrail_message": message, "current_node": "guardrail", "error": None}
    except Exception as e:
        logger.error(f"guardrail_node error: {e}")
        return {"guardrail_status": "pass", "current_node": "guardrail", "error": None}



