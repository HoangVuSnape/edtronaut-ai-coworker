from __future__ import annotations

from types import SimpleNamespace

import pytest

from coworker_api.domain.exceptions import VectorStoreError
from coworker_api.infrastructure.rag.vector_store import QdrantVectorStore


class _FakeQdrantClient:
    def __init__(self):
        self.query_kwargs = None
        self.deleted_collection = None
        self.created_kwargs = None
        self._collections = []
        self._collection_info = None

    async def query_points(self, **kwargs):
        self.query_kwargs = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    payload={"content": "doc content", "source": "kb", "document_id": "d-1"},
                    score=0.91,
                )
            ]
        )

    async def get_collections(self):
        return SimpleNamespace(collections=[SimpleNamespace(name=n) for n in self._collections])

    async def get_collection(self, collection_name: str):
        assert collection_name
        return self._collection_info

    async def delete_collection(self, *, collection_name: str):
        self.deleted_collection = collection_name

    async def create_collection(self, **kwargs):
        self.created_kwargs = kwargs


@pytest.mark.asyncio
async def test_search_uses_query_points_and_maps_payload():
    store = QdrantVectorStore(collection_name="knowledge_base", vector_size=3072)
    fake = _FakeQdrantClient()
    store._client = fake

    results = await store.search(
        query_vector=[0.1, 0.2, 0.3],
        top_k=3,
        score_threshold=0.2,
        filters={"source": "kb"},
    )

    assert fake.query_kwargs is not None
    assert fake.query_kwargs["collection_name"] == "knowledge_base"
    assert fake.query_kwargs["query"] == [0.1, 0.2, 0.3]
    assert fake.query_kwargs["limit"] == 3
    assert fake.query_kwargs["score_threshold"] == 0.2
    assert fake.query_kwargs["with_payload"] is True
    assert fake.query_kwargs["query_filter"] is not None

    assert results == [
        {
            "content": "doc content",
            "score": 0.91,
            "metadata": {"source": "kb", "document_id": "d-1"},
        }
    ]


@pytest.mark.asyncio
async def test_ensure_collection_recreates_when_dimension_mismatch_and_empty():
    store = QdrantVectorStore(collection_name="knowledge_base", vector_size=3072)
    fake = _FakeQdrantClient()
    fake._collections = ["knowledge_base"]
    fake._collection_info = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(vectors=SimpleNamespace(size=768))
        ),
        points_count=0,
    )
    store._client = fake

    await store._ensure_collection()

    assert fake.deleted_collection == "knowledge_base"
    assert fake.created_kwargs is not None
    assert fake.created_kwargs["collection_name"] == "knowledge_base"
    assert fake.created_kwargs["vectors_config"].size == 3072


@pytest.mark.asyncio
async def test_ensure_collection_raises_when_dimension_mismatch_and_has_data():
    store = QdrantVectorStore(collection_name="knowledge_base", vector_size=3072)
    fake = _FakeQdrantClient()
    fake._collections = ["knowledge_base"]
    fake._collection_info = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(vectors=SimpleNamespace(size=768))
        ),
        points_count=5,
    )
    store._client = fake

    with pytest.raises(VectorStoreError) as exc:
        await store._ensure_collection()

    assert "vector size mismatch" in str(exc.value).lower()

