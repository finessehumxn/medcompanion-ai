"""server.py â€” MedCompanion AI v2"""
import os, logging, uuid, asyncio
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

# --- Data-handling policy (trust-by-default) -----------------------------
# By DEFAULT MedCompanion stores NO health content on the server: the AI
# endpoints are stateless (answer-and-forget) and nothing a user enters is
# persisted. Server-side history is strictly opt-in and only turns on when a
# deployment explicitly sets MC_STORE_HISTORY=1 (e.g. after a signed BAA and a
# clear in-app consent). This makes the promise "your records stay on your
# device" true unless a deployment deliberately, and disclosed-ly, changes it.
STORE_HISTORY = os.getenv("MC_STORE_HISTORY", "0") == "1"

# --- Epic / MyChart SMART-on-FHIR (patient standalone launch) -------------
# Defaults point at Epic's PUBLIC SANDBOX so the flow is testable with Epic's
# test patients. To go live: register a free app at fhir.epic.com, set
# EPIC_CLIENT_ID (and register EPIC_REDIRECT_URI there). Public client + PKCE —
# no client secret. Tokens are transient: exchanged/used here, never stored.
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID", "")
EPIC_FHIR_BASE = os.getenv("EPIC_FHIR_BASE", "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4")
EPIC_AUTHORIZE_URL = os.getenv("EPIC_AUTHORIZE_URL", "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize")
EPIC_TOKEN_URL = os.getenv("EPIC_TOKEN_URL", "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token")
EPIC_REDIRECT_URI = os.getenv("EPIC_REDIRECT_URI", "https://medcompanion-ai.up.railway.app/app")
EPIC_SCOPES = os.getenv("EPIC_SCOPES", "openid fhirUser patient/Patient.read patient/Observation.read patient/Condition.read patient/MedicationRequest.read patient/AllergyIntolerance.read")

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

@app.get("/trust")
async def serve_trust():
    return FileResponse(os.path.join(frontend_dir, "trust.html"))

@app.get("/pro")
async def serve_pro():
    return FileResponse(os.path.join(frontend_dir, "pro.html"))

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
    return {
        "status": "ok", "version": "2.0.0",
        "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
        "supabase": SUPABASE_ENABLED,
        # STT diagnostic: which transcription keys the server can actually see
        # (booleans only — never exposes the key). Helps debug env-var issues.
        "stt": {
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        },
        # also surface any env var names that LOOK like a groq key but are
        # misnamed (e.g. trailing space) — shows the raw keys present.
        "groq_env_names": [k for k in os.environ if "GROQ" in k.upper()],
    }

@app.get("/data-policy")
async def data_policy():
    """Honest, machine-readable statement of how MedCompanion handles data.
    The app renders this on the 'Your data & AI' screen, and anyone (a patient,
    a hospital's compliance team) can curl it to verify the claims independently.
    It reports the LIVE configuration of this running server, not marketing copy."""
    voice_vendors = []
    if os.getenv("OPENAI_API_KEY"): voice_vendors.append("OpenAI (Whisper)")
    if os.getenv("GROQ_API_KEY"): voice_vendors.append("Groq (Whisper)")
    if os.getenv("ELEVENLABS_API_KEY"): voice_vendors.append("ElevenLabs")
    return {
        "on_device_only": [
            "Health Journal check-ins (stored only in your phone's local storage)",
            "My Records entries (stored only in your phone's local storage)",
            "The visit sheet (travels only inside the link you share; never uploaded)",
        ],
        "sent_to_ai_only_when_you_tap": {
            "text_features": {
                "vendor": "Anthropic (Claude)",
                "features": ["Explain my records", "See my patterns", "Build my visit sheet", "Companion chat"],
                "note": "Only the specific text for that feature is sent, to generate the answer.",
            },
            "voice_features": {
                "vendors": voice_vendors,
                "features": ["Voice input (speech-to-text)", "Read-aloud (text-to-speech)"],
                "note": "Audio is transcribed/spoken and not retained by MedCompanion.",
            },
        },
        "server_stores_health_content": STORE_HISTORY,   # false by default
        "server_storage_note": (
            "OFF by default: the AI features are stateless — they answer and forget, and nothing "
            "you enter is written to our database. Server-side history only turns on if a deployment "
            "explicitly enables it (MC_STORE_HISTORY=1) with disclosure and consent."
        ),
        "we_never_log_your_health_content": True,
        "ai_will_never": [
            "Diagnose you or decide your treatment",
            "Replace your doctor's judgment",
            "Train AI models on your data",
            "Sell or advertise with your data",
        ],
        "you_control": [
            "The app's core works with AI turned off",
            "Nothing is sent until you tap an AI feature",
            "You can delete everything on your device at any time",
        ],
        "not_yet": [
            "This is the product's data architecture. Formal hospital assurances "
            "(signed BAAs with each AI vendor, HIPAA program, SOC 2) are a separate, in-progress track.",
        ],
    }

