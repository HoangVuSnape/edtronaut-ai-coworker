# RAG Pipeline

## Overview

The RAG pipeline follows these steps:

1. Ingest documents
2. Chunk text
3. Embed chunks
4. Upsert into Qdrant
5. Retrieve context for chat

## Ingest service

File: `backend/src/coworker_api/application/ingest_documents_service.py`

- Input: list of documents `{ content, metadata }`.
- Chunking: character-based with `chunk_size` and `chunk_overlap`.
- Calls `RetrieverPort.add_documents` to store.

## Retriever

File: `backend/src/coworker_api/infrastructure/rag/retriever.py`

- `QdrantRetriever` uses `EmbeddingPort` to embed queries.
- Calls `QdrantVectorStore.search` to get top_k results.

## Vector store

File: `backend/src/coworker_api/infrastructure/rag/vector_store.py`

- `QdrantVectorStore` connects via gRPC.
- `_ensure_collection()` creates collection if missing.
- `upsert()` stores vectors + payloads.
- `search()` returns `{ content, score, metadata }`.

## Embedding provider

File: `backend/src/coworker_api/infrastructure/llm_providers/embedding_client.py`

- Uses OpenAI-compatible embeddings API.
- Provider can be changed via `provider_factory.py`.

## RAG in chat

File: `backend/src/coworker_api/application/chat_service.py`

- If `use_rag=true` and retriever exists, context is fetched.
- Context is injected under `## Relevant Context` in the prompt.

## Notes

- `TextProcessor` exists at `backend/src/coworker_api/infrastructure/nlp/text_processor.py` but is not used in the ingest service yet.
- You can swap to sentence-aware chunking if needed.
