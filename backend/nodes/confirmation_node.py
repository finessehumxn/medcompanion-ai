"""confirmation_node.py â€” Node 4 â€” Human-in-the-Loop"""
import logging
from langgraph.types import interrupt
from ..state import PatientState

logger = logging.getLogger(__name__)


def confirmation_node(state: PatientState) -> dict:
    if state.get("error"):
        norm = state.get("normalization", {})
        return {
            "confirmed": False,
            "final_condition": norm.get("primary_condition", ""),
            "current_node": "confirmation",
        }

    # Pull condition from normalization dict
    norm = state.get("normalization", {})
    primary = norm.get("primary_condition", "")
    plain   = norm.get("plain_condition_name", primary)
    reason  = norm.get("plain_reason", "")
    alts    = norm.get("alternate_conditions", [])

    logger.info(f"confirmation_node pausing for: {primary}")

    user_response = interrupt({
        "primary_condition":    primary,
        "plain_condition_name": plain,
        "plain_reason":         reason,
        "alternate_conditions": alts,
        "question": "Does this sound like what you've been experiencing?",
    })

    override = (user_response.get("override") or "").strip()
    confirmed = user_response.get("confirmed", True)
    final_condition = override if override else primary

    logger.info(f"confirmation_node resolved: final='{final_condition}'")

    return {
        "confirmed":       confirmed,
        "final_condition": final_condition,
        "current_node":    "confirmation",
        "error":           None,
    }

