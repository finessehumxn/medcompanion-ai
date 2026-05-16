"""
normalization_node.py — Node 3
LangSmith traced clinical term mapping.
"""
import json
import logging
from langsmith import traceable
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

SYSTEM = """Map patient language to clinical terminology. Return ONLY valid JSON:
{
  "term_mappings": [
    {
      "patient_said": "their exact words",
      "doctors_call_it": "clinical term (always spell out acronyms first)",
      "simple_meaning": "one plain sentence explanation"
    }
  ],
  "primary_condition": "most likely condition clinical name",
  "plain_condition_name": "everyday plain language name",
  "plain_reason": "1-2 warm sentences explaining why this fits",
  "alternate_conditions": ["other possibilities"],
  "confidence": "high|medium|low"
}"""


@traceable(name="normalization_node", tags=["clinical", "pipeline"])
def normalization_node(state: PatientState) -> dict:
    if state.get("error") or state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "normalization"}

    extraction = state.get("extraction", {})
    raw = state.get("raw_input", "")
    logger.info("normalization_node running")

    try:
        prompt = f"Patient said: {raw}\n\nExtracted: {json.dumps(extraction)}"
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip().replace("```json", "").replace("```", "")
        norm = json.loads(text[text.find("{"):text.rfind("}")+1])
        return {"normalization": norm, "current_node": "normalization", "error": None}
    except Exception as e:
        logger.error(f"normalization_node error: {e}")
        return {"normalization": {}, "current_node": "normalization", "error": f"Normalization failed: {e}"}
