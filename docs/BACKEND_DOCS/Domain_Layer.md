# Domain Layer Documentation

## Overview
The **Domain Layer** is the heart of the application, encapsulating the core business logic, rules, and entities. It must be independent of external frameworks, databases, or UI. It defines *what* the system does, not *how* it does it.

## Key Components

### 1. Models (`models.py`)
**Role:** Core Entities
- **Purpose:** Defines the fundamental data structures and business objects.
- **Key Entities:**
  - **`Conversation`**: Represents a chat session, holding a list of `Turn`s.
  - **`Turn`**: A single exchange (User input + AI response).
  - **`NPC`**: Represents an AI persona (e.g., Gucci CEO), including traits and style.
  - **`ScenarioState`**: Tracks the progression of a specific scenario (e.g., "Negotiation Phase 1").
  - **`Hint`**: Contextual suggestion generated for the user.

### 2. Exceptions (`exceptions.py`)
**Role:** Domain-Specific Errors
- **Purpose:** Standardizes error handling within the business logic.
- **Examples:**
  - `ConversationNotFoundError`: Accessing a non-existent session.
  - `InvalidTurnError`: Malformed user input or state transition.
  - `PersonaConfigurationError`: Missing required traits for an NPC.

### 3. Memory (`memory/`)
**Role:** State Representation
- **Purpose:** Defines how conversation history and state are structured for the domain's use.
- **Components:**
  - **`schemas.py`**: Pydantic models or clean classes defining the shape of memory objects (e.g., `MemoryState`, `Summary`).
  
### 4. Prompts (`prompts/`)
**Role:** Persona & Logic Templates
- **Purpose:** Stores the templates and logic for generating AI responses.
- **Files:**
  - **`gucci_ceo.py`**: Prompts defining the CEO persona (strategic, demanding).
  - **`gucci_chro.py`**: Prompts defining the CHRO persona (people-focused, policy-driven).
  - **`gucci_eb_ic.py`**: Prompts for Investment Banker / Individual Contributor.
  - **`__init__.py`**: Registry or factory to retrieve prompts by persona name.

### 5. Ports (`ports.py`)
**Role:** Dependency Inversion Interfaces
- **Purpose:** Defines the contracts (abstract base classes/interfaces) that the Infrastructure layer MUST implement. The Domain layer calls these ports, unaware of the implementation details.
- **Key Ports:**
  - **`LLMPort`**: Interface for generating text from an LLM.
    - *Method:* `generate(prompt: str) -> str`
  - **`RetrieverPort`**: Interface for fetching relevant documents (RAG).
    - *Method:* `retrieve(query: str, k: int) -> List[Document]`
  - **`ToolPort`**: Interface for external tools (calculators, simulators).
    - *Method:* `execute(tool_name: str, args: dict) -> Any`
  - **`MemoryPort`**: Interface for persisting and loading state.
    - *Method:* `save_conversation(conversation: Conversation)`
    - *Method:* `load_conversation(session_id: str) -> Conversation`

---

## Domain Rules & Logic

1.  **Immutability:** Core entities should ideally be immutable or have controlled state transitions.
2.  **Pure Python:** No external dependencies (like SQLalchemy, Requests, etc.) should leak into this layer.
3.  **Validation:** All data entering the Domain layer (e.g., creating a `Conversation` object) must be validated here.
