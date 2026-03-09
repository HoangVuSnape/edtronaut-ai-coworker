"""
Domain Ports (Interfaces) for Edtronaut AI Coworker.

These Abstract Base Classes define the contracts that the Infrastructure
layer MUST implement. The Domain and Application layers depend ONLY on
these interfaces, never on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from coworker_api.domain.models import Conversation


# ── LLM Port ──

class LLMPort(ABC):
    """Interface for interacting with a Large Language Model."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a text completion from the LLM."""
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Generate a streaming text completion, yielding chunks."""
        ...


# ── Retriever Port (RAG) ──

class RetrieverPort(ABC):
    """Interface for retrieving relevant documents from a knowledge base."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant document chunks for a given query.

        Returns a list of dicts, each containing:
            - content (str): The text chunk.
            - score (float): Similarity score.
            - metadata (dict): Source info (document_id, chunk_index, etc.).
        """
        ...

    @abstractmethod
    async def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        Add documents to the knowledge base.

        Each document dict should have:
            - content (str): The text.
            - metadata (dict): Source info.

        Returns the number of documents added.
        """
        ...


# ── Tool Port ──

class ToolPort(ABC):
    """Interface for executing external tools (calculators, simulators)."""

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a named tool with the given arguments."""
        ...

    @abstractmethod
    def list_tools(self) -> list[dict[str, str]]:
        """
        List available tools.

        Returns a list of dicts with:
            - name (str): Tool identifier.
            - description (str): What the tool does.
        """
        ...


# ── Memory Port ──

class MemoryPort(ABC):
    """Interface for persisting and loading conversation state."""

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None:
        """Persist the full conversation state."""
        ...

    @abstractmethod
    async def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """Load a conversation by session ID. Returns None if not found."""
        ...

    @abstractmethod
    async def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation. Returns True if something was deleted."""
        ...

    @abstractmethod
    async def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """
        List conversation summaries for a user.

        Returns lightweight dicts with: id, npc_name, status, started_at.
        """
        ...


# ── Embedding Port ──

class EmbeddingPort(ABC):
    """Interface for generating vector embeddings from text."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text strings."""
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """Generate an embedding for a single text string."""
        ...
