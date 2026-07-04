"""server.py â€” MedCompanion AI v2"""
import os, logging, uuid
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "medcompanion-ai")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from .graph import build_graph

try:
    from .supabase_client import (get_supabase, save_session, get_user_history, log_symptom,
                                  get_symptom_history, request_review, get_review,
                                  get_pending_reviews, sign_review, export_user_data, delete_user_data, clear_user_data)
    SUPABASE_ENABLED = True
except ImportError:
    SUPABASE_ENABLED = False
    async def save_session(*a, **k): return None
    async def get_user_history(u, limit=20): return []
    async def log_symptom(*a, **k): return False
    async def get_symptom_history(u, limit=50): return []
    async def request_review(*a, **k): return None
    async def get_review(*a, **k): return None
    async def get_pending_reviews(*a, **k): return []
    async def sign_review(*a, **k): return False
    async def export_user_data(*a, **k): return {}
    async def delete_user_data(*a, **k): return False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MedCompanion AI", version="2.0.0")

# CORS — required so the bundled mobile app (origin https://localhost / capacitor://localhost)
# can call this API cross-origin. No cookies are used (user_id is sent in the request body),
# so credentials are disabled and wildcard origins are safe.
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = MemorySaver()
graph = build_graph()

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url='/app')

@app.get("/app")
async def serve_app():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/privacy")
async def serve_privacy():
    return FileResponse(os.path.join(frontend_dir, "privacy.html"))

@app.get("/doctor")
async def serve_doctor():
    return FileResponse(os.path.join(frontend_dir, "doctor.html"))

@app.get("/about")
async def serve_about():
    return FileResponse(os.path.join(frontend_dir, "about.html"))

@app.get("/about-us")
async def serve_about_us():
    return FileResponse(os.path.join(frontend_dir, "about-us.html"))

@app.get("/partners")
async def serve_partners():
    return FileResponse(os.path.join(frontend_dir, "partners.html"))

@app.get("/investors")
async def serve_investors():
    return FileResponse(os.path.join(frontend_dir, "investors.html"))

# ── PWA: serve manifest, service worker, and icons from root so install works ──
@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(os.path.join(frontend_dir, "manifest.json"), media_type="application/manifest+json")

@app.get("/sw.js")
async def serve_sw():
    # Served from root so its scope can control /app
    return FileResponse(os.path.join(frontend_dir, "sw.js"), media_type="application/javascript")

@app.get("/icon-192.png")
async def serve_icon_192():
    return FileResponse(os.path.join(frontend_dir, "icon-192.png"), media_type="image/png")

@app.get("/icon-512.png")
async def serve_icon_512():
    return FileResponse(os.path.join(frontend_dir, "icon-512.png"), media_type="image/png")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")), "supabase": SUPABASE_ENABLED}

class StartRequest(BaseModel):
    raw_input: str
    image_data: Optional[str] = None
    image_media_type: Optional[str] = None
    user_id: Optional[str] = None
    viewer_type: Optional[str] = "everyday"   # "everyday" | "professional"
    intent: Optional[str] = None              # "self" | "loved_one" | "medication"

class ConfirmRequest(BaseModel):
    confirmed: bool
    override: Optional[str] = None
    user_id: Optional[str] = None

class SymptomLogRequest(BaseModel):
    user_id: str
    symptom: str
    severity: int
    notes: Optional[str] = ""

class AuthRequest(BaseModel):
    email: str
    password: str

class TranslateRequest(BaseModel):
    text: str
    target: str

@app.post("/translate")
async def translate(req: TranslateRequest):
    """Multilingual care bridge: translate a briefing summary into the patient's
    language. The doctor still gets the Visit Sheet in English. Fails soft."""
    text = (req.text or "").strip()
    target = (req.target or "").strip()
    if not text or not target:
        return {"translated": text}
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=("You are a medical translator. Translate the user's text into the target "
                    "language naturally and clearly, preserving meaning and a warm, plain-language "
                    "tone a patient can understand. Return ONLY the translation, no preamble."),
            messages=[{"role": "user", "content": f"Target language code: {target}\n\nText:\n{text}"}],
        )
        out = "".join(getattr(b, "text", "") for b in resp.content)
        return {"translated": out.strip() or text}
    except Exception as e:
        logger.error(f"translate error: {e}")
        return {"translated": text}

