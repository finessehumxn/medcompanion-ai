"""
server.py — MedCompanion AI FastAPI Server
Includes: LangSmith tracing, Supabase auth, vision endpoint, health history API
"""
import os
import base64
import logging
import uuid
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# ── LangSmith must be configured before any LangChain/LangGraph imports ──
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "medcompanion-ai")
    logging.getLogger(__name__).info("LangSmith tracing enabled")

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver

from .graph import build_graph
from .supabase_client import get_supabase, save_session, get_user_history, log_symptom, get_symptom_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MedCompanion AI", version="2.0.0")
memory = MemorySaver()
graph = build_graph(memory)

# ── Static files ──
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/app")
async def serve_app():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
        "supabase": bool(os.getenv("SUPABASE_URL")),
    }

# ══════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════

class StartRequest(BaseModel):
    raw_input: str
    image_data: Optional[str] = None        # base64 encoded
    image_media_type: Optional[str] = None  # e.g. "image/jpeg"
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

# ══════════════════════════════════════
# AUTH ENDPOINTS (Supabase)
# ══════════════════════════════════════

@app.post("/auth/signup")
async def signup(req: AuthRequest):
    sb = get_supabase()
    if not sb:
        raise HTTPException(503, "Auth service not configured")
    try:
        result = sb.auth.sign_up({"email": req.email, "password": req.password})
        return {"status": "success", "user_id": result.user.id if result.user else None}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/auth/login")
async def login(req: AuthRequest):
    sb = get_supabase()
    if not sb:
        raise HTTPException(503, "Auth service not configured")
    try:
        result = sb.auth.sign_in_with_password({"email": req.email, "password": req.password})
        return {
            "status": "success",
            "access_token": result.session.access_token if result.session else None,
            "user_id": result.user.id if result.user else None,
        }
    except Exception as e:
        raise HTTPException(401, "Invalid credentials")

# ══════════════════════════════════════
# PIPELINE ENDPOINTS
# ══════════════════════════════════════

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
    }

    try:
        result = graph.invoke(initial_state, config, interrupt_before=["confirmation"])

        guardrail = result.get("guardrail_status", "pass")
        if guardrail in ("emergency", "crisis", "off_topic", "invalid"):
            return {
                "status": guardrail,
                "guardrail_message": result.get("guardrail_message", ""),
            }
        if result.get("error"):
            return {"status": "error", "error": result["error"]}

        response = {
            "status": "awaiting_confirmation",
            "thread_id": thread_id,
            "extraction": result.get("extraction", {}),
            "normalization": result.get("normalization", {}),
        }

        # Include image analysis if image was uploaded
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
        state = graph.get_state(config)
        if not state:
            raise HTTPException(404, "Session not found")

        updates = {"confirmed": req.confirmed}
        if req.override:
            updates["final_condition"] = req.override
            updates["confirmed"] = True

        graph.update_state(config, updates, as_node="confirmation")
        result = graph.invoke(None, config)

        if result.get("error"):
            return {"status": "error", "error": result["error"]}

        briefing = result.get("briefing")

        # ── Save to Supabase if user is logged in ──
        if req.user_id and briefing:
            norm = result.get("normalization", {})
            await save_session(
                user_id=req.user_id,
                raw_input=result.get("raw_input", ""),
                condition=norm.get("primary_condition", ""),
                briefing=briefing,
            )

        return {"status": "complete", "briefing": briefing}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"session_confirm error: {e}")
        raise HTTPException(500, str(e))


# ══════════════════════════════════════
# VISION ENDPOINT (standalone)
# ══════════════════════════════════════

@app.post("/analyze/image")
async def analyze_image(req: StartRequest):
    """Analyze a medical image without running the full pipeline."""
    if not req.image_data:
        raise HTTPException(400, "No image provided")

    from .nodes.vision_node import vision_node
    state = {
        "raw_input": req.raw_input or "Please analyze this image",
        "image_data": req.image_data,
        "image_media_type": req.image_media_type or "image/jpeg",
    }
    result = vision_node(state)
    return {"status": "complete", "image_analysis": result.get("image_analysis")}


# ══════════════════════════════════════
# USER DATA ENDPOINTS
# ══════════════════════════════════════

@app.get("/user/{user_id}/history")
async def user_history(user_id: str):
    history = await get_user_history(user_id)
    return {"status": "ok", "history": history}

@app.get("/user/{user_id}/symptoms")
async def user_symptoms(user_id: str):
    symptoms = await get_symptom_history(user_id)
    return {"status": "ok", "symptoms": symptoms}

@app.post("/user/symptoms/log")
async def log_symptom_entry(req: SymptomLogRequest):
    success = await log_symptom(req.user_id, req.symptom, req.severity, req.notes or "")
    return {"status": "ok" if success else "error"}


# ══════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════

@app.get("/session/{thread_id}/state")
async def session_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        return {"status": "ok", "state": state.values if state else {}}
    except Exception as e:
        raise HTTPException(500, str(e))
