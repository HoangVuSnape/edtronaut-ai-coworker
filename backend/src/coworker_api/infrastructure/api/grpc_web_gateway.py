"""
gRPC-Web Gateway — HTTP/1.1 ↔ gRPC Translation Layer.

Provides FastAPI routes that accept standard HTTP/JSON requests from the
frontend and relay them through the internal gRPC server on port 50051.

Architecture:
    Browser (HTTP/1.1 JSON) → /rpc/* → gRPC channel → gRPC Server (:50051)

This makes gRPC the *primary* transport for all frontend communication.
No Envoy proxy required.
"""

from __future__ import annotations

import logging
from typing import Any

import grpc
from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from coworker_api.config import get_settings
from coworker_api.generated import coworker_pb2, coworker_pb2_grpc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpc", tags=["gRPC Gateway"])


# ── Request / Response models (JSON) ──


class GrpcChatRequest(BaseModel):
    sessionId: str
    npcId: str
    message: str
    useRag: bool | None = None


class GrpcLoginRequest(BaseModel):
    email: str
    password: str


class GrpcListSessionsRequest(BaseModel):
    userId: str


class GrpcSessionRequest(BaseModel):
    sessionId: str


# ── Channel pool ──

_channel: grpc.aio.Channel | None = None


async def _get_channel() -> grpc.aio.Channel:
    """Lazy-create a reusable async gRPC channel to the internal server."""
    global _channel
    if _channel is None:
        settings = get_settings()
        addr = f"localhost:{settings.grpc.port}"
        _channel = grpc.aio.insecure_channel(addr)
    return _channel


async def close_channel() -> None:
    """Close the gRPC channel (called on shutdown)."""
    global _channel
    if _channel is not None:
        await _channel.close()
        _channel = None


def _extract_token(request: Request) -> list[tuple[str, str]]:
    """Extract JWT from HTTP Authorization header → gRPC metadata."""
    auth = request.headers.get("authorization", "")
    if auth:
        return [("authorization", auth)]
    return []


# ── Auth Gateway ──


@router.post("/auth/login")
async def rpc_login(body: GrpcLoginRequest):
    """Login via gRPC AuthService."""
    channel = await _get_channel()
    stub = coworker_pb2_grpc.AuthServiceStub(channel)

    grpc_req = coworker_pb2.LoginRequest(
        email=body.email,
        password=body.password,
    )

    try:
        resp = await stub.Login(grpc_req)
        return {
            "access_token": resp.access_token,
            "token_type": resp.token_type,
            "expires_in": resp.expires_in,
            "user": {
                "id": resp.user.id,
                "email": resp.user.email,
                "role": resp.user.role,
            },
        }
    except grpc.aio.AioRpcError as e:
        _raise_http_from_grpc(e)


# ── Chat Gateway ──


@router.post("/chat/{npc_id}/send")
async def rpc_send_message(npc_id: str, body: GrpcChatRequest, request: Request):
    """Unary chat via gRPC ChatService.SendMessage."""
    channel = await _get_channel()
    stub = coworker_pb2_grpc.ChatServiceStub(channel)
    metadata = _extract_token(request)

    grpc_req = coworker_pb2.SendMessageRequest(
        session_id=body.sessionId,
        npc_id=npc_id,
        message=body.message,
    )
    if body.useRag is not None:
        grpc_req.use_rag = body.useRag

    try:
        resp = await stub.SendMessage(grpc_req, metadata=metadata)
        return {
            "npcId": resp.npc_id,
            "assistantMessage": resp.assistant_message,
            "hint": resp.hint or None,
            "safetyFlags": list(resp.safety_flags),
        }
    except grpc.aio.AioRpcError as e:
        _raise_http_from_grpc(e)


