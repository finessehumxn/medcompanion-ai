from dotenv import load_dotenv
load_dotenv()
"""
graph.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€
Assembles and compiles the complete MedBrief LangGraph StateGraph.

Full pipeline with guardrail node:

  START
    â”‚
    â–¼
  guardrail_node â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚                                                 â”‚
    â”‚ (pass)           (emergency)  â”€â”€â–º emergency_handler â”€â”€â–º END
    â”‚                  (crisis)     â”€â”€â–º crisis_handler    â”€â”€â–º END
    â”‚                  (off_topic)  â”€â”€â–º off_topic_handler â”€â”€â–º END
    â”‚                  (invalid)    â”€â”€â–º invalid_handler   â”€â”€â–º END
    â–¼
  extraction_node â”€â”€â”€â”€ (error) â”€â”€â–º error_handler â”€â”€â–º END
    â”‚
    â–¼
  normalization_node â”€â”€ (error) â”€â”€â–º error_handler â”€â”€â–º END
    â”‚
    â”‚   â—„â”€â”€â”€ LangGraph interrupt_before=["confirmation"] â”€â”€â”€â–º
    â”‚         State checkpointed to MemorySaver here.
    â”‚         Graph pauses. API returns to frontend.
    â”‚         Graph resumes after POST /session/{id}/confirm.
    â–¼
  confirmation_node   (human-in-the-loop via interrupt())
    â”‚
    â–¼
  briefing_node â”€â”€â”€â”€ (error) â”€â”€â–º error_handler â”€â”€â–º END
    â”‚
    â–¼
   END

Key LangGraph concepts:
  StateGraph       â€” typed state machine with merge-based updates
  MemorySaver      â€” in-memory checkpoint store (swap for Redis in production)
  interrupt_before â€” pauses graph before the named node, saves state
  Command(resume)  â€” resumes a paused graph with user-provided data
  conditional_edges â€” runtime routing based on state values
"""

import logging
from langgraph.graph             import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import PatientState
from .nodes.guardrail_node     import guardrail_node
from .nodes.extraction_node    import extraction_node
from .nodes.normalization_node import normalization_node
from .nodes.confirmation_node  import confirmation_node
from .nodes.briefing_node      import briefing_node

logger = logging.getLogger(__name__)


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
# TERMINAL HANDLER NODES
# These nodes write a final message to state and route to END.
# They do not call the LLM â€” they are purely structural.
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

def emergency_handler(state: PatientState) -> dict:
    """Patient described an active medical emergency. Directs to 911/ER."""
    logger.warning("Guardrail: emergency detected, routing to emergency_handler")
    return {
        "current_node":      "emergency_handler",
        "guardrail_message": state.get("guardrail_message") or (
            "This sounds like it could be a medical emergency. "
            "Please call 911 or go to your nearest emergency room right away. "
            "Don't wait â€” your safety comes first."
        ),
    }


def crisis_handler(state: PatientState) -> dict:
    """Patient expressed suicidal ideation or self-harm. Provides crisis resources."""
    logger.warning("Guardrail: crisis signals detected, routing to crisis_handler")
    return {
        "current_node":      "crisis_handler",
        "guardrail_message": state.get("guardrail_message") or (
            "It sounds like you might be going through something really difficult right now. "
            "Please know that you matter and help is available. "
            "Reach out to the 988 Suicide and Crisis Lifeline â€” "
            "just call or text 988, any time of day or night. "
            "You don't have to face this alone."
        ),
    }


def off_topic_handler(state: PatientState) -> dict:
    """Input was unrelated to health. Gently redirects."""
    logger.info("Guardrail: off-topic input, routing to off_topic_handler")
    return {
        "current_node":      "off_topic_handler",
        "guardrail_message": state.get("guardrail_message") or (
            "I'm here specifically to help with health and medical questions. "
            "Feel free to share anything you've been experiencing â€” symptoms, "
            "something a doctor told you, or even just a concern you have "
            "about how you're feeling."
        ),
    }


def invalid_handler(state: PatientState) -> dict:
    """Input was too short or unreadable. Asks for more detail."""
    logger.info("Guardrail: invalid/too-short input, routing to invalid_handler")
    return {
        "current_node":      "invalid_handler",
        "guardrail_message": state.get("guardrail_message") or (
            "Could you tell me a little more about what you've been experiencing? "
            "Even just a few words about how you're feeling or what your doctor said "
            "is a great place to start â€” I'm here to help."
        ),
    }


