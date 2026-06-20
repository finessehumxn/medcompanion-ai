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
                                  get_pending_reviews, sign_review, export_user_data, delete_user_data)
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

@app.get("/session/{thread_id}/state")
async def session_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        return {"status": "ok", "state": state.values if state else {}}
    except Exception as e:
        raise HTTPException(500, str(e))

