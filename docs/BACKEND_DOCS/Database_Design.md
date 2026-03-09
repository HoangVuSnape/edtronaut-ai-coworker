# Database Design & Rules

## 1. Overview
This project uses a **hybrid database architecture** tailored for an AI-driven application. We utilize three distinct types of storage, all containerized via Docker.

| Type | Technology | Purpose |
|------|------------|---------|
| **Relational** | **PostgreSQL** | Structured data (NPC configs, User profiles, Simulation logs, Analytics). |
| **Memory Store**| **Redis** | Ephemeral state (Active sessions, Real-time conversation context, Pub/Sub). |
| **Vector DB** | **Qdrant** | Semantic search (RAG Knowledge base, Long-term memory/reflections). |

---

## 2. Relational Database (PostgreSQL)

### Design Rules (per `schema-design.md`)
*   **Primary Keys**: Prefer **UUID** (v4) for domain tables (`users`, `npcs`, `scenarios`). Session-facing tables may use external string IDs (`conversations.id`) to align with client session keys.
*   **Timestamps**: Every table MUST have `created_at` and `updated_at` using `TIMESTAMPTZ` (UTC). Use `deleted_at` for soft deletes where audit trails are important.
*   **Normalization**: Normalize core data (User, NPC, Scenario) but allow JSONB columns for flexible schema-less data (e.g., specific NPC traits or experimental log attributes).
*   **Migrations**: Use **Alembic** migrations (`backend/migrations/`) as the source of truth for schema evolution. Avoid relying on `create_all()` in staging/production.

### Core Schema

#### 2.1 Users & Authentication
*   **`users`**
    *   `id` (UUID, PK)
    *   `email` (VARCHAR, Unique)
    *   `password_hash` (VARCHAR)
    *   `role` (ENUM: 'admin', 'user')
    *   `created_at`, `updated_at` (TIMESTAMPTZ)

#### 2.2 Domain Entities (NPCs & Scenarios)
*   **`npcs`** (Defines the AI personas)
    *   `id` (UUID, PK)
    *   `name` (VARCHAR) - e.g., "Gucci CEO"
    *   `role_title` (VARCHAR) - e.g., "Chief Executive Officer"
    *   `system_prompt_template` (TEXT) - The base prompt for this persona.
    *   `traits` (JSONB) - Flexible attributes (e.g., `{"openness": 0.8, "agreeableness": 0.2}`).

*   **`scenarios`** (Defines the simulation setup)
    *   `id` (UUID, PK)
    *   `title` (VARCHAR)
    *   `description` (TEXT)
    *   `difficulty_level` (INTEGER)
    *   `npc_id` (UUID, FK -> `npcs.id`)

#### 2.3 Application State (Sessions & Logs)
*   **`conversations`** (A specific run of a chat simulation)
    *   `id` (VARCHAR, PK) - Session ID (client-provided).
    *   `user_id` (UUID, FK -> `users.id`)
    *   `npc_name` (VARCHAR)
    *   `npc_role_title` (VARCHAR, Nullable)
    *   `npc_data` (JSON, Nullable)
    *   `scenario_data` (JSON, Nullable)
    *   `status` (VARCHAR: `active|completed|archived`)
    *   `started_at` (TIMESTAMPTZ)
    *   `ended_at` (TIMESTAMPTZ, Nullable)
    *   `created_at`, `updated_at` (TIMESTAMPTZ)

*   **`turns`** (The exact conversation record for analytics/debugging)
    *   `id` (VARCHAR, PK)
    *   `conversation_id` (VARCHAR, FK -> `conversations.id`)
    *   `turn_number` (INTEGER)
    *   `speaker` (VARCHAR: `user|npc|system`)
    *   `content` (TEXT)
    *   `metadata_json` (JSON, Nullable) - Token usage, latency, hints, tracing metadata.
    *   `created_at` (TIMESTAMPTZ)

> Note: Older docs used the names `simulations` / `simulation_logs`. Runtime implementation currently uses
> `conversations` / `turns` with equivalent semantics.

---

## 3. Memory Store (Redis)

### Usage Strategy
Redis is used for high-speed access to the *currently active* conversation context. This prevents hitting Postgres for every chat turn.

### Key Structure
*   **Session Context**: `session:{session_id}:context`
    *   Type: JSON or Hash
    *   Content: `{"current_turn": 5, "npc_mood": "angry", "short_term_history": [...]}`
    *   **TTL**: 30 minutes (auto-expire inactive sessions).

*   **User Rate Limits**: `ratelimit:{user_id}`
    *   Type: Counter
    *   **TTL**: 1 minute.

*   **Job Queues** (if needed): `queue:background_tasks`
    *   For async tasks like "Generate Learning Report" or "Ingest Document".

---

## 4. Vector Database (Qdrant)

### Usage Strategy
Qdrant stores semantic embeddings for "Long-term Memory" and "Knowledge Base" (RAG).

### Collections

#### 4.1 `knowledge_base`
*   **Purpose**: Stores static documents (PDFs, company policies, wikis).
*   **Payload**:
    *   `document_id` (String)
    *   `chunk_index` (Int)
    *   `content` (Text)
    *   `source` (String)
*   **Usage**: When the NPC needs to look up facts.

#### 4.2 `episodic_memory` (Future/Advanced)
*   **Purpose**: Stores past simulation summaries to allow the NPC to "remember" previous interactions with the user.
*   **Payload**:
    *   `user_id` (String)
    *   `simulation_id` (String)
    *   `summary` (Text)
    *   `lessons_learned` (Text)
*   **Usage**: To personalize future simulations based on past performance.

---

## 5. Docker Infrastructure

All services are defined in `docker-compose.yml`.

```yaml
version: '3.8'
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: edtronaut
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

  qdrant:
    image: qdrant/qdrant
    volumes:
      - qdrant_data:/qdrant/storage

  # Backend & Frontend services...
volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```
