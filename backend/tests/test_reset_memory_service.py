"""Unit tests for ResetMemoryService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.reset_memory_service import ResetMemoryService


def _make_service() -> tuple[ResetMemoryService, AsyncMock]:
    session_manager = AsyncMock()
    service = ResetMemoryService(session_manager=session_manager)
    return service, session_manager


class TestResetSession:
    @pytest.mark.asyncio
    async def test_reset_existing_session(self):
        service, sm = _make_service()
        sm.delete_session.return_value = True

        result = await service.reset_session("session-1")

        assert result["status"] == "reset"
        assert result["session_id"] == "session-1"
        sm.delete_session.assert_awaited_once_with("session-1")

    @pytest.mark.asyncio
    async def test_reset_nonexistent_session(self):
        service, sm = _make_service()
        sm.delete_session.return_value = False

        result = await service.reset_session("nonexistent")

        assert result["status"] == "not_found"
        assert result["session_id"] == "nonexistent"


class TestResetAllUserSessions:
    @pytest.mark.asyncio
    async def test_reset_all_deletes_all_sessions(self):
        service, sm = _make_service()
        sm.list_user_sessions.return_value = [
            {"id": "s-1", "npc_name": "ceo"},
            {"id": "s-2", "npc_name": "chro"},
            {"id": "s-3", "npc_name": "ceo"},
        ]
        sm.delete_session.return_value = True

        result = await service.reset_all_user_sessions("user-1")

        assert result["deleted_count"] == 3
        assert result["user_id"] == "user-1"
        assert sm.delete_session.await_count == 3

    @pytest.mark.asyncio
    async def test_reset_all_no_sessions(self):
        service, sm = _make_service()
        sm.list_user_sessions.return_value = []

        result = await service.reset_all_user_sessions("user-1")

        assert result["deleted_count"] == 0
        sm.delete_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reset_all_partial_deletes(self):
        service, sm = _make_service()
        sm.list_user_sessions.return_value = [
            {"id": "s-1"},
            {"id": "s-2"},
        ]
        sm.delete_session.side_effect = [True, False]

        result = await service.reset_all_user_sessions("user-1")

        assert result["deleted_count"] == 1