class SpeakRequest(BaseModel):
    text: str
    lang: Optional[str] = None

@app.post("/speak")
async def speak(req: SpeakRequest):
    """Read aloud in OUR cloned voice (ElevenLabs) instead of the robotic
    device voice. Returns MP3 the app plays. If unconfigured or it fails,
    the client falls back to the device voice — so it never breaks."""
    import httpx
    from fastapi.responses import Response
    key = os.getenv("ELEVENLABS_API_KEY")
    voice = os.getenv("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise HTTPException(503, "Voice not configured")
    text = (req.text or "").strip()[:2500]
    if not text:
        raise HTTPException(400, "No text to read")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={"xi-api-key": key, "accept": "audio/mpeg", "content-type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.3, "use_speaker_boost": True},
                },
            )
    except Exception as e:
        logger.error(f"speak error: {e}")
        raise HTTPException(502, "Voice service unavailable")
    if r.status_code != 200:
        logger.error(f"elevenlabs {r.status_code}: {r.text[:200]}")
        raise HTTPException(502, "Voice generation failed")
    return Response(content=r.content, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})

class VisitPrepRequest(BaseModel):
    user_id: str
    lang: Optional[str] = None

@app.post("/visit-prep")
async def visit_prep(req: VisitPrepRequest):
    """Turns a patient's logged symptom history into TWO summaries:
    a plain-language one for them, and a concise clinical handoff for their
    clinician — so the visit is efficient without a hundred probing questions."""
    logs = await get_symptom_history(req.user_id, limit=60)
    if not logs:
        return {"empty": True, "patient_summary": "", "clinical_summary": ""}
    # Build a chronological log text (oldest first reads like a story)
    entries = []
    for e in reversed(logs):
        when = (e.get("logged_at") or "")[:10]
        sev = e.get("severity")
        entries.append(f"[{when}] {e.get('symptom','')}"
                       + (f" (severity {sev}/10)" if sev else "")
                       + (f" — {e.get('notes','')}" if e.get('notes') else ""))
    log_text = "\n".join(entries)
    lang = (req.lang or "").strip()
    lang_line = f"Write patient_summary in this language (BCP-47 code): {lang}. Keep clinical_summary in English." if lang else ""
    system = (
        "You help a patient prepare for a doctor visit using the symptom history they logged over time. "
        "You do NOT diagnose. You organize what they recorded so the visit is efficient. " + lang_line + "\n\n"
        "Return ONLY valid JSON, no apostrophes in string values:\n"
        "{\n"
        '  "patient_summary": "warm plain-language recap of their story they can read or hand over (onset, how it changed, how it affects them)",\n'
        '  "clinical_summary": "a concise clinical handoff for the clinician in HPI style: onset/duration, course/timeline, severity, associated factors, what makes it better or worse, relevant logged details. Tight and professional.",\n'
        '  "key_questions": ["a focused question the clinician may want to explore", "another"],\n'
        '  "timeline": ["short dated milestone", "another"]\n'
        "}"
    )
    try:
        import anthropic, json as _json
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1400, system=system,
            messages=[{"role": "user", "content": f"Logged history (oldest first):\n{log_text}"}],
        )
        raw = "".join(getattr(b, "text", "") for b in resp.content).replace("```json", "").replace("```", "").strip()
        s, e = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[s:e+1]) if s != -1 else {}
        return {
            "empty": False,
            "patient_summary": data.get("patient_summary", ""),
            "clinical_summary": data.get("clinical_summary", ""),
            "key_questions": data.get("key_questions", []) or [],
            "timeline": data.get("timeline", []) or [],
            "entries": len(logs),
        }
    except Exception as ex:
        logger.error(f"visit_prep error: {ex}")
        return {"empty": False, "patient_summary": log_text, "clinical_summary": log_text, "key_questions": [], "timeline": []}

class BillRequest(BaseModel):
    text: Optional[str] = ""
    image_data: Optional[str] = None
    image_media_type: Optional[str] = "image/jpeg"
    goal: Optional[str] = "explain"   # explain | dispute | appeal | financial_assistance | itemized | payment_plan
    lang: Optional[str] = None

