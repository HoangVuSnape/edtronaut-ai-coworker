"""Unit tests for CompositeMemoryStore."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.domain.models import Conversation, NPC
from coworker_api.infrastructure.db.composite_store import CompositeMemoryStore


def _make_conversation() -> Conversation:
    return Conversation(
        id="session-1",
        user_id="user-1",
        npc=NPC(name="gucci_ceo", role_title="CEO"),
    )


def _make_store() -> tuple[CompositeMemoryStore, AsyncMock, AsyncMock]:
    redis = AsyncMock()
    postgres = AsyncMock()
    store = CompositeMemoryStore(redis_store=redis, postgres_store=postgres)
    return store, redis, postgres


class TestSaveConversation:
    @pytest.mark.asyncio
    async def test_saves_to_both_stores(self):
        store, redis, postgres = _make_store()
        conv = _make_conversation()

        await store.save_conversation(conv)

        redis.save_conversation.assert_awaited_once_with(conv)
        postgres.save_conversation.assert_awaited_once_with(conv)

    @pytest.mark.asyncio
    async def test_postgres_failure_does_not_raise(self):
        store, redis, postgres = _make_store()
        postgres.save_conversation.side_effect = RuntimeError("DB down")
        conv = _make_conversation()

        # Should not raise — Redis still has the data
        await store.save_conversation(conv)
        redis.save_conversation.assert_awaited_once()


class TestLoadConversation:
    @pytest.mark.asyncio
    async def test_redis_hit(self):
        store, redis, postgres = _make_store()
        conv = _make_conversation()
        redis.load_conversation.return_value = conv

        result = await store.load_conversation("session-1")

        assert result is conv
        postgres.load_conversation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_miss_falls_back_to_postgres(self):
        store, redis, postgres = _make_store()
        conv = _make_conversation()
        redis.load_conversation.return_value = None
        postgres.load_conversation.return_value = conv

        result = await store.load_conversation("session-1")

        assert result is conv
        # Re-cached in Redis
        redis.save_conversation.assert_awaited_once_with(conv)

    @pytest.mark.asyncio
    async def test_both_miss_returns_none(self):
        store, redis, postgres = _make_store()
        redis.load_conversation.return_value = None
        postgres.load_conversation.return_value = None

        result = await store.load_conversation("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_recache_failure_still_returns_conversation(self):
        store, redis, postgres = _make_store()
        conv = _make_conversation()
        redis.load_conversation.return_value = None
        postgres.load_conversation.return_value = conv
        redis.save_conversation.side_effect = RuntimeError("Redis down")

        result = await store.load_conversation("session-1")

        assert result is conv  # Should still return even if re-cache fails


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_deletes_from_both(self):
        store, redis, postgres = _make_store()
        redis.delete_conversation.return_value = True
        postgres.delete_conversation.return_value = True

        result = await store.delete_conversation("session-1")

        assert result is True
        redis.delete_conversation.assert_awaited_once()
        postgres.delete_conversation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_postgres_failure_returns_redis_result(self):
        store, redis, postgres = _make_store()
        redis.delete_conversation.return_value = True
        postgres.delete_conversation.side_effect = RuntimeError("DB error")

        result = await store.delete_conversation("session-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_both_false_returns_false(self):
        store, redis, postgres = _make_store()
        redis.delete_conversation.return_value = False
        postgres.delete_conversation.return_value = False

        result = await store.delete_conversation("nonexistent")

        assert result is False


class TestListConversations:
    @pytest.mark.asyncio
    async def test_reads_from_postgres(self):
        store, redis, postgres = _make_store()
        postgres.list_conversations.return_value = [{"id": "s-1"}]

        result = await store.list_conversations("user-1")

        assert result == [{"id": "s-1"}]
        redis.list_conversations.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_redis_on_postgres_error(self):
        store, redis, postgres = _make_store()
        postgres.list_conversations.side_effect = RuntimeError("PG down")
        redis.list_conversations.return_value = [{"id": "s-2"}]

        result = await store.list_conversations("user-1")

        assert result == [{"id": "s-2"}]
