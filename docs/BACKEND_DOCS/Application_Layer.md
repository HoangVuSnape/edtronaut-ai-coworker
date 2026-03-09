# Application Layer Workflow & Structure

## Overview
The **Application Layer** serves as the core orchestration center of the backend, bridging the **Domain Layer** (business logic) and the **Infrastructure Layer** (external systems like databases and LLMs). It implements specific use cases and workflows required by the application.

## Key Components & Responsibilities

Based on the architecture definition, the Application Layer consists of the following services:

### 1. `chat_service.py`
**Role:** Core Interaction Handler
- **Purpose:** Manages the primary use case where a user interacts with an AI NPC (e.g., Gucci CEO).
- **Responsibilities:**
  - Receive user input from the API layer.
  - Retrieve conversation context via `session_manager`.
  - Invoke the appropriate Domain Logic (e.g., specific persona prompts).
  - Call the `LLMPort` (Infrastructure) to generate a response.
  - Save the updated conversation state.

### 2. `director_service.py`
**Role:** Supervisor & Analysis
- **Purpose:** Acts as a "Director" or supervisor that oversees the conversation.
- **Responsibilities:**
  - Analyze the ongoing conversation for quality, tone, or adherence to guidelines.
  - Provide meta-feedback or instructions to the NPC or the user.
  - Trigger interventions if the conversation goes off-track.

### 3. `evaluation_service.py` (Optional)
**Role:** Assessment Engine
- **Purpose:** Evaluates the user's performance based on rubrics or competencies.
- **Responsibilities:**
  - analyze the interaction logs after a session.
  - Score the user on specific skills (e.g., negotiation, empathy).
  - Generate a report or feedback summary.

### 4. `ingest_documents_service.py`
**Role:** Knowledge Base Builder (RAG)
- **Purpose:** Processes raw documents to build the vector store for Retrieval-Augmented Generation.
- **Responsibilities:**
  - Read raw documents (PDFs, text files).
  - Chunk and process text using `text_processor` (Infrastructure/NLP).
  - Generate embeddings via `embedding_client` (Infrastructure).
  - Store vectors in the `vector_store` (Infrastructure).

### 5. `reset_memory_service.py`
**Role:** Session Lifecycle Management
- **Purpose:** Handles requests to clear or reset the conversation state.
- **Responsibilities:**
  - Clear history from the `MemoryPort`.
  - Reset any session-specific variables or flags.
  - Ensure a clean slate for a new simulation run.

### 6. `session_manager.py`
**Role:** State Orchestrator
- **Purpose:** Centralizes the management of session state and memory persistence.
- **Responsibilities:**
  - Abstract the `MemoryPort` operations (load/save).
  - ensure data consistency for the `Conversation` model.
  - Manage session timeouts or concurrent access if necessary.

---

## Detailed Workflows

### Workflow 1: User Chat Interaction
**Trigger:** User sends a message via Frontend.
1.  **API Layer** receives the request and calls `chat_service.process_message(user_id, message)`.
2.  **`chat_service`** calls **`session_manager`** to load the current `Conversation` history.
3.  **`chat_service`** retrieves relevant context (RAG) via `RetrieverPort` (if applicable).
4.  **`chat_service`** constructs the prompt using Domain models (e.g., `gucci_ceo.py`).
5.  **`chat_service`** invokes **`LLMPort`** to get the AI response.
6.  **`chat_service`** updates the `Conversation` object with the new turn.
7.  **`chat_service`** calls **`session_manager`** to save the updated state.
8.  **Result** is returned to the API layer.

### Workflow 2: Document Ingestion (RAG Setup)
**Trigger:** Admin uploads new knowledge documents.
1.  **API Layer** receives files and calls `ingest_documents_service.ingest(files)`.
2.  **`ingest_documents_service`** parses the files into text chunks.
3.  For each chunk, it calls **`embedding_client`** to generate vector embeddings.
4.  It calls **`vector_store`** to save the embeddings and metadata.
5.  **Result:** Knowledge base is updated and ready for retrieval.

### Workflow 3: Session Reset
**Trigger:** User clicks "Restart Simulation".
1.  **API Layer** calls `reset_memory_service.reset_session(session_id)`.
2.  **`reset_memory_service`** commands the `MemoryPort` to delete/archive data for `session_id`.
3.  **Result:** Next interaction starts with a generic/initial state.
