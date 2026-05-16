from dotenv import load_dotenv
load_dotenv()
"""
server.py
──────────
FastAPI application exposing the MedBrief LangGraph pipeline via REST.

Endpoints
─────────
POST /session/start
    Accepts raw patient input. Runs guardrail → extraction → normalization.
    If guardrail blocks, returns immediately with the guardrail message.
    If guardrail passes, graph runs until the interrupt checkpoint and returns
    the extraction + normalization results for the frontend confirmation card.

POST /session/{thread_id}/confirm
    Resumes the paused graph after the patient confirms or overrides the
    identified condition. Runs the briefing node and returns the full briefing.

GET  /session/{thread_id}/state
    Debug endpoint. Returns the raw LangGraph state snapshot for a thread.
    Useful during development to inspect exactly what each node wrote.

GET  /health
    Simple health check. Returns {"status": "ok"}.

GET  /app (static)
    Serves the frontend index.html from the /frontend directory.

How the human-in-the-loop cycle works
──────────────────────────────────────
1. POST /session/start → graph runs → hits interrupt → returns state snapshot
2. Frontend renders confirmation card from state["normalization"]
3. Patient taps "Yes" or types their own condition
4. POST /session/{thread_id}/confirm → graph resumes → briefing generated
5. Frontend renders full briefing from response["briefing"]
"""

import uuid
import logging
import os
from fastapi                     import FastAPI, HTTPException
from fastapi.middleware.cors     import CORSMiddleware
from fastapi.staticfiles         import StaticFiles
from pydantic                    import BaseModel
from typing                      import Optional
from langgraph.types             import Command

from .graph import graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MedBrief API", version="1.0.0", description="Patient health briefing pipeline")

# ── CORS ──────────────────────────────────────────────────────────────────
# Allow all origins during development.
# In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static frontend ───────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REQUEST / RESPONSE MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StartRequest(BaseModel):
    raw_input: str                       # The patient's free-text input


class ConfirmRequest(BaseModel):
    confirmed: bool = True               # True = use AI-identified condition
    override: Optional[str] = None       # Non-null = patient's own condition name


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER: BUILD LANGGRAPH CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _config(thread_id: str) -> dict:
    """Produce the LangGraph invocation config for a given thread."""
    return {"configurable": {"thread_id": thread_id}}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER: SHAPE THE API RESPONSE
# Translates raw LangGraph state into the structured dict the frontend expects.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _shape_response(state: dict, thread_id: str) -> dict:
    """
    Determines the response shape based on the current graph state.

    Possible statuses returned to the frontend:
      "emergency"             — guardrail detected active medical emergency
      "crisis"                — guardrail detected crisis / self-harm signals
      "off_topic"             — guardrail detected non-health content
      "invalid"               — guardrail detected unreadable/too-short input
      "error"                 — a pipeline node encountered an unrecoverable error
      "awaiting_confirmation" — graph paused, normalization done, waiting for user
      "complete"              — briefing generated, pipeline finished
    """

    # ── Guardrail blocked the request ────────────────────────────────────
    guardrail_status = state.get("guardrail_status", "pass")
    if guardrail_status in ("emergency", "crisis", "off_topic", "invalid"):
        return {
            "thread_id":         thread_id,
            "status":            guardrail_status,
            "guardrail_message": state.get("guardrail_message", ""),
        }

    # ── Pipeline error ────────────────────────────────────────────────────
    if state.get("error"):
        return {
            "thread_id": thread_id,
            "status":    "error",
            "error":     state.get("error", "An unexpected error occurred."),
        }

    # ── Extraction result block (shared between awaiting and complete) ────
    extraction_block = {
        "symptoms":          state.get("symptoms",          []),
        "duration":          state.get("duration",          []),
        "severity":          state.get("severity",          []),
        "medications":       state.get("medications",       []),
        "body_parts":        state.get("body_parts",        []),
        "emotional_context": state.get("emotional_context", []),
    }

    # ── Normalization result block (shared between awaiting and complete) ─
    normalization_block = {
        "term_mappings":        state.get("term_mappings",        []),
        "primary_condition":    state.get("primary_condition",    ""),
        "plain_condition_name": state.get("plain_condition_name", ""),
        "icd_code":             state.get("icd_code",             ""),
        "confidence":           state.get("confidence",           ""),
        "plain_reason":         state.get("plain_reason",         ""),
        "alternate_conditions": state.get("alternate_conditions", []),
    }

    # ── Complete — briefing is ready ──────────────────────────────────────
    if state.get("briefing"):
        return {
            "thread_id":      thread_id,
            "status":         "complete",
            "extraction":     extraction_block,
            "normalization":  normalization_block,
            "final_condition": state.get("final_condition", ""),
            "briefing":       state.get("briefing"),
        }

    # ── Awaiting confirmation — graph paused at interrupt ─────────────────
    return {
        "thread_id":     thread_id,
        "status":        "awaiting_confirmation",
        "extraction":    extraction_block,
        "normalization": normalization_block,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/session/start")
def start_session(body: StartRequest):
    """
    Start a new pipeline session.

    Runs: guardrail → extraction → normalization → [interrupt]

    Returns immediately with guardrail_message if guardrail blocks.
    Otherwise returns extraction + normalization results and a thread_id
    the frontend uses to resume after confirmation.
    """
    if not body.raw_input or not body.raw_input.strip():
        raise HTTPException(status_code=400, detail="raw_input cannot be empty.")

    thread_id = str(uuid.uuid4())
    config    = _config(thread_id)

    logger.info(f"Starting session {thread_id} | input_length={len(body.raw_input)}")

    initial_state = {
        "raw_input":        body.raw_input.strip(),
        "current_node":     "start",
        "error":            None,
        "thread_id":        thread_id,
        # Pre-populate list fields so state is always valid
        "symptoms":          [],
        "duration":          [],
        "severity":          [],
        "medications":       [],
        "body_parts":        [],
        "emotional_context": [],
        "term_mappings":     [],
        "alternate_conditions": [],
    }

    state = graph.invoke(initial_state, config=config)
    return _shape_response(state, thread_id)


@app.post("/session/{thread_id}/confirm")
def confirm_condition(thread_id: str, body: ConfirmRequest):
    """
    Resume a paused pipeline session after the patient confirms the condition.

    Runs: confirmation_node → briefing_node → END

    The patient either confirmed the AI-identified condition (confirmed=True)
    or provided their own correction (override="condition name").

    Returns the full briefing on success.
    """
    config = _config(thread_id)

    # Verify the session exists and is still paused
    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{thread_id}' not found or has already completed."
        )

    logger.info(
        f"Resuming session {thread_id} | "
        f"confirmed={body.confirmed}, override='{body.override or ''}'"
    )

    resume_payload = {
        "confirmed": body.confirmed,
        "override":  (body.override or "").strip(),
    }

    state = graph.invoke(Command(resume=resume_payload), config=config)
    return _shape_response(state, thread_id)


@app.get("/session/{thread_id}/state")
def get_session_state(thread_id: str):
    """
    Debug endpoint. Returns the raw LangGraph state snapshot for a thread.
    Use this during development to inspect what each node wrote to state.
    """
    config   = _config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Session '{thread_id}' not found.")

    return {
        "thread_id": thread_id,
        "values":    snapshot.values,
        "next":      list(snapshot.next),
        "metadata":  snapshot.metadata,
    }


@app.get("/health")
def health_check():
    """Simple health check for load balancers and uptime monitors."""
    return {"status": "ok", "service": "MedBrief API", "version": "1.0.0"}
