# Application Layer

## Source location

- `backend/src/coworker_api/application`

## Responsibility

The Application Layer orchestrates workflows between the Domain and Infrastructure layers.

## Key services

### ChatService

File: `backend/src/coworker_api/application/chat_service.py`

- Inputs: `session_id`, `user_message`, `use_rag`.
- Loads session via `SessionManager`.
- Creates Langfuse trace nodes (`director`, `rag`, `npc`).
- If RAG is enabled, calls `RetrieverPort.retrieve`.
- Calls `LLMPort.generate` to produce the response.
- Appends turns and saves via `MemoryPort`.
- Outputs: `response`, `turn_number`, `session_id`.

### SessionManager

File: `backend/src/coworker_api/application/session_manager.py`

- Wrapper around `MemoryPort`.
- Create, load, save, delete sessions.
- List sessions for a user.

### DirectorService

File: `backend/src/coworker_api/application/director_service.py`

- Uses LLM to analyze conversation quality.
- Returns a structured JSON string (currently not strict-parsed).

### EvaluationService

File: `backend/src/coworker_api/application/evaluation_service.py`

- Evaluates user performance after a session.
- Returns a rubric-style JSON string.

### IngestDocumentsService

File: `backend/src/coworker_api/application/ingest_documents_service.py`

- Pipeline: chunk -> embed -> upsert to vector store.
- Uses `RetrieverPort.add_documents` and `EmbeddingPort`.

### ResetMemoryService

File: `backend/src/coworker_api/application/reset_memory_service.py`

- Deletes a session or all sessions for a user.

## Dependency wiring

- All services are created in `backend/src/coworker_api/infrastructure/api/main.py`.
- Dependency injection is handled by `AppContainer`.
