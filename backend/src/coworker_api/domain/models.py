"""
Domain Models for Edtronaut AI Coworker.

Core business entities: Conversation, Turn, NPC, ScenarioState, Hint.
These are pure Pydantic models with no external dependencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──

class Speaker(str, Enum):
    """Who is speaking in a conversation turn."""
    USER = "user"
    NPC = "npc"
    SYSTEM = "system"


class SimulationStatus(str, Enum):
    """Status of a simulation session."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    USER = "user"


# ── Value Objects ──

class Turn(BaseModel):
    """A single exchange in a conversation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    turn_number: int
    speaker: Speaker
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)


class Hint(BaseModel):
    """Contextual suggestion for the user during a simulation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    hint_type: str = "suggestion"  # suggestion, warning, praise
    relevance_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Entities ──

class NPC(BaseModel):
    """Represents an AI persona (Non-Player Character)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role_title: str
    company: str = ""
    system_prompt_template: str = ""
    traits: dict[str, float] = Field(default_factory=dict)
    communication_style: dict[str, Any] = Field(default_factory=dict)
    knowledge_domains: list[str] = Field(default_factory=list)


class ScenarioState(BaseModel):
    """Tracks the progression of a running scenario."""
    scenario_id: str
    title: str = ""
    description: str = ""
    difficulty_level: int = 1
    current_phase: str = "introduction"
    objectives_met: list[str] = Field(default_factory=list)
    is_complete: bool = False


class Conversation(BaseModel):
    """
    Aggregate root: a full conversation session between a user and an NPC.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    npc: NPC
    scenario: Optional[ScenarioState] = None
    turns: list[Turn] = Field(default_factory=list)
    status: SimulationStatus = SimulationStatus.ACTIVE
    hints: list[Hint] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def last_turn(self) -> Optional[Turn]:
        return self.turns[-1] if self.turns else None

    def add_turn(self, speaker: Speaker, content: str, metadata: dict | None = None) -> Turn:
        """Create and append a new turn to the conversation."""
        turn = Turn(
            turn_number=self.turn_count + 1,
            speaker=speaker,
            content=content,
            metadata=metadata or {},
        )
        self.turns.append(turn)
        return turn

    def add_hint(self, content: str, hint_type: str = "suggestion", score: float = 0.0) -> Hint:
        """Add a contextual hint to the conversation."""
        hint = Hint(content=content, hint_type=hint_type, relevance_score=score)
        self.hints.append(hint)
        return hint

    def end_conversation(self) -> None:
        """Mark the conversation as completed."""
        self.status = SimulationStatus.COMPLETED
        self.ended_at = datetime.now(timezone.utc)
