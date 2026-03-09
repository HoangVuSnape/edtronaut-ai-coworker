"""
gRPC Server — Service Implementation.

Maps gRPC RPC methods to Application layer services.
Uses compiled proto stubs from coworker_api.generated.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent import futures
from typing import Any

import grpc
import httpx

from coworker_api.config import get_settings
from coworker_api.generated import coworker_pb2, coworker_pb2_grpc

logger = logging.getLogger(__name__)

_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL_SECONDS = 3600

# NPC roles — mirrors REST routes NPC_ROLES
NPC_ROLES: dict[str, str] = {
    "gucci_ceo": "Chief Executive Officer, Gucci",
    "gucci_chro": "Chief Human Resources Officer, Gucci",
    "gucci_eb_ic": "Investment Banker & Individual Contributor, Gucci Group Finance",
}


# ── JWT Auth Interceptor ──

# Context variable to pass user claims from interceptor to servicers
import contextvars
_user_claims_var: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "user_claims", default={}
)


class JWTAuthInterceptor(grpc.aio.ServerInterceptor):
    """
    gRPC server interceptor that validates JWT tokens from metadata.

    Unauthenticated RPCs (like Login) are whitelisted.
    Sets user claims in a contextvars.ContextVar for servicers to read.
    """

    # Methods that do NOT require authentication
    PUBLIC_METHODS = frozenset({
        "/edtronaut.AuthService/Login",
    })

    async def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method

        # Skip auth for public methods
        if method in self.PUBLIC_METHODS:
            return await continuation(handler_call_details)

        # Extract token from metadata
        metadata = dict(handler_call_details.invocation_metadata or [])
        auth_value = metadata.get("authorization", "")

        if not auth_value.startswith("Bearer "):
            return self._unauthenticated_handler("Missing or invalid Authorization metadata")

        token = auth_value[7:]  # strip "Bearer "

        try:
            claims = _decode_jwt(token)
        except Exception as e:
            logger.error(f"JWT Verification failed in interceptor: {e}")
            return self._unauthenticated_handler(str(e))

        # Store claims in context variable — servicers read via _get_user_claims()
        _user_claims_var.set(claims)

        return await continuation(handler_call_details)

    @staticmethod
    def _unauthenticated_handler(detail: str):
        async def _abort(request, context):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, detail)

        return grpc.unary_unary_rpc_method_handler(_abort)



def _decode_jwt(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises on failure."""
    from jose import JWTError, jwt

    settings = get_settings()
    allowed_algorithms = _get_allowed_jwt_algorithms(settings)

    header_alg = _get_token_alg(token)

    # Supabase JWT verification path
    supabase_secret = settings.auth.supabase_jwt_secret.strip()
    if supabase_secret:
        try:
            if header_alg and header_alg not in allowed_algorithms:
                if header_alg.startswith(("RS", "ES")):
                    jwks_urls = _get_supabase_jwks_urls(token)
                    jwk_key = _get_jwks_key(jwks_urls, token)
                    payload = jwt.decode(
                        token,
                        jwk_key,
                        algorithms=[header_alg],
                        audience="authenticated",
                    )
                else:
                    raise JWTError(f"The specified alg value is not allowed: {header_alg}")
            elif header_alg and header_alg.startswith(("RS", "ES")):
                jwks_urls = _get_supabase_jwks_urls(token)
                jwk_key = _get_jwks_key(jwks_urls, token)
                payload = jwt.decode(
                    token,
                    jwk_key,
                    algorithms=[header_alg],
                    audience="authenticated",
                )
            else:
                payload = jwt.decode(
                    token,
                    supabase_secret,
                    algorithms=allowed_algorithms,
                    audience="authenticated",
                )
        except JWTError as e:
            _log_jwt_decode_failure("supabase", token, allowed_algorithms, e)
            raise ValueError(f"Invalid or expired token: {e}")

        if not payload.get("sub"):
            raise ValueError("Invalid token payload: missing sub")

        # Extract role from app_metadata
        app_metadata = payload.get("app_metadata", {})
        role = app_metadata.get("role", "user") if isinstance(app_metadata, dict) else "user"
        payload["role"] = role
        return payload

    # Legacy self-issued JWT path
    secret = settings.auth.jwt_secret_key.strip()

    if not secret or secret == "CHANGE_ME_IN_PRODUCTION":
        raise ValueError("Authentication is not configured")

    try:
        payload = jwt.decode(
            token, secret, algorithms=allowed_algorithms
        )
    except JWTError as e:
        _log_jwt_decode_failure("legacy", token, allowed_algorithms, e)
        raise ValueError(f"Invalid or expired token: {e}")

    if not payload.get("sub"):
        raise ValueError("Invalid token payload: missing sub")

    return payload


