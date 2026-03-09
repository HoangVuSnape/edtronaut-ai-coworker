# Backend Overview

## Goal
The backend powers an AI coworker simulation with chat, RAG, tracing, and session management. The architecture is layered to keep business logic independent from infrastructure details.

## Core layers

- Domain Layer: core models, rules, and interfaces (Ports).
- Application Layer: use-case orchestration and workflows.
- Infrastructure Layer: concrete implementations (DB, API, LLM, RAG, logging).

## Chat flow (summary)

1. REST API receives `POST /api/npc/{npc_id}/chat` in `backend/src/coworker_api/infrastructure/api/rest_routes.py`.
2. `ChatService.process_message` loads session via `SessionManager` and starts a trace.
3. If RAG is enabled, `QdrantRetriever` fetches context from Qdrant.
4. `LLMPort.generate` produces the response.
5. The new turn is stored through `MemoryPort` (Composite store).
6. Response is returned to the client.

## Main directories

- `backend/src/coworker_api/domain`
- `backend/src/coworker_api/application`
- `backend/src/coworker_api/infrastructure`
- `backend/src/coworker_api/config.py`

## gRPC status

- `backend/src/coworker_api/infrastructure/api/grpc_server.py` is a skeleton. Auth interceptors are not implemented yet.

## Configuration

- `backend/src/coworker_api/config.py` loads `.env` and `backend/configs/default.yml`.
- LLM and embedding providers are created via `provider_factory.py`.