# ── Epic / MyChart SMART-on-FHIR (patient standalone) ─────────────────────
@app.get("/epic/config")
async def epic_config():
    """What the app needs to start the Epic sign-in. `configured` is false until
    EPIC_CLIENT_ID is set — the app then falls back to file import."""
    return {
        "configured": bool(EPIC_CLIENT_ID),
        "client_id": EPIC_CLIENT_ID,
        "authorize_url": EPIC_AUTHORIZE_URL,
        "fhir_base": EPIC_FHIR_BASE,
        "redirect_uri": EPIC_REDIRECT_URI,
        "scopes": EPIC_SCOPES,
    }

class EpicTokenReq(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: Optional[str] = None

@app.post("/epic/token")
async def epic_token(req: EpicTokenReq):
    """Exchange the auth code for an access token (public client + PKCE).
    The token is returned to the device and NOT stored server-side."""
    if not EPIC_CLIENT_ID:
        raise HTTPException(400, "Epic isn't configured (set EPIC_CLIENT_ID).")
    import httpx
    data = {
        "grant_type": "authorization_code",
        "code": req.code,
        "redirect_uri": req.redirect_uri or EPIC_REDIRECT_URI,
        "client_id": EPIC_CLIENT_ID,
        "code_verifier": req.code_verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(EPIC_TOKEN_URL, data=data,
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
        if r.status_code != 200:
            logger.error(f"epic token exchange status {r.status_code}")
            raise HTTPException(502, "Epic sign-in couldn't be completed.")
        t = r.json()
        return {"access_token": t.get("access_token"), "patient": t.get("patient"),
                "scope": t.get("scope"), "token_type": t.get("token_type")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"epic token error: {e}")
        raise HTTPException(502, "Epic sign-in error.")

class EpicRecordsReq(BaseModel):
    access_token: str
    patient: str
    fhir_base: Optional[str] = None

@app.post("/epic/records")
async def epic_records(req: EpicRecordsReq):
    """Read the patient's FHIR resources with their token and return the raw
    resources for the device to map. Token and records are not persisted; only
    error classes are logged (never tokens or PHI bodies)."""
    import httpx
    base = (req.fhir_base or EPIC_FHIR_BASE).rstrip("/")
    headers = {"Authorization": f"Bearer {req.access_token}", "Accept": "application/fhir+json"}
    queries = {
        "Observation": f"{base}/Observation?patient={req.patient}&category=laboratory",
        "Condition": f"{base}/Condition?patient={req.patient}",
        "MedicationRequest": f"{base}/MedicationRequest?patient={req.patient}",
        "AllergyIntolerance": f"{base}/AllergyIntolerance?patient={req.patient}",
    }
    resources = []
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            for name, url in queries.items():
                try:
                    r = await client.get(url, headers=headers)
                    if r.status_code == 200:
                        for e in (r.json().get("entry") or []):
                            res = e.get("resource")
                            if res:
                                resources.append(res)
                    else:
                        logger.error(f"epic fetch {name} status {r.status_code}")
                except Exception as ie:
                    logger.error(f"epic fetch {name} error: {type(ie).__name__}")
    except Exception as e:
        logger.error(f"epic records error: {type(e).__name__}")
        raise HTTPException(502, "Couldn't read your Epic records.")
    return {"resources": resources}

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

class InsightsRequest(BaseModel):
    entries: list          # on-device check-ins: [{date, symptoms, severity, mood, energy, sleep, notes, meds}]
    lang: Optional[str] = None

@app.post("/insights")
async def insights(req: InsightsRequest):
    """Health Timeline insights. The app keeps daily check-ins ON THE DEVICE and
    sends them here only to be analyzed — nothing is stored server-side. Claude
    finds patterns, likely triggers, and trends, and preps what to raise with a
    doctor. Information, never diagnosis. Fails soft to an empty-but-valid shape."""
    import json as _json
    entries = req.entries or []
    empty = {"summary": "", "patterns": [], "triggers": [], "trend": "", "watch": [], "doctor": []}
    if len(entries) < 3:
        empty["summary"] = "Log a few more check-ins (about 3+) and I'll start spotting patterns and triggers for you."
        return empty
    # Compact the entries into a readable log for the model (cap to recent 60).
    lines = []
    for e in entries[-60:]:
        if not isinstance(e, dict):
            continue
        parts = [str(e.get("date", ""))]
        for k in ("severity", "mood", "energy", "sleep"):
            if e.get(k) not in (None, "", []):
                parts.append(f"{k}={e.get(k)}")
        if e.get("symptoms"):
            s = e["symptoms"]
            parts.append("symptoms=" + (", ".join(s) if isinstance(s, list) else str(s)))
        if e.get("meds"):
            m = e["meds"]
            parts.append("meds=" + (", ".join(m) if isinstance(m, list) else str(m)))
        if e.get("notes"):
            parts.append("notes=" + str(e["notes"])[:200])
        lines.append(" · ".join(p for p in parts if p))
    log = "\n".join(lines)
    lang_line = f"\nWrite the output in this language (code): {req.lang}." if req.lang else ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1400,
            system=(
                "You are MedCompanion's health-pattern analyst. You look at a person's own daily "
                "check-ins and surface honest, useful observations in plain language. HARD RULES: "
                "you provide information, NEVER a diagnosis or treatment; never alarm; correlation is "
                "not causation, so hedge ('may line up with', 'worth noticing'); if data is thin, say so. "
                "Encourage bringing findings to their clinician. "
                "Return ONLY a JSON object with keys: summary (2-3 warm sentences), patterns (array of short "
                "strings — recurring symptoms/timing), triggers (array — possible correlations, each hedged), "
                "trend (one sentence: improving/steady/worsening and over what span), watch (array — things to "
                "keep an eye on), doctor (array — specific things to raise at the next appointment). No prose "
                "outside the JSON."
            ),
            messages=[{"role": "user", "content": f"Here are my check-ins (most recent last):\n{log}{lang_line}"}],
        )
        out = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if out.startswith("```"):
            out = out.strip("`").split("\n", 1)[-1] if "\n" in out else out
            out = out.replace("json", "", 1).strip()
        data = _json.loads(out)
        for k in empty:
            data.setdefault(k, empty[k])
        return data
    except Exception as e:
        logger.error(f"insights error: {e}")
        empty["summary"] = "Couldn't analyze your patterns just now — please try again in a moment."
        return empty

class RecordsRequest(BaseModel):
    labs: list = []            # [{name, value, unit, range, date}]  (from FHIR Observation)
    medications: list = []     # [{name, dose, reason}]              (from FHIR MedicationRequest)
    conditions: list = []      # [{name, date}]                      (from FHIR Condition)
    lang: Optional[str] = None

@app.post("/explain-records")
async def explain_records(req: RecordsRequest):
    """Explain a person's REAL medical records — labs, meds, conditions imported
    from their hospital's MyChart / Epic via FHIR — in plain language, flag what's
    out of range, and prep questions for their doctor. Information, not diagnosis.
    Stateless: records are analyzed, not stored. Fails soft to a valid empty shape."""
    import json as _json
    labs, meds, conds = req.labs or [], req.medications or [], req.conditions or []
    empty = {"summary": "", "labs": [], "medications": [], "conditions": [], "questions": []}
    if not (labs or meds or conds):
        empty["summary"] = "No records yet — connect your MyChart or add a few to get plain-language explanations."
        return empty

    def fmt(items, keys):
        rows = []
        for it in items[:80]:
            if isinstance(it, dict):
                rows.append(", ".join(f"{k}={it.get(k)}" for k in keys if it.get(k) not in (None, "", [])))
            else:
                rows.append(str(it))
        return "\n".join(rows)
    payload = ""
    if labs:  payload += "LABS:\n" + fmt(labs, ["name", "value", "unit", "range", "date"]) + "\n\n"
    if meds:  payload += "MEDICATIONS:\n" + fmt(meds, ["name", "dose", "reason"]) + "\n\n"
    if conds: payload += "CONDITIONS:\n" + fmt(conds, ["name", "date"]) + "\n\n"
    lang_line = f"\nWrite everything in this language (code): {req.lang}." if req.lang else ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2400,
            system=(
                "You are MedCompanion. A person imported their real medical records (from their hospital's "
                "MyChart / Epic, via FHIR). Explain them warmly and in plain language so they walk into their "
                "appointment understanding their own chart. HARD RULES: information, NEVER a diagnosis or a "
                "treatment change; never alarm; when a value is out of range, say what that generally can indicate "
                "and to discuss it with their clinician — without concluding what's wrong. "
                "Return ONLY a JSON object with keys: summary (2-3 warm sentences), labs (array of "
                "{name, value, status: 'normal'|'high'|'low'|'unknown', plain: one plain sentence}), medications "
                "(array of {name, plain: what it's typically for in plain words}), conditions (array of {name, "
                "plain: what it means in plain words}), questions (array of specific things to ask the doctor). "
                "No prose outside the JSON."
            ),
            messages=[{"role": "user", "content": f"Here are my records:\n\n{payload}{lang_line}"}],
        )
        out = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if out.startswith("```"):
            out = out.strip("`")
            if out[:4].lower() == "json":
                out = out[4:]
            out = out.strip()
        data = _json.loads(out)
        for k, dflt in empty.items():
            data.setdefault(k, dflt)
        return data
    except Exception as e:
        logger.error(f"explain-records error: {e}")
        empty["summary"] = "Couldn't explain your records just now — please try again in a moment."
        return empty

class ChronologyRequest(BaseModel):
    # Attorney / paralegal lens on the SAME record engine: organize a client's
    # medical records into a factual, dated chronology for an injury/med-mal matter.
    labs: list = []
    medications: list = []
    conditions: list = []
    notes: Optional[str] = ""        # pasted records / visit notes / free text
    matter: Optional[str] = ""       # optional case context, e.g. "MVA 2025-03-14"
    lang: Optional[str] = None

@app.post("/chronology")
async def chronology(req: ChronologyRequest):
    """Attorney lens: turn a client's medical records into a factual, dated
    medical chronology (timeline + key findings + gaps) for a legal workflow.
    Factual organization ONLY — never legal advice, causation, or liability
    opinions. A DRAFT to verify against source records. Stateless; not stored."""
    import json as _json
    labs, meds, conds = req.labs or [], req.medications or [], req.conditions or []
    notes = (req.notes or "").strip()
    empty = {"summary": "", "timeline": [], "key_findings": [], "gaps": [], "disclaimer": ""}
    if not (labs or meds or conds or notes):
        empty["summary"] = "No records provided. Import a FHIR/JSON export or paste the records to build a chronology."
        return empty

    def fmt(items, keys):
        rows = []
        for it in items[:120]:
            if isinstance(it, dict):
                rows.append(", ".join(f"{k}={it.get(k)}" for k in keys if it.get(k) not in (None, "", [])))
            else:
                rows.append(str(it))
        return "\n".join(rows)
    payload = ""
    if req.matter: payload += f"MATTER CONTEXT: {req.matter}\n\n"
    if labs:  payload += "LABS/RESULTS:\n" + fmt(labs, ["name", "value", "unit", "range", "date"]) + "\n\n"
    if meds:  payload += "MEDICATIONS:\n" + fmt(meds, ["name", "dose", "reason", "date"]) + "\n\n"
    if conds: payload += "CONDITIONS/DIAGNOSES:\n" + fmt(conds, ["name", "date"]) + "\n\n"
    if notes: payload += "RECORDS / NOTES (free text):\n" + notes[:8000] + "\n\n"
    lang_line = f"\nWrite everything in this language (code): {req.lang}." if req.lang else ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=(
                "You organize a person's MEDICAL RECORDS into a factual, dated medical chronology for a "
                "paralegal/attorney workflow (e.g., personal-injury or med-mal case prep). You EXTRACT and "
                "ORDER facts that are present in the provided records. "
                "HARD RULES — this is factual organization, NOT advice: "
                "(1) NEVER give legal advice; NEVER opine on causation, fault, liability, damages, settlement, "
                "or prognosis. (2) NEVER invent facts, dates, providers, or findings not in the records. "
                "(3) When a date is missing/ambiguous, put the entry with date='' and note it under gaps — do not guess. "
                "(4) Flag missing or discontinuous records under gaps. "
                "(5) This is a DRAFT to be verified against the source records by a qualified person. "
                "Return ONLY a JSON object with keys: "
                "summary (3-5 factual sentences, no opinion), "
                "timeline (array of {date: 'YYYY-MM-DD' or '', event: short factual label, detail: one factual sentence, "
                "category: 'visit'|'lab'|'medication'|'diagnosis'|'procedure'|'imaging'|'other'}), sorted earliest first, "
                "key_findings (array of factual, record-cited strings), "
                "gaps (array of strings: missing dates, missing records, ambiguities to verify), "
                "disclaimer (one sentence: factual draft from provided records, not legal or medical advice, verify against source). "
                "No prose outside the JSON."
            ),
            messages=[{"role": "user", "content": f"Records to organize into a chronology:\n\n{payload}{lang_line}"}],
        )
        out = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if out.startswith("```"):
            out = out.strip("`")
            if out[:4].lower() == "json":
                out = out[4:]
            out = out.strip()
        data = _json.loads(out)
        for k, dflt in empty.items():
            data.setdefault(k, dflt)
        if not data.get("disclaimer"):
            data["disclaimer"] = ("Factual draft organized from the records provided — not legal or medical advice. "
                                  "Verify every entry against the source records.")
        return data
    except Exception as e:
        logger.error(f"chronology error: {e}")
        empty["summary"] = "Couldn't build the chronology just now — please try again."
        return empty

