# Infrastructure Layer Documentation

## Overview
The **Infrastructure Layer** implements the technical details required to support the Application and Domain layers. It interacts with external systems (databases, APIs, LLM providers) and adapts them to the interfaces (Ports) defined in the Domain layer.

## Key Components

### 1. API (`api/`)
**Role:** Entry Point & Delivery Mechanism
- **Purpose:** Exposes the application logic to the outside world (Frontend).
- **Components:**
  - **`main.py`**: Factors the FastAPI application, wires up dependencies (DI), and starts the server.
  - **`rest_routes.py`**: Standard REST endpoints for health checks, debugging, or simple CRUD if needed.
  - **`grpc_server.py`**: The **SOLE** communication channel for all Client-Server interactions (Frontend ↔ Backend).
  - **`protos/`**: Directory containing all `.proto` definitions shared between FE and BE.

### 1b. GRPC Rules
- **Protocol**: HTTP/2 with Protocol Buffers (Probobuf).
- **Scope**:
    1.  **Frontend ↔ Backend**: All user interactions (Chat, Helpers, Auth).
    2.  **Retrieval (RAG)**: The search/retrieval API is exposed via gRPC.
    3.  **Vector DB (Qdrant)**: Backend connects to Qdrant using its gRPC interface for maximum performance.


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
- **Primary Transport**: gRPC (Google Remote Procedure Call).
- **IDL**: Protocol Buffers header files (`.proto`) must be the single source of truth for API schemas.
- **Tools**: Use `protoc` or `buf` to generate Python (Backend) and TypeScript (Frontend) stubs.
- **Retrieval**: When the Application Layer requests context, it MAY use a gRPC client to query a standalone RAG service (if decoupled) or simply expose the Retrieval data map to the Frontend via gRPC.

---

## Infrastructure Workflows

### 1. Dependency Injection (Wiring)
- In `api/main.py`, the specific implementations (e.g., `OpenAIClient`, `RedisMemoryStore`) are instantiated.
- These instances are passed into the Application services (`ChatService`, `SessionManager`).
- This ensures the Application layer remains decoupled from specific technologies.

### 2. Request Handling
- `grpc_server.py` receives a Protobuf message.
- It translates the message into a Domain object or primitive.
- It calls the appropriate Application Service method.
- It translates the result back to a Protobuf response.
