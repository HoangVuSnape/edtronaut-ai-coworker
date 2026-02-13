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
*   **Primary Keys**: Use **UUID** (v4) for all tables to ensure global uniqueness and easier data migration/merging in the future.
*   **Timestamps**: Every table MUST have `created_at` and `updated_at` using `TIMESTAMPTZ` (UTC). Use `deleted_at` for soft deletes where audit trails are important.
*   **Normalization**: Normalize core data (User, NPC, Scenario) but allow JSONB columns for flexible schema-less data (e.g., specific NPC traits or experimental log attributes).

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
*   **`simulations`** (A specific run of a scenario)
    *   `id` (UUID, PK)
    *   `user_id` (UUID, FK -> `users.id`)
    *   `scenario_id` (UUID, FK -> `scenarios.id`)
    *   `status` (ENUM: 'active', 'completed', 'archived')
    *   `learning_outcome_score` (FLOAT, Nullable) - To be filled by `Analysis Service`.
    *   `started_at` (TIMESTAMPTZ)
    *   `ended_at` (TIMESTAMPTZ, Nullable)

*   **`simulation_logs`** (The exact conversation record for analytics)
    *   `id` (UUID, PK)
    *   `simulation_id` (UUID, FK -> `simulations.id`)
    *   `turn_number` (INTEGER)
    *   `speaker` (ENUM: 'user', 'npc', 'system')
    *   `content` (TEXT)
    *   `metadata` (JSONB) - Token usage, latency, sentiment score.
    *   `created_at` (TIMESTAMPTZ)

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
