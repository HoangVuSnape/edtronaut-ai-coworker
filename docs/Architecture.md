Dưới đây là bản Architecture.md đã “nâng cấp” với 3 layer: **Domain / Application / Infrastructure**, giữ nguyên cấu trúc thư mục của bạn nhưng giải thích lại theo clean architecture. Bạn chỉ cần copy paste và chỉnh nhẹ wording nếu muốn.

***

# Cấu Trúc Dự Án (Project Architecture)

Dự án `edtronaut-ai-coworker` được thiết kế theo hướng **Clean Architecture/Hexagonal**, với ba lớp chính:

- **Domain layer** – mô hình hoá bài toán mô phỏng AI Co‑worker: NPC, hội thoại, kịch bản, Director.  
- **Application layer** – orchestrate luồng nghiệp vụ: use‑case “user chat với NPC”, “Director giám sát”, quản lý session.  
- **Infrastructure layer** – FastAPI, LLM, Vector DB, frontend, notebooks, CI… hiện thực hoá các “cổng” (ports) của domain/application.  

Cách chia này giúp tách rõ **logic sản phẩm** khỏi **chi tiết kỹ thuật** (LLM nào, DB gì), dễ test và dễ mở rộng sang simulation khác (không chỉ Gucci). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

***

## 1. Sơ đồ thư mục tổng quan

```text
edtronaut-ai-coworker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── domain/          # ★ Domain layer
│   │   ├── agents/          # ★ Domain + Application (orchestration logic)
│   │   ├── pipelines/       # Infrastructure (RAG, tools, NLP)
│   │   ├── models/          # Infrastructure adapters (LLM, embeddings)
│   │   ├── data/            # Infrastructure (data loading, vector store)
│   │   ├── services/        # ★ Application layer (use-cases, session)
│   │   └── utils/
│   ├── tests/
│   ├── configs/
│   └── requirements.txt
│
├── frontend/
├── docs/
├── notebooks/
├── .github/
├── CLAUDE.md
├── README.md
└── pyproject.toml
```

***

## 2. Domain Layer – Mô hình hoá Co‑worker Engine

Domain layer chứa **khái niệm cốt lõi của simulation** và logic thuần business, không phụ thuộc vào FastAPI, OpenAI hay FAISS. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

```text
backend/app/domain/
├── models.py      # Conversation, Turn, NPC, ScenarioState, Hint
└── ports.py       # LLMPort, RetrieverPort, ToolPort (abstract interfaces)
```

- `models.py` (ví dụ):  
  - `NPC`: id, role (CEO/CHRO/EB&IC), goals & KPIs, tools được phép dùng.  
  - `Turn`: speaker (user/npc/director), text, timestamp, safety_flags, intents.  
  - `Conversation`: danh sách `Turn`, trạng thái nhiệm vụ.  
  - `ScenarioState`: tiến độ trong simulation (đã đụng Vision/Entrepreneurship/Passion/Trust? đã nói về mobility?).  
  - `Hint`: nội dung gợi ý Director gửi cho user.  

- `ports.py`:  
  - `LLMPort`: interface sinh text (`generate(prompt) -> str`).  
  - `RetrieverPort`: interface truy xuất context (`retrieve(query, persona_id)`).  
  - `ToolPort`: interface gọi tool (KPI calculator, A/B simulator…).  

Nhờ đó, domain có thể được unit test mà không cần API key hay kết nối mạng. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

***

## 3. Application Layer – Orchestration & Use‑cases

Application layer điều phối domain models và ports để xử lý các use‑case như “user chat với NPC Gucci CHRO”, “Director phát hiện user bị kẹt”. Nó không biết chi tiết OpenAI/Pinecone, chỉ gọi qua interfaces. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

```text
backend/app/services/
├── chat_service.py      # Use-case: InteractWithNpc
└── session_manager.py   # Quản lý session, load/save Conversation
```

- `chat_service.py`:  
  - Nhận `npc_id`, `user_message`, `session_id`.  
  - Lấy `Conversation` hiện tại qua `session_manager`.  
  - Gọi **Director** để phân tích xem user có bị kẹt / off‑track không.  
  - Gọi **NPCAgent** (ở `agents/`) với `LLMPort`, `RetrieverPort`, `ToolPort` để sinh câu trả lời.  
  - Cập nhật `Conversation` (thêm `Turn` mới, update `ScenarioState`) và lưu lại.  

- `session_manager.py`:  
  - Lưu state vào in‑memory/Redis/DB (tuỳ implementation infra).  

