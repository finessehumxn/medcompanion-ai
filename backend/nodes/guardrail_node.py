"""guardrail_node.py — Node 1"""
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
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )
        result = json.loads(resp.content[0].text.strip())
        return {"guardrail_status": result.get("status", "pass"), "guardrail_message": result.get("message", ""), "current_node": "guardrail", "error": None}
    except Exception as e:
        logger.error(f"guardrail_node error: {e}")
        return {"guardrail_status": "pass", "current_node": "guardrail", "error": None}
