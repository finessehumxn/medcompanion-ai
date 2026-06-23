"""briefing_node.py â€” Node 5 â€” Fixed: proper web_search tool handling + fallback"""
import json, re, logging
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
 
 
def clean_for_json(text: str) -> str:
    """Remove characters that break JSON parsing."""
    if not text:
        return ""
    text = text.replace('\u2018', '').replace('\u2019', '').replace('\u201c', '"').replace('\u201d', '"')
    text = re.sub(r"(\w)'(\w)", r"\1\2", text)
    text = text.replace("'", "")
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = re.sub(r' +', ' ', text).strip()
    return text
 
 
def safe_json_loads(text: str) -> dict:
    """Try multiple strategies to parse JSON from LLM output."""
    text = text.replace("```json", "").replace("```", "").strip()
    s = text.find("{")
    e = text.rfind("}")
    if s == -1:
        raise ValueError("No JSON object in response")
 
    json_str = text[s:e+1]
 
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
 
    cleaned = re.sub(r',(\s*[}\]])', r'\1', json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
 
    def fix_string_values(m):
        val = m.group(0)
        val = re.sub(r"(?<=\w)'(?=\w)", '', val)
        val = val.replace("'", "")
        val = val.replace('\n', ' ').replace('\r', ' ')
        return val
 
    cleaned2 = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_values, cleaned, flags=re.DOTALL)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError:
        pass
 
    cleaned3 = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned2)
    cleaned3 = re.sub(r',(\s*[}\]])', r'\1', cleaned3)
    try:
        return json.loads(cleaned3)
    except json.JSONDecodeError:
        pass

    # Final fallback: the purpose-built json-repair library, which fixes the
    # structural errors LLMs produce in long JSON (missing commas/delimiters,
    # unescaped quotes, truncated tails). Run it on the RAW extracted object.
    try:
        from json_repair import repair_json
        repaired = repair_json(json_str, return_objects=True)
        if isinstance(repaired, dict) and repaired:
            logger.info("Recovered briefing JSON via json_repair fallback")
            return repaired
    except Exception as e:
        logger.warning(f"json_repair fallback failed: {e}")

    raise ValueError("All JSON repair strategies failed.")
 
 
def extract_text_from_response(response) -> str:
    """
    Extract all text from an Anthropic response, including after tool_use blocks.
    When web_search is used, the response contains:
      [tool_use block] -> [tool_result block] -> [text block with final answer]
    We need to collect ALL text blocks, not just the first one.
    """
    texts = ""
    for block in response.content:
        # Standard text block
        if hasattr(block, "text") and block.text:
            texts += block.text
        # Some SDK versions wrap text differently
        elif hasattr(block, "type") and block.type == "text" and hasattr(block, "text"):
            texts += block.text
 
    logger.info(f"Extracted {len(texts)} chars from {len(response.content)} content blocks "
                f"(types: {[getattr(b, 'type', '?') for b in response.content]})")
    return texts
 
 
BRIEFING_TOOL = {
    "name": "emit_briefing",
    "description": "Return the complete patient briefing as structured data. After researching, you MUST call this exactly once with every field filled in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "condition_name": {"type": "string"},
            "plain_name": {"type": "string"},
            "opening": {"type": "string"},
            "standard_of_care": {
                "type": "object",
                "properties": {
                    "plain_summary": {"type": "string"},
                    "treatments": {"type": "array", "items": {"type": "object", "properties": {
                        "name": {"type": "string"}, "phase": {"type": "string"},
                        "plain_description": {"type": "string"}, "what_this_means_for_you": {"type": "string"}}}},
                },
            },
            "emerging": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "phase": {"type": "string"}, "plain_description": {"type": "string"}}}},
            "holistic": {
                "type": "object",
                "properties": {
                    "intro": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "object", "properties": {
                        "name": {"type": "string"}, "type": {"type": "string"},
                        "plain_description": {"type": "string"}, "note": {"type": "string"}}}},
                    "reminder": {"type": "string"},
                },
            },
            "companies": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "type": {"type": "string"}, "focus": {"type": "string"}}}},
            "sources": {"type": "array", "items": {"type": "object", "properties": {
                "title": {"type": "string"}, "url": {"type": "string"}}}},
            "doctor_questions": {"type": "array", "items": {"type": "string"}},
            "closing": {"type": "string"},
        },
        "required": ["condition_name", "plain_name", "opening", "standard_of_care", "doctor_questions", "closing"],
    },
}