def _get_allowed_jwt_algorithms(settings) -> list[str]:
    raw = settings.auth.jwt_algorithm or ""
    parts = [part.strip().upper() for part in raw.split(",")]
    allowed = [part for part in parts if part]
    return allowed or ["HS256"]


def _get_token_alg(token: str) -> str:
    from jose import jwt

    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return ""
    alg = str(header.get("alg", "")).upper()
    return alg


def _get_supabase_jwks_urls(token: str) -> list[str]:
    from jose import jwt

    try:
        claims = jwt.get_unverified_claims(token)
    except Exception:
        claims = {}

    iss = str(claims.get("iss", "")).rstrip("/")
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or ""
    supabase_url = supabase_url.rstrip("/")

    base_url = ""
    if iss:
        if iss.endswith("/auth/v1"):
            base_url = iss[: -len("/auth/v1")]
        else:
            base_url = iss
    elif supabase_url:
        base_url = supabase_url

    if not base_url:
        raise ValueError("Supabase URL is not configured for JWKS lookup")

    return [
        f"{base_url}/auth/v1/keys",
        f"{base_url}/auth/v1/.well-known/jwks.json",
        f"{base_url}/.well-known/jwks.json",
    ]


def _get_jwks_key(jwks_urls: list[str], token: str) -> dict[str, Any]:
    from jose import jwt

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = _fetch_jwks_any(jwks_urls)
    keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
    if keys:
        return keys[0]
    raise ValueError("No JWKS keys available for token verification")


def _fetch_jwks_any(jwks_urls: list[str]) -> dict[str, Any]:
    last_error: Exception | None = None
    for jwks_url in jwks_urls:
        try:
            return _fetch_jwks(jwks_url)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is None:
        raise ValueError("Failed to fetch JWKS: no URLs provided")
    raise last_error


def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    cached = _JWKS_CACHE.get(jwks_url)
    if cached and now - cached[0] < _JWKS_TTL_SECONDS:
        return cached[1]

    headers: dict[str, str] = {}
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY") or ""
    if supabase_anon_key:
        headers["apikey"] = supabase_anon_key

    try:
        resp = httpx.get(jwks_url, headers=headers, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise ValueError(f"Failed to fetch JWKS: {exc}")

    _JWKS_CACHE[jwks_url] = (now, data)
    return data


def _log_jwt_decode_failure(path: str, token: str, allowed_algorithms: list[str], error: Exception) -> None:
    from jose import jwt

    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        header = {}

    try:
        claims = jwt.get_unverified_claims(token)
    except Exception:
        claims = {}

    alg = header.get("alg")
    kid = header.get("kid")
    iss = claims.get("iss")
    logger.error(
        "JWT decode failed (%s): alg=%s kid=%s iss=%s allowed=%s err=%s",
        path,
        alg,
        kid,
        iss,
        allowed_algorithms,
        error,
    )


def _get_user_claims(context) -> dict[str, Any]:
    """Extract user claims from context variable (set by interceptor)."""
    return _user_claims_var.get({})


# ── Auth Servicer ──

class AuthServicer(coworker_pb2_grpc.AuthServiceServicer):
    """gRPC servicer for authentication."""

    def __init__(self, container):
        self._container = container

    async def Login(self, request, context):
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
        store = self._container.postgres_store

        if store is None:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "PostgreSQL store is not initialized"
            )

        email = request.email.strip().lower()
        try:
            user = await store.get_user_auth_by_email(email)
        except Exception:
            await context.abort(
                grpc.StatusCode.INTERNAL, "Failed to authenticate user"
            )

        if user is None:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Invalid email or password"
            )

        # Verify password in thread pool to avoid blocking event loop
        valid = await asyncio.to_thread(
            pwd_context.verify, request.password, user["password_hash"]
        )
        if not valid:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "Invalid email or password"
            )

        # Create JWT token
        from datetime import datetime, timedelta, timezone
        from jose import jwt

        settings = get_settings()
        secret = settings.auth.jwt_secret_key.strip()
        now = datetime.now(timezone.utc)
        expires_in = max(settings.auth.access_token_expire_minutes, 1) * 60
        claims = {
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        access_token = jwt.encode(
            claims, secret, algorithm=settings.auth.jwt_algorithm
        )

        return coworker_pb2.LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=coworker_pb2.UserInfo(
                id=user["id"],
                email=user["email"],
                role=user["role"],
            ),
        )


# ── Chat Servicer ──