### Agents như “application logic đặc thù”

`agents/` nằm giữa domain và infra, chứa logic NPC & Director nhưng vẫn dựa trên ports/domain:

```text
backend/app/agents/
├── personas/
│   ├── base.py
│   ├── gucci_ceo.py
│   ├── gucci_chro.py
│   └── gucci_eb_ic.py
├── npc_agent.py         # Dùng LLMPort, RetrieverPort, ToolPort
├── director_agent.py    # Dùng Conversation/domain logic để detect stuck
└── state.py             # Kiểu state sử dụng trong domain Conversation
```

- `npc_agent.py`:  
  - Build prompt từ `persona`, `Conversation` summary, context từ RAG (qua `RetrieverPort`).  
  - Gọi `LLMPort.generate()` để sinh câu trả lời.  
  - Tạo `Turn` mới và `SafetyFlags` cho domain.  

- `director_agent.py`:  
  - Đọc `Conversation`, phát hiện loop, user bị kẹt, off‑topic, potential jailbreak.  
  - Sinh `Hint` (domain object) để gắn vào response hoặc hiển thị ở UI.  

***

## 4. Infrastructure Layer – FastAPI, LLM, Vector DB, Tools

Infrastructure layer hiện thực hoá `ports` và expose hệ thống qua HTTP/API. Đây là phần có thể thay thế (OpenAI → Claude, FAISS → Pinecone…) mà không đổi domain/application. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

### 4.1. API & Core

```text
backend/app/main.py          # Khởi chạy FastAPI
backend/app/api/
  ├── deps.py                # Khởi tạo LLMPort, RetrieverPort, ToolPort, session_manager
  ├── routes_npc.py          # POST /npc/{npc_id}/chat -> gọi chat_service
  ├── routes_director.py     # /director/debug (optional)
  └── routes_health.py       # /health
backend/app/core/
  ├── config.py              # cấu hình (env, YAML)
  └── security.py            # API key, input validation, basic safety
```

### 4.2. RAG, Tools, NLP (adapters “bên ngoài”)

```text
backend/app/pipelines/
├── rag/
│   ├── embedder.py          # Hiện thực EmbeddingPort bằng model cụ thể
│   ├── retriever.py         # Hiện thực RetrieverPort (FAISS/Chroma/Pinecone)
│   └── generator.py         # RAG orchestration (có thể dùng thẳng trong infra hoặc agent)
├── tools/
│   ├── kpi_calculator.py
│   ├── ab_simulator.py
│   └── portfolio_pack.py
└── nlp/
    ├── intent_detector.py
    └── processor.py
```

### 4.3. LLM, Embedding, Data Access

```text
backend/app/models/
  ├── llm_client.py          # OpenAI/Claude/Gemini client implement LLMPort
  ├── embedding_client.py    # Embedding model adapter
  └── inference.py           # Helpers

backend/app/data/
  ├── raw/
  ├── processed/
  ├── loader.py              # Nạp docs Gucci, chunking
  └── vector_store.py        # Khởi tạo vector DB và map vào RetrieverPort
```

### 4.4. Utils, Configs, Tests

```text
backend/app/utils/
  ├── logger.py
  ├── tracing.py
  └── helpers.py

backend/configs/
  ├── default.yml
  ├── npc_gucci.yml          # Cấu hình persona, tools, model params cho Gucci
  └── logging.yml

backend/tests/
  ├── test_npc_agent.py
  ├── test_director_agent.py
  ├── test_rag_pipeline.py
  └── test_api.py
```

***

## 5. Frontend, Docs, Notebooks, CI (phần Infrastructure bổ trợ)

```text
frontend/            # React UI: ChatWindow, NpcTogglePanel, HintBanner
docs/                # README_backend, README_frontend, NPC_DESIGN, API_DOCS, ARCHITECTURE
notebooks/           # R&D cho RAG: chunking, embedding, hits@k demo
.github/             # CI/CD (ci.yml), copilot-instructions
README.md            # Overview dự án, hướng dẫn quickstart
```

Frontend và notebooks cũng thuộc Infrastructure (delivery & R&D), tương tác với Application layer qua HTTP API và data pipeline. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/104041347/14eb2b42-60f7-4af6-b211-caaa25fbe0d4/Architecture.md)

***

Bạn có thể:

- Thêm thư mục `backend/app/domain/` thật (dù code rất mỏng) để khớp với Architecture.  
- Trong slide, vẽ 3 vòng Domain – Application – Infrastructure và map các folder như trên để thể hiện rõ bạn hiểu clean architecture.