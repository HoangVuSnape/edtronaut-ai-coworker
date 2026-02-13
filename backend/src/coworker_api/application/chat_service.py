"""
Chat Service — Core Interaction Handler.

Use-case: User interacts with an AI NPC. This service orchestrates
the full pipeline: load context → build prompt → call LLM → save state.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from coworker_api.domain.models import Conversation, Speaker, Turn
from coworker_api.domain.ports import LLMPort, RetrieverPort
from coworker_api.domain.prompts import get_persona_prompt, get_persona_few_shots
from coworker_api.domain.memory.schemas import MemoryState
from coworker_api.application.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ChatService:
    """
    Manages the primary use case where a user interacts with an AI NPC.

    Workflow:
        1. Receive user input
        2. Load conversation context via SessionManager
        3. Retrieve relevant RAG context (if applicable)
        4. Construct the prompt using persona templates
        5. Call the LLMPort to generate a response
        6. Save the updated conversation state
        7. Return the NPC response
    """

    def __init__(
        self,
        session_manager: SessionManager,
        llm_port: LLMPort,
        retriever_port: Optional[RetrieverPort] = None,
    ):
        self._session_manager = session_manager
        self._llm = llm_port
        self._retriever = retriever_port

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        *,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        """
        Process a user message and return the NPC response.

        Args:
            session_id: The conversation session ID.
            user_message: The user's input text.
            use_rag: Whether to retrieve RAG context.

        Returns:
            Dict with keys: response, turn_number, session_id.
        """
        # 1. Load conversation
        conversation = await self._session_manager.load_session(session_id)

        # 2. Record user turn
        conversation.add_turn(speaker=Speaker.USER, content=user_message)

        # 3. Retrieve RAG context (if enabled and retriever available)
        rag_context = ""
        if use_rag and self._retriever:
            rag_context = await self._retrieve_context(user_message)

        # 4. Build the prompt
        prompt = self._build_prompt(conversation, rag_context)
        system_prompt = get_persona_prompt(conversation.npc.name)

        # 5. Call LLM
        logger.info(
            "Calling LLM",
            extra={"session_id": session_id, "turn": conversation.turn_count},
        )
        npc_response = await self._llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        # 6. Record NPC turn
        npc_turn = conversation.add_turn(
            speaker=Speaker.NPC,
            content=npc_response,
            metadata={"rag_used": bool(rag_context)},
        )

        # 7. Save state
        await self._session_manager.save_session(conversation)

        return {
            "response": npc_response,
            "turn_number": npc_turn.turn_number,
            "session_id": session_id,
        }

    async def _retrieve_context(self, query: str) -> str:
        """Retrieve relevant documents and format as context string."""
        if not self._retriever:
            return ""

        results = await self._retriever.retrieve(query, top_k=3)
        if not results:
            return ""

        context_parts = []
        for doc in results:
            context_parts.append(doc.get("content", ""))

        return "\n---\n".join(context_parts)

    def _build_prompt(self, conversation: Conversation, rag_context: str) -> str:
        """
        Build the user prompt from conversation history and RAG context.

        Follows the Prompt Sandwich structure:
        [System] → [Knowledge/RAG] → [History] → [Current Input]
        System is handled separately; this builds the user-side content.
        """
        parts: list[str] = []

        # RAG knowledge block
        if rag_context:
            parts.append("## Relevant Context")
            parts.append(rag_context)
            parts.append("")

        # Conversation history (last N turns)
        history_window = conversation.turns[-10:]  # Last 10 turns
        if len(history_window) > 1:  # More than just the current message
            parts.append("## Conversation History")
            for turn in history_window[:-1]:  # Exclude current user message
                label = turn.speaker.value.capitalize()
                parts.append(f"{label}: {turn.content}")
            parts.append("")

        # Current user input
        current_turn = conversation.turns[-1]
        parts.append(f"User: {current_turn.content}")

        return "\n".join(parts)
