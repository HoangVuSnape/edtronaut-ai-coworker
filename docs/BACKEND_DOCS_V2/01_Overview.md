# Backend Overview

## Goal
The backend powers the **Edtronaut AI Coworker Simulation**, providing a robust engine for intelligent chat, Retrieval-Augmented Generation (RAG), comprehensive tracing, and secure session management. The architecture follows a strict **Clean Architecture** pattern to keep core business logic entirely independent of external infrastructure and frameworks.

---

## Architectural Layers

The codebase is organized into three distinct layers, ensuring separation of concerns:

1. **Domain Layer** (`backend/src/coworker_api/domain`)
   - Contains core business models (`Conversation`, `Turn`, `NPC`).
   - Defines strict interfaces (Ports) such as `LLMPort`, `RetrieverPort`, and `MemoryPort` that the outer layers must implement.
   - Houses the prompt registry and system instruction templates for personas like the Gucci CEO or CHRO.

2. **Application Layer** (`backend/src/coworker_api/application`)
   - Orchestrates use cases by linking Domain rules with Infrastructure implementations.
   - **Key Services**:
     - `ChatService`: Manages the flow of receiving a message, pulling RAG context, and generating an LLM response.
     - `SessionManager`: Manages loading and saving the user's conversation state.
     - `DirectorService`: Analyzes conversations to provide subtle hints or steer the user.
     - `IngestDocumentsService`: Processes and embeds documents for the vector knowledge base.

3. **Infrastructure Layer** (`backend/src/coworker_api/infrastructure`)
   - Implements the Domain Ports using concrete technologies:
     - **API**: FastAPI providing both REST routes and a gRPC-Web gateway.
     - **Database**: A `CompositeMemoryStore` utilizing **Redis** for hot session caching and **PostgreSQL** for durable persistence.
     - **LLM**: Connects to OpenAI-compatible endpoints.
     - **RAG**: Utilizes **Qdrant** via gRPC for high-performance vector search.
     - **Auth**: Validates customized JWTs and integrates deeply with **Supabase** for external Google/Gmail OAuth.

---

## Core Workflows

### 1. Chat & Simulation Flow
When a user sends a message (`POST /api/npc/{npc_id}/chat`):
1. The **API** layer authenticates the user.
2. The `ChatService` loads the conversation session from the **Composite Store** (Redis/PG).
3. The `DirectorService` analyzes the ongoing conversation.
4. The `QdrantRetriever` fetches relevant RAG context from the vector database.
5. The `LLMPort` generates the NPC's response based on the persona, context, and history.
6. A new `Turn` is appended to the `Conversation` and persisted.

### 2. Observability (Tracing & Logging)
We use **Langfuse** to trace the simulation as an "Agent Graph".
- Every chat turn creates a distinct trace.
- Internal steps (e.g., `director_decision`, `rag_retrieval`, `npc_generation`) are recorded as structured nodes.
- This provides full visibility into individual latency, prompt performance, and agent interactions.

### 3. Identity and Security
- Uses **Supabase** to manage external identity (Google Login).
- Frontend clients trade OAuth grants for a Supabase JWT.
- Backend FastAPI routes enforce security via `HTTPBearer`, validating the JWT signature gracefully using configuration secrets. Waitlisted or new users are auto-provisioned securely into the PostgreSQL layer.

---

## Main Technical Stack
- **Web Framework**: FastAPI, gRPC-Web
- **Primary Database**: PostgreSQL (via SQLAlchemy / Alembic)
- **Caching**: Redis
- **Vector Search**: Qdrant
- **Identity Provider**: Supabase
- **Tracing / LLMOps**: Langfuse
- **Package Management**: `uv`
