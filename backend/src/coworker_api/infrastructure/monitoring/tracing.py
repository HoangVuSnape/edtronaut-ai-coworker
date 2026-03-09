"""Langfuse tracing utilities for agent graph logging."""

from __future__ import annotations

import logging
from typing import Any

from coworker_api.config import get_settings

logger = logging.getLogger(__name__)

_langfuse_client = None


def _get_langfuse():
    """Lazy-initialize the Langfuse client."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    settings = get_settings()

    has_keys = bool(settings.langfuse.public_key and settings.langfuse.secret_key)
    enabled = bool(settings.langfuse.enabled or has_keys)
    if not enabled:
        logger.debug("Langfuse tracing disabled by configuration")
        return None

    if not has_keys:
        logger.warning(
            "Langfuse is enabled but keys are missing (LANGFUSE__PUBLIC_KEY / LANGFUSE__SECRET_KEY)"
        )
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse.public_key,
            secret_key=settings.langfuse.secret_key,
            host=settings.langfuse.host,
        )
        logger.info("Langfuse tracing initialized")
        return _langfuse_client
    except ImportError:
        logger.warning("langfuse package not installed, tracing disabled")
        return None
    except Exception as e:
        logger.warning("Failed to initialize Langfuse: %s", e)
        return None


def _safe_call(obj: Any, method_name: str, **kwargs: Any) -> Any:
    method = getattr(obj, method_name, None)
    if not callable(method):
        return None
    try:
        return method(**kwargs)
    except Exception:
        logger.debug("Langfuse call failed: %s", method_name, exc_info=True)
        return None


def _start_observation(
    *,
    name: str,
    as_type: str,
    input_data: Any = None,
    metadata: dict[str, Any] | None = None,
    parent: Any = None,
):
    """Start an observation/span for a graph node."""
    kwargs = {
        "name": name,
        "input": input_data,
        "metadata": metadata or {},
    }

    target = parent if parent is not None else _get_langfuse()
    if target is None:
        return None

    obs = _safe_call(target, "start_observation", as_type=as_type, **kwargs)
    if obs is not None:
        return obs

    # Fallback to span API if observation API is unavailable.
    obs = _safe_call(target, "start_span", **kwargs)
    return obs


def finish_observation(
    observation: Any,
    *,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
    level: str | None = None,
    status_message: str | None = None,
) -> None:
    """Finish a node and attach output/metadata."""
    if observation is None:
        return

    update_kwargs: dict[str, Any] = {}
    if output is not None:
        update_kwargs["output"] = output
    if metadata:
        update_kwargs["metadata"] = metadata
    if level:
        update_kwargs["level"] = level
    if status_message:
        update_kwargs["status_message"] = status_message

    if update_kwargs:
        _safe_call(observation, "update", **update_kwargs)

    _safe_call(observation, "end")


def start_chat_trace(
    session_id: str,
    user_id: str | None,
    persona_id: str,
    *,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    input_text: str | None = None,
):
    """Create one trace root node per chat turn."""
    settings = get_settings()
    root = _start_observation(
        name="chat_turn",
        as_type="chain",
        input_data=input_text,
        metadata={
            "persona_id": persona_id,
            "layer": "chat_service",
            **(metadata or {}),
        },
    )

    if root is None:
        return None

    env_tag = f"env:{'debug' if settings.debug else 'prod'}"
    trace_tags = [
        f"persona:{persona_id}",
        "layer:chat_service",
        env_tag,
        *(tags or []),
    ]

    _safe_call(
        root,
        "update_trace",
        name="chat_turn",
        session_id=session_id,
        user_id=user_id or None,
        metadata={"persona_id": persona_id, **(metadata or {})},
        tags=trace_tags,
    )

    return root


def update_chat_trace(
    trace: Any,
    *,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Update trace-level output/metadata."""
    if trace is None:
        return

    _safe_call(
        trace,
        "update_trace",
        output=output,
        metadata=metadata or {},
    )


def start_director_node(
    trace: Any,
    *,
    input_text: str,
    metadata: dict[str, Any] | None = None,
):
    return _start_observation(
        parent=trace,
        name="director_decision",
        as_type="agent",
        input_data=input_text,
        metadata={"layer": "director", **(metadata or {})},
    )


def start_rag_node(
    parent_obs: Any,
    *,
    query: str,
    metadata: dict[str, Any] | None = None,
):
    return _start_observation(
        parent=parent_obs,
        name="rag_retrieval",
        as_type="retriever",
        input_data=query,
        metadata={"layer": "rag", **(metadata or {})},
    )


def start_npc_node(
    parent_obs: Any,
    *,
    persona_id: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
):
    return _start_observation(
        parent=parent_obs,
        name=f"npc:{persona_id}",
        as_type="agent",
        input_data=prompt,
        metadata={"layer": "npc", "persona_id": persona_id, **(metadata or {})},
    )


def start_tool_node(
    parent_obs: Any,
    *,
    tool_name: str,
    args: dict[str, Any],
    metadata: dict[str, Any] | None = None,
):
    return _start_observation(
        parent=parent_obs,
        name=f"tool:{tool_name}",
        as_type="tool",
        input_data=args,
        metadata={"layer": "tool", "tool_name": tool_name, **(metadata or {})},
    )


def log_director_node(trace: Any, input_text: str, decision: dict[str, Any]):
    obs = start_director_node(trace, input_text=input_text)
    finish_observation(obs, output=decision)
    return obs


def log_rag_node(trace: Any, parent_obs: Any, query: str, docs: list[dict[str, Any]]):
    obs = start_rag_node(parent_obs or trace, query=query)
    finish_observation(obs, output={"docs": docs})
    return obs


def log_npc_node(
    trace: Any,
    parent_obs: Any,
    persona_id: str,
    prompt: str,
    response: str,
):
    obs = start_npc_node(parent_obs or trace, persona_id=persona_id, prompt=prompt)
    finish_observation(obs, output=response)
    return obs


def log_tool_node(
    trace: Any,
    parent_obs: Any,
    tool_name: str,
    args: dict[str, Any],
    result: dict[str, Any],
):
    obs = start_tool_node(parent_obs or trace, tool_name=tool_name, args=args)
    finish_observation(obs, output=result)
    return obs


def get_trace_id(obj: Any) -> str | None:
    return getattr(obj, "trace_id", None)


def get_observation_id(obj: Any) -> str | None:
    return getattr(obj, "id", None)


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

    _safe_call(
        client,
        "create_score",
        trace_id=trace_id or None,
        name=name,
        value=value,
        comment=comment,
    )


def end_trace(trace: Any) -> None:
    """Close root trace observation/span."""
    if trace is None:
        return
    _safe_call(trace, "end")


def flush() -> None:
    """Flush any pending traces to Langfuse."""
    client = _get_langfuse()
    if client is None:
        return
    _safe_call(client, "flush")