class VisitSummaryRequest(BaseModel):
    reason: Optional[str] = ""      # why they're going / main concern (patient's words)
    checkins: list = []             # from the Health Journal (on-device)
    labs: list = []
    medications: list = []
    conditions: list = []
    lang: Optional[str] = None

@app.post("/visit-summary")
async def visit_summary(req: VisitSummaryRequest):
    """The clinician hand-off — the load-lightener. Turns the patient's OWN data
    (reason for visit + on-device check-ins + records) into a concise sheet a
    clinician can read in ~20 seconds, plus the patient's questions. Everything is
    patient-REPORTED, never a clinical assessment. Stateless; nothing stored."""
    import json as _json
    reason = (req.reason or "").strip()
    checkins, labs, meds, conds = req.checkins or [], req.labs or [], req.medications or [], req.conditions or []
    empty = {"reason": reason, "summary": "", "highlights": [], "questions": [], "patient_note": ""}
    if not (reason or checkins or labs or meds or conds):
        empty["summary"] = "Add your reason for the visit, a few check-ins, or your records and I'll build a sheet for your doctor."
        return empty

    def fmt(items, keys):
        rows = []
        for it in items[:60]:
            if isinstance(it, dict):
                rows.append(", ".join(f"{k}={it.get(k)}" for k in keys if it.get(k) not in (None, "", [])))
            else:
                rows.append(str(it))
        return "\n".join(rows)
    blocks = []
    if reason:  blocks.append("REASON FOR VISIT (patient's words): " + reason)
    if checkins: blocks.append("DAILY CHECK-INS:\n" + fmt(checkins, ["date", "severity", "mood", "energy", "sleep", "symptoms", "notes"]))
    if labs:  blocks.append("LABS:\n" + fmt(labs, ["name", "value", "unit", "range", "date"]))
    if meds:  blocks.append("MEDICATIONS:\n" + fmt(meds, ["name", "dose", "reason"]))
    if conds: blocks.append("CONDITIONS:\n" + fmt(conds, ["name", "date"]))
    payload = "\n\n".join(blocks)
    lang_line = f"\nWrite the patient_note in this language (code): {req.lang}. Keep the clinician summary and highlights in English (for the clinician)." if req.lang else ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1600,
            system=(
                "You are MedCompanion, preparing a concise hand-off a busy clinician can read in about 20 "
                "seconds. Everything here is PATIENT-REPORTED — present it as such ('patient reports…'), never "
                "as your own clinical assessment, diagnosis, or triage. Be tight, factual, and free of alarm. "
                "Surface only what's decision-relevant: the reason for the visit, patient-tracked patterns "
                "(frequency, timing, what seems to line up), and pertinent records (out-of-range labs, active "
                "meds/conditions). "
                "Return ONLY JSON with keys: reason (one line), summary (2-4 tight clinician-facing sentences, "
                "'patient reports…' style), highlights (array of short factual bullets — the decision-relevant "
                "points), questions (array — the patient's questions for the visit), patient_note (2 warm "
                "sentences telling the patient what this sheet does and to share it). No prose outside the JSON."
            ),
            messages=[{"role": "user", "content": payload + lang_line}],
        )
        out = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if out.startswith("```"):
            out = out.strip("`")
            if out[:4].lower() == "json":
                out = out[4:]
            out = out.strip()
        data = _json.loads(out)
        for k, dflt in empty.items():
            data.setdefault(k, dflt)
        return data
    except Exception as e:
        logger.error(f"visit-summary error: {e}")
        empty["summary"] = "Couldn't build your visit sheet just now — please try again."
        return empty

