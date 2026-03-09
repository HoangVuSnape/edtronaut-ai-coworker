"""
Reset Memory Service — Session Lifecycle Management.

Handles requests to clear or reset the conversation state.
"""

from __future__ import annotations

import logging

from coworker_api.domain.ports import MemoryPort
from coworker_api.application.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ResetMemoryService:
    """Clears session state from MemoryPort for a fresh simulation."""

    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    async def reset_session(self, session_id: str) -> dict[str, str]:
        """
        Delete a specific session and its history.

        Args:
            session_id: The session to reset.

        Returns:
            Dict with status and session_id.
        """
        deleted = await self._session_manager.delete_session(session_id)

        if deleted:
            logger.info("Session reset", extra={"session_id": session_id})
            return {"status": "reset", "session_id": session_id}
        else:
            logger.warning("Session not found for reset", extra={"session_id": session_id})
            return {"status": "not_found", "session_id": session_id}

    async def reset_all_user_sessions(self, user_id: str) -> dict[str, int]:
        """
        Delete all sessions for a given user.

        Returns:
            Dict with count of deleted sessions.
        """
        sessions = await self._session_manager.list_user_sessions(user_id)
        deleted_count = 0
        for session in sessions:
            sid = session.get("id", "")
            if sid:
                was_deleted = await self._session_manager.delete_session(sid)
                if was_deleted:
                    deleted_count += 1

        logger.info(
            "All user sessions reset",
            extra={"user_id": user_id, "deleted_count": deleted_count},
        )
        return {"deleted_count": deleted_count, "user_id": user_id}