@app.post("/billhelp")
async def billhelp(req: BillRequest):
    """First-of-its-kind: decode a confusing medical bill / EOB / insurance denial,
    flag likely errors and overcharges, and draft a letter to send. General guidance,
    not legal or financial advice. Never invents codes/amounts the user did not give."""
    text = (req.text or "").strip()
    if not text and not req.image_data:
        return {"summary": "", "flags": [], "actions": [], "letter": ""}
    lang = (req.lang or "").strip()
    lang_line = f"Write all output in this language (BCP-47 code): {lang}." if lang else ""
    goal = (req.goal or "explain").lower()
    goal_map = {
        "explain": "Focus on explaining it clearly; still flag anything worth questioning.",
        "dispute": "The user wants to dispute likely errors/overcharges. Draft a firm but polite dispute letter.",
        "appeal": "The user wants to appeal an insurance denial. Draft an appeal letter requesting reconsideration and the specific reason for denial.",
        "financial_assistance": "The user needs help paying. Draft a letter requesting financial assistance / charity care and a hardship discount.",
        "itemized": "Draft a letter requesting a fully itemized bill with billing (CPT/HCPCS) codes.",
        "payment_plan": "Draft a letter requesting an interest-free payment plan and a prompt-pay or self-pay discount.",
    }
    system = (
        "You are a calm, savvy medical-billing and insurance advocate helping an ordinary person understand "
        "a confusing medical bill, Explanation of Benefits (EOB), or insurance denial, and fight back when "
        "something looks wrong. Explain in plain language. Flag the things most worth questioning: duplicate "
        "charges, services not received, upcoding, unbundling, out-of-network surprise or balance billing, "
        "missing itemization, charges that should be covered, and amounts above typical. "
        "Then draft a polite, effective letter the user can edit and send. "
        + goal_map.get(goal, goal_map["explain"]) + " " + lang_line + "\n\n"
        "IMPORTANT: You are NOT a lawyer or the insurer; this is general guidance, not legal or financial advice. "
        "NEVER invent specific billing codes, dates, or dollar amounts the user did not provide — if itemization "
        "is missing, the first action is to request an itemized bill. Be encouraging; people can often lower these bills.\n\n"
        "Return ONLY valid JSON, no apostrophes inside string values:\n"
        "{\n"
        '  "summary": "plain-language explanation of what this bill or denial actually is",\n'
        '  "flags": ["a specific thing worth questioning", "another"],\n'
        '  "actions": ["a concrete next step the person can take", "another"],\n'
        '  "letter": "a complete, ready-to-edit letter with [BRACKETED] placeholders for details to fill in"\n'
        "}"
    )
    content = []
    if req.image_data:
        content.append({"type": "image", "source": {"type": "base64", "media_type": req.image_media_type or "image/jpeg", "data": req.image_data}})
    content.append({"type": "text", "text": text or "Please review this medical bill or insurance document."})
    try:
        import anthropic, json as _json
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=2500, system=system,
            messages=[{"role": "user", "content": content}],
        )
        raw = "".join(getattr(b, "text", "") for b in resp.content).replace("```json", "").replace("```", "").strip()
        s, e = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[s:e+1]) if s != -1 else {}
        return {"summary": data.get("summary", ""), "flags": data.get("flags", []) or [],
                "actions": data.get("actions", []) or [], "letter": data.get("letter", "")}
    except Exception as ex:
        logger.error(f"billhelp error: {ex}")
        return {"summary": "I could not read that fully just now. A safe first step is to call the billing office and request a fully itemized bill with codes — then we can review it together.",
                "flags": [], "actions": ["Request a fully itemized bill with billing codes", "Do not pay until you have reviewed the itemized bill"], "letter": ""}

class AdvocateRequest(BaseModel):
    task: str = "bill_explain"
    text: Optional[str] = ""
    image_data: Optional[str] = None
    image_media_type: Optional[str] = "image/jpeg"
    finance: Optional[str] = ""      # e.g. "No insurance", "Medicaid", "Aetna PPO, high deductible"
    lang: Optional[str] = None

