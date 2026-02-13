"""
LangFuse Tracing — Observability for LLM calls.

Provides decorators and utilities for tracing LLM interactions,
cost tracking, and quality evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from functools import wraps

from coworker_api.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-initialized LangFuse client
_langfuse_client = None


def _get_langfuse():
    """Lazy-initialize the LangFuse client."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    settings = get_settings()
    if not settings.langfuse.enabled:
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse.public_key,
            secret_key=settings.langfuse.secret_key,
            host=settings.langfuse.host,
        )
        logger.info("LangFuse tracing initialized")
        return _langfuse_client
    except ImportError:
        logger.warning("langfuse package not installed, tracing disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize LangFuse: {e}")
        return None


def create_trace(
    name: str,
    *,
    user_id: str = "",
    session_id: str = "",
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
):
    """Create a new LangFuse trace for a user interaction."""
    client = _get_langfuse()
    if client is None:
        return None

    return client.trace(
        name=name,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata or {},
        tags=tags or [],
    )


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: str = "",
) -> None:
    """Score a trace for quality evaluation."""
    client = _get_langfuse()
    if client is None:
        return

    client.score(
        trace_id=trace_id,
        name=name,
        value=value,
        comment=comment,
    )


def flush() -> None:
    """Flush any pending traces to LangFuse."""
    client = _get_langfuse()
    if client is not None:
        client.flush()
