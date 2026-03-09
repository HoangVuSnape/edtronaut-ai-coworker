"""
PostgreSQL ORM Models - SQLAlchemy table definitions.

Contains both:
1) core domain tables from Database_Design.md (users, npcs, scenarios),
2) existing conversation persistence tables (conversations, turns).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class UserRow(Base):
    """Application user."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        SAEnum("admin", "user", name="user_role_enum", native_enum=True),
        nullable=False,
        default="user",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class NPCRow(Base):
    """AI persona configuration."""

    __tablename__ = "npcs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    role_title = Column(String(255), nullable=False)
    system_prompt_template = Column(Text, nullable=False, default="")
    traits = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    scenarios = relationship("ScenarioRow", back_populates="npc")


class ScenarioRow(Base):
    """Simulation setup template."""

    __tablename__ = "scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    difficulty_level = Column(Integer, nullable=False, default=1)
    npc_id = Column(
        UUID(as_uuid=True),
        ForeignKey("npcs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    npc = relationship("NPCRow", back_populates="scenarios")


class ConversationRow(Base):
    """Persisted conversation session (legacy active runtime storage)."""

    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    npc_name = Column(String(128), nullable=False)
    npc_role_title = Column(String(256), nullable=True)
    npc_data = Column(JSON, nullable=True)
    scenario_data = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    turns = relationship(
        "TurnRow",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="TurnRow.turn_number",
    )


class TurnRow(Base):
    """A single message turn within a conversation."""

    __tablename__ = "turns"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "turn_number",
            name="uq_turns_conversation_turn_number",
        ),
    )

    id = Column(String(64), primary_key=True)
    conversation_id = Column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    speaker = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    conversation = relationship("ConversationRow", back_populates="turns")
