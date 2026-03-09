# Observability and Tracing

## Logging

File: `backend/src/coworker_api/infrastructure/monitoring/logging.py`

- `setup_logging()` loads `backend/configs/logging.yml` if present.
- Otherwise, it uses a basic fallback logger.

## Langfuse tracing

File: `backend/src/coworker_api/infrastructure/monitoring/tracing.py`

Helpers:

- `start_chat_trace`
- `start_director_node`
- `start_rag_node`
- `start_npc_node`
- `start_tool_node`
- `finish_observation`

Enablement:

- `LANGFUSE__PUBLIC_KEY` and `LANGFUSE__SECRET_KEY` are set.
- `LANGFUSE__ENABLED=true` or keys are present.

## Trace usage in ChatService

File: `backend/src/coworker_api/application/chat_service.py`

- One trace per chat turn.
- Nodes in order:
- `director_decision`
- `rag_retrieval` (if RAG enabled)
- `npc:<persona>`

## Structured log fields

`ChatService` logs with fields:

- `trace_id`
- `observation_id`
- `session_id`
- `persona_id`
- `layer`
- `duration_ms`

## Notes

- Tracing is safe to disable if keys or package are missing.
- `_safe_call` prevents tracing failures from crashing requests.
