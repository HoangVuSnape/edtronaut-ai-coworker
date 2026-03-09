# Infrastructure Layer Documentation

## Overview
The **Infrastructure Layer** implements the technical details required to support the Application and Domain layers. It interacts with external systems (databases, APIs, LLM providers) and adapts them to the interfaces (Ports) defined in the Domain layer.

## Key Components

### 1. API (`api/`)
**Role:** Entry Point & Delivery Mechanism
- **Purpose:** Exposes the application logic to the outside world (Frontend).
- **Components:**
  - **`main.py`**: Factors the FastAPI application, wires up dependencies (DI), and starts the server.
  - **`rest_routes.py`**: Primary API surface today (health, auth, CRUD, chat action endpoints).
  - **`grpc_server.py`**: Skeleton/in-progress channel for future client-server RPC flows.
  - **`protos/`**: Directory containing all `.proto` definitions shared between FE and BE.

### 1b. GRPC Rules
- **Protocol**: HTTP/2 with Protocol Buffers (Probobuf).
- **Scope**:
    1.  **Frontend ↔ Backend**: Planned for high-throughput RPC and streaming use cases.
    2.  **Retrieval (RAG)**: May be exposed via gRPC when retrieval service is decoupled.
    3.  **Vector DB (Qdrant)**: Backend connects to Qdrant using its gRPC interface for performance.


### 2. Database / Memory Store (`db/`)
**Role:** Persistence Implementation
- **Purpose:** Implements the `MemoryPort` to save and retrieve state.
- **File:** `memory_store.py`
- **Implementation:**
  - Could use **Redis** for fast, ephemeral session storage.
  - Could use **SQLite/PostgreSQL** for persistent history.
  - Maps Domain `Conversation` objects to database rows/documents and back.

### 3. LLM Providers (`llm_providers/`)
**Role:** AI Intelligence Implementation
- **Purpose:** Implements the `LLMPort` to generate text.
- **Components:**
  - **`openai_client.py`**: Adapter for the OpenAI API (GPT-4, etc.).
  - **`embedding_client.py`**: Adapter for generating vector embeddings (e.g., `text-embedding-ada-002`).

### 4. RAG (Retrieval-Augmented Generation) (`rag/`)
**Role:** Knowledge Retrieval
- **Purpose:** Implements `RetrieverPort` to find relevant context.
- **Components:**
  - **`vector_store.py`**: Manages the vector database (FAISS, Chroma, Pinecone). Handles adding documents and similarity search.
  - **`retriever.py`**: Logic to query the vector store and format results for the Application layer.

### 5. Tools (`tools/`)
**Role:** External Utilities
- **Purpose:** Implements `ToolPort` for specific functional capabilities.
- **Components:**
  - **`kpi_calculator.py`**: Logic/Formulae for calculating business metrics.
  - **`ab_simulator.py`**: Simulation logic for A/B testing scenarios.
  - **`portfolio_pack.py`**: Utilities for managing investment portfolios.

### 6. Monitoring (`monitoring/`)
**Role:** Observability
- **Purpose:** Ensures the system is healthy and debuggable.
- **Components:**
  - **`logging.py`**: Configures structured logging (JSON format).
  - **`tracing.py`**: (Optional) OpenTelemetry or similar for tracing request flows across services.

### 7. NLP (`nlp/`)
**Role:** Natural Language Processing Utilities
- **Purpose:** Helper functions for text analysis before/after LLM calls.
- **Components:**
  - **`intent_detector.py`**: Heuristic or model-based classification of user intent ("Is the user asking for help?").
  - **`text_processor.py`**: Cleaning, chunking, and formatting text for RAG or prompts.

### 8. External Clients (`grpc_clients/`)
**Role:** Outbound Communication
- **Purpose:** If the backend needs to call other services (e.g., a separate specialized microservice or the Frontend for notifications).
- **File:** `frontend_client.py` (if bidirectional streaming is needed).

### 9. Communication Protocols (Rules)
- **Primary Transport (current runtime)**: REST (FastAPI).
- **Secondary/Planned Transport**: gRPC (Google Remote Procedure Call).
- **IDL for gRPC**: Protocol Buffers header files (`.proto`) are the source of truth for gRPC schemas.
- **Tools**: Use `protoc` or `buf` to generate Python (Backend) and TypeScript (Frontend) stubs.
- **Retrieval**: When the Application Layer requests context, it MAY use a gRPC client to query a standalone RAG service (if decoupled) or simply expose the Retrieval data map to the Frontend via gRPC.

---

## Infrastructure Workflows

### 1. Dependency Injection (Wiring)
- In `api/main.py`, the specific implementations (e.g., `OpenAIClient`, `RedisMemoryStore`) are instantiated.
- These instances are passed into the Application services (`ChatService`, `SessionManager`).
- This ensures the Application layer remains decoupled from specific technologies.

### 2. Request Handling
- `rest_routes.py` currently receives HTTP/JSON requests and maps them to Application services.
- `grpc_server.py` remains available for incremental RPC adoption once service definitions are finalized.
