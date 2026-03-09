"""
Unit Tests for Edtronaut AI Coworker Backend — Domain & Application Layer.

Tests use mocked LLM/Memory ports (no real external services).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# ── Domain Model Tests ──

from coworker_api.domain.models import (
    Conversation,
    Turn,
    NPC,
    ScenarioState,
    Hint,
    Speaker,
    SimulationStatus,
)
from coworker_api.domain.exceptions import (
    ConversationNotFoundError,
    LLMConnectionError,
    DomainException,
)
from coworker_api.domain.memory.schemas import MemoryState, ConversationSummary


class TestNPC:
    def test_create_npc(self):
        npc = NPC(name="Test CEO", role_title="CEO")
        assert npc.name == "Test CEO"
        assert npc.role_title == "CEO"
        assert npc.id  # UUID generated

    def test_npc_with_traits(self):
        npc = NPC(
            name="CEO",
            role_title="Chief Executive",
            traits={"openness": 0.8, "agreeableness": 0.3},
        )
        assert npc.traits["openness"] == 0.8
        assert len(npc.traits) == 2


class TestConversation:
    def _make_npc(self) -> NPC:
        return NPC(name="gucci_ceo", role_title="CEO", company="Gucci")

    def test_create_conversation(self):
        conv = Conversation(user_id="user-1", npc=self._make_npc())
        assert conv.user_id == "user-1"
        assert conv.turn_count == 0
        assert conv.status == SimulationStatus.ACTIVE
        assert conv.last_turn is None

    def test_add_turns(self):
        conv = Conversation(user_id="user-1", npc=self._make_npc())
        t1 = conv.add_turn(Speaker.USER, "Hello!")
        assert t1.turn_number == 1
        assert t1.speaker == Speaker.USER

        t2 = conv.add_turn(Speaker.NPC, "Welcome.")
        assert t2.turn_number == 2
        assert conv.turn_count == 2
        assert conv.last_turn == t2

    def test_end_conversation(self):
        conv = Conversation(user_id="user-1", npc=self._make_npc())
        conv.end_conversation()
        assert conv.status == SimulationStatus.COMPLETED
        assert conv.ended_at is not None

    def test_add_hint(self):
        conv = Conversation(user_id="user-1", npc=self._make_npc())
        hint = conv.add_hint("Try being more assertive", "suggestion", 0.8)
        assert hint.content == "Try being more assertive"
        assert len(conv.hints) == 1


class TestExceptions:
    def test_exception_has_grpc_code(self):
        from grpc import StatusCode
        err = ConversationNotFoundError()
        assert err.grpc_code == StatusCode.NOT_FOUND
        assert "not found" in err.message.lower()

    def test_custom_message(self):
        err = LLMConnectionError("Timeout reached")
        assert err.message == "Timeout reached"

    def test_base_exception(self):
        err = DomainException()
        assert err.message == "An unexpected error occurred."


class TestMemorySchemas:
    def test_memory_state_add_message(self):
        state = MemoryState(session_id="s1", user_id="u1", current_turn=1)
        state.add_message("user", "Hello")
        assert len(state.short_term_history) == 1
        assert state.short_term_history[0]["speaker"] == "user"

    def test_memory_state_truncation(self):
        state = MemoryState(session_id="s1", user_id="u1")
        for i in range(25):
            state.add_message("user", f"Message {i}")
        assert len(state.short_term_history) == 20  # Capped at 20

    def test_context_string(self):
        state = MemoryState(session_id="s1", user_id="u1")
        state.add_message("user", "Hi")
        state.add_message("npc", "Hello")
        ctx = state.to_context_string()
        assert "User: Hi" in ctx
        assert "Npc: Hello" in ctx


class TestPromptRegistry:
    def test_get_persona_prompt(self):
        from coworker_api.domain.prompts import get_persona_prompt
        prompt = get_persona_prompt("gucci_ceo")
        assert "Marco Bizzarri" in prompt

    def test_get_unknown_persona_raises(self):
        from coworker_api.domain.prompts import get_persona_prompt
        from coworker_api.domain.exceptions import NPCNotFoundError
        with pytest.raises(NPCNotFoundError):
            get_persona_prompt("unknown_persona")

    def test_list_personas(self):
        from coworker_api.domain.prompts import list_personas
        personas = list_personas()
        assert len(personas) == 3
        names = {p["name"] for p in personas}
        assert "gucci_ceo" in names
        assert "gucci_chro" in names
        assert "gucci_eb_ic" in names


# ── Infrastructure Tool Tests (no external deps) ──

class TestKPICalculator:
    def test_revenue_growth(self):
        from coworker_api.infrastructure.tools.kpi_calculator import KPICalculator
        calc = KPICalculator()
        result = calc.calculate("revenue_growth", {
            "current_revenue": 120,
            "previous_revenue": 100,
        })
        assert result["value"] == 20.0
        assert result["unit"] == "%"

    def test_unknown_kpi(self):
        from coworker_api.infrastructure.tools.kpi_calculator import KPICalculator
        calc = KPICalculator()
        result = calc.calculate("nonexistent", {})
        assert "error" in result


class TestIntentDetector:
    def test_detect_question(self):
        from coworker_api.infrastructure.nlp.intent_detector import IntentDetector, Intent
        detector = IntentDetector()
        assert detector.detect("What is the revenue?") == Intent.QUESTION

    def test_detect_greeting(self):
        from coworker_api.infrastructure.nlp.intent_detector import IntentDetector, Intent
        detector = IntentDetector()
        assert detector.detect("Hello, nice to meet you") == Intent.GREETING

    def test_detect_unknown(self):
        from coworker_api.infrastructure.nlp.intent_detector import IntentDetector, Intent
        detector = IntentDetector()
        assert detector.detect("") == Intent.UNKNOWN


class TestTextProcessor:
    def test_clean_text(self):
        from coworker_api.infrastructure.nlp.text_processor import TextProcessor
        result = TextProcessor.clean_text("  hello   world  ")
        assert result == "hello world"

    def test_chunk_by_sentences(self):
        from coworker_api.infrastructure.nlp.text_processor import TextProcessor
        text = "First sentence. Second sentence. Third sentence."
        chunks = TextProcessor.chunk_by_sentences(text, max_chunk_size=30)
        assert len(chunks) >= 2
