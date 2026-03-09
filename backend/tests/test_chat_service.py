"""Unit tests for ChatService."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from coworker_api.application.chat_service import ChatService
from coworker_api.domain.models import Conversation, NPC, Speaker


def _make_npc() -> NPC:
    return NPC(name="gucci_ceo", role_title="Chief Executive Officer, Gucci")


def _make_conversation(user_id: str = "user-1") -> Conversation:
    conv = Conversation(id="session-1", user_id=user_id, npc=_make_npc())
    return conv


def _make_service(
    *,
    conversation: Conversation | None = None,
    llm_response: str = "Hello from NPC",
    with_retriever: bool = False,
) -> ChatService:
    session_manager = AsyncMock()
    if conversation:
        session_manager.load_session.return_value = conversation
    else:
        session_manager.load_session.return_value = _make_conversation()

    llm = AsyncMock()
    llm.generate.return_value = llm_response

    retriever = None
    if with_retriever:
        retriever = AsyncMock()
        retriever.retrieve.return_value = [
            {"content": "Revenue grew 15%", "score": 0.9, "metadata": {"source": "kb", "document_id": "d-1"}},
        ]

    service = ChatService(
        session_manager=session_manager,
        llm_port=llm,
        retriever_port=retriever,
    )
    return service


# Patch tracing to no-ops so tests don't need Langfuse
_TRACING_MODULE = "coworker_api.application.chat_service"


@pytest.fixture(autouse=True)
def _mock_tracing():
    """Disable Langfuse tracing for all tests in this module."""
    with (
        patch(f"{_TRACING_MODULE}.start_chat_trace", return_value=None),
        patch(f"{_TRACING_MODULE}.start_director_node", return_value=None),
        patch(f"{_TRACING_MODULE}.start_rag_node", return_value=None),
        patch(f"{_TRACING_MODULE}.start_npc_node", return_value=None),
        patch(f"{_TRACING_MODULE}.update_chat_trace"),
        patch(f"{_TRACING_MODULE}.finish_observation"),
        patch(f"{_TRACING_MODULE}.end_trace"),
        patch(f"{_TRACING_MODULE}.flush"),
        patch(f"{_TRACING_MODULE}.get_trace_id", return_value="trace-1"),
        patch(f"{_TRACING_MODULE}.get_observation_id", return_value="obs-1"),
    ):
        yield


class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_process_message_without_rag(self):
        service = _make_service(llm_response="NPC says hello")
        result = await service.process_message(
            session_id="session-1",
            user_message="Hi there",
            use_rag=False,
        )

        assert result["response"] == "NPC says hello"
        assert result["session_id"] == "session-1"
        assert result["turn_number"] == 2  # user turn + NPC turn
        service._llm.generate.assert_awaited_once()
        service._session_manager.save_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_message_with_rag(self):
        service = _make_service(
            llm_response="Based on the data, revenue grew 15%.",
            with_retriever=True,
        )
        result = await service.process_message(
            session_id="session-1",
            user_message="What is the revenue?",
            use_rag=True,
        )

        assert "revenue" in result["response"].lower()
        service._retriever.retrieve.assert_awaited_once()
        service._llm.generate.assert_awaited_once()

        # Verify the prompt included RAG context
        call_kwargs = service._llm.generate.call_args.kwargs
        prompt = call_kwargs.get("prompt", "")
        assert "Revenue grew 15%" in prompt

    @pytest.mark.asyncio
    async def test_process_message_rag_disabled_skips_retriever(self):
        service = _make_service(with_retriever=True)
        await service.process_message(
            session_id="session-1",
            user_message="Hello",
            use_rag=False,
        )

        service._retriever.retrieve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_message_no_retriever_available(self):
        service = _make_service(with_retriever=False)
        result = await service.process_message(
            session_id="session-1",
            user_message="Hello",
            use_rag=True,
        )

        assert result["response"] == "Hello from NPC"

    @pytest.mark.asyncio
    async def test_process_message_saves_both_turns(self):
        conv = _make_conversation()
        service = _make_service(conversation=conv)

        await service.process_message(
            session_id="session-1",
            user_message="User says hi",
        )

        # Conversation should have 2 turns: user + NPC
        assert conv.turn_count == 2
        assert conv.turns[0].speaker == Speaker.USER
        assert conv.turns[0].content == "User says hi"
        assert conv.turns[1].speaker == Speaker.NPC

    @pytest.mark.asyncio
    async def test_process_message_llm_error_propagates(self):
        service = _make_service()
        service._llm.generate.side_effect = RuntimeError("LLM timeout")

        with pytest.raises(RuntimeError, match="LLM timeout"):
            await service.process_message(
                session_id="session-1",
                user_message="Hello",
            )


class TestBuildPrompt:
    def test_build_prompt_without_context(self):
        service = _make_service()
        conv = _make_conversation()
        conv.add_turn(Speaker.USER, "Hello")

        prompt = service._build_prompt(conv, rag_context="")

        assert "User: Hello" in prompt
        assert "Relevant Context" not in prompt

    def test_build_prompt_with_context(self):
        service = _make_service()
        conv = _make_conversation()
        conv.add_turn(Speaker.USER, "What is revenue?")

        prompt = service._build_prompt(conv, rag_context="Revenue grew 15% in Q4.")

        assert "Relevant Context" in prompt
        assert "Revenue grew 15% in Q4." in prompt
        assert "User: What is revenue?" in prompt

    def test_build_prompt_with_history(self):
        service = _make_service()
        conv = _make_conversation()
        conv.add_turn(Speaker.USER, "Hi")
        conv.add_turn(Speaker.NPC, "Hello!")
        conv.add_turn(Speaker.USER, "How are you?")

        prompt = service._build_prompt(conv, rag_context="")

        assert "Conversation History" in prompt
        assert "User: Hi" in prompt
        assert "Npc: Hello!" in prompt
        assert "User: How are you?" in prompt


class TestRetrieveContextWithDocs:
    @pytest.mark.asyncio
    async def test_retrieve_context_no_retriever(self):
        service = _make_service(with_retriever=False)
        context, docs = await service._retrieve_context_with_docs("query")

        assert context == ""
        assert docs == []

    @pytest.mark.asyncio
    async def test_retrieve_context_with_results(self):
        service = _make_service(with_retriever=True)
        context, docs = await service._retrieve_context_with_docs("revenue")

        assert "Revenue grew 15%" in context
        assert len(docs) == 1
        assert docs[0]["source"] == "kb"

    @pytest.mark.asyncio
    async def test_retrieve_context_empty_results(self):
        service = _make_service(with_retriever=True)
        service._retriever.retrieve.return_value = []

        context, docs = await service._retrieve_context_with_docs("obscure")

        assert context == ""
        assert docs == []
