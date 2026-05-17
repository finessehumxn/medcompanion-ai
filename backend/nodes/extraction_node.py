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

SYSTEM = """Extract health entities from the patient message. The message may be about the patient themselves OR about a family member or loved one.

Return ONLY valid JSON with no extra text:
{
  "symptoms": ["list of symptoms, conditions, or diagnoses mentioned"],
  "body_parts": ["body areas mentioned"],
  "duration": ["any time expressions"],
  "severity": ["severity descriptors"],
  "medications": ["any medications mentioned"],
  "emotional_context": ["emotional states like scared, worried, confused, terrified"],
  "context_type": "self or caregiver or inquiry",
  "conditions_mentioned": ["any specific medical conditions or diagnoses named"]
}

If the person is asking about a family member, still extract the conditions and emotional context.
If a field has nothing, use an empty list [].
Return ONLY the JSON object, nothing else."""


@traceable(name="extraction_node", tags=["nlp"])
def extraction_node(state: PatientState) -> dict:
    if state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "extraction"}
    raw = state.get("raw_input", "")
    if not raw:
        return {"extraction": {}, "current_node": "extraction", "error": "No input"}

    logger.info(f"extraction_node: {raw[:60]}")
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": raw}]
        )
        text = resp.content[0].text.strip().replace("```json","").replace("```","")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            raise ValueError(f"No JSON in response: {text[:100]}")
        extraction = json.loads(text[start:end])

        # Merge conditions_mentioned into symptoms if symptoms is empty
        if not extraction.get("symptoms") and extraction.get("conditions_mentioned"):
            extraction["symptoms"] = extraction["conditions_mentioned"]

        logger.info(f"extraction_node done: {len(extraction.get('symptoms',[]))} items")
        return {"extraction": extraction, "current_node": "extraction", "error": None}
    except Exception as e:
        logger.error(f"extraction_node error: {e}")
        return {"extraction": {}, "current_node": "extraction", "error": f"Extraction failed: {e}"}
