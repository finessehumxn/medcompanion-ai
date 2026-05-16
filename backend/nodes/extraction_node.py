"""
extraction_node.py — Node 2
LangSmith traced NLP entity extraction.
"""
import json
import logging
from langsmith import traceable
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

SYSTEM = """Extract health entities from the patient's message. Return ONLY valid JSON:
{
  "symptoms": ["list of symptoms described"],
  "body_parts": ["body areas mentioned"],
  "duration": ["time expressions"],
  "severity": ["severity descriptors"],
  "medications": ["any medications mentioned"],
  "emotional_context": ["emotional states expressed"],
  "has_image": false
}"""


@traceable(name="extraction_node", tags=["nlp", "pipeline"])
def extraction_node(state: PatientState) -> dict:
    if state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "extraction"}

    raw = state.get("raw_input", "")
    logger.info("extraction_node running")

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )
        text = resp.content[0].text.strip().replace("```json", "").replace("```", "")
        extraction = json.loads(text[text.find("{"):text.rfind("}")+1])
        return {"extraction": extraction, "current_node": "extraction", "error": None}
    except Exception as e:
        logger.error(f"extraction_node error: {e}")
        return {"extraction": {}, "current_node": "extraction", "error": f"Extraction failed: {e}"}
