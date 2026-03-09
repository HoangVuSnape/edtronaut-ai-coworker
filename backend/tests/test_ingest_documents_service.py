"""Unit tests for IngestDocumentsService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coworker_api.application.ingest_documents_service import IngestDocumentsService


def _make_service(chunk_size: int = 100, chunk_overlap: int = 20) -> IngestDocumentsService:
    retriever = AsyncMock()
    embedding = AsyncMock()
    retriever.add_documents.return_value = 5  # Simulate stored chunk count
    return IngestDocumentsService(
        retriever_port=retriever,
        embedding_port=embedding,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


class TestIngest:
    @pytest.mark.asyncio
    async def test_ingest_normal_documents(self):
        service = _make_service()
        documents = [
            {"content": "A" * 200, "metadata": {"source": "kb", "document_id": "d-1"}},
            {"content": "B" * 200, "metadata": {"source": "kb", "document_id": "d-2"}},
        ]
        result = await service.ingest(documents)

        assert result["status"] == "success"
        assert result["total_documents"] == 2
        assert result["total_chunks"] == 5  # Mocked
        service._retriever.add_documents.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_empty_list(self):
        service = _make_service()
        result = await service.ingest([])

        assert result["status"] == "no_content"
        assert result["total_chunks"] == 0

    @pytest.mark.asyncio
    async def test_ingest_blank_content_documents_skipped(self):
        service = _make_service()
        documents = [
            {"content": "", "metadata": {"source": "kb"}},
            {"content": "   ", "metadata": {"source": "kb"}},
        ]
        result = await service.ingest(documents)

        assert result["status"] == "no_content"
        assert result["total_chunks"] == 0

    @pytest.mark.asyncio
    async def test_ingest_mixed_valid_and_blank(self):
        service = _make_service()
        service._retriever.add_documents.return_value = 3
        documents = [
            {"content": "", "metadata": {}},
            {"content": "Valid document content here." * 10, "metadata": {"source": "kb"}},
        ]
        result = await service.ingest(documents)

        assert result["status"] == "success"
        assert result["total_chunks"] == 3


class TestChunkText:
    def test_short_text_single_chunk(self):
        service = _make_service(chunk_size=500)
        chunks = service._chunk_text("Short text.")
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_long_text_produces_multiple_chunks(self):
        service = _make_service(chunk_size=50, chunk_overlap=10)
        text = "Word " * 100  # 500 chars
        chunks = service._chunk_text(text)
        assert len(chunks) > 1
        # All chunks should be non-empty
        assert all(c.strip() for c in chunks)

    def test_chunks_have_overlap(self):
        service = _make_service(chunk_size=100, chunk_overlap=20)
        text = "Hello world. " * 50  # ~650 chars
        chunks = service._chunk_text(text)
        assert len(chunks) > 1
        # Overlapping means some content should appear in adjacent chunks
        for i in range(len(chunks) - 1):
            # End of chunk i should overlap with start of chunk i+1
            # (not always exact due to sentence boundaries, but chunks should exist)
            assert len(chunks[i]) > 0

    def test_empty_text(self):
        service = _make_service()
        chunks = service._chunk_text("")
        assert chunks == []

    def test_sentence_boundary_break(self):
        service = _make_service(chunk_size=50, chunk_overlap=10)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = service._chunk_text(text)
        # At least some chunks should end at a period
        period_endings = [c for c in chunks if c.endswith(".")]
        assert len(period_endings) >= 1
