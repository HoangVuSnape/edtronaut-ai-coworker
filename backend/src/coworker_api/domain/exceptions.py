"""
Domain Exceptions for Edtronaut AI Coworker.

Each exception carries a gRPC status code mapping for consistent
error propagation to the Frontend (see Error_Handling_Standards.md).
"""

from __future__ import annotations

from grpc import StatusCode


class DomainException(Exception):
    """Base exception for all domain-level errors."""

    grpc_code: StatusCode = StatusCode.INTERNAL
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


# ── Not Found ──

class ConversationNotFoundError(DomainException):
    """The requested conversation/session does not exist."""
    grpc_code = StatusCode.NOT_FOUND
    message = "Conversation not found."


class NPCNotFoundError(DomainException):
    """The requested NPC persona does not exist."""
    grpc_code = StatusCode.NOT_FOUND
    message = "NPC persona not found."


class ScenarioNotFoundError(DomainException):
    """The requested scenario does not exist."""
    grpc_code = StatusCode.NOT_FOUND
    message = "Scenario not found."


# ── Auth ──

class UserNotAuthenticatedError(DomainException):
    """Missing or invalid JWT token."""
    grpc_code = StatusCode.UNAUTHENTICATED
    message = "Authentication required."


class PermissionDeniedError(DomainException):
    """User does not have the required role."""
    grpc_code = StatusCode.PERMISSION_DENIED
    message = "You do not have permission to perform this action."


# ── Validation ──

class InvalidTurnError(DomainException):
    """Malformed user input or invalid state transition."""
    grpc_code = StatusCode.INVALID_ARGUMENT
    message = "Invalid turn data."


class PersonaConfigurationError(DomainException):
    """Missing or invalid persona/NPC configuration."""
    grpc_code = StatusCode.INVALID_ARGUMENT
    message = "NPC persona configuration is invalid."


# ── Resource Limits ──

class ContextWindowExceededError(DomainException):
    """Conversation exceeds the LLM's token context window."""
    grpc_code = StatusCode.RESOURCE_EXHAUSTED
    message = "Conversation exceeds the context window. Please summarize or reset."


class RateLimitExceededError(DomainException):
    """User or system rate limit has been exceeded."""
    grpc_code = StatusCode.RESOURCE_EXHAUSTED
    message = "Rate limit exceeded. Please try again later."


# ── External Service Errors ──

class LLMConnectionError(DomainException):
    """Failed to connect to the LLM provider (OpenAI, etc.)."""
    grpc_code = StatusCode.UNAVAILABLE
    message = "LLM service is currently unavailable."


class VectorStoreError(DomainException):
    """Failed to communicate with the vector database (Qdrant)."""
    grpc_code = StatusCode.UNAVAILABLE
    message = "Vector store service is currently unavailable."


class MemoryStoreError(DomainException):
    """Failed to communicate with the memory store (Redis)."""
    grpc_code = StatusCode.UNAVAILABLE
    message = "Memory store service is currently unavailable."
