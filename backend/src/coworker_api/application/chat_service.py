"""
Chat Service - Core interaction handler.

This service orchestrates one chat turn and emits agent-graph tracing nodes:
director -> rag -> npc -> (optional) tool.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, AsyncIterator, Optional

from coworker_api.application.session_manager import SessionManager
from coworker_api.domain.models import Conversation, Speaker
from coworker_api.domain.ports import LLMPort, RetrieverPort
from coworker_api.domain.prompts import get_persona_prompt
from coworker_api.infrastructure.monitoring.tracing import (
    end_trace,
    finish_observation,
    flush,
    get_observation_id,
    get_trace_id,
    start_chat_trace,
    start_director_node,
    start_npc_node,
    start_rag_node,
    update_chat_trace,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Handles user <-> NPC message processing."""

    def __init__(
        self,
        session_manager: SessionManager,
        llm_port: LLMPort,
        retriever_port: Optional[RetrieverPort] = None,
    ):
        self._session_manager = session_manager
        self._llm = llm_port
        self._retriever = retriever_port

    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        *,
        use_rag: bool = True,
    ) -> AsyncIterator[str]:
        """Stream NPC response chunks."""
        conversation = await self._session_manager.load_session(session_id)
        persona_id = conversation.npc.name

        # For streaming, we still want to log the start of the trace
        trace = start_chat_trace(
            session_id=session_id,
            user_id=conversation.user_id,
            persona_id=persona_id,
            metadata={
                "message_length": len(user_message),
                "requested_rag": use_rag,
                "streaming": True,
            },
            input_text=user_message,
        )

        try:
            conversation.add_turn(speaker=Speaker.USER, content=user_message)

            rag_context = ""
            if use_rag and self._retriever:
                rag_context, _ = await self._retrieve_context_with_docs(user_message)

            prompt = self._build_prompt(conversation, rag_context)
            system_prompt = get_persona_prompt(persona_id)

            full_response = []
            async for chunk in self._llm.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
            ):
                full_response.append(chunk)
                yield chunk

            # After streaming finished, save the turn
            npc_response = "".join(full_response)
            npc_turn = conversation.add_turn(
                speaker=Speaker.NPC,
                content=npc_response,
                metadata={"rag_used": bool(rag_context), "streaming": True},
            )
            await self._session_manager.save_session(conversation)

            update_chat_trace(
                trace,
                output={
                    "final_response": npc_response,
                    "turn_number": npc_turn.turn_number,
                },
                metadata={"status": "success"},
            )
        except Exception as e:
            update_chat_trace(trace, metadata={"status": "error", "error": str(e)})
            logger.exception("Streaming error")
            yield f"Error: {str(e)}"
        finally:
            end_trace(trace)
            flush()

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        *,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        """Process one user message and return NPC response."""
        conversation = await self._session_manager.load_session(session_id)
        persona_id = conversation.npc.name

        trace = start_chat_trace(
            session_id=session_id,
            user_id=conversation.user_id,
            persona_id=persona_id,
            metadata={
                "message_length": len(user_message),
                "requested_rag": use_rag,
            },
            tags=[f"rag:{'on' if use_rag else 'off'}"],
            input_text=user_message,
        )

        director_obs = None
        rag_obs = None
        npc_obs = None

        try:
            director_start = perf_counter()
            director_obs = start_director_node(
                trace,
                input_text=user_message,
                metadata={"session_id": session_id, "persona_id": persona_id},
            )
            director_decision = {
                "use_rag": bool(use_rag and self._retriever),
                "retriever_available": bool(self._retriever),
                "persona_id": persona_id,
                "turn_before": conversation.turn_count,
            }
            director_duration_ms = self._duration_ms(director_start)
            finish_observation(
                director_obs,
                output=director_decision,
                metadata={"duration_ms": director_duration_ms, "layer": "director"},
            )
            self._log_step(
                "director_decision",
                trace=trace,
                observation=director_obs,
                session_id=session_id,
                persona_id=persona_id,
                layer="director",
                duration_ms=director_duration_ms,
            )

            conversation.add_turn(speaker=Speaker.USER, content=user_message)

            rag_context = ""
            rag_docs_for_trace: list[dict[str, Any]] = []
            if director_decision["use_rag"]:
                rag_start = perf_counter()
                rag_obs = start_rag_node(
                    director_obs or trace,
                    query=user_message,
                    metadata={"session_id": session_id, "persona_id": persona_id},
                )
                rag_context, rag_docs_for_trace = await self._retrieve_context_with_docs(
                    user_message
                )
                rag_duration_ms = self._duration_ms(rag_start)
                finish_observation(
                    rag_obs,
                    output={"docs": rag_docs_for_trace},
                    metadata={
                        "duration_ms": rag_duration_ms,
                        "doc_count": len(rag_docs_for_trace),
                        "layer": "rag",
                    },
                )
                self._log_step(
                    "rag_retrieval",
                    trace=trace,
                    observation=rag_obs,
                    session_id=session_id,
                    persona_id=persona_id,
                    layer="rag",
                    duration_ms=rag_duration_ms,
                    doc_count=len(rag_docs_for_trace),
                )

            prompt = self._build_prompt(conversation, rag_context)
            system_prompt = get_persona_prompt(persona_id)

            npc_start = perf_counter()
            npc_obs = start_npc_node(
                rag_obs or director_obs or trace,
                persona_id=persona_id,
                prompt=prompt,
                metadata={"session_id": session_id, "persona_id": persona_id},
            )

            npc_response = await self._llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            npc_duration_ms = self._duration_ms(npc_start)
            finish_observation(
                npc_obs,
                output=npc_response,
                metadata={
                    "duration_ms": npc_duration_ms,
                    "prompt_length": len(prompt),
                    "response_length": len(npc_response),
                    "layer": "npc",
                },
            )
            self._log_step(
                "npc_response",
                trace=trace,
                observation=npc_obs,
                session_id=session_id,
                persona_id=persona_id,
                layer="npc",
                duration_ms=npc_duration_ms,
                response_length=len(npc_response),
            )

            npc_turn = conversation.add_turn(
                speaker=Speaker.NPC,
                content=npc_response,
                metadata={"rag_used": bool(rag_context)},
            )
            await self._session_manager.save_session(conversation)

            update_chat_trace(
                trace,
                output={
                    "final_response": npc_response,
                    "turn_number": npc_turn.turn_number,
                },
                metadata={
                    "status": "success",
                    "rag_used": bool(rag_context),
                    "turn_number": npc_turn.turn_number,
                },
            )

            return {
                "response": npc_response,
                "turn_number": npc_turn.turn_number,
                "session_id": session_id,
            }
        except Exception as e:
            finish_observation(
                npc_obs,
                output={"error": str(e)},
                metadata={"layer": "npc"},
                level="ERROR",
                status_message=str(e),
            )
            finish_observation(
                rag_obs,
                output={"error": str(e)},
                metadata={"layer": "rag"},
                level="ERROR",
                status_message=str(e),
            )
            finish_observation(
                director_obs,
                output={"error": str(e)},
                metadata={"layer": "director"},
                level="ERROR",
                status_message=str(e),
            )
            update_chat_trace(
                trace,
                metadata={"status": "error", "error": str(e)},
            )
            raise
        finally:
            end_trace(trace)
            flush()

    async def _retrieve_context_with_docs(self, query: str) -> tuple[str, list[dict[str, Any]]]:
        """Retrieve documents and return both joined context and compact doc metadata."""
        if not self._retriever:
            return "", []

        results = await self._retriever.retrieve(query, top_k=3)
        if not results:
            return "", []

        context_parts: list[str] = []
        docs_for_trace: list[dict[str, Any]] = []

        for idx, doc in enumerate(results):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {}) or {}
            score = doc.get("score")
            context_parts.append(content)

            docs_for_trace.append(
                {
                    "id": metadata.get("document_id") or metadata.get("id") or f"doc-{idx}",
                    "score": score,
                    "source": metadata.get("source"),
                }
            )

        return "\n---\n".join(context_parts), docs_for_trace

    def _build_prompt(self, conversation: Conversation, rag_context: str) -> str:
        """Build user prompt from context + history + current input."""
        parts: list[str] = []

        if rag_context:
            parts.append("## Relevant Context")
            parts.append(rag_context)
            parts.append("")

        history_window = conversation.turns[-10:]
        if len(history_window) > 1:
            parts.append("## Conversation History")
            for turn in history_window[:-1]:
                label = turn.speaker.value.capitalize()
                parts.append(f"{label}: {turn.content}")
            parts.append("")

        current_turn = conversation.turns[-1]
        parts.append(f"User: {current_turn.content}")

        return "\n".join(parts)

    @staticmethod
    def _duration_ms(start: float) -> int:
        return int((perf_counter() - start) * 1000)

    @staticmethod
    def _log_step(
        event: str,
        *,
        trace: Any,
        observation: Any,
        session_id: str,
        persona_id: str,
        layer: str,
        duration_ms: int,
        **extra_fields: Any,
    ) -> None:
        logger.info(
            event,
            extra={
                "trace_id": get_trace_id(trace),
                "observation_id": get_observation_id(observation),
                "session_id": session_id,
                "persona_id": persona_id,
                "layer": layer,
                "duration_ms": duration_ms,
                **extra_fields,
            },
        )