class SpeakRequest(BaseModel):
    text: str
    lang: Optional[str] = None

@app.post("/speak")
async def speak(req: SpeakRequest):
    """Read the answer aloud. Uses whichever text-to-speech provider is
    configured — ElevenLabs (cloned voice) -> OpenAI -> Groq — and returns the
    audio the app plays. Add ANY one of these keys and read-aloud works:
    ELEVENLABS_API_KEY (+ ELEVENLABS_VOICE_ID), OPENAI_API_KEY, or GROQ_API_KEY.
    If none work, the client falls back to the device voice — it never breaks."""
    import httpx
    from fastapi.responses import Response
    text = (req.text or "").strip()[:2500]
    if not text:
        raise HTTPException(400, "No text to read")

    el_key = os.getenv("ELEVENLABS_API_KEY")
    el_voice = os.getenv("ELEVENLABS_VOICE_ID")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not (el_key and el_voice) and not openai_key:
        raise HTTPException(503, "Voice not configured — add OPENAI_API_KEY or ELEVENLABS_API_KEY")

    cache = {"Cache-Control": "public, max-age=86400"}
    errors = []
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # 1) ElevenLabs — the cloned voice, if fully configured
            if el_key and el_voice:
                r = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{el_voice}",
                    headers={"xi-api-key": el_key, "accept": "audio/mpeg", "content-type": "application/json"},
                    json={"text": text, "model_id": "eleven_multilingual_v2",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.3, "use_speaker_boost": True}},
                )
                if r.status_code == 200:
                    return Response(content=r.content, media_type="audio/mpeg", headers=cache)
                errors.append(f"elevenlabs {r.status_code}")

            # 2) OpenAI TTS — rock-solid, one key
            if openai_key:
                r = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {openai_key}", "content-type": "application/json"},
                    json={"model": "tts-1", "input": text, "voice": "alloy", "response_format": "mp3"},
                )
                if r.status_code == 200:
                    return Response(content=r.content, media_type="audio/mpeg", headers=cache)
                errors.append(f"openai {r.status_code}")

            # (Groq's PlayAI TTS was decommissioned — no longer an option.)
    except Exception as e:
        logger.error(f"speak error: {e}")
        raise HTTPException(502, f"Voice service unavailable: {e}")

    detail = " | ".join(errors) or "no provider attempted"
    logger.error(f"speak failed: {detail}")
    raise HTTPException(502, f"Voice generation failed — {detail}")

