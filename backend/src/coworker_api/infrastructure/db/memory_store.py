"""
Redis Memory Store — Implements MemoryPort.

Stores conversation state in Redis with JSON serialization and TTL.
Used for fast, ephemeral session storage.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from coworker_api.domain.models import Conversation
from coworker_api.domain.ports import MemoryPort
from coworker_api.domain.exceptions import MemoryStoreError

logger = logging.getLogger(__name__)


class RedisMemoryStore(MemoryPort):
    """Redis-backed implementation of the MemoryPort interface."""

    KEY_PREFIX = "session"

    def __init__(self, redis_url: str, session_ttl: int = 1800):
        self._redis_url = redis_url
        self._session_ttl = session_ttl
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Lazy-initialize the Redis client."""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                )
            except Exception as e:
                raise MemoryStoreError(f"Failed to connect to Redis: {e}") from e
        return self._client

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}:{session_id}"

    def _user_index_key(self, user_id: str) -> str:
        return f"user_sessions:{user_id}"

    async def save_conversation(self, conversation: Conversation) -> None:
        """Persist the full conversation state to Redis as JSON."""
        client = await self._get_client()
        try:
            data = conversation.model_dump_json()
            pipe = client.pipeline()
            pipe.set(self._key(conversation.id), data, ex=self._session_ttl)
            # Add to user index set
            pipe.sadd(self._user_index_key(conversation.user_id), conversation.id)
            await pipe.execute()
        except Exception as e:
            logger.error("Failed to save conversation", exc_info=True)
            raise MemoryStoreError(f"Failed to save conversation: {e}") from e

    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """Load a conversation by session ID from Redis."""
        client = await self._get_client()
        try:
            data = await client.get(self._key(session_id))
            if data is None:
                return None
            return Conversation.model_validate_json(data)
        except Exception as e:
            logger.error("Failed to load conversation", exc_info=True)
            raise MemoryStoreError(f"Failed to load conversation: {e}") from e

    async def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation from Redis."""
        client = await self._get_client()
        try:
            deleted = await client.delete(self._key(session_id))
            return deleted > 0
        except Exception as e:
            logger.error("Failed to delete conversation", exc_info=True)
            raise MemoryStoreError(f"Failed to delete conversation: {e}") from e

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """List conversation summaries for a user."""
        client = await self._get_client()
        try:
            session_ids = await client.smembers(self._user_index_key(user_id))
            summaries = []
            for sid in session_ids:
                data = await client.get(self._key(sid))
                if data:
                    conv = Conversation.model_validate_json(data)
                    summaries.append({
                        "id": conv.id,
                        "npc_name": conv.npc.name,
                        "status": conv.status.value,
                        "turn_count": conv.turn_count,
                        "started_at": conv.started_at.isoformat(),
                    })
            return summaries
        except Exception as e:
            logger.error("Failed to list conversations", exc_info=True)
            raise MemoryStoreError(f"Failed to list conversations: {e}") from e

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
