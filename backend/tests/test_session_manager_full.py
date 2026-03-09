"""Unit tests for SessionManager — full coverage beyond create tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.session_manager import SessionManager
from coworker_api.domain.exceptions import ConversationNotFoundError
from coworker_api.domain.models import Conversation, NPC, Speaker


def _make_npc() -> NPC:
    return NPC(name="gucci_ceo", role_title="Chief Executive Officer")


def _make_conversation(user_id: str = "user-1") -> Conversation:
    return Conversation(id="session-1", user_id=user_id, npc=_make_npc())


# ── load_session ──


@pytest.mark.asyncio
async def test_load_session_success():
    memory = AsyncMock()
    conv = _make_conversation()
    memory.load_conversation.return_value = conv

    manager = SessionManager(memory_port=memory)
    result = await manager.load_session("session-1")

    assert result is conv
    memory.load_conversation.assert_awaited_once_with("session-1")


@pytest.mark.asyncio
async def test_load_session_not_found_raises():
    memory = AsyncMock()
    memory.load_conversation.return_value = None

    manager = SessionManager(memory_port=memory)
    with pytest.raises(ConversationNotFoundError):
        await manager.load_session("nonexistent")


# ── save_session ──


@pytest.mark.asyncio
async def test_save_session_delegates_to_memory():
    memory = AsyncMock()
    conv = _make_conversation()

    manager = SessionManager(memory_port=memory)
    await manager.save_session(conv)

    memory.save_conversation.assert_awaited_once_with(conv)


# ── delete_session ──


@pytest.mark.asyncio
async def test_delete_session_returns_true():
    memory = AsyncMock()
    memory.delete_conversation.return_value = True

    manager = SessionManager(memory_port=memory)
    result = await manager.delete_session("session-1")

    assert result is True
    memory.delete_conversation.assert_awaited_once_with("session-1")


@pytest.mark.asyncio
async def test_delete_session_returns_false():
    memory = AsyncMock()
    memory.delete_conversation.return_value = False

    manager = SessionManager(memory_port=memory)
    result = await manager.delete_session("nonexistent")

    assert result is False


# ── list_user_sessions ──


@pytest.mark.asyncio
async def test_list_user_sessions():
    memory = AsyncMock()
    memory.list_conversations.return_value = [
        {"id": "s-1", "npc_name": "gucci_ceo", "status": "active"},
        {"id": "s-2", "npc_name": "gucci_chro", "status": "completed"},
    ]

    manager = SessionManager(memory_port=memory)
    result = await manager.list_user_sessions("user-1")

    assert len(result) == 2
    memory.list_conversations.assert_awaited_once_with("user-1")


# ── add_turn_to_session ──


@pytest.mark.asyncio
async def test_add_turn_to_session():
    memory = AsyncMock()
    conv = _make_conversation()
    memory.load_conversation.return_value = conv

    manager = SessionManager(memory_port=memory)
    result = await manager.add_turn_to_session(
        session_id="session-1",
        speaker=Speaker.USER,
        content="Hello!",
    )

    assert result.turn_count == 1
    assert result.turns[0].speaker == Speaker.USER
    assert result.turns[0].content == "Hello!"
    memory.save_conversation.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_turn_to_session_not_found_raises():
    memory = AsyncMock()
    memory.load_conversation.return_value = None

    manager = SessionManager(memory_port=memory)
    with pytest.raises(ConversationNotFoundError):
        await manager.add_turn_to_session(
            session_id="nonexistent",
            speaker=Speaker.USER,
            content="Hello!",
        )
