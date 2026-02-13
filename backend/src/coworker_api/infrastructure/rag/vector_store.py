"""
Qdrant Vector Store — Manages the vector database.

Handles adding documents (with embeddings) and similarity search
using Qdrant's gRPC interface for maximum performance.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from coworker_api.domain.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant adapter for vector storage and similarity search."""

    def __init__(
        self,
        host: str = "localhost",
        grpc_port: int = 6334,
        collection_name: str = "knowledge_base",
        vector_size: int = 1536,
    ):
        self._host = host
        self._grpc_port = grpc_port
        self._collection_name = collection_name
        self._vector_size = vector_size
        self._client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Lazy-initialize the Qdrant client with gRPC."""
        if self._client is None:
            try:
                self._client = AsyncQdrantClient(
                    host=self._host,
                    grpc_port=self._grpc_port,
                    prefer_grpc=True,
                )
                # Ensure collection exists
                await self._ensure_collection()
            except Exception as e:
                raise VectorStoreError(f"Failed to connect to Qdrant: {e}") from e
        return self._client

    async def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        client = self._client
        if client is None:
            return
        collections = await client.get_collections()
        existing = [c.name for c in collections.collections]
        if self._collection_name not in existing:
            await client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {self._collection_name}")

    async def upsert(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> int:
        """
        Upsert vectors with payloads into the collection.

        Returns the number of points upserted.
        """
        client = await self._get_client()
        if not vectors:
            return 0

        point_ids = ids or [str(uuid.uuid4()) for _ in vectors]
        points = [
            PointStruct(
                id=pid,
                vector=vec,
                payload=payload,
            )
            for pid, vec, payload in zip(point_ids, vectors, payloads)
        ]

        try:
            await client.upsert(
                collection_name=self._collection_name,
                points=points,
            )
            logger.info(f"Upserted {len(points)} vectors into {self._collection_name}")
            return len(points)
        except Exception as e:
            raise VectorStoreError(f"Failed to upsert vectors: {e}") from e

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.

        Returns list of dicts with: content, score, metadata.
        """
        client = await self._get_client()

        # Build Qdrant filter
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        try:
            results = await client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=qdrant_filter,
            )

            return [
                {
                    "content": hit.payload.get("content", "") if hit.payload else "",
                    "score": hit.score,
                    "metadata": {
                        k: v
                        for k, v in (hit.payload or {}).items()
                        if k != "content"
                    },
                }
                for hit in results
            ]
        except Exception as e:
            raise VectorStoreError(f"Vector search failed: {e}") from e

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            await self._client.close()
            self._client = None