ADVOCATE_TASKS = {
    "bill_explain": "Explain this medical bill or EOB in plain language; flag anything worth questioning (duplicate charges, services not received, upcoding, surprise out-of-network, missing itemization).",
    "bill_dispute": "Draft a firm but polite letter disputing likely errors or overcharges on this bill.",
    "appeal": "Draft an insurance-denial appeal letter requesting reconsideration and the specific reason for denial, citing the patient's right to appeal.",
    "financial_assistance": "Draft a letter requesting financial assistance / charity care and a hardship discount.",
    "itemized": "Draft a letter requesting a fully itemized bill with billing (CPT/HCPCS) codes.",
    "payment_plan": "Draft a letter requesting an interest-free payment plan and a prompt-pay or self-pay discount.",
    "records": "The user wants their medical records. Explain their right to access them (in the US, the HIPAA Right of Access — providers generally must respond within 30 days). Draft a clear records-request letter with [BRACKETED] placeholders for dates of service, the records wanted, and delivery method.",
    "consent": "The user is being asked to sign a form or consent. Explain in plain language what it appears to say and what they would be agreeing to, and flag anything to ASK ABOUT or be cautious of before signing. Do not tell them whether to sign — help them ask good questions.",
    "coverage": "Explain the user's insurance coverage in plain language from what they share (plan summary, card, EOB, or description): what deductible, copay, coinsurance, out-of-pocket max, and in- vs out-of-network mean FOR THEM, what is likely covered, and how to verify. Provide a short call script to confirm coverage as the letter.",
    "alternatives": "The user cannot get a timely appointment (often booked out months) or needs care sooner. Suggest legitimate interim options matched to their urgency and finances: telehealth, urgent care, retail/pharmacy clinics, community health centers (FQHCs) and sliding-scale clinics, nurse advice lines, asking to be added to a cancellation list, and when the ER is appropriate. If anything sounds like an emergency, tell them to call their local emergency number now. The letter field can be a short script to ask for an earlier appointment or a cancellation slot.",
}

@app.post("/advocate")
async def advocate(req: AdvocateRequest):
    """The Healthcare Advocate: understand a document, flag problems, and draft the
    letter/script — for bills, denials, records, consent forms, coverage, and finding
    care when appointments are booked out. General guidance, not legal/financial advice."""
    text = (req.text or "").strip()
    if not text and not req.image_data:
        return {"summary": "", "flags": [], "actions": [], "letter": ""}
    task = (req.task or "bill_explain").lower()
    instr = ADVOCATE_TASKS.get(task, ADVOCATE_TASKS["bill_explain"])
    lang = (req.lang or "").strip()
    lang_line = f"Write all output in this language (BCP-47 code): {lang}." if lang else ""
    fin = (req.finance or "").strip()
    fin_line = (f"\nThe user's insurance/financial situation: {fin}. Tailor cost and access advice to this — "
                "for example uninsured: community health centers (FQHCs), sliding-scale clinics, cash-pay/prompt-pay "
                "discounts, hospital charity care, and patient-assistance programs; Medicaid/Medicare: covered options "
                "and the right network; private insurance: in-network options, prior-auth, and appeals.") if fin else ""
    system = (
        "You are a calm, savvy patient advocate who helps ordinary people handle the parts of healthcare that are "
        "confusing or unfair — bills, denials, records, consent forms, coverage, and getting care in time. "
        "Explain in plain language, flag what is worth questioning, give concrete next steps, and draft a polite, "
        "effective letter or script the person can edit and use. " + instr + " " + lang_line + fin_line + "\n\n"
        "IMPORTANT: You are NOT a lawyer, doctor, or insurer; this is general guidance, not legal, medical, or financial "
        "advice. NEVER invent specific codes, dates, dollar amounts, or policy numbers the user did not provide. "
        "If anything sounds like an emergency, tell them to call their local emergency number. Be encouraging.\n\n"
        "Return ONLY valid JSON, no apostrophes inside string values:\n"
        "{\n"
        '  "summary": "plain-language explanation of the situation",\n'
        '  "flags": ["something worth questioning or watching for", "another"],\n'
        '  "actions": ["a concrete next step", "another"],\n'
        '  "letter": "a complete, ready-to-edit letter or call script with [BRACKETED] placeholders (empty string if not applicable)"\n'
        "}"
    )
    content = []
    if req.image_data:
        content.append({"type": "image", "source": {"type": "base64", "media_type": req.image_media_type or "image/jpeg", "data": req.image_data}})
    content.append({"type": "text", "text": text or "Please help me with this healthcare document or situation."})
    try:
        import anthropic, json as _json
        client = anthropic.Anthropic()
        resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=2500, system=system,
                                      messages=[{"role": "user", "content": content}])
        raw = "".join(getattr(b, "text", "") for b in resp.content).replace("```json", "").replace("```", "").strip()
        s, e = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[s:e+1]) if s != -1 else {}
        return {"summary": data.get("summary", ""), "flags": data.get("flags", []) or [],
                "actions": data.get("actions", []) or [], "letter": data.get("letter", "")}
    except Exception as ex:
        logger.error(f"advocate error: {ex}")
        return {"summary": "I could not fully process that just now — please try again.", "flags": [],
                "actions": ["Try again in a moment", "If urgent, call your provider or local emergency number"], "letter": ""}

