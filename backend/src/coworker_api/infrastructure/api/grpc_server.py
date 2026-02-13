"""
gRPC Server — Service Implementation.

Maps gRPC RPC methods to Application layer services.
This is a skeleton that will be fully wired once .proto
files are compiled with grpcio-tools.
"""

from __future__ import annotations

import logging
from concurrent import futures
from typing import Optional

import grpc

from coworker_api.config import get_settings

logger = logging.getLogger(__name__)


class ChatServicer:
    """
    gRPC servicer for chat-related RPCs.

    Once .proto files are defined and compiled, this class will inherit from
    the generated `ChatServiceServicer` base class.

    Methods will delegate to the ChatService in the Application layer.
    """

    def __init__(self, container):
        self._container = container

    # Example RPC method (will match the .proto definition):
    # async def SendMessage(self, request, context):
    #     result = await self._container.chat_service.process_message(
    #         session_id=request.session_id,
    #         user_message=request.message,
    #     )
    #     return SendMessageResponse(
    #         response=result["response"],
    #         turn_number=result["turn_number"],
    #     )


class SessionServicer:
    """
    gRPC servicer for session management RPCs.
    """

    def __init__(self, container):
        self._container = container


async def start_grpc_server(container) -> grpc.aio.Server:
    """
    Start the async gRPC server with all servicers registered.

    Args:
        container: The AppContainer with initialized services.

    Returns:
        The running gRPC server instance.
    """
    settings = get_settings()
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
    )

    # Register servicers once .proto stubs are generated:
    # chat_pb2_grpc.add_ChatServiceServicer_to_server(
    #     ChatServicer(container), server
    # )
    # session_pb2_grpc.add_SessionServiceServicer_to_server(
    #     SessionServicer(container), server
    # )

    listen_addr = f"{settings.grpc.host}:{settings.grpc.port}"
    server.add_insecure_port(listen_addr)
    await server.start()

    logger.info(f"gRPC server started on {listen_addr}")
    return server


async def stop_grpc_server(server: grpc.aio.Server) -> None:
    """Gracefully stop the gRPC server."""
    await server.stop(grace=5)
    logger.info("gRPC server stopped")
