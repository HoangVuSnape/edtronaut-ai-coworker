# Infrastructure Layer

## Source location

- `backend/src/coworker_api/infrastructure`

## Responsibility

Implements the concrete technical details required by the Domain ports: API, DB, LLM, RAG, logging, and tools.

## Modules

### API (REST + gRPC skeleton)

- `backend/src/coworker_api/infrastructure/api/main.py`
- `backend/src/coworker_api/infrastructure/api/rest_routes.py`
- `backend/src/coworker_api/infrastructure/api/grpc_server.py`

REST is the primary API. gRPC is a skeleton (no generated stubs or auth interceptors yet).

### Database / Memory Stores

- `backend/src/coworker_api/infrastructure/db/memory_store.py` (Redis)
- `backend/src/coworker_api/infrastructure/db/postgres_store.py` (PostgreSQL)
- `backend/src/coworker_api/infrastructure/db/composite_store.py` (Redis + Postgres)
- `backend/src/coworker_api/infrastructure/db/postgres_models.py` (ORM tables)

### LLM Providers

- `backend/src/coworker_api/infrastructure/llm_providers/openai_client.py`
- `backend/src/coworker_api/infrastructure/llm_providers/embedding_client.py`
- `backend/src/coworker_api/infrastructure/llm_providers/provider_factory.py`

Supports any OpenAI-compatible API by changing provider config.

### RAG

- `backend/src/coworker_api/infrastructure/rag/vector_store.py` (Qdrant)
- `backend/src/coworker_api/infrastructure/rag/retriever.py`

### NLP utilities

- `backend/src/coworker_api/infrastructure/nlp/text_processor.py`
- `backend/src/coworker_api/infrastructure/nlp/intent_detector.py`

### Tools

- `backend/src/coworker_api/infrastructure/tools/kpi_calculator.py`
- `backend/src/coworker_api/infrastructure/tools/ab_simulator.py`
- `backend/src/coworker_api/infrastructure/tools/portfolio_pack.py`

### Monitoring

- `backend/src/coworker_api/infrastructure/monitoring/logging.py`
- `backend/src/coworker_api/infrastructure/monitoring/tracing.py`

### gRPC Clients

- `backend/src/coworker_api/infrastructure/grpc_clients/frontend_client.py`

## Dependency container

- `AppContainer` in `backend/src/coworker_api/infrastructure/api/main.py` wires all services and adapters.