class TranscribeRequest(BaseModel):
    audio: str                       # base64 (optionally a data: URL)
    mime: Optional[str] = "audio/webm"

@app.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    """Speech-to-text for the in-app mic. The app records audio in the WebView
    and posts it here; we transcribe via whichever provider is configured
    (Groq Whisper → OpenAI Whisper → ElevenLabs Scribe) and return the text.
    This works on the LIVE build over the network — no native plugin needed."""
    import base64, httpx
    b64 = req.audio or ""
    if "," in b64[:64]:
        b64 = b64.split(",", 1)[1]
    try:
        audio = base64.b64decode(b64)
    except Exception:
        raise HTTPException(400, "Bad audio data")
    if not audio:
        raise HTTPException(400, "No audio")

    mime = (req.mime or "audio/webm").split(";")[0].strip()
    ext = {"audio/webm": "webm", "audio/mp4": "mp4", "audio/aac": "aac", "audio/mpeg": "mp3",
           "audio/wav": "wav", "audio/x-m4a": "m4a", "audio/mp4a-latm": "mp4",
           "video/mp4": "mp4", "audio/ogg": "ogg"}.get(mime, "webm")
    fname = f"audio.{ext}"

    groq = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    eleven = os.getenv("ELEVENLABS_API_KEY")
    if not (groq or openai_key or eleven):
        raise HTTPException(503, "Transcription not configured")

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            if groq:
                r = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq}"},
                    files={"file": (fname, audio, mime)},
                    data={"model": "whisper-large-v3-turbo", "response_format": "json"},
                )
                if r.status_code == 200:
                    return {"text": (r.json().get("text") or "").strip()}
                logger.error(f"groq stt {r.status_code} (response body not logged)")
            if openai_key:
                r = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    files={"file": (fname, audio, mime)},
                    data={"model": "whisper-1", "response_format": "json"},
                )
                if r.status_code == 200:
                    return {"text": (r.json().get("text") or "").strip()}
                logger.error(f"openai stt {r.status_code} (response body not logged)")
            if eleven:
                r = await client.post(
                    "https://api.elevenlabs.io/v1/speech-to-text",
                    headers={"xi-api-key": eleven},
                    files={"file": (fname, audio, mime)},
                    data={"model_id": "scribe_v1"},
                )
                if r.status_code == 200:
                    return {"text": (r.json().get("text") or "").strip()}
                logger.error(f"eleven stt {r.status_code} (response body not logged)")
    except Exception as e:
        logger.error(f"transcribe error: {e}")
        raise HTTPException(502, "Transcription unavailable")
    raise HTTPException(502, "Transcription failed")

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

