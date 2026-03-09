"""Unit tests for QdrantRetriever."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.infrastructure.rag.retriever import QdrantRetriever


def _make_retriever() -> tuple[QdrantRetriever, AsyncMock, AsyncMock]:
    vector_store = AsyncMock()
    embedding_port = AsyncMock()
    retriever = QdrantRetriever(
        vector_store=vector_store,
        embedding_port=embedding_port,
    )
    return retriever, vector_store, embedding_port


class TestRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_embeds_then_searches(self):
        retriever, store, embedding = _make_retriever()
        embedding.embed_single.return_value = [0.1, 0.2, 0.3]
        store.search.return_value = [
            {"content": "doc1", "score": 0.95, "metadata": {"source": "kb"}},
        ]

        results = await retriever.retrieve("What is revenue?", top_k=3)

        embedding.embed_single.assert_awaited_once_with("What is revenue?")
        store.search.assert_awaited_once()
        call_kwargs = store.search.call_args.kwargs
        assert call_kwargs["query_vector"] == [0.1, 0.2, 0.3]
        assert call_kwargs["top_k"] == 3
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_retrieve_passes_filters(self):
        retriever, store, embedding = _make_retriever()
        embedding.embed_single.return_value = [0.1]
        store.search.return_value = []

        await retriever.retrieve("query", filters={"source": "annual_report"})

        call_kwargs = store.search.call_args.kwargs
        assert call_kwargs["filters"] == {"source": "annual_report"}

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        retriever, store, embedding = _make_retriever()
        embedding.embed_single.return_value = [0.1]
        store.search.return_value = []

        results = await retriever.retrieve("obscure query")

        assert results == []


class TestAddDocuments:
    @pytest.mark.asyncio
    async def test_add_documents_embeds_and_upserts(self):
        retriever, store, embedding = _make_retriever()
        embedding.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        store.upsert.return_value = 2

        docs = [
            {"content": "Doc 1", "metadata": {"source": "kb"}},
            {"content": "Doc 2", "metadata": {"source": "kb"}},
        ]
        result = await retriever.add_documents(docs)

        assert result == 2
        embedding.embed.assert_awaited_once_with(["Doc 1", "Doc 2"])
        store.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_empty_documents_returns_zero(self):
        retriever, store, embedding = _make_retriever()

        result = await retriever.add_documents([])

        assert result == 0
        embedding.embed.assert_not_awaited()
        store.upsert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_add_documents_payloads_include_content_and_metadata(self):
        retriever, store, embedding = _make_retriever()
        embedding.embed.return_value = [[0.1]]
        store.upsert.return_value = 1

        docs = [{"content": "Hello", "metadata": {"doc_id": "d-1", "source": "kb"}}]
        await retriever.add_documents(docs)

        call_kwargs = store.upsert.call_args.kwargs
        payloads = call_kwargs["payloads"]
        assert len(payloads) == 1
        assert payloads[0]["content"] == "Hello"
        assert payloads[0]["doc_id"] == "d-1"
        assert payloads[0]["source"] == "kb"
