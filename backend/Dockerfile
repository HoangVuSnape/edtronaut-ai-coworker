# ═══════════════════════════════════════════════════════
# Edtronaut AI Coworker — Backend Dockerfile
# Multi-stage build with UV for fast, reproducible installs
# ═══════════════════════════════════════════════════════

# ── Stage 1: Builder ──
FROM python:3.13-slim AS builder

# Install UV from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* README.md ./

# Install production dependencies only (no dev)
# --frozen ensures exact lockfile versions; falls back to resolution if no lockfile
RUN uv sync --frozen --no-dev --no-editable 2>/dev/null \
    || uv sync --no-dev --no-editable

# ── Stage 2: Runtime ──
FROM python:3.13-slim

# Security: non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

WORKDIR /app

# Copy the virtual env from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source and configs
COPY src/ ./src/
COPY configs/ ./configs/

# Set PATH so the venv Python is used
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Correct ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Expose REST + gRPC
EXPOSE 8000 50051

# Health check against REST /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI via uvicorn
CMD ["uvicorn", "coworker_api.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
