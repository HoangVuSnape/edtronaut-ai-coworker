"""
OpenAI-Compatible Embedding Client — Implements EmbeddingPort.

Works with any provider that exposes an OpenAI-compatible embeddings API.
For providers without embedding support (e.g., DeepSeek), falls back
to a compatible alternative.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from coworker_api.domain.ports import EmbeddingPort
from coworker_api.domain.exceptions import LLMConnectionError

logger = logging.getLogger(__name__)


class OpenAIEmbeddingClient(EmbeddingPort):
    """
    OpenAI-compatible embedding adapter.

    Supports OpenAI, Gemini (via OpenAI endpoint), and other compatible APIs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        base_url: str | None = None,
        provider_name: str = "openai",
    ):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._dimensions = dimensions
        self._provider_name = provider_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []
        try:
            kwargs = {
                "model": self._model,
                "input": texts,
            }
            # Only pass dimensions if provider supports it
            if self._provider_name in ("openai",):
                kwargs["dimensions"] = self._dimensions

            response = await self._client.embeddings.create(**kwargs)
            embeddings = [item.embedding for item in response.data]
            logger.debug(
                "Embeddings generated",
                extra={
                    "provider": self._provider_name,
                    "count": len(texts),
                    "model": self._model,
                },
            )
            return embeddings
        except Exception as e:
            logger.error(f"{self._provider_name} embedding failed", exc_info=True)
            raise LLMConnectionError(f"{self._provider_name} embedding error: {e}") from e

    async def embed_single(self, text: str) -> list[float]:
        """Generate an embedding for a single text string."""
        results = await self.embed([text])
        return results[0] if results else []
