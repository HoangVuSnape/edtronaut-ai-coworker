# Edtronaut AI Coworker

## Architecture

This project follows a **Clean Architecture** design pattern, maintaining a strict separation of concerns between the Domain, Application, and Infrastructure layers.

The overall system empowers users to interact with AI-driven personas (e.g., Gucci CEO, CHRO, Employer Branding & IC Manager). It features local REST and gRPC endpoints, robust conversation state management, and an external authentication layer backed by Supabase.

---

## Directory Structure

```text
edtronaut-ai-coworker/
├── backend/
│   ├── src/
│   │   └── coworker_api/
│   │       ├── config.py                 # Core configurations (YAML + .env)
│   │       │
│   │       ├── domain/                   # DOMAIN LAYER (No infra dependencies)
│   │       │   ├── models.py             # Core entities: Conversation, Turn, NPC
│   │       │   ├── memory/               # Memory interfaces and schemas
│   │       │   ├── prompts/              # NPC Prompts (Gucci CEO/CHRO/EB_IC)
│   │       │   └── ports.py              # Interfaces: LLMPort, RetrieverPort, MemoryPort
│   │       │
│   │       ├── application/              # APPLICATION LAYER (Use Cases)
│   │       │   ├── chat_service.py       # Interacts with NPC
│   │       │   ├── director_service.py   # Supervisor/coach logic
│   │       │   ├── session_manager.py    # Manages MemoryPort & sessions
│   │       │   └── ingest_documents_service.py # Vector DB seeding
│   │       │
│   │       └── infrastructure/           # INFRASTRUCTURE LAYER
│   │           ├── api/                  # FastAPI (REST routes & gRPC Web Gateway)
│   │           ├── db/                   # Composite Store (Redis Cache + PostgreSQL)
│   │           ├── llm_providers/        # OpenAI & Embedding clients
│   │           ├── rag/                  # Qdrant Vector Store
│   │           ├── auth/                 # JWT verification (Internal + Supabase)
│   │           └── monitoring/           # Logging & Langfuse tracing
│   │
│   ├── configs/                          # Config YAMLs
│   └── tests/                            # Pytest suite
│
├── frontend/
│   └── src/
│       ├── api/                          # gRPC-Web client / REST Fallback
│       ├── components/                   # React UI (ChatWindow, HintBanner, TogglePanel)
│       └── App.tsx                       # Root component with AuthProvider (Supabase)
│
└── docs/                                 # Extensive Documentation (V2 available)
```

---

## Core Systems & Data Flow

### 1. Authentication & Users
The platform leverages **Supabase** for secure user authentication (like Google/Gmail logins).
- The `frontend` acts as the entry point, authenticating the user via Supabase and retrieving a JWT.
- API requests passing to the `backend` include this JWT as a Bearer Token.
- The `infrastructure/api/rest_routes.py` validates the token against `auth.supabase_jwt_secret`. If the user has not interacted before, the backend securely auto-provisions their user record in the database.

### 2. Conversation Storage (Composite Store)
We employ a **Composite Memory Store** to optimize both speed and reliability:
- **Redis**: Acts as the "hot-path" cache, managing active session data quickly.
- **PostgreSQL**: Acts as the long-term system of record, storing `users`, `conversations`, and individual `turns`.

### 3. AI & RAG Pipeline
Incoming messages are passed through the `ChatService`.
- **RAG (Retrieval-Augmented Generation)**: Uses `Qdrant` via gRPC to pull relevant internal documents (e.g., HR manuals, Gucci guidelines).
- **LLM**: Context, user messages, and system prompts are combined and sent via `llm_providers` (defaulting to OpenAI) to stream the NPC's response back to the client.
- **Tracing**: Every AI generation step is tracked using `Langfuse` for observability and prompt optimization.

### 4. Communication Protocols
- **Primary:** The frontend uses **gRPC-web** generated clients to speak with the backend efficiently.
- **Fallback/Admin:** Standard **REST** APIs exist for health checks, local testing (e.g., `POST /api/auth/login`, `POST /api/npc/{npc_id}/chat`), and CMS capabilities.

---

## Technical Stack Overview

* **Backend**: Python, FastAPI, SQLAlchemy (PostgreSQL), Redis, Qdrant
* **Frontend**: React (Vite), TypeScript, Supabase JS Client, gRPC-web
* **AI Tooling**: Langfuse, OpenAI
* **Infrastructure**: Docker, `uv` (Python package manager)
