"""
Memory Schemas for Edtronaut AI Coworker.

Defines the structure of memory objects used for session state
and conversation summaries in the Memory Port.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    """A condensed summary of a conversation for long-term storage."""
    conversation_id: str
    user_id: str
    npc_name: str
    scenario_title: str = ""
    total_turns: int = 0
    key_topics: list[str] = Field(default_factory=list)
    summary_text: str = ""
    lessons_learned: list[str] = Field(default_factory=list)
    user_performance_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryState(BaseModel):
    """
    The in-memory state of an active session, stored in Redis.

    This is the "hot" state that changes every turn, separate from
    the full Conversation model stored in Postgres.
    """
    session_id: str
    user_id: str
    npc_persona: str = ""
    current_turn: int = 0
    npc_mood: str = "neutral"
    director_feedback: Optional[str] = None
    short_term_history: list[dict[str, Any]] = Field(default_factory=list)
    rag_context: list[str] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, speaker: str, content: str) -> None:
        """Append a message to the short-term history window."""
        self.short_term_history.append({
            "speaker": speaker,
            "content": content,
            "turn": self.current_turn,
        })
        # Keep only the last 20 messages in short-term memory
        if len(self.short_term_history) > 20:
            self.short_term_history = self.short_term_history[-20:]

    def to_context_string(self) -> str:
        """Serialize the short-term history into a string for prompt injection."""
        lines = []
        for msg in self.short_term_history:
            lines.append(f"{msg['speaker'].capitalize()}: {msg['content']}")
        return "\n".join(lines)
