# Local Testing Guide

This document provides examples and commands for testing the backend API and running unit tests locally.

---

## 1. Local API Testing

You can easily interact with the backend API using tools like Postman, cURL, or the VS Code REST Client extension. Ensure your local FastAPI server is running (usually on port `8000`).

### 1.1. Authentication (Login)

Use the login endpoint to retrieve a JWT Bearer access token.

**Request:**
```http
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "email": "admin@test.com",
  "password": "Admin@123"
}
```

*Note: Copy the `access_token` from the JSON response to authenticate following requests.*

### 1.2. Chat Interaction

Interact with a specific NPC persona by passing its ID in the URL structure.

**Request Details:**
- **URL Parameter (`npc_id`)**: The ID of the persona (e.g., `gucci_ceo`, `gucci_chro`).
- **Authorization**: Requires your previously acquired `access_token`.

**Request:**
```http
POST http://localhost:8000/api/npc/gucci_ceo/chat
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "sessionId": "session-001",
  "message": "Hello, who are you?",
  "useRag": true
}
```
*Tip: `sessionId` helps the system maintain conversation context. Keep it the same across multiple turns in the same conversation.*

---

## 2. Automated Testing

We use `uv`—a lightning-fast Python package installer and resolver—to manage our environment and execute the testing suite using `pytest`.

### 2.1. Environment Synchronization
This command automatically creates the virtual environment `.venv` and installs all dependencies (including `dev` tools) defined in `pyproject.toml` or `uv.lock`.

```bash
uv sync
```

### 2.2. Running the Test Suite
Execute the testing suite against the `tests/` directory with verbose (`-v`) output for clear and distinct logs.

```bash
uv run pytest tests/ -v
```