@router.post("/chat/{npc_id}/stream")
async def rpc_stream_message(npc_id: str, body: GrpcChatRequest, request: Request):
    """
    Server-streaming chat via gRPC ChatService.StreamMessage.

    Returns a chunked text/plain response — each chunk is a token from the LLM,
    streamed through gRPC server-streaming internally.
    """
    channel = await _get_channel()
    stub = coworker_pb2_grpc.ChatServiceStub(channel)
    metadata = _extract_token(request)

    grpc_req = coworker_pb2.StreamMessageRequest(
        session_id=body.sessionId,
        npc_id=npc_id,
        message=body.message,
    )
    if body.useRag is not None:
        grpc_req.use_rag = body.useRag

    async def _stream():
        try:
            async for chunk in stub.StreamMessage(grpc_req, metadata=metadata):
                if chunk.text:
                    yield chunk.text.encode("utf-8")
        except grpc.aio.AioRpcError as e:
            logger.error(f"gRPC stream error: {e.code()} {e.details()}")
            # Can't raise HTTP error after stream started, log it
            return

    return StreamingResponse(_stream(), media_type="text/plain")


# ── Session Gateway ──


@router.post("/sessions/list")
async def rpc_list_sessions(body: GrpcListSessionsRequest, request: Request):
    """List user sessions via gRPC SessionService."""
    channel = await _get_channel()
    stub = coworker_pb2_grpc.SessionServiceStub(channel)
    metadata = _extract_token(request)

    grpc_req = coworker_pb2.ListUserSessionsRequest(user_id=body.userId)

    try:
        resp = await stub.ListUserSessions(grpc_req, metadata=metadata)
        return {
            "sessions": [
                {
                    "id": s.id,
                    "npcName": s.npc_name,
                    "status": s.status,
                    "startedAt": s.started_at,
                }
                for s in resp.sessions
            ]
        }
    except grpc.aio.AioRpcError as e:
        _raise_http_from_grpc(e)


@router.post("/sessions/get")
async def rpc_get_session(body: GrpcSessionRequest, request: Request):
    """Get session detail via gRPC SessionService."""
    channel = await _get_channel()
    stub = coworker_pb2_grpc.SessionServiceStub(channel)
    metadata = _extract_token(request)

    grpc_req = coworker_pb2.GetSessionRequest(session_id=body.sessionId)

    try:
        resp = await stub.GetSession(grpc_req, metadata=metadata)
        return _session_detail_to_dict(resp)
    except grpc.aio.AioRpcError as e:
        _raise_http_from_grpc(e)


@router.post("/sessions/delete")
async def rpc_delete_session(body: GrpcSessionRequest, request: Request):
    """Delete session via gRPC SessionService."""
    channel = await _get_channel()
    stub = coworker_pb2_grpc.SessionServiceStub(channel)
    metadata = _extract_token(request)

    grpc_req = coworker_pb2.DeleteSessionRequest(session_id=body.sessionId)

    try:
        resp = await stub.DeleteSession(grpc_req, metadata=metadata)
        return {"deleted": resp.deleted, "id": resp.id}
    except grpc.aio.AioRpcError as e:
        _raise_http_from_grpc(e)


# ── Helpers ──


def _raise_http_from_grpc(error: grpc.aio.AioRpcError) -> None:
    """Map gRPC status codes to HTTP status codes."""
    mapping = {
        grpc.StatusCode.NOT_FOUND: 404,
        grpc.StatusCode.UNAUTHENTICATED: 401,
        grpc.StatusCode.PERMISSION_DENIED: 403,
        grpc.StatusCode.UNAVAILABLE: 503,
        grpc.StatusCode.INVALID_ARGUMENT: 400,
        grpc.StatusCode.ALREADY_EXISTS: 409,
    }
    status = mapping.get(error.code(), 500)
    raise HTTPException(status_code=status, detail=error.details() or "Internal gRPC error")


def _session_detail_to_dict(session) -> dict[str, Any]:
    """Convert SessionDetail protobuf → dict."""
    result: dict[str, Any] = {
        "id": session.id,
        "userId": session.user_id,
        "npc": {
            "name": session.npc.name,
            "roleTitle": session.npc.role_title,
        },
        "status": session.status,
        "startedAt": session.started_at or None,
        "endedAt": session.ended_at or None,
        "turns": [
            {
                "id": t.id,
                "turnNumber": t.turn_number,
                "speaker": t.speaker,
                "content": t.content,
                "createdAt": t.created_at or None,
            }
            for t in session.turns
        ],
    }
    if session.HasField("scenario"):
        result["scenario"] = {
            "id": session.scenario.id,
            "title": session.scenario.title,
            "description": session.scenario.description,
            "difficultyLevel": session.scenario.difficulty_level,
        }
    return result