class QuickTakeRequest(BaseModel):
    topic: str

@app.post("/quick-take")
async def quick_take(req: QuickTakeRequest):
    """Two-phase speed: a fast plain-language first answer shown while the full
    web-grounded briefing loads. No web search, small output — returns in a few seconds."""
    import anthropic, json as _qjson
    topic = (req.topic or "").strip()[:400]
    if not topic:
        return {"status": "error"}
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=("You are a warm, plain-language health companion giving a quick first take while a "
                    "fuller briefing loads. Educational only, never a diagnosis. Keep it short and calm."),
            messages=[{"role": "user", "content": (
                "Give a quick plain-language take for a patient who asked about: " + topic +
                "\nReturn ONLY this JSON: {\"quick\": \"2 to 3 short plain sentences\", "
                "\"questions\": [\"a short question to ask your doctor\", \"another\", \"another\"]}")}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        s, e = text.find("{"), text.rfind("}")
        data = {}
        if s != -1:
            try:
                data = _qjson.loads(text[s:e + 1])
            except Exception:
                try:
                    from json_repair import repair_json
                    data = repair_json(text[s:e + 1], return_objects=True) or {}
                except Exception:
                    data = {}
        return {"status": "ok", "quick": data.get("quick", ""), "questions": (data.get("questions") or [])[:3]}
    except Exception as ex:
        logger.error(f"quick_take error: {ex}")
        return {"status": "error"}


class CompanionRequest(BaseModel):
    message: str                 # their question, or a request to re-explain
    context: Optional[str] = ""  # the health topic being discussed
    lang: Optional[str] = None

@app.post("/companion")
async def companion(req: CompanionRequest):
    """Conversational companion: answers a question or re-explains, the way a
    warm, patient friend would — short, plain, human. Never diagnoses."""
    msg = (req.message or "").strip()
    if not msg:
        return {"reply": ""}
    lang = (req.lang or "").strip()
    lang_line = f"Reply in this language (BCP-47 code): {lang}." if lang else "Reply in the same language they used."
    ctx = (req.context or "").strip()
    system = (
        "You are a warm, patient health companion talking WITH someone the way a caring friend or "
        "family member would explain things at the kitchen table. Keep every reply SHORT "
        "(2 to 4 sentences), plain, and human - no jargon, no lists unless they ask. "
        "You do NOT diagnose or give medical advice; you help them understand and prepare to talk to "
        "their own doctor, who has the final say. If they ask something only their doctor can answer, "
        "gently say that is a great question for their doctor and offer to help them phrase it. "
        "End naturally - sometimes with a gentle check-in like 'does that make sense?' " + lang_line
        + (f"\n\nThe health topic you are discussing: {ctx}" if ctx else "")
    )
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=400, system=system,
            messages=[{"role": "user", "content": msg}],
        )
        reply = "".join(getattr(b, "text", "") for b in resp.content).strip()
        return {"reply": reply or "I am here with you. Could you say a little more about what you mean?"}
    except Exception as ex:
        logger.error(f"companion error: {ex}")
        return {"reply": "I am still here with you. That might be a good one to ask your doctor too."}

