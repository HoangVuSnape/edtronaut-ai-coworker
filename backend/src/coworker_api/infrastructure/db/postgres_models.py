"""
PostgreSQL ORM Models — SQLAlchemy table definitions.

Defines the relational schema for persisting conversation history
to PostgreSQL for long-term storage.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ConversationRow(Base):
    """Persisted conversation session."""

    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    npc_name = Column(String(128), nullable=False)
    npc_role_title = Column(String(256), nullable=True)
    npc_data = Column(JSON, nullable=True)          # full NPC snapshot
    scenario_data = Column(JSON, nullable=True)      # scenario state snapshot
    status = Column(String(32), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    turns = relationship(
        "TurnRow",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="TurnRow.turn_number",
    )


class TurnRow(Base):
    """A single message turn within a conversation."""

    __tablename__ = "turns"

    id = Column(String(64), primary_key=True)
    conversation_id = Column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    speaker = Column(String(16), nullable=False)     # "user", "npc", "system"
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    # Relationship
    conversation = relationship("ConversationRow", back_populates="turns")
