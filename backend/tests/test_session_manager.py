from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.session_manager import SessionManager
from coworker_api.domain.models import NPC


@pytest.mark.asyncio
async def test_create_session_applies_scenario_id():
    memory = AsyncMock()
    manager = SessionManager(memory_port=memory)
    npc = NPC(name="gucci_ceo", role_title="Chief Executive Officer")

    conversation = await manager.create_session(
        user_id="11111111-1111-1111-1111-111111111111",
        npc=npc,
        scenario_id="22222222-2222-2222-2222-222222222222",
    )

    assert conversation.scenario is not None
    assert conversation.scenario.scenario_id == "22222222-2222-2222-2222-222222222222"
    memory.save_conversation.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_session_without_scenario_id_keeps_none():
    memory = AsyncMock()
    manager = SessionManager(memory_port=memory)
    npc = NPC(name="gucci_ceo", role_title="Chief Executive Officer")

    conversation = await manager.create_session(
        user_id="11111111-1111-1111-1111-111111111111",
        npc=npc,
    )

    assert conversation.scenario is None
