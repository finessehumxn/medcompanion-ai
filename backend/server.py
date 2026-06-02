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
    from .supabase_client import get_supabase, save_session, get_user_history, log_symptom, get_symptom_history
    SUPABASE_ENABLED = True
except ImportError:
    SUPABASE_ENABLED = False
    async def save_session(*a, **k): return None
    async def get_user_history(u, limit=20): return []
    async def log_symptom(*a, **k): return False
    async def get_symptom_history(u, limit=50): return []

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

@app.get("/")
def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url='/app')

@app.get("/")
def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url='/app')

@app.get("/app")
async def serve_app():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")), "supabase": SUPABASE_ENABLED}

class StartRequest(BaseModel):
    raw_input: str
    image_data: Optional[str] = None
    image_media_type: Optional[str] = None
    user_id: Optional[str] = None

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
        "user_id": req.user_id
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

@app.get("/session/{thread_id}/state")
async def session_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        return {"status": "ok", "state": state.values if state else {}}
    except Exception as e:
        raise HTTPException(500, str(e))

