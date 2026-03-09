"""Unit tests for EvaluationService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.evaluation_service import EvaluationService
from coworker_api.domain.models import Conversation, NPC, Speaker


def _make_npc() -> NPC:
    return NPC(name="gucci_ceo", role_title="CEO")


class TestEvaluationService:
    @pytest.mark.asyncio
    async def test_evaluate_session_with_turns(self):
        llm = AsyncMock()
        llm.generate.return_value = '{"overall_score": 7.5}'

        service = EvaluationService(llm_port=llm)
        conv = Conversation(user_id="user-1", npc=_make_npc())
        conv.add_turn(Speaker.USER, "I'd like to discuss the Q4 results.")
        conv.add_turn(Speaker.NPC, "Certainly. Revenue grew 15% year-over-year.")
        conv.add_turn(Speaker.USER, "What about APAC growth?")

        result = await service.evaluate_session(conv)

        llm.generate.assert_awaited_once()
        assert result["session_id"] == conv.id
        assert result["npc_name"] == "gucci_ceo"
        assert result["total_turns"] == 3
        assert "raw_evaluation" in result

    @pytest.mark.asyncio
    async def test_evaluate_session_zero_turns_returns_empty(self):
        llm = AsyncMock()
        service = EvaluationService(llm_port=llm)
        conv = Conversation(user_id="user-1", npc=_make_npc())

        result = await service.evaluate_session(conv)

        llm.generate.assert_not_awaited()
        assert result["overall_score"] == 0.0
        assert result["summary"] == "No turns to evaluate."
        assert result["strengths"] == []
        assert result["areas_for_improvement"] == []

    def test_empty_evaluation_structure(self):
        llm = AsyncMock()
        service = EvaluationService(llm_port=llm)
        result = service._empty_evaluation()

        expected_keys = {"communication", "negotiation", "decision_making",
                         "emotional_intelligence", "strategic_thinking"}
        assert set(result["scores"].keys()) == expected_keys
        assert all(v == 0 for v in result["scores"].values())

    @pytest.mark.asyncio
    async def test_evaluate_session_llm_prompt_contains_transcript(self):
        llm = AsyncMock()
        llm.generate.return_value = "{}"

        service = EvaluationService(llm_port=llm)
        conv = Conversation(user_id="user-1", npc=_make_npc())
        conv.add_turn(Speaker.USER, "Hello world")

        await service.evaluate_session(conv)

        # Verify the prompt sent to the LLM contains the conversation content
        call_args = llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", "")
        assert "Hello world" in prompt
        assert "gucci_ceo" in prompt
