POST http://localhost:8000/api/auth/login
Content-Type: application/json
{
  "email": "admin@test.com",
  "password": "Admin@123"
}



------

npc_id: gucci_ceo


{
  "sessionId": "session-001",
  "message": "Hello, who are you?",
  "useRag": true
}

-----

# Tự động tạo venv và cài mọi thứ (bao gồm cả dev dependencies)
uv sync
# Chạy test qua uv
uv run pytest tests/ -v