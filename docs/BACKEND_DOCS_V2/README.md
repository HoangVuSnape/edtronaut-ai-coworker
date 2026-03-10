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
- `docs/BACKEND_DOCS_V2/09_Tracing_And_Logging.md`
- `docs/BACKEND_DOCS_V2/10_Local_Testing.md`
- `docs/BACKEND_DOCS_V2/11_Supabase_Gmail_Login.md`

## Key deltas from old docs

- Auth is REST-based (JWT + HTTP Bearer) in `backend/src/coworker_api/infrastructure/api/rest_routes.py`. It includes Supabase Gmail login integration, documented in `docs/BACKEND_DOCS_V2/11_Supabase_Gmail_Login.md`.
- Memory store is **Composite**: Redis cache + PostgreSQL persistence in `backend/src/coworker_api/infrastructure/db/composite_store.py`.
- RAG uses Qdrant gRPC in `backend/src/coworker_api/infrastructure/rag/vector_store.py`.
- Langfuse tracing is implemented in `backend/src/coworker_api/infrastructure/monitoring/tracing.py` and used in `backend/src/coworker_api/application/chat_service.py`.
- Provider factory lives in `backend/src/coworker_api/infrastructure/llm_providers/provider_factory.py`.

## Testing APIs Locally

You can test the authentication and chat endpoints locally using standard HTTP requests.

### 1. Test Login
```http
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "email": "admin@test.com",
  "password": "Admin@123"
}
```

### 2. Test Chat Action
```http
POST http://localhost:8000/api/npc/gucci_ceo/chat
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "sessionId": "session-001",
  "message": "Hello, who are you?",
  "useRag": true
}
```

### 3. Running Unit Tests
Generate the virtual environment and install components, then run:

```bash
uv sync
uv run pytest tests/ -v
```
