"""
Ingest Documents Service — Knowledge Base Builder (RAG).

Processes raw documents to build the vector store for
Retrieval-Augmented Generation.
"""

from __future__ import annotations

import logging
from typing import Any

from coworker_api.domain.ports import RetrieverPort, EmbeddingPort

logger = logging.getLogger(__name__)


class IngestDocumentsService:
    """
    RAG pipeline: parse documents → chunk → embed → store in vector DB.
    """

    def __init__(
        self,
        retriever_port: RetrieverPort,
        embedding_port: EmbeddingPort,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        self._retriever = retriever_port
        self._embedding = embedding_port
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Process and store documents in the knowledge base.

        Args:
            documents: List of dicts with 'content' (str) and 'metadata' (dict).
                       metadata should include 'source', 'document_id', etc.

        Returns:
            Dict with total_chunks and status.
        """
        all_chunks: list[dict[str, Any]] = []

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            if not content.strip():
                logger.warning("Skipping empty document", extra=metadata)
                continue

            # Chunk the document
            chunks = self._chunk_text(content)
            for idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                    },
                })

        if not all_chunks:
            return {"total_chunks": 0, "status": "no_content"}

        # Store in vector DB via RetrieverPort
        stored = await self._retriever.add_documents(all_chunks)

        logger.info(
            "Documents ingested",
            extra={
                "total_documents": len(documents),
                "total_chunks": stored,
            },
        )

        return {
            "total_documents": len(documents),
            "total_chunks": stored,
            "status": "success",
        }

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Uses a simple character-based chunking strategy.
        In production, consider sentence-aware or semantic chunking.
        """
        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self._chunk_size
            chunk = text[start:end]

            # Try to break at a sentence boundary
            if end < text_len:
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)
                if break_point > self._chunk_size // 2:
                    chunk = chunk[: break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - self._chunk_overlap

        return [c for c in chunks if c]
