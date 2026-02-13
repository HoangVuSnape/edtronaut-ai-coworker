"""
gRPC Frontend Client — Outbound gRPC calls to the Frontend.

Used for server-push notifications or streaming updates to the
frontend (e.g., director interventions, real-time hints).
"""

from __future__ import annotations

import logging
from typing import Optional

import grpc

logger = logging.getLogger(__name__)


class FrontendGRPCClient:
    """Client for sending gRPC messages to the frontend."""

    def __init__(self, target: str = "localhost:50052"):
        self._target = target
        self._channel: Optional[grpc.aio.Channel] = None

    async def _get_channel(self) -> grpc.aio.Channel:
        """Lazy-initialize the gRPC channel."""
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._target)
        return self._channel

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None

    # Placeholder methods — will be implemented once .proto stubs are generated:
    #
    # async def push_hint(self, session_id: str, hint: str) -> None:
    #     channel = await self._get_channel()
    #     stub = frontend_pb2_grpc.FrontendServiceStub(channel)
    #     await stub.PushHint(frontend_pb2.HintNotification(
    #         session_id=session_id,
    #         hint=hint,
    #     ))
    #
    # async def push_director_feedback(self, session_id: str, feedback: str) -> None:
    #     channel = await self._get_channel()
    #     stub = frontend_pb2_grpc.FrontendServiceStub(channel)
    #     await stub.PushDirectorFeedback(...)
