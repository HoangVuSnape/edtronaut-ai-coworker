from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from coworker_api.domain.exceptions import ConversationNotFoundError
from coworker_api.domain.models import Conversation, NPC
from coworker_api.infrastructure.api import rest_routes


def _test_settings():
    return SimpleNamespace(
        auth=SimpleNamespace(
            jwt_secret_key="unit-test-secret",
            jwt_algorithm="HS256",
            access_token_expire_minutes=15,
            supabase_jwt_secret="",
        ),
        rag=SimpleNamespace(enabled=True),
        app_name="test-app",
        app_version="0.0.1",
        llm=SimpleNamespace(model="test-model"),
    )


def _make_token(*, role: str = "admin", sub: str = "user-1", email: str = "user@example.com") -> str:
    settings = _test_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )


def _build_client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(rest_routes.router)
    monkeypatch.setattr(rest_routes, "get_settings", _test_settings)
    return TestClient(app)


def test_login_success_returns_jwt(monkeypatch):
    class FakeStore:
        async def get_user_auth_by_email(self, email: str):
            assert email == "admin@example.com"
            return {
                "id": "u-1",
                "email": "admin@example.com",
                "password_hash": rest_routes._hash_password("StrongPass123"),
                "role": "admin",
            }

    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: FakeStore())
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={"email": "ADMIN@example.com", "password": "StrongPass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"] == {
        "id": "u-1",
        "email": "admin@example.com",
        "role": "admin",
    }

    decoded = jwt.decode(
        body["access_token"],
        _test_settings().auth.jwt_secret_key,
        algorithms=[_test_settings().auth.jwt_algorithm],
    )
    assert decoded["sub"] == "u-1"
    assert decoded["role"] == "admin"
    assert decoded["email"] == "admin@example.com"


def test_login_invalid_password_returns_401(monkeypatch):
    class FakeStore:
        async def get_user_auth_by_email(self, email: str):
            return {
                "id": "u-1",
                "email": "admin@example.com",
                "password_hash": rest_routes._hash_password("CorrectPass123"),
                "role": "admin",
            }

    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: FakeStore())
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "WrongPass123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_users_endpoint_requires_auth(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get("/api/users")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"


