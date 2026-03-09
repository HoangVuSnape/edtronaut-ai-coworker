# Domain Layer

## Source location

- `backend/src/coworker_api/domain`

## Responsibility

The Domain Layer contains **core business rules and models**. It must not depend on databases, HTTP, or external SDKs. It defines the interfaces that the Infrastructure layer must implement.

## Main components

### Models

File: `backend/src/coworker_api/domain/models.py`

- `Conversation`: aggregate root for a chat session.
- `Turn`: one exchange in the conversation.
- `NPC`: AI persona definition.
- `ScenarioState`: scenario progression state.
- `Hint`: contextual hint for the user.
- `Speaker`, `SimulationStatus`, `UserRole`: enums.

### Ports (interfaces)

File: `backend/src/coworker_api/domain/ports.py`

- `LLMPort`: LLM text generation (`generate`, `generate_stream`).
- `RetrieverPort`: RAG retrieval and document ingest.
- `EmbeddingPort`: embedding generation.
- `ToolPort`: external tools (KPI, A/B, portfolio).
- `MemoryPort`: session persistence and retrieval.

### Exceptions

File: `backend/src/coworker_api/domain/exceptions.py`

- `DomainException` base with gRPC `StatusCode` mapping.
- Error groups: NotFound, Auth, Validation, ResourceLimits, ExternalService.

### Prompt registry

File: `backend/src/coworker_api/domain/prompts/__init__.py`

- Persona registry for `gucci_ceo`, `gucci_chro`, `gucci_eb_ic`.
- APIs: `get_persona_prompt`, `list_personas`.

### Memory schemas

File: `backend/src/coworker_api/domain/memory/schemas.py`

- `MemoryState`: hot session state (Redis).
- `ConversationSummary`: long-term summary structure.

## Principles

- No infrastructure imports in the domain.
- Core validation and rules belong here.
- Ports are the contracts between layers.
