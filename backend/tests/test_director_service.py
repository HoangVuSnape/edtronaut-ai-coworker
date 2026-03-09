"""Unit tests for DirectorService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.director_service import DirectorService
from coworker_api.domain.models import Conversation, NPC, Speaker


def _make_npc() -> NPC:
    return NPC(name="gucci_ceo", role_title="CEO")


def _make_conversation_with_turns(n_turns: int = 4) -> Conversation:
    conv = Conversation(user_id="user-1", npc=_make_npc())
    for i in range(n_turns):
        speaker = Speaker.USER if i % 2 == 0 else Speaker.NPC
        conv.add_turn(speaker, f"Turn {i + 1}")
    return conv


class TestDirectorService:
    @pytest.mark.asyncio
    async def test_analyze_conversation_calls_llm(self):
        llm = AsyncMock()
        llm.generate.return_value = '{"overall_score": 0.8}'

        service = DirectorService(llm_port=llm)
        conv = _make_conversation_with_turns(4)
        result = await service.analyze_conversation(conv)

        llm.generate.assert_awaited_once()
        call_kwargs = llm.generate.call_args
        assert "gucci_ceo" in call_kwargs.kwargs.get("prompt", "") or "gucci_ceo" in call_kwargs.args[0]
        assert result["session_id"] == conv.id
        assert result["turns_analyzed"] == 4
        assert "raw_analysis" in result

    @pytest.mark.asyncio
    async def test_analyze_empty_turns_returns_empty_assessment(self):
        llm = AsyncMock()
        service = DirectorService(llm_port=llm)
        conv = Conversation(user_id="user-1", npc=_make_npc())

        result = await service.analyze_conversation(conv)

        llm.generate.assert_not_awaited()
        assert result["overall_score"] == 0.0
        assert result["intervention"]["needed"] is False

    @pytest.mark.asyncio
    async def test_should_intervene_too_early(self):
        llm = AsyncMock()
        service = DirectorService(llm_port=llm)
        conv = Conversation(user_id="user-1", npc=_make_npc())
        conv.add_turn(Speaker.USER, "Hi")

        result = await service.should_intervene(conv)

        assert result is None
        llm.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_intervene_with_enough_turns(self):
        llm = AsyncMock()
        llm.generate.return_value = '{"intervention": {"needed": false}}'
        service = DirectorService(llm_port=llm)
        conv = _make_conversation_with_turns(4)

        result = await service.should_intervene(conv)

        # Current implementation returns None as placeholder
        assert result is None
        llm.generate.assert_awaited_once()

    def test_empty_assessment_structure(self):
        llm = AsyncMock()
        service = DirectorService(llm_port=llm)
        result = service._empty_assessment()

        assert "user_assessment" in result
        assert "npc_assessment" in result
        assert "intervention" in result
        assert "overall_score" in result
        assert result["user_assessment"]["communication_style"] == "unknown"
        assert result["intervention"]["needed"] is False
