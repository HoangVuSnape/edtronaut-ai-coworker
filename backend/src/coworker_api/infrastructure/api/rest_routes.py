"""
REST routes: health, domain CRUD APIs, session read/delete, and chat action API.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from coworker_api.config import get_settings
from coworker_api.domain.prompts import list_personas

logger = logging.getLogger(__name__)

system_router = APIRouter(tags=["system"])
auth_router = APIRouter(tags=["auth"])
users_router = APIRouter(tags=["users"])
npcs_router = APIRouter(tags=["npcs"])
scenarios_router = APIRouter(tags=["scenarios"])
sessions_router = APIRouter(tags=["sessions"])
chat_router = APIRouter(tags=["chat"])
router = APIRouter()
# Use pbkdf2_sha256 for stable cross-platform hashing; keep bcrypt for backward verify.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# Chat persona display mapping (matches frontend NPC_META)
NPC_ROLES: dict[str, str] = {
    "gucci_ceo": "Chief Executive Officer, Gucci",
    "gucci_chro": "Chief Human Resources Officer, Gucci",
    "gucci_eb_ic": "Investment Banker & Individual Contributor, Gucci Group Finance",
}


class ChatRequestBody(BaseModel):
    sessionId: str
    message: str
    useRag: bool | None = None


class ChatResponseBody(BaseModel):
    npcId: str
    assistantMessage: str
    hint: str | None = None
    safetyFlags: list[str] | None = None


class UserCreateBody(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserUpdateBody(BaseModel):
    email: str | None = None
    password: str | None = None
    role: str | None = None


class LoginRequestBody(BaseModel):
    email: str
    password: str


class LoginResponseBody(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, Any]


class NPCCreateBody(BaseModel):
    name: str
    role_title: str
    system_prompt_template: str = ""
    traits: dict[str, Any] = Field(default_factory=dict)


class NPCUpdateBody(BaseModel):
    name: str | None = None
    role_title: str | None = None
    system_prompt_template: str | None = None
    traits: dict[str, Any] | None = None


class ScenarioCreateBody(BaseModel):
    title: str
    description: str = ""
    difficulty_level: int = 1
    npc_id: str


class ScenarioUpdateBody(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty_level: int | None = None
    npc_id: str | None = None


def _get_container():
    from coworker_api.infrastructure.api.main import container

    return container


def _get_postgres_store():
    container = _get_container()
    store = container.postgres_store
    if store is None:
        raise HTTPException(status_code=503, detail="PostgreSQL store is not initialized")
    return store


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(plain_password: str) -> str:
    """Sync version – only call from sync context or via asyncio.to_thread."""
    password = plain_password.strip()
    if len(password) < 8:
        raise _bad_request("Password must be at least 8 characters")
    return pwd_context.hash(password)


async def _hash_password_async(plain_password: str) -> str:
    """Offload blocking hash to thread pool to avoid blocking event loop."""
    return await asyncio.to_thread(_hash_password, plain_password)


def _verify_password(plain_password: str, password_hash: str) -> bool:
    """Sync version – only call via asyncio.to_thread."""
    return pwd_context.verify(plain_password, password_hash)


async def _verify_password_async(plain_password: str, password_hash: str) -> bool:
    """Offload blocking verify to thread pool to avoid blocking event loop."""
    return await asyncio.to_thread(_verify_password, plain_password, password_hash)


def _create_access_token(payload: dict[str, Any], expires_minutes: int) -> tuple[str, int]:
    settings = get_settings()
    secret = settings.auth.jwt_secret_key.strip()
    if not secret or secret == "CHANGE_ME_IN_PRODUCTION":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    now = datetime.now(timezone.utc)
    expires_in = max(expires_minutes, 1) * 60
    claims = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(
        claims,
        secret,
        algorithm=settings.auth.jwt_algorithm,
    )
    return token, expires_in


def _decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    secret = settings.auth.jwt_secret_key.strip()
    if not secret or secret == "CHANGE_ME_IN_PRODUCTION":
        logger.error("JWT secret key is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.auth.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_authenticated(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_access_token(credentials.credentials)


def _is_admin(user_claims: dict[str, Any]) -> bool:
    return str(user_claims.get("role", "")).lower() == "admin"


def _ensure_user_access(user_claims: dict[str, Any], target_user_id: str) -> None:
    if _is_admin(user_claims):
        return
    if str(user_claims.get("sub")) != target_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _internal_error(log_message: str, public_detail: str) -> HTTPException:
    logger.exception(log_message)
    return HTTPException(status_code=500, detail=public_detail)


def require_admin(
    user_claims: dict[str, Any] = Security(require_authenticated),
) -> dict[str, Any]:
    if not _is_admin(user_claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user_claims


@auth_router.post("/api/auth/login", response_model=LoginResponseBody)
async def login(body: LoginRequestBody):
    store = _get_postgres_store()

    try:
        user = await store.get_user_auth_by_email(_normalize_email(body.email))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to authenticate user")

    if user is None or not await _verify_password_async(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    settings = get_settings()
    access_token, expires_in = _create_access_token(
        payload={
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
        expires_minutes=settings.auth.access_token_expire_minutes,
    )
    return LoginResponseBody(
        access_token=access_token,
        expires_in=expires_in,
        user={
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
    )


@system_router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@system_router.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies are available."""
    return {"status": "ready"}


