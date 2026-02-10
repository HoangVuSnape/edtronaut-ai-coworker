edtronaut-ai-coworker/
├── backend/
│   ├── src/
│   │   └── coworker_api/
│   │       ├── __init__.py
│   │       ├── config.py                 # Load env/YAML chung
│   │       │
│   │       ├── domain/                   # DOMAIN LAYER
│   │       │   ├── __init__.py
│   │       │   ├── models.py             # Conversation, Turn, NPC, ScenarioState, Hint
│   │       │   ├── exceptions.py         # Domain-level errors
│   │       │   ├── memory/               # Domain view of memory
│   │       │   │   ├── __init__.py
│   │       │   │   └── schemas.py        # State schema, summary objects
│   │       │   ├── prompts/              # System prompts, templates (Gucci CEO/CHRO/EB&IC)
│   │       │   │   ├── __init__.py
│   │       │   │   ├── gucci_ceo.py
│   │       │   │   ├── gucci_chro.py
│   │       │   │   └── gucci_eb_ic.py
│   │       │   └── ports.py              # LLMPort, RetrieverPort, ToolPort, MemoryPort
│   │       │
│   │       ├── application/              # APPLICATION LAYER (use-cases, orchestration)
│   │       │   ├── __init__.py
│   │       │   ├── chat_service.py       # Use-case: user interacts with NPC
│   │       │   ├── director_service.py   # Use-case: supervisor analyzes conversation
│   │       │   ├── evaluation_service.py # (optional) đánh giá competency/rubric
│   │       │   ├── ingest_documents_service.py  # Build vector store from raw docs
│   │       │   ├── reset_memory_service.py      # Clear session / memory
│   │       │   └── session_manager.py    # Orchestrate MemoryPort, load/save Conversation
│   │       │
│   │       ├── infrastructure/           # INFRASTRUCTURE LAYER
│   │       │   ├── __init__.py
│   │       │   ├── api/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── main.py           # FastAPI entrypoint (REST + gRPC server bootstrap)
│   │       │   │   ├── rest_routes.py    # /health, /debug, etc. (REST optional)
│   │       │   │   └── grpc_server.py    # gRPC service implementation (front ↔ back)
│   │       │   │
│   │       │   ├── grpc_clients/
│   │       │   │   ├── __init__.py
│   │       │   │   └── frontend_client.py # (optional) nếu backend gọi ngược sang FE/microservice khác
│   │       │   │
│   │       │   ├── db/
│   │       │   │   ├── __init__.py
│   │       │   │   └── memory_store.py   # Redis/sqlite implementation for MemoryPort
│   │       │   │
│   │       │   ├── llm_providers/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── openai_client.py  # implements LLMPort
│   │       │   │   └── embedding_client.py
│   │       │   │
│   │       │   ├── rag/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── vector_store.py   # FAISS/Chroma/Pinecone
│   │       │   │   └── retriever.py      # implements RetrieverPort
│   │       │   │
│   │       │   ├── tools/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── kpi_calculator.py # Tool implementations for ToolPort
│   │       │   │   ├── ab_simulator.py
│   │       │   │   └── portfolio_pack.py
│   │       │   │
│   │       │   ├── monitoring/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── logging.py
│   │       │   │   └── tracing.py
│   │       │   │
│   │       │   └── nlp/
│   │       │       ├── __init__.py
│   │       │       ├── intent_detector.py
│   │       │       └── text_processor.py
│   │       │
│   │       └── utils/
│   │           ├── __init__.py
│   │           └── helpers.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_coworker_api.py
│   │
│   ├── configs/
│   │   ├── default.yml
│   │   ├── npc_gucci.yml
│   │   └── logging.yml
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── grpc_client.ts     # gRPC-web client kết nối backend
│   │   │   └── rest_client.ts     # (optional) REST fallback
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── NpcTogglePanel.tsx
│   │   │   ├── HintBanner.tsx
│   │   │   └── SimulationLayout.tsx
│   │   └── styles/
│   └── public/
│       └── index.html
│
├── docs/
├── notebooks/
├── .github/
├── CLAUDE.md
├── README.md
└── pyproject.toml