class TriageRequest(BaseModel):
    text: str
    lang: Optional[str] = None

@app.post("/triage")
async def triage(req: TriageRequest):
    """ER-or-not: a fast, single-call safety triage. NOT a diagnosis — it errs
    toward caution and always tells the user to seek care if unsure. Fails safe."""
    text = (req.text or "").strip()
    if not text:
        return {"level": "", "headline": "", "action": "", "signs": [], "note": ""}
    lang = (req.lang or "").strip()
    lang_line = f"Respond in this language (BCP-47 code): {lang}." if lang else "Respond in the same language the person used."
    system = (
        "You are a careful safety triage helper for a health-information app. You are NOT a doctor and do "
        "NOT diagnose. You ONLY help a worried person decide how urgently to seek care, and you ALWAYS err "
        "toward caution. If there is any reasonable chance of a serious problem, choose a higher urgency. " + lang_line + "\n\n"
        "Return ONLY valid JSON, no apostrophes in string values:\n"
        "{\n"
        '  "level": "emergency | urgent | soon | self_care",\n'
        '  "headline": "one short, calm, direct sentence about what to do",\n'
        '  "action": "the concrete next step (e.g. Call 911 now, Go to the ER, Call your doctor today)",\n'
        '  "signs": ["warning sign to watch for that would mean go now", "another"],\n'
        '  "note": "one short, non-alarming reassurance"\n'
        "}\n"
        "Use emergency for possible life-threatening signs (chest pain, trouble breathing, stroke signs, severe bleeding, etc.)."
    )
    try:
        import anthropic, json as _json
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=600, system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw = "".join(getattr(b, "text", "") for b in resp.content).replace("```json", "").replace("```", "").strip()
        s, e = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[s:e+1]) if s != -1 else {}
        lvl = data.get("level", "soon")
        if lvl not in ("emergency", "urgent", "soon", "self_care"):
            lvl = "soon"
        return {"level": lvl, "headline": data.get("headline", ""), "action": data.get("action", ""),
                "signs": data.get("signs", []) or [], "note": data.get("note", "")}
    except Exception as ex:
        logger.error(f"triage error: {ex}")
        # Fail safe: when unsure, encourage seeking care.
        return {"level": "urgent", "headline": "If you are worried, it is okay to get checked.",
                "action": "If this feels serious or is getting worse, call your doctor or local emergency number now.",
                "signs": [], "note": "When in doubt, getting checked is never the wrong choice."}

class VisitAssistRequest(BaseModel):
    text: str                          # what the doctor said / what is happening right now
    lang: Optional[str] = None         # patient's language (BCP-47 code) for the reply
    context: Optional[str] = None      # the condition/topic from their briefing, if any

@app.post("/visit-assist")
async def visit_assist(req: VisitAssistRequest):
    """Live Visit Companion: real-time, in-the-room help. Decodes what the doctor
    said into plain language and hands the patient the next smart question to ask.
    Fails soft so the room experience never breaks."""
    text = (req.text or "").strip()
    if not text:
        return {"plain": "", "jargon": [], "questions": [], "note": ""}
    lang = (req.lang or "").strip()
    context = (req.context or "").strip()
    lang_line = f"Reply in this language (BCP-47 code): {lang}." if lang else "Reply in the same language the patient used."
    ctx_line = f"For context, the visit is about: {context}." if context else ""
    system = (
        "You are a calm, real-time companion sitting WITH a patient during their doctor visit. "
        "The patient tells you what the doctor just said. You help them keep up and speak up. "
        "You never give medical advice, never contradict the doctor, and never tell them to argue. "
        "You help them understand and ask good questions so the DOCTOR can decide. "
        + lang_line + " " + ctx_line + "\n\n"
        "Return ONLY valid JSON, no apostrophes inside string values:\n"
        "{\n"
        '  "plain": "what the doctor said, in warm plain language (2-3 sentences)",\n'
        '  "jargon": [{"term": "medical term they used", "meaning": "plain meaning"}],\n'
        '  "questions": ["a smart, specific question to ask the doctor right now", "another"],\n'
        '  "note": "one short reassuring line"\n'
        "}"
    )
    try:
        import anthropic, json as _json, re as _re
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=900,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw = "".join(getattr(b, "text", "") for b in resp.content)
        raw = raw.replace("```json", "").replace("```", "").strip()
        s, e = raw.find("{"), raw.rfind("}")
        data = _json.loads(raw[s:e+1]) if s != -1 else {}
        return {
            "plain": data.get("plain", ""),
            "jargon": data.get("jargon", []) or [],
            "questions": data.get("questions", []) or [],
            "note": data.get("note", ""),
        }
    except Exception as ex:
        logger.error(f"visit_assist error: {ex}")
        return {"plain": text, "jargon": [], "questions": [], "note": "Saved. You can ask your doctor to repeat anything."}

