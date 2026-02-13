"""
Session Manager — State Orchestrator.

Centralizes the management of session state and memory persistence.
Abstracts the MemoryPort operations (load/save) and ensures data
consistency for the Conversation model.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from coworker_api.domain.models import Conversation, NPC, Speaker
from coworker_api.domain.exceptions import ConversationNotFoundError
from coworker_api.domain.ports import MemoryPort
from coworker_api.domain.memory.schemas import MemoryState

logger = logging.getLogger(__name__)


class SessionManager:
    """Orchestrates MemoryPort to load/save Conversation objects."""

    def __init__(self, memory_port: MemoryPort):
        self._memory = memory_port

    async def create_session(
        self,
        user_id: str,
        npc: NPC,
        scenario_id: str | None = None,
    ) -> Conversation:
        """Create a new conversation session and persist it."""
        conversation = Conversation(
            user_id=user_id,
            npc=npc,
        )
        await self._memory.save_conversation(conversation)
        logger.info(
            "Session created",
            extra={"session_id": conversation.id, "user_id": user_id, "npc": npc.name},
        )
        return conversation

    async def load_session(self, session_id: str) -> Conversation:
        """
        Load a conversation by session ID.

        Raises:
            ConversationNotFoundError: If the session does not exist.
        """
        conversation = await self._memory.load_conversation(session_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Session '{session_id}' not found."
            )
        return conversation

    async def save_session(self, conversation: Conversation) -> None:
        """Persist the current state of a conversation."""
        await self._memory.save_conversation(conversation)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted."""
        deleted = await self._memory.delete_conversation(session_id)
        if deleted:
            logger.info("Session deleted", extra={"session_id": session_id})
        return deleted

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all sessions for a given user."""
        return await self._memory.list_conversations(user_id)

    async def add_turn_to_session(
        self,
        session_id: str,
        speaker: Speaker,
        content: str,
        metadata: dict | None = None,
    ) -> Conversation:
        """Load session, add a turn, save, and return the updated conversation."""
        conversation = await self.load_session(session_id)
        conversation.add_turn(speaker=speaker, content=content, metadata=metadata)
        await self.save_session(conversation)
        return conversation
