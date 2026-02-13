"""
PostgreSQL Conversation Store — Persistent storage for conversations.

Saves conversation history to PostgreSQL for long-term storage,
complementing the Redis ephemeral cache.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from coworker_api.domain.models import (
    Conversation,
    NPC,
    ScenarioState,
    Speaker,
    SimulationStatus,
    Turn,
)
from coworker_api.infrastructure.db.postgres_models import (
    Base,
    ConversationRow,
    TurnRow,
)

logger = logging.getLogger(__name__)


class PostgresConversationStore:
    """
    Persists full conversation state to PostgreSQL.

    This is NOT a MemoryPort implementation — it's a secondary
    persistence layer used alongside Redis for durable storage.
    """

    def __init__(self, database_url: str):
        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL tables ensured (conversations, turns)")

    async def save_conversation(self, conversation: Conversation) -> None:
        """Upsert the full conversation and its turns to PostgreSQL."""
        async with self._session_factory() as session:
            async with session.begin():
                # Check if conversation already exists
                existing = await session.get(ConversationRow, conversation.id)

                if existing:
                    # Update existing conversation
                    existing.status = conversation.status.value
                    existing.ended_at = conversation.ended_at
                    existing.npc_data = conversation.npc.model_dump()
                    if conversation.scenario:
                        existing.scenario_data = conversation.scenario.model_dump()

                    # Delete old turns and re-insert (simple upsert strategy)
                    await session.execute(
                        delete(TurnRow).where(
                            TurnRow.conversation_id == conversation.id
                        )
                    )
                else:
                    # Create new conversation row
                    conv_row = ConversationRow(
                        id=conversation.id,
                        user_id=conversation.user_id,
                        npc_name=conversation.npc.name,
                        npc_role_title=conversation.npc.role_title,
                        npc_data=conversation.npc.model_dump(),
                        scenario_data=(
                            conversation.scenario.model_dump()
                            if conversation.scenario
                            else None
                        ),
                        status=conversation.status.value,
                        started_at=conversation.started_at,
                        ended_at=conversation.ended_at,
                    )
                    session.add(conv_row)

                # Insert all turns
                for turn in conversation.turns:
                    turn_row = TurnRow(
                        id=turn.id,
                        conversation_id=conversation.id,
                        turn_number=turn.turn_number,
                        speaker=turn.speaker.value,
                        content=turn.content,
                        metadata_json=turn.metadata,
                        created_at=turn.created_at,
                    )
                    session.add(turn_row)

        logger.debug(
            "Conversation saved to PostgreSQL",
            extra={
                "session_id": conversation.id,
                "turns": len(conversation.turns),
            },
        )

    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """Load a conversation from PostgreSQL by session ID."""
        async with self._session_factory() as session:
            row = await session.get(ConversationRow, session_id)
            if row is None:
                return None

            # Load turns
            result = await session.execute(
                select(TurnRow)
                .where(TurnRow.conversation_id == session_id)
                .order_by(TurnRow.turn_number)
            )
            turn_rows = result.scalars().all()

            # Reconstruct domain model
            npc = NPC(**row.npc_data) if row.npc_data else NPC(
                name=row.npc_name, role_title=row.npc_role_title or ""
            )
            scenario = (
                ScenarioState(**row.scenario_data) if row.scenario_data else None
            )
            turns = [
                Turn(
                    id=t.id,
                    turn_number=t.turn_number,
                    speaker=Speaker(t.speaker),
                    content=t.content,
                    metadata=t.metadata_json or {},
                    created_at=t.created_at,
                )
                for t in turn_rows
            ]

            return Conversation(
                id=row.id,
                user_id=row.user_id,
                npc=npc,
                scenario=scenario,
                turns=turns,
                status=SimulationStatus(row.status),
                started_at=row.started_at,
                ended_at=row.ended_at,
            )

    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """List conversation summaries for a user from PostgreSQL."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ConversationRow)
                .where(ConversationRow.user_id == user_id)
                .order_by(ConversationRow.started_at.desc())
            )
            rows = result.scalars().all()

            return [
                {
                    "id": row.id,
                    "npc_name": row.npc_name,
                    "npc_role_title": row.npc_role_title,
                    "status": row.status,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                }
                for row in rows
            ]

    async def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation and its turns from PostgreSQL."""
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(ConversationRow, session_id)
                if row is None:
                    return False
                await session.delete(row)
                return True

    async def close(self) -> None:
        """Dispose the engine."""
        await self._engine.dispose()
        logger.info("PostgreSQL connection closed")
