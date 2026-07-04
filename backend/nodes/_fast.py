"""
_fast.py — model tiering with a safe fallback.

Mechanical pipeline steps (extraction, normalization) don't need the top
model. Run them on a fast model to cut the wait. If the fast model isn't
available for any reason, we permanently fall back to the strong model for
this process — so nothing ever breaks.

NEVER use this for safety-critical steps (guardrail) or the final medical
briefing — those stay on the strong model.
"""
import os
import logging

logger = logging.getLogger(__name__)

FAST_MODEL = os.getenv("FAST_MODEL", "claude-haiku-4-5-20251001")
STRONG_MODEL = os.getenv("STRONG_MODEL", "claude-sonnet-4-6")

_fast_enabled = [True]


def fast_create(client, **kwargs):
    """messages.create() on the fast model, with automatic fallback to strong."""
    if _fast_enabled[0]:
        try:
            return client.messages.create(model=FAST_MODEL, **kwargs)
        except Exception as e:
            logger.warning(f"fast model '{FAST_MODEL}' unavailable ({e}); falling back to '{STRONG_MODEL}'")
            _fast_enabled[0] = False
    return client.messages.create(model=STRONG_MODEL, **kwargs)