def call_claude_with_search(condition: str, user_prompt: str):
    """Call Claude with web search + the emit_briefing tool. Returns the raw response."""
    response = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}, BRIEFING_TOOL],
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response
 
 
def call_claude_without_search(condition: str, user_prompt: str) -> str:
    """Fallback: Call Claude without web search (uses training knowledge)."""
    logger.info("Falling back to no-search briefing generation")
    response = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[BRIEFING_TOOL],
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response
 
 
SYSTEM_PROMPT = """You are a medical information specialist generating patient-friendly health briefings.

CARE-PARTNERSHIP PRINCIPLES (apply to every field):
- Your job is to help the reader PREPARE for and PARTNER WITH their own doctor — never to replace, second-guess, or override their clinician.
- Frame guidance as understanding and as questions to bring to their care team, NOT as instructions or a diagnosis. Prefer "a question to ask your doctor is..." over "you should...".
- Never tell the reader their doctor is wrong or that they should argue, demand a specific treatment, or change/stop medication on their own. Their care team knows their full history.
- The opening and closing should reinforce that this is meant to support the conversation with their doctor, and that their doctor has the final say.
- Be warm, human, and relatable — like a knowledgeable friend who helps them feel calm and prepared, not a clinical printout.

CRITICAL: Return a single valid JSON object. Follow these rules exactly:
- NO apostrophes anywhere. Write "does not" not "doesn't". Write "it is" not "it's".
- NO line breaks inside string values. Each value must be on one continuous line.
- NO citation markers like [1] or [2].
- NO markdown inside values.
- Use double quotes for all strings.
- Include at least 2 items in every array.
- doctor_questions: include 3 to 5 specific, genuinely useful questions the reader should ask their own doctor about this. This is the most important field for helping them prepare for their visit.
 
Return this exact structure:
{
  "condition_name": "clinical name here",
  "plain_name": "everyday name here",
  "opening": "warm 2-3 sentence opening without apostrophes",
  "standard_of_care": {
    "plain_summary": "how doctors treat this without apostrophes",
    "treatments": [
      {"name": "name", "phase": "First-line", "plain_description": "description without apostrophes", "what_this_means_for_you": "one sentence without apostrophes"}
    ]
  },
  "emerging": [
    {"name": "name", "phase": "phase", "plain_description": "description without apostrophes"}
  ],
  "holistic": {
    "intro": "intro without apostrophes",
    "options": [
      {"name": "name", "type": "type", "plain_description": "description without apostrophes", "note": "note without apostrophes"}
    ],
    "reminder": "reminder without apostrophes"
  },
  "companies": [
    {"name": "org name", "type": "type", "focus": "focus without apostrophes"}
  ],
  "sources": [
    {"title": "title", "url": "https://url.org"}
  ],
  "doctor_questions": ["a specific useful question to ask your doctor without apostrophes", "another question to ask your doctor without apostrophes"],
  "closing": "warm closing without apostrophes"
}"""


