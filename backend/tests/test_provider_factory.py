"""Unit tests for coworker_api.infrastructure.llm_providers.provider_factory."""

from __future__ import annotations

import os

import pytest

from coworker_api.infrastructure.llm_providers.provider_factory import (
    PROVIDERS,
    create_embedding_client,
    create_llm_client,
)
from coworker_api.infrastructure.llm_providers.openai_client import OpenAIClient
from coworker_api.infrastructure.llm_providers.embedding_client import OpenAIEmbeddingClient


class TestCreateLLMClient:
    def test_returns_openai_client(self):
        client = create_llm_client(provider="openai", api_key="test-key")
        assert isinstance(client, OpenAIClient)

    def test_uses_default_model_for_provider(self):
        client = create_llm_client(provider="gemini", api_key="test-key")
        assert isinstance(client, OpenAIClient)

    def test_model_override(self):
        client = create_llm_client(
            provider="openai", model="gpt-4o-mini", api_key="test-key"
        )
        assert isinstance(client, OpenAIClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client(provider="nonexistent", api_key="x")

    def test_all_registered_providers_valid(self):
        for provider_name in PROVIDERS:
            client = create_llm_client(provider=provider_name, api_key="test-key")
            assert isinstance(client, OpenAIClient)


class TestCreateEmbeddingClient:
    def test_returns_embedding_client(self):
        client = create_embedding_client(provider="openai", api_key="test-key")
        assert isinstance(client, OpenAIEmbeddingClient)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_embedding_client(provider="nonexistent", api_key="x")

    def test_deepseek_falls_back_to_gemini(self):
        """DeepSeek has no embedding API → should fall back."""
        client = create_embedding_client(
            provider="deepseek",
            api_key="test-key",
            fallback_provider="openai",
        )
        assert isinstance(client, OpenAIEmbeddingClient)

    def test_provider_with_embeddings_returns_directly(self):
        client = create_embedding_client(provider="gemini", api_key="test-key")
        assert isinstance(client, OpenAIEmbeddingClient)