class ReviewRequest(BaseModel):
    briefing: dict
    condition: Optional[str] = ""
    raw_input: Optional[str] = ""

class SignRequest(BaseModel):
    key: str
    doctor_name: str
    verdict: str                 # "accurate" | "edited" | "see_your_doctor"
    note: Optional[str] = ""

def _doctor_key_ok(key: str) -> bool:
    want = os.getenv("DOCTOR_KEY")
    return bool(want) and key == want

@app.post("/review/request")
async def review_request(req: ReviewRequest):
    """Patient asks a real physician on the medical board to review this briefing."""
    if not SUPABASE_ENABLED:
        return {"status": "unavailable"}
    row = await request_review(req.raw_input or "", req.condition or "", req.briefing or {})
    if not row:
        return {"status": "error"}
    return {"status": "pending", "id": row.get("id")}

@app.get("/review/{review_id}")
async def review_status(review_id: str):
    r = await get_review(review_id)
    return r or {"status": "unknown"}

@app.get("/review/pending/list")
async def review_pending(key: str = ""):
    """Medical-board only: list briefings awaiting review."""
    if not _doctor_key_ok(key):
        raise HTTPException(401, "Invalid board access key")
    return {"reviews": await get_pending_reviews()}

@app.post("/review/{review_id}/sign")
async def review_sign(review_id: str, req: SignRequest):
    """Medical-board only: co-sign a briefing with a verdict + note."""
    if not _doctor_key_ok(req.key):
        raise HTTPException(401, "Invalid board access key")
    ok = await sign_review(review_id, req.doctor_name, req.verdict, req.note or "")
    return {"ok": ok}

@app.post("/auth/signup")
async def signup(req: AuthRequest):
    if not SUPABASE_ENABLED:
        raise HTTPException(503, "Auth not configured yet")
    try:
        sb = get_supabase()
        result = sb.auth.sign_up({"email": req.email, "password": req.password})
        return {"status": "success", "user_id": result.user.id if result.user else None}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/auth/login")
async def login(req: AuthRequest):
    if not SUPABASE_ENABLED:
        raise HTTPException(503, "Auth not configured yet")
    try:
        sb = get_supabase()
        result = sb.auth.sign_in_with_password({"email": req.email, "password": req.password})
        return {"status": "success", "access_token": result.session.access_token if result.session else None, "user_id": result.user.id if result.user else None}
    except Exception as e:
        raise HTTPException(401, "Invalid credentials")

@app.post("/session/start")
async def session_start(req: StartRequest):
    if not req.raw_input.strip():
        raise HTTPException(400, "Please share what's going on")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "raw_input": req.raw_input,
        "image_data": req.image_data,
        "image_media_type": req.image_media_type or "image/jpeg",
        "user_id": req.user_id,
        "viewer_type": req.viewer_type or "everyday",
        "intent": req.intent,
    }
    try:
        result = graph.invoke(initial_state, config, interrupt_before=["confirmation"])
        guardrail = result.get("guardrail_status", "pass")
        if guardrail in ("emergency", "crisis", "off_topic", "invalid"):
            return {"status": guardrail, "guardrail_message": result.get("guardrail_message", "")}
        if result.get("error"):
            return {"status": "error", "error": result["error"]}
        response = {
            "status": "awaiting_confirmation",
            "thread_id": thread_id,
            "extraction": result.get("extraction", {}),
            "normalization": result.get("normalization", {})
        }
        if result.get("image_analysis"):
            response["image_analysis"] = result["image_analysis"]
        return response
    except Exception as e:
        logger.error(f"session_start error: {e}")
        raise HTTPException(500, str(e))

