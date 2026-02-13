"""
Retriever — Implements RetrieverPort.

Orchestrates the EmbeddingPort and QdrantVectorStore to provide
a unified retrieval interface for the Application layer.
"""

from __future__ import annotations

import logging
from typing import Any

from coworker_api.domain.ports import RetrieverPort, EmbeddingPort
from coworker_api.infrastructure.rag.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


class QdrantRetriever(RetrieverPort):
    """Implements RetrieverPort using Qdrant vector store + embeddings."""

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedding_port: EmbeddingPort,
    ):
        self._store = vector_store
        self._embedding = embedding_port

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.

        Pipeline: query → embed → search → results.
        """
        # 1. Embed the query
        query_vector = await self._embedding.embed_single(query)

        # 2. Search the vector store
        results = await self._store.search(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
            filters=filters,
        )

        logger.debug(
            "Retrieval complete",
            extra={"query_len": len(query), "results": len(results)},
        )
        return results

    async def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        Add documents to the knowledge base.

        Pipeline: documents → embed → store in vector DB.
        """
        if not documents:
            return 0

        # Extract texts for embedding
        texts = [doc.get("content", "") for doc in documents]
        metadata_list = [doc.get("metadata", {}) for doc in documents]

        # Generate embeddings in batch
        embeddings = await self._embedding.embed(texts)

        # Build payloads (content + metadata)
        payloads = [
            {"content": text, **meta}
            for text, meta in zip(texts, metadata_list)
        ]

        # Upsert into vector store
        stored = await self._store.upsert(
            vectors=embeddings,
            payloads=payloads,
        )

        logger.info(f"Added {stored} documents to knowledge base")
        return stored
