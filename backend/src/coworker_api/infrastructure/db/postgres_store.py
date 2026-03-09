"""
PostgreSQL Conversation Store â€” Persistent storage for conversations.

Saves conversation history to PostgreSQL for long-term storage,
complementing the Redis ephemeral cache.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional

from pathlib import Path

from sqlalchemy import inspect, select
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
from passlib.context import CryptContext
from coworker_api.infrastructure.db.postgres_models import (
    Base,
    ConversationRow,
    NPCRow,
    ScenarioRow,
    TurnRow,
    UserRow,
)

logger = logging.getLogger(__name__)

# Use the same hashing context as rest_routes for consistency
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


class PostgresConversationStore:
    """
    Persists full conversation state to PostgreSQL.

    This is NOT a MemoryPort implementation â€” it's a secondary
    persistence layer used alongside Redis for durable storage.
    """

    def __init__(self, database_url: str):
        self._database_url = database_url
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
        logger.info(
            "PostgreSQL tables ensured (users, npcs, scenarios, conversations, turns)"
        )

    async def save_conversation(self, conversation: Conversation) -> None:
        """Upsert conversation and turns without destructive delete/reinsert."""
        async with self._session_factory() as session:
            async with session.begin():
                # Check if conversation already exists
                existing = await session.get(ConversationRow, conversation.id)
                existing_turns_by_id: dict[str, TurnRow] = {}

                if existing:
                    # Update existing conversation
                    existing.status = conversation.status.value
                    existing.ended_at = conversation.ended_at
                    existing.npc_data = conversation.npc.model_dump()
                    if conversation.scenario:
                        existing.scenario_data = conversation.scenario.model_dump()

                    turn_result = await session.execute(
                        select(TurnRow).where(TurnRow.conversation_id == conversation.id)
                    )
                    existing_turns_by_id = {row.id: row for row in turn_result.scalars().all()}
                else:
                    # Create new conversation row
                    conv_row = ConversationRow(
                        id=conversation.id,
                        user_id=self._to_uuid(conversation.user_id),
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
                    if turn.id in existing_turns_by_id:
                        turn_row = existing_turns_by_id[turn.id]
                        turn_row.turn_number = turn.turn_number
                        turn_row.speaker = turn.speaker.value
                        turn_row.content = turn.content
                        turn_row.metadata_json = turn.metadata
                        turn_row.created_at = turn.created_at
                        continue

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
                user_id=str(row.user_id),
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
                .where(ConversationRow.user_id == self._to_uuid(user_id))
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

    async def bootstrap_data(self) -> None:
        """Seed default admin user and NPCs if the database is empty."""
        async with self._session_factory() as session:
            async with session.begin():
                # 1. Bootstrap Admin User
                res = await session.execute(select(UserRow).limit(1))
                if not res.scalar_one_or_none():
                    admin_email = "admin@test.com"
                    admin_pass = "Admin@123"
                    admin_hash = pwd_context.hash(admin_pass)
                    admin = UserRow(
                        email=admin_email,
                        password_hash=admin_hash,
                        role="admin",
                    )
                    session.add(admin)
                    logger.info(f"Bootstrap: Created default admin user ({admin_email})")

                # 2. Bootstrap NPCs (Gucci group)
                res = await session.execute(select(NPCRow).limit(1))
                if not res.scalar_one_or_none():
                    gucci_npcs = [
                        {
                            "id": uuid.UUID("900ab9be-7ced-4b44-a193-6d70842d46e1"), # deterministic for dev
                            "name": "Marco Bizzarri",
                            "role_title": "Chief Executive Officer, Gucci",
                        },
                        {
                            "id": uuid.UUID("900ab9be-7ced-4b44-a193-6d70842d46e2"),
                            "name": "Elena Rossi",
                            "role_title": "Chief Human Resources Officer, Gucci",
                        },
                        {
                            "id": uuid.UUID("900ab9be-7ced-4b44-a193-6d70842d46e3"),
                            "name": "Alessandro Vitale",
                            "role_title": "Investment Banker, Gucci Group Finance",
                        },
                    ]
                    for npc_data in gucci_npcs:
                        npc = NPCRow(
                            id=npc_data["id"],
                            name=npc_data["name"],
                            role_title=npc_data["role_title"],
                            traits={},
                            system_prompt_template="",
                        )
                        session.add(npc)
                    logger.info("Bootstrap: Seeded default Gucci NPCs")

    async def migrate_to_head(self) -> None:
        """Apply Alembic migrations to head revision."""
        from alembic import command
        from alembic.config import Config

        backend_dir = Path(__file__).resolve().parents[4]
        alembic_ini = backend_dir / "alembic.ini"
        migrations_dir = backend_dir / "migrations"

        cfg = Config(str(alembic_ini))
        cfg.set_main_option("script_location", str(migrations_dir))
        cfg.set_main_option("sqlalchemy.url", self._database_url)

        async with self._engine.begin() as conn:
            table_names = set(
                await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            )

        def _upgrade_or_stamp(existing_tables: set[str]) -> None:
            has_alembic_version = "alembic_version" in existing_tables
            has_legacy_schema = bool(
                {"users", "npcs", "scenarios", "conversations", "turns"} & existing_tables
            )
            if not has_alembic_version and has_legacy_schema:
                command.stamp(cfg, "head")
                logger.warning(
                    "Detected pre-Alembic schema; stamped database to head. "
                    "Create a follow-up migration if schema drift exists."
                )
                return

            command.upgrade(cfg, "head")

        await asyncio.to_thread(_upgrade_or_stamp, table_names)
        logger.info("Alembic migrations applied to head")

    async def create_user(self, *, email: str, password_hash: str, role: str = "user") -> dict[str, Any]:
        """Create a user row and return a serialized representation."""
        user = UserRow(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
        )
        async with self._session_factory() as session:
            async with session.begin():
                session.add(user)
            try:
                await session.refresh(user)
            except Exception:
                pass
        return self._serialize_user(user)

    async def list_users(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(select(UserRow).order_by(UserRow.created_at.desc()))
            rows = result.scalars().all()
            return [self._serialize_user(row) for row in rows]

    async def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            row = await session.get(UserRow, self._to_uuid(user_id))
            return self._serialize_user(row) if row else None

    async def get_user_auth_by_email(self, email: str) -> Optional[dict[str, Any]]:
        normalized_email = email.strip().lower()
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserRow).where(UserRow.email == normalized_email)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return {
                "id": str(row.id),
                "email": row.email,
                "password_hash": row.password_hash,
                "role": row.role,
            }

    async def update_user(
        self,
        user_id: str,
        *,
        email: str | None = None,
        password_hash: str | None = None,
        role: str | None = None,
    ) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(UserRow, self._to_uuid(user_id))
                if row is None:
                    return None
                if email is not None:
                    row.email = email.strip().lower()
                if password_hash is not None:
                    row.password_hash = password_hash
                if role is not None:
                    row.role = role
            await session.refresh(row)
            return self._serialize_user(row)

    async def delete_user(self, user_id: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(UserRow, self._to_uuid(user_id))
                if row is None:
                    return False
                await session.delete(row)
                return True

    async def create_npc(
        self,
        *,
        name: str,
        role_title: str,
        system_prompt_template: str = "",
        traits: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        npc = NPCRow(
            name=name,
            role_title=role_title,
            system_prompt_template=system_prompt_template,
            traits=traits or {},
        )
        async with self._session_factory() as session:
            async with session.begin():
                session.add(npc)
            await session.refresh(npc)
        return self._serialize_npc(npc)

    async def list_npcs(self) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(select(NPCRow).order_by(NPCRow.created_at.desc()))
            rows = result.scalars().all()
            return [self._serialize_npc(row) for row in rows]

    async def get_npc(self, npc_id: str) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            row = await session.get(NPCRow, self._to_uuid(npc_id))
            return self._serialize_npc(row) if row else None

    async def update_npc(
        self,
        npc_id: str,
        *,
        name: str | None = None,
        role_title: str | None = None,
        system_prompt_template: str | None = None,
        traits: dict[str, Any] | None = None,
    ) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(NPCRow, self._to_uuid(npc_id))
                if row is None:
                    return None
                if name is not None:
                    row.name = name
                if role_title is not None:
                    row.role_title = role_title
                if system_prompt_template is not None:
                    row.system_prompt_template = system_prompt_template
                if traits is not None:
                    row.traits = traits
            await session.refresh(row)
            return self._serialize_npc(row)

    async def delete_npc(self, npc_id: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(NPCRow, self._to_uuid(npc_id))
                if row is None:
                    return False
                await session.delete(row)
                return True

    async def create_scenario(
        self,
        *,
        title: str,
        description: str,
        difficulty_level: int,
        npc_id: str,
    ) -> dict[str, Any]:
        scenario = ScenarioRow(
            title=title,
            description=description,
            difficulty_level=difficulty_level,
            npc_id=self._to_uuid(npc_id),
        )
        async with self._session_factory() as session:
            async with session.begin():
                session.add(scenario)
            await session.refresh(scenario)
        return self._serialize_scenario(scenario)

    async def list_scenarios(self, *, npc_id: str | None = None) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            stmt = select(ScenarioRow).order_by(ScenarioRow.created_at.desc())
            if npc_id:
                stmt = stmt.where(ScenarioRow.npc_id == self._to_uuid(npc_id))
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._serialize_scenario(row) for row in rows]

    async def get_scenario(self, scenario_id: str) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            row = await session.get(ScenarioRow, self._to_uuid(scenario_id))
            return self._serialize_scenario(row) if row else None

    async def update_scenario(
        self,
        scenario_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        difficulty_level: int | None = None,
        npc_id: str | None = None,
    ) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(ScenarioRow, self._to_uuid(scenario_id))
                if row is None:
                    return None
                if title is not None:
                    row.title = title
                if description is not None:
                    row.description = description
                if difficulty_level is not None:
                    row.difficulty_level = difficulty_level
                if npc_id is not None:
                    row.npc_id = self._to_uuid(npc_id)
            await session.refresh(row)
            return self._serialize_scenario(row)

    async def delete_scenario(self, scenario_id: str) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.get(ScenarioRow, self._to_uuid(scenario_id))
                if row is None:
                    return False
                await session.delete(row)
                return True

    @staticmethod
    def _to_uuid(value: str) -> uuid.UUID:
        return uuid.UUID(value)


    @staticmethod
    def _serialize_user(row: UserRow) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "email": row.email,
            "role": row.role,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _serialize_npc(row: NPCRow) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "name": row.name,
            "role_title": row.role_title,
            "system_prompt_template": row.system_prompt_template,
            "traits": row.traits or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _serialize_scenario(row: ScenarioRow) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "difficulty_level": row.difficulty_level,
            "npc_id": str(row.npc_id),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