@app.post("/session/{thread_id}/confirm")
async def session_confirm(thread_id: str, req: ConfirmRequest):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        # Get current state to extract the condition
        state_snapshot = graph.get_state(config)
        if not state_snapshot:
            raise HTTPException(404, "Session not found")

        # Determine final condition from override or normalization
        override = (req.override or "").strip()
        if override:
            final_condition = override
        else:
            norm = state_snapshot.values.get("normalization", {})
            final_condition = norm.get("primary_condition", "") or norm.get("plain_condition_name", "")

        logger.info(f"confirm: final_condition='{final_condition}'")

        # Update state with final_condition BEFORE resuming
        graph.update_state(config, {"final_condition": final_condition}, as_node="confirmation")

        # Resume with Command
        result = graph.invoke(
            Command(resume={"confirmed": req.confirmed, "override": override}),
            config
        )

        if result.get("error"):
            return {"status": "error", "error": result["error"]}

        briefing = result.get("briefing")
        if not briefing:
            logger.error(f"No briefing returned. State: {result.keys()}")
            return {"status": "error", "error": "Briefing generation failed. Please try again."}

        if req.user_id and SUPABASE_ENABLED:
            await save_session(
                user_id=req.user_id,
                raw_input=state_snapshot.values.get("raw_input", ""),
                condition=final_condition,
                briefing=briefing
            )

        return {"status": "complete", "briefing": briefing}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"session_confirm error: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@app.post("/analyze/image")
async def analyze_image(req: StartRequest):
    if not req.image_data:
        raise HTTPException(400, "No image provided")
    try:
        from .nodes.vision_node import vision_node
        result = vision_node({
            "raw_input": req.raw_input or "Analyze this image",
            "image_data": req.image_data,
            "image_media_type": req.image_media_type or "image/jpeg"
        })
        return {"status": "complete", "image_analysis": result.get("image_analysis")}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/user/{user_id}/history")
async def user_history(user_id: str):
    return {"status": "ok", "history": await get_user_history(user_id)}

@app.get("/user/{user_id}/symptoms")
async def user_symptoms(user_id: str):
    return {"status": "ok", "symptoms": await get_symptom_history(user_id)}

@app.post("/user/symptoms/log")
async def log_symptom_entry(req: SymptomLogRequest):
    success = await log_symptom(req.user_id, req.symptom, req.severity, req.notes or "")
    return {"status": "ok" if success else "error"}

@app.get("/user/{user_id}/export")
async def user_export(user_id: str):
    """HIPAA patient right: download everything we store about you."""
    data = await export_user_data(user_id)
    return {"status": "ok", "exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "data": data}

class DeleteRequest(BaseModel):
    user_id: str

@app.post("/user/delete")
async def user_delete(req: DeleteRequest):
    """HIPAA patient right: delete your account and all your data."""
    ok = await delete_user_data(req.user_id)
    return {"status": "ok" if ok else "error"}

@app.post("/user/data/clear")
async def user_data_clear(req: DeleteRequest):
    """Patient right: delete all health data (logs, history) WITHOUT deleting the account."""
    ok = await clear_user_data(req.user_id)
    return {"status": "ok" if ok else "error"}

@app.get("/session/{thread_id}/state")
async def session_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        return {"status": "ok", "state": state.values if state else {}}
    except Exception as e:
        raise HTTPException(500, str(e))

# Catch-all (MUST stay last): serve any other root-level frontend file by name, so the
# same relative links/assets (e.g. /about.html, /brand-mark.png) resolve on the web AND
# in the bundled mobile app. All explicit routes + API endpoints above take precedence.
@app.get("/{filename:path}")
async def serve_root_asset(filename: str):
    safe = os.path.normpath(filename).replace("\\", "/").lstrip("/")
    if not safe or ".." in safe:
        raise HTTPException(404)
    fp = os.path.join(frontend_dir, safe)
    if os.path.isfile(fp):
        return FileResponse(fp)
    raise HTTPException(404)

