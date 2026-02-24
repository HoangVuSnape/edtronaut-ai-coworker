# Database and Storage

## Overview

The backend uses three storage systems:

- PostgreSQL for durable data (users, npcs, scenarios, conversations, turns).
- Redis for hot session cache and state.
- Qdrant for vector storage used by RAG.

## PostgreSQL

ORM file: `backend/src/coworker_api/infrastructure/db/postgres_models.py`

Main tables:

- `users` (id, email, password_hash, role, created_at, updated_at)
- `npcs` (id, name, role_title, system_prompt_template, traits)
- `scenarios` (id, title, description, difficulty_level, npc_id)
- `conversations` (id, user_id, npc_name, npc_role_title, status, started_at, ended_at)
- `turns` (id, conversation_id, turn_number, speaker, content, metadata_json)

Store:

- `backend/src/coworker_api/infrastructure/db/postgres_store.py`
- SQLAlchemy Async with Alembic `migrate_to_head()`.

## Redis

File: `backend/src/coworker_api/infrastructure/db/memory_store.py`

- Stores `Conversation` JSON with TTL.
- Key prefix: `session:{session_id}`.
- User index: `user_sessions:{user_id}`.

## Composite store

File: `backend/src/coworker_api/infrastructure/db/composite_store.py`

- Write: Redis + PostgreSQL.
- Read: Redis first, fallback to Postgres.
- List: Postgres primary.

## Qdrant (vector DB)

File: `backend/src/coworker_api/infrastructure/rag/vector_store.py`

- gRPC for performance.
- Default collection: `knowledge_base`.
- Validates vector size on startup.
