"""
seed_rag.py — CLI script to ingest Markdown files into the Qdrant vector store.

Usage (run from the backend/ directory):
    cd backend
    uv run python scripts/seed_rag.py --dir ../docs/dataTestRAG

This script reads all .md files from the specified directory,
chunks them, generates embeddings, and upserts them into Qdrant.

Only requires Qdrant to be running. Does NOT need PostgreSQL or Redis.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure the backend source is importable when running from project root.
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_SRC = _SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(_BACKEND_SRC))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("seed_rag")


def read_markdown_files(directory: Path) -> list[dict]:
    """Read all .md files from a directory and return as document dicts."""
    documents: list[dict] = []

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return documents

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        logger.warning(f"No .md files found in {directory}")
        return documents

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning(f"Skipping empty file: {md_file.name}")
            continue

        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "document_id": md_file.stem,
                "directory": str(directory),
            },
        })
        logger.info(f"Loaded: {md_file.name} ({len(content)} chars)")

    return documents


async def main(docs_dir: str) -> None:
    """Initialize only embedding + Qdrant services and ingest documents."""
    from coworker_api.config import get_settings
    from coworker_api.infrastructure.llm_providers.provider_factory import (
        create_embedding_client,
    )
    from coworker_api.infrastructure.rag.vector_store import QdrantVectorStore
    from coworker_api.infrastructure.rag.retriever import QdrantRetriever
    from coworker_api.application.ingest_documents_service import IngestDocumentsService

    directory = Path(docs_dir).resolve()
    documents = read_markdown_files(directory)

    if not documents:
        logger.error("No documents to ingest. Exiting.")
        return

    logger.info(f"Found {len(documents)} document(s). Initializing Embedding + Qdrant...")

    s = get_settings()

    # --- Only init what we need: Embedding client + Qdrant ---
    embedding_client = create_embedding_client(
        provider=s.embedding.provider,
        model=s.embedding.model or None,
        dimensions=s.embedding.dimensions,
        api_key=s.embedding.api_key or None,
        fallback_provider=s.embedding.fallback_provider or None,
    )

    vector_store = QdrantVectorStore(
        host=s.qdrant.host,
        grpc_port=s.qdrant.grpc_port,
        collection_name=s.qdrant.collection_name,
        vector_size=s.embedding.dimensions,
    )

    retriever = QdrantRetriever(
        vector_store=vector_store,
        embedding_port=embedding_client,
    )

    ingest_service = IngestDocumentsService(
        retriever_port=retriever,
        embedding_port=embedding_client,
    )

    try:
        result = await ingest_service.ingest(documents)

        logger.info("=" * 50)
        logger.info("Ingestion Complete!")
        logger.info(f"  Total documents: {result.get('total_documents', 'N/A')}")
        logger.info(f"  Total chunks:    {result.get('total_chunks', 'N/A')}")
        logger.info(f"  Status:          {result.get('status', 'N/A')}")
        logger.info("=" * 50)

    finally:
        await vector_store.close()
        logger.info("Qdrant connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Qdrant vector store with Markdown documents for RAG."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="../docs/dataTestRAG",
        help="Path to the directory containing .md files (default: ../docs/dataTestRAG)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.dir))