class ChatServicer(coworker_pb2_grpc.ChatServiceServicer):
    """gRPC servicer for chat-related RPCs."""

    def __init__(self, container):
        self._container = container

    async def SendMessage(self, request, context):
        """Unary chat: process a message and return the full response."""
        from coworker_api.domain.exceptions import ConversationNotFoundError
        from coworker_api.domain.models import Conversation, NPC

        claims = _get_user_claims(context)
        npc_id = request.npc_id

        if npc_id not in NPC_ROLES:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Unknown NPC '{npc_id}'. Available: {list(NPC_ROLES.keys())}",
            )

        if not self._container.chat_service:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "Service not yet initialized"
            )

        session_id = request.session_id

        try:
            try:
                existing = await self._container.session_manager.load_session(session_id)
                owner_id = str(existing.user_id)
                caller_id = str(claims.get("sub", ""))
                if claims.get("role") != "admin" and owner_id != caller_id:
                    await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Forbidden")
            except ConversationNotFoundError:
                user_id = str(claims.get("sub"))
                
                settings = get_settings()
                if settings.auth.supabase_jwt_secret:
                    store = self._container.postgres_store
                    if not await store.get_user(user_id):
                        try:
                            await store.create_user(
                                id=user_id,
                                email=claims.get("email", ""),
                                password_hash="supabase-oauth-no-password",
                                role=claims.get("role", "user")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to auto-create local user: {e}")

                npc = NPC(name=npc_id, role_title=NPC_ROLES[npc_id])
                conv = Conversation(
                    id=session_id,
                    user_id=user_id,
                    npc=npc,
                )
                await self._container.session_manager.save_session(conv)

            settings = get_settings()
            use_rag = request.use_rag if request.HasField("use_rag") else settings.rag.enabled

            result = await self._container.chat_service.process_message(
                session_id=session_id,
                user_message=request.message,
                use_rag=use_rag,
            )

            return coworker_pb2.SendMessageResponse(
                npc_id=npc_id,
                assistant_message=result["response"],
            )

        except grpc.aio.AbortError:
            raise
        except Exception:
            logger.exception("gRPC Chat error", extra={"npc_id": npc_id, "session_id": session_id})
            await context.abort(
                grpc.StatusCode.INTERNAL, "Failed to process chat message"
            )

    async def StreamMessage(self, request, context):
        """Server-streaming chat: stream response chunks."""
        from coworker_api.domain.exceptions import ConversationNotFoundError
        from coworker_api.domain.models import Conversation, NPC

        claims = _get_user_claims(context)
        npc_id = request.npc_id

        if npc_id not in NPC_ROLES:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Unknown NPC '{npc_id}'. Available: {list(NPC_ROLES.keys())}",
            )

        if not self._container.chat_service:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "Service not yet initialized"
            )

        session_id = request.session_id

        try:
            try:
                existing = await self._container.session_manager.load_session(session_id)
                owner_id = str(existing.user_id)
                caller_id = str(claims.get("sub", ""))
                if claims.get("role") != "admin" and owner_id != caller_id:
                    await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Forbidden")
            except ConversationNotFoundError:
                user_id = str(claims.get("sub"))
                
                settings = get_settings()
                if settings.auth.supabase_jwt_secret:
                    store = self._container.postgres_store
                    if not await store.get_user(user_id):
                        try:
                            await store.create_user(
                                id=user_id,
                                email=claims.get("email", ""),
                                password_hash="supabase-oauth-no-password",
                                role=claims.get("role", "user")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to auto-create local user: {e}")

                npc = NPC(name=npc_id, role_title=NPC_ROLES[npc_id])
                conv = Conversation(
                    id=session_id,
                    user_id=user_id,
                    npc=npc,
                )
                await self._container.session_manager.save_session(conv)

            settings = get_settings()
            use_rag = request.use_rag if request.HasField("use_rag") else settings.rag.enabled

            async for chunk in self._container.chat_service.stream_message(
                session_id=session_id,
                user_message=request.message,
                use_rag=use_rag,
            ):
                if chunk:
                    yield coworker_pb2.StreamMessageChunk(text=chunk)

        except grpc.aio.AbortError:
            raise
        except Exception:
            logger.exception(
                "gRPC streaming error",
                extra={"npc_id": npc_id, "session_id": session_id},
            )
            await context.abort(
                grpc.StatusCode.INTERNAL, "Failed to stream chat message"
            )


# ── Session Servicer ──

class SessionServicer(coworker_pb2_grpc.SessionServiceServicer):
    """gRPC servicer for session management RPCs."""

    def __init__(self, container):
        self._container = container

    async def ListUserSessions(self, request, context):
        claims = _get_user_claims(context)
        user_id = request.user_id

        # Access control: only owner or admin
        if claims.get("role") != "admin" and str(claims.get("sub")) != user_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Forbidden")

        if not self._container.session_manager:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "Service not yet initialized"
            )

        try:
            sessions = await self._container.session_manager.list_user_sessions(user_id)
            session_protos = []
            for s in sessions:
                session_protos.append(coworker_pb2.SessionSummary(
                    id=str(s.get("id", "")),
                    npc_name=str(s.get("npc_name", "")),
                    status=str(s.get("status", "")),
                    started_at=str(s.get("started_at", "")),
                ))
            return coworker_pb2.ListUserSessionsResponse(sessions=session_protos)
        except Exception:
            logger.exception("gRPC ListUserSessions error")
            await context.abort(
                grpc.StatusCode.INTERNAL, "Failed to list sessions"
            )

    async def GetSession(self, request, context):
        from coworker_api.domain.exceptions import ConversationNotFoundError

        claims = _get_user_claims(context)

        if not self._container.session_manager:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "Service not yet initialized"
            )

        try:
            conversation = await self._container.session_manager.load_session(
                request.session_id
            )
        except ConversationNotFoundError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")
        except Exception:
            logger.exception("gRPC GetSession error")
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to load session")

        # Access control
        if (
            claims.get("role") != "admin"
            and str(conversation.user_id) != str(claims.get("sub"))
        ):
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Forbidden")

        turns = []
        for t in conversation.turns:
            turns.append(coworker_pb2.TurnInfo(
                id=str(t.id),
                turn_number=t.turn_number,
                speaker=t.speaker.value,
                content=t.content,
                created_at=t.created_at.isoformat() if t.created_at else "",
            ))

        npc_info = coworker_pb2.NpcInfo(
            name=conversation.npc.name,
            role_title=conversation.npc.role_title,
        )

        scenario_info = None
        if conversation.scenario:
            scenario_info = coworker_pb2.ScenarioInfo(
                id=str(getattr(conversation.scenario, "id", "")),
                title=getattr(conversation.scenario, "title", ""),
                description=getattr(conversation.scenario, "description", ""),
                difficulty_level=getattr(conversation.scenario, "difficulty_level", 1),
            )

        return coworker_pb2.SessionDetail(
            id=conversation.id,
            user_id=str(conversation.user_id),
            npc=npc_info,
            scenario=scenario_info,
            status=conversation.status.value,
            started_at=(
                conversation.started_at.isoformat() if conversation.started_at else ""
            ),
            ended_at=(
                conversation.ended_at.isoformat() if conversation.ended_at else ""
            ),
            turns=turns,
        )

    async def DeleteSession(self, request, context):
        from coworker_api.domain.exceptions import ConversationNotFoundError

        claims = _get_user_claims(context)

        if not self._container.session_manager:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE, "Service not yet initialized"
            )

        try:
            conversation = await self._container.session_manager.load_session(
                request.session_id
            )
        except ConversationNotFoundError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")
        except Exception:
            logger.exception("gRPC DeleteSession error")
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to delete session")

        # Access control
        if (
            claims.get("role") != "admin"
            and str(conversation.user_id) != str(claims.get("sub"))
        ):
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "Forbidden")

        try:
            deleted = await self._container.session_manager.delete_session(
                request.session_id
            )
        except Exception:
            logger.exception("gRPC DeleteSession error")
            await context.abort(grpc.StatusCode.INTERNAL, "Failed to delete session")

        if not deleted:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")

        return coworker_pb2.DeleteSessionResponse(
            deleted=True, id=request.session_id
        )


# ── Server Lifecycle ──

async def start_grpc_server(container) -> grpc.aio.Server:
    """
    Start the async gRPC server with all servicers registered.

    Args:
        container: The AppContainer with initialized services.

    Returns:
        The running gRPC server instance.
    """
    settings = get_settings()

    interceptors = [JWTAuthInterceptor()]

    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors,
    )

    # Register servicers
    coworker_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServicer(container), server
    )
    coworker_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServicer(container), server
    )
    coworker_pb2_grpc.add_SessionServiceServicer_to_server(
        SessionServicer(container), server
    )

    listen_addr = f"{settings.grpc.host}:{settings.grpc.port}"
    server.add_insecure_port(listen_addr)
    await server.start()

    logger.info(f"gRPC server started on {listen_addr}")
    return server


async def stop_grpc_server(server: grpc.aio.Server) -> None:
    """Gracefully stop the gRPC server."""
    await server.stop(grace=5)
    logger.info("gRPC server stopped")
