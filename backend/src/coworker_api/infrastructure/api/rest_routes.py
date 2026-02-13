"""
REST Routes — Health Check, Info & Chat Endpoints.

Lightweight REST endpoints for monitoring and the primary chat interface.
Business logic is delegated to Application services via the DI container.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from coworker_api.config import get_settings
from coworker_api.domain.prompts import list_personas

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check — verifies dependencies are available.

    In production, this should ping Redis, Qdrant, etc.
    """
    return {"status": "ready"}


@router.get("/info")
async def service_info():
    """Return service metadata and available personas."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "llm_model": settings.llm.model,
        "personas": list_personas(),
    }


# ── Chat API ──

# NPC display name mapping (matches frontend NPC_META)
NPC_ROLES: dict[str, str] = {
    "gucci_ceo": "Chief Executive Officer, Gucci",
    "gucci_chro": "Chief Human Resources Officer, Gucci",
    "gucci_eb_ic": "Investment Banker & Individual Contributor, Gucci Group Finance",
}


class ChatRequestBody(BaseModel):
    sessionId: str
    message: str


class ChatResponseBody(BaseModel):
    npcId: str
    assistantMessage: str
    hint: str | None = None
    safetyFlags: list[str] | None = None


@router.post("/api/npc/{npc_id}/chat", response_model=ChatResponseBody)
async def chat_with_npc(npc_id: str, body: ChatRequestBody):
    """
    Main chat endpoint — send a message to an NPC and get a response.

    The frontend calls this as POST /api/npc/{npcId}/chat with:
        { sessionId: string, message: string }

    Returns:
        { npcId, assistantMessage, hint?, safetyFlags? }
    """
    from coworker_api.infrastructure.api.main import container
    from coworker_api.domain.models import NPC, Conversation
    from coworker_api.domain.exceptions import ConversationNotFoundError

    if not container.chat_service:
        raise HTTPException(status_code=503, detail="Service not yet initialized")

    # Validate NPC ID
    if npc_id not in NPC_ROLES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown NPC '{npc_id}'. Available: {list(NPC_ROLES.keys())}",
        )

    try:
        # Try to load existing session, or create one for first message
        try:
            await container.session_manager.load_session(body.sessionId)
        except ConversationNotFoundError:
            # First message — auto-create the session
            npc = NPC(name=npc_id, role_title=NPC_ROLES[npc_id])
            conv = Conversation(
                id=body.sessionId,
                user_id="anonymous",
                npc=npc,
            )
            await container.session_manager.save_session(conv)
            logger.info(
                "Auto-created session",
                extra={"session_id": body.sessionId, "npc": npc_id},
            )

        # Process the message (RAG disabled until collection is seeded)
        result = await container.chat_service.process_message(
            session_id=body.sessionId,
            user_message=body.message,
            use_rag=False,
        )

        return ChatResponseBody(
            npcId=npc_id,
            assistantMessage=result["response"],
        )

    except Exception as e:
        logger.exception("Chat error", extra={"npc_id": npc_id, "session_id": body.sessionId})
        raise HTTPException(status_code=500, detail=str(e))

