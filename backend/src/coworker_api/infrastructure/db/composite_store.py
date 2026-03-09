"""
Composite Memory Store — Redis (fast) + PostgreSQL (persistent).

Writes to both stores on every save. Reads from Redis first (cache),
falls back to PostgreSQL if the session expired from Redis.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from coworker_api.domain.models import Conversation
from coworker_api.domain.ports import MemoryPort
from coworker_api.infrastructure.db.memory_store import RedisMemoryStore
from coworker_api.infrastructure.db.postgres_store import PostgresConversationStore

logger = logging.getLogger(__name__)


class CompositeMemoryStore(MemoryPort):
    """
    Dual-write memory store:
    - Redis: fast, ephemeral cache (TTL-based)
    - PostgreSQL: durable, long-term storage

    Read strategy: Redis first → fallback to PostgreSQL.
    Write strategy: write to both simultaneously.
    """

    def __init__(
        self,
        redis_store: RedisMemoryStore,
        postgres_store: PostgresConversationStore,
    ):
        self._redis = redis_store
        self._postgres = postgres_store

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save to both Redis (cache) and PostgreSQL (persistent)."""
        # Write to Redis (fast, for active sessions)
        await self._redis.save_conversation(conversation)

        # Write to PostgreSQL (durable, for history)
        try:
            await self._postgres.save_conversation(conversation)
        except Exception:
            logger.error(
                "Failed to save to PostgreSQL (Redis still has data)",
                exc_info=True,
            )

    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """Load from Redis first; if expired, try PostgreSQL."""
        # Try Redis first (fast path)
        conversation = await self._redis.load_conversation(session_id)
        if conversation is not None:
            return conversation

        # Fallback to PostgreSQL
        logger.info(
            "Session not in Redis, loading from PostgreSQL",
            extra={"session_id": session_id},
        )
        conversation = await self._postgres.load_conversation(session_id)

        # Re-cache in Redis if found in PostgreSQL
        if conversation is not None:
            try:
                await self._redis.save_conversation(conversation)
            except Exception:
                logger.warning("Failed to re-cache conversation in Redis", exc_info=True)

        return conversation

    async def delete_conversation(self, session_id: str) -> bool:
        """Delete from both stores."""
        redis_deleted = await self._redis.delete_conversation(session_id)

        try:
            pg_deleted = await self._postgres.delete_conversation(session_id)
        except Exception:
            logger.error("Failed to delete from PostgreSQL", exc_info=True)
            pg_deleted = False

        return redis_deleted or pg_deleted

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """List from PostgreSQL (complete history, not just cached)."""
        try:
            return await self._postgres.list_conversations(user_id)
        except Exception:
            logger.error(
                "Failed to list from PostgreSQL, falling back to Redis",
                exc_info=True,
            )
            return await self._redis.list_conversations(user_id)

    async def close(self) -> None:
        """Close both stores."""
        await self._redis.close()
        await self._postgres.close()
