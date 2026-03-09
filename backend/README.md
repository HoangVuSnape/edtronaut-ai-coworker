# Edtronaut AI Coworker — Backend

FastAPI + gRPC backend for the AI Coworker simulation platform.

See [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) for setup instructions.

## Database Migrations

Schema changes are managed with Alembic.

- Apply latest migration:
  - `uv run alembic -c alembic.ini upgrade head`
- Show current head revision:
  - `uv run alembic -c alembic.ini heads`
