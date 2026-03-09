"""
Domain Layer — Edtronaut AI Coworker.

Exports core models, exceptions, and port interfaces.
"""

from coworker_api.domain.models import (
    Conversation,
    Turn,
    NPC,
    ScenarioState,
    Hint,
    Speaker,
    SimulationStatus,
    UserRole,
)
from coworker_api.domain.exceptions import (
    DomainException,
    ConversationNotFoundError,
    NPCNotFoundError,
    ScenarioNotFoundError,
    UserNotAuthenticatedError,
    PermissionDeniedError,
    InvalidTurnError,
    PersonaConfigurationError,
    ContextWindowExceededError,
    RateLimitExceededError,
    LLMConnectionError,
    VectorStoreError,
    MemoryStoreError,
)

__all__ = [
    # Models
    "Conversation",
    "Turn",
    "NPC",
    "ScenarioState",
    "Hint",
    "Speaker",
    "SimulationStatus",
    "UserRole",
    # Exceptions
    "DomainException",
    "ConversationNotFoundError",
    "NPCNotFoundError",
    "ScenarioNotFoundError",
    "UserNotAuthenticatedError",
    "PermissionDeniedError",
    "InvalidTurnError",
    "PersonaConfigurationError",
    "ContextWindowExceededError",
    "RateLimitExceededError",
    "LLMConnectionError",
    "VectorStoreError",
    "MemoryStoreError",
]