# In-memory briefing jobs (thread_id -> {status, briefing/error}). The
# briefing runs in the background so the client never holds a 40s request
# open (which drops on flaky networks). Single uvicorn worker -> shared.
_briefing_jobs = {}

async def _briefing_task(thread_id, config, confirmed, override, user_id, raw_input, final_condition):
    try:
        # graph.invoke is blocking -> run it off the event loop
        result = await asyncio.to_thread(
            graph.invoke,
            Command(resume={"confirmed": confirmed, "override": override}),
            config,
        )
        if result.get("error"):
            _briefing_jobs[thread_id] = {"status": "error", "error": result["error"]}
            return
        briefing = result.get("briefing")
        if not briefing:
            logger.error(f"No briefing returned. State: {list(result.keys())}")
            _briefing_jobs[thread_id] = {"status": "error", "error": "Briefing generation failed. Please try again."}
            return
        if user_id and SUPABASE_ENABLED and STORE_HISTORY:
            # Opt-in only (MC_STORE_HISTORY=1). Off by default: no health input
            # is written to the server, so the default deployment stores nothing.
            try:
                await save_session(user_id=user_id, raw_input=raw_input, condition=final_condition, briefing=briefing)
            except Exception as se:
                logger.warning(f"save_session failed (non-fatal): {se}")
        _briefing_jobs[thread_id] = {"status": "complete", "briefing": briefing}
    except Exception as e:
        logger.error(f"briefing task error: {e}", exc_info=True)
        _briefing_jobs[thread_id] = {"status": "error", "error": "Something went wrong generating your briefing. Please try again."}

