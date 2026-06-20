"""
vision_node.py — Optional Node
LangSmith traced image analysis for lab results, prescriptions, rashes.
Activated when the user uploads an image alongside their text input.
"""
import json
import base64
import logging
from langsmith import traceable
import anthropic
from ..state import PatientState

logger = logging.getLogger(__name__)
client = None

def get_client():
    global client
    if client is None:
        client = anthropic.Anthropic()
    return client

SYSTEM = """You are analyzing a medical image uploaded by a patient.
The image could be: lab results, a prescription, a skin condition, a medication bottle, or other health-related content.

Respond ONLY with valid JSON:
{
  "image_type": "lab_results|prescription|skin_condition|medication|xray|other",
  "findings": "plain language description of what you see — written warmly for a non-medical person",
  "key_values": [
    {"name": "item name", "value": "value shown", "flag": "normal|low|high|unknown"}
  ],
  "plain_summary": "2-3 sentences summarizing what this shows in everyday language",
  "important_notes": "anything the patient should pay attention to or ask their doctor about",
  "disclaimer": "This is a general reading of the image only. Your doctor interprets results in the context of your full health history."
}

If the image is not health-related, return: {"image_type": "not_medical", "findings": "This does not appear to be a medical image.", "key_values": [], "plain_summary": "", "important_notes": "", "disclaimer": ""}"""


@traceable(name="vision_node", tags=["vision", "multimodal", "pipeline"])
def vision_node(state: PatientState) -> dict:
    """Process an uploaded medical image using Claude Vision."""
    image_data = state.get("image_data")
    image_media_type = state.get("image_media_type", "image/jpeg")

    if not image_data:
        return {"image_analysis": None, "current_node": "vision"}

    logger.info(f"vision_node analyzing {image_media_type} image")

    try:
        resp = get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Please analyze this medical image. The patient also said: {state.get('raw_input', 'No additional context provided.')}"
                    }
                ]
            }]
        )
        text = resp.content[0].text.strip().replace("```json", "").replace("```", "")
        analysis = json.loads(text[text.find("{"):text.rfind("}")+1])
        logger.info(f"vision_node completed: type={analysis.get('image_type')}")
        return {"image_analysis": analysis, "current_node": "vision", "error": None}
    except Exception as e:
        logger.error(f"vision_node error: {e}")
        return {"image_analysis": None, "current_node": "vision", "error": f"Image analysis failed: {e}"}



