"""extraction_node.py — Node 2"""
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

SYSTEM = """Extract health entities from the patient message. The message may be about the patient OR a family member.

Return ONLY valid JSON:
{
  "symptoms": ["symptoms, conditions, or diagnoses mentioned"],
  "body_parts": ["body areas mentioned"],
  "duration": ["time expressions like 'for 3 days'"],
  "severity": ["severity words like 'severe', 'mild'"],
  "medications": ["medications mentioned"],
  "emotional_context": ["emotions like scared, worried, confused"],
  "context_type": "self or caregiver or inquiry",
  "conditions_mentioned": ["specific medical conditions named"]
}
Use empty lists [] for fields with nothing. Return ONLY the JSON object."""


@traceable(name="extraction_node", tags=["nlp"])
def extraction_node(state: PatientState) -> dict:
    if state.get("guardrail_status") not in ("pass", None):
        return {"current_node": "extraction"}
    raw = state.get("raw_input", "")
    image_data = state.get("image_data")
    if not raw and not image_data:
        return {"extraction": {}, "current_node": "extraction", "error": "No input"}

    updates = {"current_node": "extraction", "error": None}

    # If a photo was attached, actually READ it (vision). Otherwise the image is
    # invisible to extraction, normalization, and the final briefing — which is
    # why "photograph a lab result and understand it" produced nothing.
    image_findings = ""
    if image_data:
        try:
            from ._fast import STRONG_MODEL
            media = state.get("image_media_type") or "image/jpeg"
            vresp = get_client().messages.create(
                model=STRONG_MODEL,  # vision reading of a medical doc — use the strong model
                max_tokens=700,
                system=(
                    "You read a photo of a lab result, prescription, or medical document. "
                    "In plain language, say what the document is and list the key items — "
                    "test names with their values and normal ranges if shown, medication "
                    "names and doses, or the main findings. Do NOT diagnose or give medical "
                    "advice. If the image is not a medical document, say that briefly."
                ),
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media, "data": image_data}},
                    {"type": "text", "text": (raw or "Please read this and list what it shows.")}
                ]}]
            )
            for block in vresp.content:
                if hasattr(block, "text") and block.text:
                    image_findings = block.text.strip()
                    break
        except Exception as e:
            logger.error(f"extraction_node image read error: {e}")

    # What the rest of the pipeline reasons about = user's text + what the photo shows.
    effective_raw = raw
    if image_findings:
        effective_raw = (raw + "\n\nFrom the attached document:\n" + image_findings).strip()
        updates["raw_input"] = effective_raw          # normalization + briefing now see it
        updates["image_analysis"] = {"summary": image_findings}

    logger.info(f"extraction_node: {effective_raw[:60]}")
    try:
        from ._fast import fast_create
        resp = fast_create(
            get_client(),
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": effective_raw}]
        )

        # Safe content extraction - handle tool use blocks
        text = ""
        for block in resp.content:
            if hasattr(block, "text") and block.text:
                text = block.text
                break

        if not text:
            logger.warning("extraction_node: no text block in response")
            return {**updates, "extraction": {}}

        text = text.strip().replace("```json", "").replace("```", "")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            logger.warning(f"extraction_node: no JSON found in: {text[:100]}")
            return {**updates, "extraction": {}}

        extraction = json.loads(text[start:end])

        # Merge conditions into symptoms if symptoms empty
        if not extraction.get("symptoms") and extraction.get("conditions_mentioned"):
            extraction["symptoms"] = extraction["conditions_mentioned"]

        logger.info(f"extraction_node done: {len(extraction.get('symptoms', []))} items")
        return {**updates, "extraction": extraction}

    except Exception as e:
        logger.error(f"extraction_node error: {e}")
        # Return empty extraction instead of crashing - let pipeline continue
        return {**updates, "extraction": {}}