@app.post("/session/{thread_id}/confirm")
async def session_confirm(thread_id: str, req: ConfirmRequest):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = graph.get_state(config)
        if not state_snapshot:
            raise HTTPException(404, "Session not found")

        override = (req.override or "").strip()
        if override:
            final_condition = override
        else:
            norm = state_snapshot.values.get("normalization", {})
            final_condition = norm.get("primary_condition", "") or norm.get("plain_condition_name", "")

        logger.info(f"confirm: final_condition='{final_condition}' (async)")
        graph.update_state(config, {"final_condition": final_condition}, as_node="confirmation")

        raw_input = state_snapshot.values.get("raw_input", "")
        _briefing_jobs[thread_id] = {"status": "processing"}
        asyncio.create_task(_briefing_task(thread_id, config, req.confirmed, override, req.user_id, raw_input, final_condition))
        return {"status": "processing"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"session_confirm error: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@app.get("/session/{thread_id}/result")
async def session_result(thread_id: str):
    """Poll for the background briefing. Short + cheap — the app calls this
    every few seconds until the briefing is ready."""
    job = _briefing_jobs.get(thread_id)
    if not job:
        return {"status": "unknown"}
    if job["status"] == "complete":
        return {"status": "complete", "briefing": job["briefing"]}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "Briefing failed. Please try again.")}
    return {"status": "processing"}

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