def audience_directive(viewer_type: str, intent: str) -> str:
    """Tailor tone + focus of the briefing to who is asking and why.
    The JSON structure stays identical so the frontend renders consistently —
    only voice, depth, and emphasis change."""
    viewer_type = (viewer_type or "everyday").lower()
    intent = (intent or "").lower()

    if intent == "caregiver":
        return (
            "AUDIENCE: A caregiver looking after another person (a parent, partner, child, or friend). Speak to THEM as "
            "the caregiver: explain the condition, what to watch for, how to help day to day, how to coordinate care and "
            "talk with the care team, and a gentle reminder to care for themselves too.\n"
        )
    if intent == "pediatric":
        return (
            "AUDIENCE: A parent or guardian asking about a child. Use warm, reassuring, plain language. Note where children "
            "differ from adults, what is normal versus when to call the pediatrician or seek urgent care, and good questions "
            "to ask the child's doctor. Never replace pediatric medical care.\n"
        )
    if intent == "athlete":
        return (
            "AUDIENCE: An athlete or active person focused on training, injury, recovery, and performance. Explain what is "
            "happening, general recovery and return-to-activity considerations, when to rest versus seek care, and questions "
            "for a sports-medicine clinician. Avoid prescriptive training or medical instructions.\n"
        )
    if intent == "veteran":
        return (
            "AUDIENCE: A military veteran. Be respectful and practical. Where relevant, mention VA care navigation and that "
            "some conditions may relate to service. Keep it plain and supportive, and point toward their VA or civilian "
            "care team and resources available to veterans.\n"
        )
    if intent == "pregnancy":
        return (
            "AUDIENCE: Someone who is pregnant, trying to conceive, or postpartum. Use warm, careful, plain language. "
            "Emphasize what is common versus warning signs that need prompt care (for example heavy bleeding, severe "
            "headache, reduced fetal movement), caution about medication safety in pregnancy, and questions for their OB or "
            "midwife. Never replace prenatal care.\n"
        )
    if intent == "device":
        return (
            "AUDIENCE: A person who has a medical device or implant — for example a pacemaker, defibrillator (ICD), "
            "insulin pump, continuous glucose monitor, neurostimulator, cochlear or other implant, prosthetic, or "
            "wearable medical technology. Explain their device in plain language: what it does, what is normal versus "
            "concerning, practical daily-living tips, and important safety notes where relevant (for example MRI safety, "
            "electromagnetic interference, airport/security screening). Tell them the signs that mean they should seek "
            "help, and what to ask their device clinic or the manufacturer. Do NOT give device-specific programming or "
            "settings instructions — that belongs to their device team. Frame everything as understanding plus questions "
            "for their care team.\n"
        )
    if intent == "integrative":
        return (
            "AUDIENCE: A holistic, integrative, naturopathic, functional, or traditional/Eastern-medicine practitioner "
            "(for example Traditional Chinese Medicine, acupuncture, Ayurveda, naturopathy). Present a balanced, respectful, "
            "professional briefing that covers BOTH the conventional (Western) standard of care AND evidence-informed "
            "complementary or traditional approaches. Clearly note the strength of evidence for each, and flag any safety or "
            "interaction concerns (for example herb-drug interactions). Use appropriate professional terminology. Never "
            "disparage either tradition; support integrative decision-making alongside the patient's full care team.\n"
        )
    if intent == "pharmacist":
        return (
            "AUDIENCE: A pharmacist or pharmacy professional.\n"
            "Write a drug-focused clinical reference (Lexicomp / FDA-label style):\n"
            "- Lead with drug class, key indications, and usual dosing considerations.\n"
            "- Emphasize interactions (drug-drug, drug-food), major contraindications, and monitoring parameters.\n"
            "- Include concise PATIENT COUNSELING POINTS the pharmacist can relay.\n"
            "- Use precise terminology; cite FDA labels, package inserts, and reputable drug references with URLs.\n"
            "POSITIONING: This supports the pharmacist's professional judgment and the patient's own prescriber; "
            "it does not direct therapy or replace the label.\n"
        )
    if intent == "medication":
        return (
            "AUDIENCE: Someone checking medication safety and interactions.\n"
            "FOCUS THE BRIEFING ON INTERACTIONS, not on treating a disease:\n"
            "- opening: summarize the most important interaction warnings up front.\n"
            "- standard_of_care.treatments: list specific interactions to watch. For each, "
            "name = the interaction (e.g. drug with grapefruit), phase = severity "
            "(Avoid / Caution / Usually safe), plain_description = what happens and why, "
            "what_this_means_for_you = the concrete action to take.\n"
            "- holistic: foods, drinks, and timing tips (what to separate, what to take with food).\n"
            "- Always remind the reader to confirm with a pharmacist or prescriber before changing anything.\n"
        )
    if viewer_type == "professional":
        return (
            "AUDIENCE: A medical professional (clinician, nurse, or healthcare staff).\n"
            "Write a clinical, evidence-forward reference in the spirit of OpenEvidence or UpToDate:\n"
            "- Use precise clinical terminology; do not oversimplify.\n"
            "- Indicate level/strength of evidence and guideline bodies where relevant "
            "(e.g. first-line per ADA/NICE), within the plain_description fields.\n"
            "- Prioritize current standard of care, then emerging/trial-stage options.\n"
            "- sources: cite authoritative references (PubMed, NIH, FDA labels, specialty guidelines). Include real URLs.\n"
            "POSITIONING: This is a point-of-care reference that SUPPORTS the clinician's "
            "judgment — it does not direct patient care or replace clinical decision-making. "
            "Frame it as a tool the professional uses WITH their patient, never one that "
            "overrides the professional. Do not make individualized treatment decisions.\n"
        )
    if intent == "loved_one":
        return (
            "AUDIENCE: Someone trying to understand and support a loved one.\n"
            "Write warmly and in plain language. Frame guidance around how to help, what to "
            "expect, and what questions to ask the care team. Avoid alarming language.\n"
        )
    return (
        "AUDIENCE: An everyday person trying to understand their own health.\n"
        "Write warmly and in plain language, like a knowledgeable friend. Explain every term. "
        "Help them feel prepared and less alone, and ready to talk with their doctor.\n"
    )


