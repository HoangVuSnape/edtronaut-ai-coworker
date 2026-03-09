# Backend Docs V2

Purpose: describe the backend architecture based on the **current codebase**, reflecting changes from the older BACKEND_DOCS.

## Documents

- `docs/BACKEND_DOCS_V2/01_Overview.md`
- `docs/BACKEND_DOCS_V2/02_Domain_Layer.md`
- `docs/BACKEND_DOCS_V2/03_Application_Layer.md`
- `docs/BACKEND_DOCS_V2/04_Infrastructure_Layer.md`
- `docs/BACKEND_DOCS_V2/05_Security_And_Auth.md`
- `docs/BACKEND_DOCS_V2/06_Observability_And_Tracing.md`
- `docs/BACKEND_DOCS_V2/07_Database_And_Storage.md`
- `docs/BACKEND_DOCS_V2/08_RAG_Pipeline.md`

## Key deltas from old docs

- Auth is REST-based (JWT + HTTP Bearer) in `backend/src/coworker_api/infrastructure/api/rest_routes.py`.
- Memory store is **Composite**: Redis cache + PostgreSQL persistence in `backend/src/coworker_api/infrastructure/db/composite_store.py`.
- RAG uses Qdrant gRPC in `backend/src/coworker_api/infrastructure/rag/vector_store.py`.
- Langfuse tracing is implemented in `backend/src/coworker_api/infrastructure/monitoring/tracing.py` and used in `backend/src/coworker_api/application/chat_service.py`.
- Provider factory lives in `backend/src/coworker_api/infrastructure/llm_providers/provider_factory.py`.
