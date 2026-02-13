# Edtronaut AI Coworker — Setup Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| **Docker Desktop** | ≥ 24.0 | `docker --version` |
| **Docker Compose** | ≥ 2.20 (bundled) | `docker compose version` |
| **Git** | any | `git --version` |

> [!TIP]
> For local development without Docker, also install **Node.js ≥ 20** and **UV** (`pip install uv`).

---

## Option A: Docker Compose (One-Command Start)

### Step 1 — Clone & Configure

```bash
git clone https://github.com/your-org/edtronaut-ai-coworker.git
cd edtronaut-ai-coworker

# Create your .env file
cp .env.example .env
```

Edit `.env` and fill in your **API key** (Gemini is the default — free tier available!):

```
# Gemini is default and FREE!
GEMINI_API_KEY=your-gemini-api-key-here
```

> [!TIP]
> Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey)

### Step 2 — Start Everything

```bash
docker compose up --build
```

This spins up **5 services**:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | React UI |
| **Backend REST** | http://localhost:8000 | FastAPI health/info |
| **Backend gRPC** | localhost:50051 | Business logic RPCs |
| **PostgreSQL** | localhost:5432 | Relational data |
| **Redis** | localhost:6379 | Session memory |
| **Qdrant** | localhost:6333 / 6334 | Vector search |

### Step 3 — Verify

```bash
# Check all containers are healthy
docker compose ps

# Test backend health
curl http://localhost:8000/health
# → {"status":"healthy","service":"edtronaut-ai-coworker","version":"0.1.0"}

# Test backend info
curl http://localhost:8000/info
# → Shows LLM model + available personas

# Open frontend
# Visit http://localhost:3000 in your browser
```

### Step 4 — Stop

```bash
# Stop all services (keep data)
docker compose down

# Stop and DELETE all data
docker compose down -v
```

---

## Option A+ : Development Mode (Hot Reload)

For live code editing with auto-reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This will:
- **Backend**: Mount `src/` and `configs/` as volumes, run with `--reload`
- **Frontend**: Use Vite dev server with HMR instead of Nginx
- Changes to source files will auto-reload both services

---

## Switching LLM Providers

The backend supports **4 LLM providers** out of the box:

| Provider | Models | Embedding | Free Tier |
|----------|--------|-----------|-----------|
| **gemini** (default) | `gemini-2.0-flash`, `gemini-pro` | `text-embedding-004` | ✅ Yes |
| **openai** | `gpt-4o`, `gpt-4o-mini` | `text-embedding-3-small` | ❌ Paid |
| **deepseek** | `deepseek-chat`, `deepseek-r1-0528` | ❌ (uses fallback) | ✅ Free credits |
| **zhipu** | `glm-4.5`, `glm-4.6` | `embedding-3` | ✅ Free credits |

### Step 1 — Set the API key in `.env`

```bash
# Uncomment and set the key for your chosen provider:
GEMINI_API_KEY=your-key
# OPENAI_API_KEY=sk-your-key
# DEEPSEEK_API_KEY=your-key
# ZHIPU_API_KEY=your-key
```

### Step 2 — Change the provider in `backend/configs/default.yml`

```yaml
llm:
  provider: "deepseek"     # ← change to: openai, gemini, deepseek, zhipu
  model: ""                # leave empty for provider default, or specify

embedding:
  provider: "gemini"       # ← must support embeddings (not deepseek)
  model: ""
```

> [!IMPORTANT]
> DeepSeek has no embedding API. If using DeepSeek for LLM, keep embedding provider as `gemini` or `openai`.

### Example: DeepSeek chat + Gemini embeddings

```yaml
# default.yml
llm:
  provider: "deepseek"
  model: "deepseek-chat"
embedding:
  provider: "gemini"
```

```bash
# .env
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=AIza-xxx
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port already in use | Stop conflicting service or change ports in `docker-compose.yml` |
| Backend unhealthy | Check `docker compose logs backend` — usually missing API key in `.env` |
| Frontend can't reach backend | Ensure backend is healthy first: `docker compose ps` |
| Qdrant won't start | Increase Docker memory limit to ≥ 4GB |
| Redis connection refused | Check `docker compose logs redis` |

### Useful Commands

```bash
# View logs for a specific service
docker compose logs -f backend

# Rebuild a single service
docker compose build backend

# Enter a running container
docker compose exec backend bash

# Run backend tests inside container
docker compose exec backend python -m pytest tests/ -v
```