def briefing_from_response(response):
    """Prefer the schema-validated emit_briefing tool input (valid structure
    guaranteed by the API); fall back to parsing any text the model wrote."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "emit_briefing":
            if isinstance(block.input, dict) and block.input:
                logger.info("Briefing via validated emit_briefing tool call")
                return block.input
    text = extract_text_from_response(response)
    text = re.sub(r'<cite[^>]*>.*?</cite>', '', text, flags=re.DOTALL)
    text = re.sub(r'</?cite[^>]*>', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    if len(text.strip()) >= 50:
        logger.info("emit_briefing tool not called; parsing text fallback")
        return safe_json_loads(text)
    return None


@traceable(name="briefing_node", tags=["briefing", "pipeline"])
def briefing_node(state: PatientState) -> dict:
    if state.get("error"):
        return {"current_node": "briefing"}
 
    condition = (state.get("final_condition") or "").strip()
    if not condition:
        norm = state.get("normalization", {})
        condition = (norm.get("primary_condition") or norm.get("plain_condition_name") or "").strip()
    if not condition:
        condition = state.get("raw_input", "").strip()[:150]
 
    if not condition:
        return {"briefing": None, "current_node": "briefing",
                "error": "No condition name available."}
 
    directive = audience_directive(state.get("viewer_type"), state.get("intent"))
    logger.info(f"briefing_node: generating briefing for '{condition}' "
                f"(viewer={state.get('viewer_type')}, intent={state.get('intent')})")

    user_prompt = (
        f"Generate a complete patient briefing for: {condition}\n\n"
        f"{directive}\n"
        f"Search for current information. Use NIH, Mayo Clinic, FDA, PubMed, OpenEvidence.\n"
        f"If multiple conditions mentioned, cover their relationship.\n\n"
        f"CRITICAL RULES:\n"
        f"1. NO apostrophes in any text. Use full words only.\n"
        f"2. NO line breaks inside string values.\n"
        f"3. NO citation markers.\n"
        f"4. At least 2 items in every array.\n"
        f"5. Return ONLY the JSON object, nothing before or after it."
    )
 
    briefing = None

    # Attempt 1: research with web search, emit via the schema-locked tool
    try:
        resp = call_claude_with_search(condition, user_prompt)
        briefing = briefing_from_response(resp)
    except Exception as e:
        logger.warning(f"Web search briefing call failed: {e}. Trying without search.")

    # Attempt 2: fallback without web search
    if not briefing:
        try:
            resp = call_claude_without_search(condition, user_prompt)
            briefing = briefing_from_response(resp)
        except Exception as e:
            logger.error(f"Fallback briefing call also failed: {e}")
            return {"briefing": None, "current_node": "briefing",
                    "error": f"Briefing generation failed: {e}"}

    if briefing:
        logger.info(f"briefing_node complete for '{condition}'")
        return {"briefing": briefing, "current_node": "briefing", "error": None}

    logger.error(f"Briefing could not be produced for '{condition}'")
    return {"briefing": None, "current_node": "briefing",
            "error": "Briefing parse failed"}