def test_users_endpoint_forbids_non_admin(monkeypatch):
    client = _build_client(monkeypatch)

    token = _make_token(role="user")
    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_create_user_hashes_password_server_side(monkeypatch):
    class FakeStore:
        def __init__(self):
            self.captured_hash = ""

        async def create_user(self, *, email: str, password_hash: str, role: str = "user"):
            self.captured_hash = password_hash
            return {
                "id": "u-2",
                "email": email,
                "role": role,
                "created_at": "2026-02-15T00:00:00Z",
                "updated_at": "2026-02-15T00:00:00Z",
            }

    fake_store = FakeStore()
    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: fake_store)
    client = _build_client(monkeypatch)
    token = _make_token(role="admin", sub="admin-1", email="admin@example.com")

    response = client.post(
        "/api/users",
        json={
            "email": "new.user@example.com",
            "password": "StrongPass123",
            "role": "user",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "password_hash" not in body
    assert body["email"] == "new.user@example.com"
    assert fake_store.captured_hash
    assert fake_store.captured_hash != "StrongPass123"
    assert rest_routes._verify_password("StrongPass123", fake_store.captured_hash)


def test_create_user_db_error_does_not_leak_internal_message(monkeypatch):
    class FakeStore:
        async def create_user(self, *, email: str, password_hash: str, role: str = "user"):
            raise RuntimeError("duplicate key value violates unique constraint users_email_key")

    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: FakeStore())
    client = _build_client(monkeypatch)
    token = _make_token(role="admin")

    response = client.post(
        "/api/users",
        json={"email": "dupe@example.com", "password": "StrongPass123", "role": "user"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create user"
    assert "duplicate key" not in response.text.lower()


def test_users_create_requires_password_not_password_hash(monkeypatch):
    class FakeStore:
        async def create_user(self, *, email: str, password_hash: str, role: str = "user"):
            return {"id": "u-2", "email": email, "role": role}

    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: FakeStore())
    client = _build_client(monkeypatch)
    token = _make_token(role="admin")

    response = client.post(
        "/api/users",
        json={"email": "new.user@example.com", "password_hash": "fakehash", "role": "user"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_chat_auto_create_uses_authenticated_user_id(monkeypatch):
    class FakeSessionManager:
        def __init__(self):
            self.saved = None

        async def load_session(self, session_id: str):
            raise ConversationNotFoundError()

        async def save_session(self, conversation: Conversation):
            self.saved = conversation

    class FakeChatService:
        async def process_message(self, session_id: str, user_message: str, use_rag: bool = False):
            return {"response": "ok"}

    fake_session_manager = FakeSessionManager()
    fake_container = SimpleNamespace(
        chat_service=FakeChatService(),
        session_manager=fake_session_manager,
    )
    monkeypatch.setattr(rest_routes, "_get_container", lambda: fake_container)
    client = _build_client(monkeypatch)

    user_id = "11111111-1111-1111-1111-111111111111"
    token = _make_token(role="user", sub=user_id, email="user@example.com")
    response = client.post(
        "/api/npc/gucci_ceo/chat",
        json={"sessionId": "s-1", "message": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert fake_session_manager.saved is not None
    assert fake_session_manager.saved.user_id == user_id
    assert fake_session_manager.saved.user_id != "anonymous"


def test_chat_forbids_access_to_other_users_session(monkeypatch):
    class FakeSessionManager:
        async def load_session(self, session_id: str):
            return Conversation(
                id=session_id,
                user_id="owner-1",
                npc=NPC(name="gucci_ceo", role_title="Chief Executive Officer, Gucci"),
            )

        async def save_session(self, conversation: Conversation):
            return None

    class FakeChatService:
        async def process_message(self, session_id: str, user_message: str, use_rag: bool = False):
            return {"response": "should-not-run"}

    fake_container = SimpleNamespace(
        chat_service=FakeChatService(),
        session_manager=FakeSessionManager(),
    )
    monkeypatch.setattr(rest_routes, "_get_container", lambda: fake_container)
    client = _build_client(monkeypatch)

    token = _make_token(role="user", sub="other-user")
    response = client.post(
        "/api/npc/gucci_ceo/chat",
        json={"sessionId": "s-2", "message": "hi"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_get_session_forbidden_for_non_owner(monkeypatch):
    class FakeSessionManager:
        async def load_session(self, session_id: str):
            return Conversation(
                id=session_id,
                user_id="owner-1",
                npc=NPC(name="gucci_ceo", role_title="Chief Executive Officer, Gucci"),
            )

        async def delete_session(self, session_id: str):
            return True

    fake_container = SimpleNamespace(
        chat_service=object(),
        session_manager=FakeSessionManager(),
    )
    monkeypatch.setattr(rest_routes, "_get_container", lambda: fake_container)
    client = _build_client(monkeypatch)

    token = _make_token(role="user", sub="other-user")
    response = client.get(
        "/api/sessions/s-3",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_chat_uses_rag_setting_by_default(monkeypatch):
    class FakeSessionManager:
        async def load_session(self, session_id: str):
            return Conversation(
                id=session_id,
                user_id="11111111-1111-1111-1111-111111111111",
                npc=NPC(name="gucci_ceo", role_title="Chief Executive Officer, Gucci"),
            )

    class FakeChatService:
        def __init__(self):
            self.last_use_rag = None

        async def process_message(self, session_id: str, user_message: str, use_rag: bool = False):
            self.last_use_rag = use_rag
            return {"response": "ok"}

    fake_chat = FakeChatService()
    fake_container = SimpleNamespace(
        chat_service=fake_chat,
        session_manager=FakeSessionManager(),
    )
    monkeypatch.setattr(rest_routes, "_get_container", lambda: fake_container)
    client = _build_client(monkeypatch)

    token = _make_token(role="user", sub="11111111-1111-1111-1111-111111111111")
    response = client.post(
        "/api/npc/gucci_ceo/chat",
        json={"sessionId": "s-4", "message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert fake_chat.last_use_rag is True


def test_chat_request_can_override_rag(monkeypatch):
    class FakeSessionManager:
        async def load_session(self, session_id: str):
            return Conversation(
                id=session_id,
                user_id="11111111-1111-1111-1111-111111111111",
                npc=NPC(name="gucci_ceo", role_title="Chief Executive Officer, Gucci"),
            )

    class FakeChatService:
        def __init__(self):
            self.last_use_rag = None

        async def process_message(self, session_id: str, user_message: str, use_rag: bool = True):
            self.last_use_rag = use_rag
            return {"response": "ok"}

    fake_chat = FakeChatService()
    fake_container = SimpleNamespace(
        chat_service=fake_chat,
        session_manager=FakeSessionManager(),
    )
    monkeypatch.setattr(rest_routes, "_get_container", lambda: fake_container)
    client = _build_client(monkeypatch)

    token = _make_token(role="user", sub="11111111-1111-1111-1111-111111111111")
    response = client.post(
        "/api/npc/gucci_ceo/chat",
        json={"sessionId": "s-5", "message": "hello", "useRag": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert fake_chat.last_use_rag is False


# ── Supabase JWT verification tests ──────────────────────────────────

def _supabase_settings():
    return SimpleNamespace(
        auth=SimpleNamespace(
            jwt_secret_key="unit-test-secret",
            jwt_algorithm="HS256",
            access_token_expire_minutes=15,
            supabase_jwt_secret="supabase-test-secret",
        ),
        rag=SimpleNamespace(enabled=True),
        app_name="test-app",
        app_version="0.0.1",
        llm=SimpleNamespace(model="test-model"),
    )


def _make_supabase_token(
    *,
    sub: str = "sb-user-1",
    email: str = "user@gmail.com",
    role: str = "user",
    expired: bool = False,
) -> str:
    settings = _supabase_settings()
    now = datetime.now(timezone.utc)
    if expired:
        exp = now - timedelta(minutes=10)
    else:
        exp = now + timedelta(minutes=30)
    payload = {
        "sub": sub,
        "email": email,
        "aud": "authenticated",
        "app_metadata": {"role": role},
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.auth.supabase_jwt_secret,
        algorithm=settings.auth.jwt_algorithm,
    )


def _build_supabase_client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(rest_routes.router)
    monkeypatch.setattr(rest_routes, "get_settings", _supabase_settings)
    return TestClient(app)


def test_supabase_jwt_admin_access(monkeypatch):
    """Supabase JWT with app_metadata.role=admin grants admin access."""
    class FakeStore:
        async def list_users(self):
            return [{"id": "sb-user-1", "email": "user@gmail.com", "role": "admin"}]

    monkeypatch.setattr(rest_routes, "_get_postgres_store", lambda: FakeStore())
    client = _build_supabase_client(monkeypatch)

    token = _make_supabase_token(role="admin", sub="sb-admin-1")
    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_supabase_jwt_default_role_is_user(monkeypatch):
    """Supabase JWT without role in app_metadata defaults to 'user'."""
    settings = _supabase_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "sb-user-2",
        "email": "new@gmail.com",
        "aud": "authenticated",
        "app_metadata": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.auth.supabase_jwt_secret,
        algorithm=settings.auth.jwt_algorithm,
    )

    client = _build_supabase_client(monkeypatch)
    # GET /api/users requires admin, so a default "user" role should be forbidden
    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_supabase_jwt_expired_returns_401(monkeypatch):
    """Expired Supabase JWT returns 401."""
    client = _build_supabase_client(monkeypatch)
    token = _make_supabase_token(expired=True)
    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