@system_router.get("/info")
async def service_info():
    """Return service metadata and available personas."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "llm_model": settings.llm.model,
        "personas": list_personas(),
    }


# Users CRUD
@users_router.post("/api/users", dependencies=[Security(require_admin)])
async def create_user(body: UserCreateBody):
    store = _get_postgres_store()
    try:
        return await store.create_user(
            email=_normalize_email(body.email),
            password_hash=await _hash_password_async(body.password),
            role=body.role,
        )
    except HTTPException:
        raise
    except Exception:
        raise _internal_error("Create user failed", "Failed to create user")


@users_router.get("/api/users", dependencies=[Security(require_admin)])
async def list_users():
    store = _get_postgres_store()
    return await store.list_users()


@users_router.get("/api/users/{user_id}", dependencies=[Security(require_admin)])
async def get_user(user_id: str):
    store = _get_postgres_store()
    try:
        user = await store.get_user(user_id)
    except ValueError:
        raise _bad_request("Invalid user_id format")

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@users_router.put("/api/users/{user_id}", dependencies=[Security(require_admin)])
async def update_user(user_id: str, body: UserUpdateBody):
    store = _get_postgres_store()
    try:
        user = await store.update_user(
            user_id,
            email=_normalize_email(body.email) if body.email is not None else None,
            password_hash=await _hash_password_async(body.password) if body.password is not None else None,
            role=body.role,
        )
    except ValueError:
        raise _bad_request("Invalid user_id format")
    except HTTPException:
        raise
    except Exception:
        raise _internal_error("Update user failed", "Failed to update user")

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@users_router.delete("/api/users/{user_id}", dependencies=[Security(require_admin)])
async def delete_user(user_id: str):
    store = _get_postgres_store()
    try:
        deleted = await store.delete_user(user_id)
    except ValueError:
        raise _bad_request("Invalid user_id format")

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True, "id": user_id}


# NPCs CRUD
@npcs_router.post("/api/npcs", dependencies=[Security(require_admin)])
async def create_npc(body: NPCCreateBody):
    store = _get_postgres_store()
    try:
        return await store.create_npc(
            name=body.name,
            role_title=body.role_title,
            system_prompt_template=body.system_prompt_template,
            traits=body.traits,
        )
    except Exception:
        raise _internal_error("Create NPC failed", "Failed to create NPC")


@npcs_router.get("/api/npcs", dependencies=[Security(require_admin)])
async def list_npcs():
    store = _get_postgres_store()
    return await store.list_npcs()


@npcs_router.get("/api/npcs/{npc_id}", dependencies=[Security(require_admin)])
async def get_npc(npc_id: str):
    store = _get_postgres_store()
    try:
        npc = await store.get_npc(npc_id)
    except ValueError:
        raise _bad_request("Invalid npc_id format")

    if npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")
    return npc


@npcs_router.put("/api/npcs/{npc_id}", dependencies=[Security(require_admin)])
async def update_npc(npc_id: str, body: NPCUpdateBody):
    store = _get_postgres_store()
    try:
        npc = await store.update_npc(
            npc_id,
            name=body.name,
            role_title=body.role_title,
            system_prompt_template=body.system_prompt_template,
            traits=body.traits,
        )
    except ValueError:
        raise _bad_request("Invalid npc_id format")
    except Exception:
        raise _internal_error("Update NPC failed", "Failed to update NPC")

    if npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")
    return npc


@npcs_router.delete("/api/npcs/{npc_id}", dependencies=[Security(require_admin)])
async def delete_npc(npc_id: str):
    store = _get_postgres_store()
    try:
        deleted = await store.delete_npc(npc_id)
    except ValueError:
        raise _bad_request("Invalid npc_id format")
    except Exception:
        raise _internal_error("Delete NPC failed", "Failed to delete NPC")

    if not deleted:
        raise HTTPException(status_code=404, detail="NPC not found")
    return {"deleted": True, "id": npc_id}


# Scenarios CRUD
@scenarios_router.post("/api/scenarios", dependencies=[Security(require_admin)])
async def create_scenario(body: ScenarioCreateBody):
    store = _get_postgres_store()
    try:
        return await store.create_scenario(
            title=body.title,
            description=body.description,
            difficulty_level=body.difficulty_level,
            npc_id=body.npc_id,
        )
    except ValueError:
        raise _bad_request("Invalid npc_id format")
    except Exception:
        raise _internal_error("Create scenario failed", "Failed to create scenario")


@scenarios_router.get("/api/scenarios", dependencies=[Security(require_admin)])
async def list_scenarios(npc_id: str | None = Query(default=None)):
    store = _get_postgres_store()
    try:
        return await store.list_scenarios(npc_id=npc_id)
    except ValueError:
        raise _bad_request("Invalid npc_id format")


@scenarios_router.get("/api/scenarios/{scenario_id}", dependencies=[Security(require_admin)])
async def get_scenario(scenario_id: str):
    store = _get_postgres_store()
    try:
        scenario = await store.get_scenario(scenario_id)
    except ValueError:
        raise _bad_request("Invalid scenario_id format")

    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@scenarios_router.put("/api/scenarios/{scenario_id}", dependencies=[Security(require_admin)])
async def update_scenario(scenario_id: str, body: ScenarioUpdateBody):
    store = _get_postgres_store()
    try:
        scenario = await store.update_scenario(
            scenario_id,
            title=body.title,
            description=body.description,
            difficulty_level=body.difficulty_level,
            npc_id=body.npc_id,
        )
    except ValueError:
        raise _bad_request("Invalid scenario_id or npc_id format")
    except Exception:
        raise _internal_error("Update scenario failed", "Failed to update scenario")

    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@scenarios_router.delete("/api/scenarios/{scenario_id}", dependencies=[Security(require_admin)])
async def delete_scenario(scenario_id: str):
    store = _get_postgres_store()
    try:
        deleted = await store.delete_scenario(scenario_id)
    except ValueError:
        raise _bad_request("Invalid scenario_id format")

    if not deleted:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True, "id": scenario_id}


# Session read/delete (append via chat endpoint)
@sessions_router.get("/api/users/{user_id}/sessions")
async def list_user_sessions(
    user_id: str,
    user_claims: dict[str, Any] = Security(require_authenticated),
):
    _ensure_user_access(user_claims, user_id)
    container = _get_container()
    if not container.session_manager:
        raise HTTPException(status_code=503, detail="Service not yet initialized")
    try:
        return await container.session_manager.list_user_sessions(user_id)
    except Exception:
        raise _internal_error("List sessions failed", "Failed to list sessions")


@sessions_router.get("/api/sessions/{session_id}")
async def get_session(
    session_id: str,
    user_claims: dict[str, Any] = Security(require_authenticated),
):
    from coworker_api.domain.exceptions import ConversationNotFoundError

    container = _get_container()
    if not container.session_manager:
        raise HTTPException(status_code=503, detail="Service not yet initialized")

    try:
        conversation = await container.session_manager.load_session(session_id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception:
        raise _internal_error("Get session failed", "Failed to load session")

    if not _is_admin(user_claims) and str(conversation.user_id) != str(user_claims.get("sub")):
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "npc": conversation.npc.model_dump(),
        "scenario": conversation.scenario.model_dump() if conversation.scenario else None,
        "status": conversation.status.value,
        "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
        "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        "turns": [
            {
                "id": t.id,
                "turn_number": t.turn_number,
                "speaker": t.speaker.value,
                "content": t.content,
                "metadata": t.metadata,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in conversation.turns
        ],
    }


@sessions_router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_claims: dict[str, Any] = Security(require_authenticated),
):
    from coworker_api.domain.exceptions import ConversationNotFoundError

    container = _get_container()
    if not container.session_manager:
        raise HTTPException(status_code=503, detail="Service not yet initialized")

    try:
        conversation = await container.session_manager.load_session(session_id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception:
        raise _internal_error("Load session before delete failed", "Failed to delete session")

    if not _is_admin(user_claims) and str(conversation.user_id) != str(user_claims.get("sub")):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        deleted = await container.session_manager.delete_session(session_id)
    except Exception:
        raise _internal_error("Delete session failed", "Failed to delete session")

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "id": session_id}


# Chat action endpoint (append to conversation)
@chat_router.post("/api/npc/{npc_id}/chat/stream")
async def chat_with_npc_stream(
    npc_id: str,
    body: ChatRequestBody,
    user_claims: dict[str, Any] = Security(require_authenticated),
):
    """
    Streaming chat endpoint.
    """
    from coworker_api.domain.exceptions import ConversationNotFoundError
    from coworker_api.domain.models import Conversation, NPC

    container = _get_container()
    if not container.chat_service:
        raise HTTPException(status_code=503, detail="Service not yet initialized")

    if npc_id not in NPC_ROLES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown NPC '{npc_id}'. Available: {list(NPC_ROLES.keys())}",
        )

    # Ensure session exists or create it
    try:
        try:
            existing = await container.session_manager.load_session(body.sessionId)
            if not _is_admin(user_claims) and str(existing.user_id) != str(user_claims.get("sub")):
                raise HTTPException(status_code=403, detail="Forbidden")
        except ConversationNotFoundError:
            npc = NPC(name=npc_id, role_title=NPC_ROLES[npc_id])
            conv = Conversation(
                id=body.sessionId,
                user_id=str(user_claims.get("sub")),
                npc=npc,
            )
            await container.session_manager.save_session(conv)

        async def _stream_generator():
            async for chunk in container.chat_service.stream_message(
                session_id=body.sessionId,
                user_message=body.message,
                use_rag=(body.useRag if body.useRag is not None else get_settings().rag.enabled),
            ):
                if chunk:
                    yield chunk.encode("utf-8")

        return StreamingResponse(_stream_generator(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat streaming error", extra={"npc_id": npc_id, "session_id": body.sessionId})
        raise HTTPException(status_code=500, detail="Failed to stream chat message")


@chat_router.post("/api/npc/{npc_id}/chat", response_model=ChatResponseBody)
async def chat_with_npc(
    npc_id: str,
    body: ChatRequestBody,
    user_claims: dict[str, Any] = Security(require_authenticated),
):
    """
    Chat action endpoint.

    This is intentionally command-style, not CRUD:
    POST /api/npc/{npcId}/chat { sessionId, message }
    """
    from coworker_api.domain.exceptions import ConversationNotFoundError
    from coworker_api.domain.models import Conversation, NPC

    container = _get_container()
    if not container.chat_service:
        raise HTTPException(status_code=503, detail="Service not yet initialized")

    if npc_id not in NPC_ROLES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown NPC '{npc_id}'. Available: {list(NPC_ROLES.keys())}",
        )

    try:
        try:
            existing = await container.session_manager.load_session(body.sessionId)
            if not _is_admin(user_claims) and str(existing.user_id) != str(user_claims.get("sub")):
                raise HTTPException(status_code=403, detail="Forbidden")
        except ConversationNotFoundError:
            npc = NPC(name=npc_id, role_title=NPC_ROLES[npc_id])
            conv = Conversation(
                id=body.sessionId,
                user_id=str(user_claims.get("sub")),
                npc=npc,
            )
            await container.session_manager.save_session(conv)
            logger.info(
                "Auto-created session",
                extra={"session_id": body.sessionId, "npc": npc_id},
            )

        result = await container.chat_service.process_message(
            session_id=body.sessionId,
            user_message=body.message,
            use_rag=(body.useRag if body.useRag is not None else get_settings().rag.enabled),
        )

        return ChatResponseBody(
            npcId=npc_id,
            assistantMessage=result["response"],
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat error", extra={"npc_id": npc_id, "session_id": body.sessionId})
        raise HTTPException(status_code=500, detail="Failed to process chat message")


# Register sub-routers after route declarations.
router.include_router(system_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(npcs_router)
router.include_router(scenarios_router)
router.include_router(sessions_router)
router.include_router(chat_router)
