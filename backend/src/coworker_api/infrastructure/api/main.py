"""
FastAPI Application Factory & gRPC Server Bootstrap.

Entry point for the backend. Initializes all dependencies,
wires up the DI container, and starts both the REST and gRPC servers.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from coworker_api.config import get_settings, load_npc_config
from coworker_api.infrastructure.monitoring.logging import setup_logging

logger = logging.getLogger(__name__)


# ── Dependency Container ──

class AppContainer:
    """Simple dependency injection container for wiring services."""

    def __init__(self):
        self.settings = get_settings()
        self._initialized = False

        # Infrastructure adapters (lazy)
        self.redis_store = None
        self.postgres_store = None
        self.memory_store = None  # CompositeMemoryStore (Redis + PG)
        self.llm_client = None
        self.embedding_client = None
        self.vector_store = None
        self.retriever = None

        # Application services (lazy)
        self.session_manager = None
        self.chat_service = None
        self.director_service = None
        self.evaluation_service = None
        self.ingest_service = None
        self.reset_service = None

    async def initialize(self) -> None:
        """Wire all dependencies."""
        if self._initialized:
            return

        from coworker_api.infrastructure.db.memory_store import RedisMemoryStore
        from coworker_api.infrastructure.db.postgres_store import PostgresConversationStore
        from coworker_api.infrastructure.db.composite_store import CompositeMemoryStore
        from coworker_api.infrastructure.llm_providers.provider_factory import (
            create_llm_client, create_embedding_client,
        )
        from coworker_api.infrastructure.rag.vector_store import QdrantVectorStore
        from coworker_api.infrastructure.rag.retriever import QdrantRetriever
        from coworker_api.application.session_manager import SessionManager
        from coworker_api.application.chat_service import ChatService
        from coworker_api.application.director_service import DirectorService
        from coworker_api.application.evaluation_service import EvaluationService
        from coworker_api.application.ingest_documents_service import IngestDocumentsService
        from coworker_api.application.reset_memory_service import ResetMemoryService

        s = self.settings

        # Infrastructure — Redis (fast cache)
        self.redis_store = RedisMemoryStore(
            redis_url=s.redis.url,
            session_ttl=s.redis.session_ttl_seconds,
        )

        # Infrastructure — PostgreSQL (persistent history)
        self.postgres_store = PostgresConversationStore(
            database_url=s.postgres.url,
        )
        await self.postgres_store.create_tables()

        # Infrastructure — Composite (Redis + PostgreSQL)
        self.memory_store = CompositeMemoryStore(
            redis_store=self.redis_store,
            postgres_store=self.postgres_store,
        )
        self.llm_client = create_llm_client(
            provider=s.llm.provider,
            model=s.llm.model or None,
            temperature=s.llm.temperature,
            max_tokens=s.llm.max_tokens,
            api_key=s.llm.api_key or None,
            base_url=s.llm.base_url or None,
        )
        self.embedding_client = create_embedding_client(
            provider=s.embedding.provider,
            model=s.embedding.model or None,
            dimensions=s.embedding.dimensions,
            api_key=s.embedding.api_key or None,
            fallback_provider=s.embedding.fallback_provider or None,
        )
        self.vector_store = QdrantVectorStore(
            host=s.qdrant.host,
            grpc_port=s.qdrant.grpc_port,
            collection_name=s.qdrant.collection_name,
            vector_size=s.embedding.dimensions,
        )
        self.retriever = QdrantRetriever(
            vector_store=self.vector_store,
            embedding_port=self.embedding_client,
        )

        # Application services
        self.session_manager = SessionManager(memory_port=self.memory_store)
        self.chat_service = ChatService(
            session_manager=self.session_manager,
            llm_port=self.llm_client,
            retriever_port=self.retriever,
        )
        self.director_service = DirectorService(llm_port=self.llm_client)
        self.evaluation_service = EvaluationService(llm_port=self.llm_client)
        self.ingest_service = IngestDocumentsService(
            retriever_port=self.retriever,
            embedding_port=self.embedding_client,
        )
        self.reset_service = ResetMemoryService(session_manager=self.session_manager)

        self._initialized = True
        logger.info("Application container initialized")

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self.memory_store:
            await self.memory_store.close()
        if self.vector_store:
            await self.vector_store.close()
        logger.info("Application container shut down")



# ── Global container instance ──
container = AppContainer()


# ── FastAPI App Factory ──

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    setup_logging()
    logger.info("Starting Edtronaut AI Coworker backend...")
    await container.initialize()
    yield
    logger.info("Shutting down...")
    await container.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Register REST routes
    from coworker_api.infrastructure.api.rest_routes import router
    app.include_router(router)

    return app


# ── Module-level app for uvicorn ──
app = create_app()
