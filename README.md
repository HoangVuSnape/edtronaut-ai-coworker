# Edtronaut AI Coworker Engine

Welcome to the **Edtronaut AI Coworker** project. This repository contains the source code for an AI-enabled Job Simulation Platform, allowing users (learners) to collaborate with dynamic, persona-driven AI agents (NPCs) in simulated workplace scenarios.

## 🚀 Key Features
- **Intelligent NPC Simulation**: Interact with personas like the Gucci CEO or Regional Managers.
- **Retrieval-Augmented Generation (RAG)**: AI agents pull real-time policies and frameworks from a vector database (Qdrant).
- **Director / Supervisor Agent**: Invisible orchestrator that monitors pacing and ensures the conversation stays on track.
- **Extensive Observability**: Powered by Langfuse to monitor AI latency, context retrieval, and decision workflows.

---

## 🏗 Technology & Architecture

The application is built using a modern, scalable tech stack, split into a frontend UI and a robust backend engine.

### Technology Stack
- **Frontend**: Next.js (React), TailwindCSS, gRPC-Web / REST for API integration.
- **Backend**: Python, FastAPI, and gRPC.
- **Databases**: 
  - **PostgreSQL**: Primary data store (managed via Alembic / SQLAlchemy).
  - **Redis**: Fast, hot-state session caching.
  - **Qdrant**: High-performance Vector Store for RAG representations.
- **Auth Provider**: Supabase (Handles Google / external OAuth flows mapping to customized JWTs).
- **AI / LLMOps**: Langfuse (Tracing graph execution), OpenAI-compatible LLM endpoints (OpenAI, Gemini, DeepSeek).

### Backend Design: Clean Architecture
The backend strictly adheres to **Clean Architecture** patterns to decouple business logic from external frameworks:
1. **Domain Layer**: Houses core entities (`Conversation`, `Turn`, `NPC`) and strict interfaces (`LLMPort`, `RetrieverPort`). Contains **ZERO** dependencies on FastAPI or PostgreSQL.
2. **Application Layer**: Contains Use Cases and Services (e.g., `ChatService`, `SessionManager`, `DirectorService`). Coordinates the Domain with the outer world.
3. **Infrastructure Layer**: Concrete implementations of Domain ports. Includes FastAPI routes, Supabase JWT validators, SQL Repositories, and the Qdrant retriever.

---

## 🛠 Step-by-Step Setup Guide

Follow these steps to run the simulation engine locally.

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Node.js](https://nodejs.org/en/) (v18+)
- [Python 3.10+](https://www.python.org/) & [uv](https://github.com/astral-sh/uv) (for ultra-fast python package management)

### 1. Boot Supporting Infrastructure
First, start the necessary databases and tracing tools via Docker.
```bash
docker compose up -d
```
*This will start PostgreSQL, Redis, Qdrant, and optionally Langfuse.*

### 2. Configure Environment Variables
You need `.env` files in both the frontend and backend.
- **Backend**: Copy `backend/.env.example` to `backend/.env` and add your LLM API keys (e.g., `OPENAI_API_KEY`) and Supabase secrets.
- **Frontend**: Copy `frontend/.env.local.example` to `frontend/.env.local` and add your Supabase public keys.

### 3. Setup and Run the Backend
Navigate to the backend directory, install dependencies, and start the API server.
```bash
cd backend
uv sync
uv run fastapi dev src/coworker_api/infrastructure/api/main.py --host 0.0.0.0 --port 8000
```
*Note: The backend automatically runs Alembic database migrations on startup.*

### 4. Seed Knowledge Base (RAG)
For the AI to have context (e.g., Gucci Competency Frameworks), seed the vector database:
```bash
cd backend
uv run python scripts/seed_rag.py --dir ../docs/dataTestRAG
```
*This script will chunk and embed the `.md` files, pushing them directly into Qdrant.*

### 5. Setup and Run the Frontend
In a new terminal, start the Next.js client.
```bash
cd frontend
npm install
npm run dev
```

The application should now be accessible at `http://localhost:3000`.

---

## 📖 Further Reading

For deeper dives into specific components, refer to our comprehensive documentation:
- **[Architecture & Flow details](docs/Architecture.md)**
- **[Backend V2 Specs](docs/BACKEND_DOCS_V2/01_Overview.md)**
- **[Frontend Architecture](docs/Frontend.md)**
- **[Langfuse Tracing Setup](docs/BACKEND_DOCS_V2/09_Tracing_And_Logging.md)**
