"""
guardrail_node.py — Node 1
LangSmith traced safety gate.
"""
import logging
from langsmith import traceable
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

SYSTEM = """You are a safety classifier for a patient health information tool.
Classify the input into one of these categories:
- pass: health-related question appropriate to answer
- emergency: life-threatening symptoms requiring immediate 911 response
- crisis: mental health crisis or suicidal ideation requiring 988 referral
- off_topic: not health-related at all
- invalid: gibberish or too vague to process

Respond ONLY with JSON:
{"status": "<category>", "message": "<warm human message if blocked, else empty string>"}"""


@traceable(name="guardrail_node", tags=["safety", "pipeline"])
def guardrail_node(state: PatientState) -> dict:
    raw = state.get("raw_input", "").strip()
    if not raw:
        return {"guardrail_status": "invalid", "guardrail_message": "Please share what's on your mind.", "current_node": "guardrail"}

    logger.info(f"guardrail_node evaluating input (len={len(raw)})")

    try:
        import json
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )
        result = json.loads(resp.content[0].text.strip())
        return {
            "guardrail_status": result.get("status", "pass"),
            "guardrail_message": result.get("message", ""),
            "current_node": "guardrail",
            "error": None,
        }
    except Exception as e:
        logger.error(f"guardrail_node error: {e}")
        return {"guardrail_status": "pass", "current_node": "guardrail", "error": None}