def error_handler(state: PatientState) -> dict:
    """Catches errors from any pipeline node. Ensures clean termination."""
    logger.error(f"Pipeline error caught by error_handler: {state.get('error')}")
    return {
        "current_node": "error_handler",
    }


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
# CONDITIONAL ROUTING FUNCTIONS
# Return the name of the next node based on current state.
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

def route_after_guardrail(state: PatientState) -> str:
    """Fan-out from guardrail to appropriate handler or extraction."""
    status = state.get("guardrail_status", "pass")
    route_map = {
        "pass":      "extraction",
        "emergency": "emergency_handler",
        "crisis":    "crisis_handler",
        "off_topic": "off_topic_handler",
        "invalid":   "invalid_handler",
    }
    destination = route_map.get(status, "extraction")
    logger.info(f"Guardrail routing: status='{status}' â†’ '{destination}'")
    return destination


def route_after_extraction(state: PatientState) -> str:
    """Route to error_handler if extraction failed, else continue."""
    if state.get("error"):
        logger.warning("Routing to error_handler after extraction failure")
        return "error_handler"
    return "normalization"


def route_after_normalization(state: PatientState) -> str:
    """Route to error_handler if normalization failed, else continue."""
    if state.get("error"):
        logger.warning("Routing to error_handler after normalization failure")
        return "error_handler"
    return "confirmation"


def route_after_briefing(state: PatientState) -> str:
    """Route to error_handler if briefing failed, else END."""
    if state.get("error"):
        logger.warning("Routing to error_handler after briefing failure")
        return "error_handler"
    return END


# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
# GRAPH ASSEMBLY
# â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

def build_graph():
    """
    Builds and compiles the MedBrief StateGraph.

    Returns a compiled LangGraph graph ready for invocation.
    Requires a thread_id in the config dict for checkpointing to work:

        config = {"configurable": {"thread_id": "some-uuid"}}

        # First call â€” runs until interrupt (extraction + normalization done)
        state = graph.invoke({"raw_input": "..."}, config=config)

        # Second call â€” resume after user confirmation
        from langgraph.types import Command
        state = graph.invoke(
            Command(resume={"confirmed": True, "override": ""}),
            config=config
        )

    In production, replace MemorySaver with a persistent checkpointer:
        from langgraph.checkpoint.postgres import PostgresSaver
        checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    """
    builder = StateGraph(PatientState)

    # â”€â”€ Register all nodes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    builder.add_node("guardrail",         guardrail_node)
    builder.add_node("extraction",        extraction_node)
    builder.add_node("normalization",     normalization_node)
    builder.add_node("confirmation",      confirmation_node)
    builder.add_node("briefing",          briefing_node)
    builder.add_node("emergency_handler", emergency_handler)
    builder.add_node("crisis_handler",    crisis_handler)
    builder.add_node("off_topic_handler", off_topic_handler)
    builder.add_node("invalid_handler",   invalid_handler)
    builder.add_node("error_handler",     error_handler)

    # â”€â”€ Entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    builder.add_edge(START, "guardrail")

    # â”€â”€ Guardrail fan-out â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    builder.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "extraction":        "extraction",
            "emergency_handler": "emergency_handler",
            "crisis_handler":    "crisis_handler",
            "off_topic_handler": "off_topic_handler",
            "invalid_handler":   "invalid_handler",
        }
    )

    # â”€â”€ Main pipeline with error routing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    builder.add_conditional_edges(
        "extraction",
        route_after_extraction,
        {"normalization": "normalization", "error_handler": "error_handler"}
    )
    builder.add_conditional_edges(
        "normalization",
        route_after_normalization,
        {"confirmation": "confirmation", "error_handler": "error_handler"}
    )
    builder.add_conditional_edges(
        "briefing",
        route_after_briefing,
        {END: END, "error_handler": "error_handler"}
    )

    # â”€â”€ Linear terminal edges â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    builder.add_edge("confirmation",      "briefing")
    builder.add_edge("emergency_handler", END)
    builder.add_edge("crisis_handler",    END)
    builder.add_edge("off_topic_handler", END)
    builder.add_edge("invalid_handler",   END)
    builder.add_edge("error_handler",     END)

    # â”€â”€ Compile with MemorySaver for interrupt/resume support â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    memory = MemorySaver()
    compiled = builder.compile(
        checkpointer=memory,
        interrupt_before=["confirmation"]   # Pause BEFORE confirmation node
    )

    logger.info("MedBrief LangGraph compiled successfully")
    return compiled


# Module-level singleton â€” imported by server.py
graph = build_graph()

