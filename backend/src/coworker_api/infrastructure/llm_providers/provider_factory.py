"""
LLM Provider Factory — Creates the right LLM and Embedding clients
based on the configured provider name.

Supported providers:
  ┌──────────────┬───────────────────────────────┬────────────────────────────┐
  │ Provider     │ LLM Models                    │ Embedding Models           │
  ├──────────────┼───────────────────────────────┼────────────────────────────┤
  │ openai       │ gpt-4o, gpt-4o-mini, ...      │ text-embedding-3-small     │
  │ gemini       │ gemini-2.0-flash, gemini-pro  │ text-embedding-004         │
  │ deepseek     │ deepseek-chat, deepseek-r1    │ (use gemini/openai)        │
  │ zhipu        │ glm-4.5, glm-4.6              │ embedding-3                │
  └──────────────┴───────────────────────────────┴────────────────────────────┘

All providers use the OpenAI-compatible API protocol.
"""

from __future__ import annotations

import os
import logging
from typing import NamedTuple

from coworker_api.domain.ports import LLMPort, EmbeddingPort
from coworker_api.infrastructure.llm_providers.openai_client import OpenAIClient
from coworker_api.infrastructure.llm_providers.embedding_client import OpenAIEmbeddingClient

logger = logging.getLogger(__name__)


# ── Provider Registry ──

class ProviderConfig(NamedTuple):
    """Configuration for an OpenAI-compatible provider."""
    base_url: str | None
    env_key_name: str
    default_model: str
    default_embedding_model: str | None
    default_embedding_dimensions: int


PROVIDERS: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        base_url=None,  # AsyncOpenAI default
        env_key_name="OPENAI_API_KEY",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
        default_embedding_dimensions=1536,
    ),
    "gemini": ProviderConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key_name="GEMINI_API_KEY",
        default_model="gemini-2.0-flash",
        default_embedding_model="text-embedding-004",
        default_embedding_dimensions=768,
    ),
    "deepseek": ProviderConfig(
        base_url="https://api.deepseek.com",
        env_key_name="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        default_embedding_model=None,  # DeepSeek has no embedding API
        default_embedding_dimensions=768,
    ),
    "zhipu": ProviderConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        env_key_name="ZHIPU_API_KEY",
        default_model="glm-4.5",
        default_embedding_model="embedding-3",
        default_embedding_dimensions=2048,
    ),
}


def create_llm_client(
    provider: str = "openai",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMPort:
    """
    Factory to create an LLM client for the specified provider.

    Args:
        provider: One of "openai", "gemini", "deepseek", "zhipu".
        model: Override the model name. Defaults to provider's default.
        temperature: Sampling temperature.
        max_tokens: Max tokens in response.
        api_key: API key (falls back to env variable).
        base_url: Override base URL (e.g. for AgentRouter/proxies).

    Returns:
        An LLMPort-compatible client.
    """
    provider = provider.lower()
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Available: {', '.join(PROVIDERS.keys())}"
        )

    config = PROVIDERS[provider]
    resolved_key = api_key or os.environ.get(config.env_key_name, "")
    resolved_model = model or config.default_model
    resolved_base_url = base_url or config.base_url

    logger.info(
        f"Creating LLM client: provider={provider}, model={resolved_model}, url={resolved_base_url}"
    )

    return OpenAIClient(
        api_key=resolved_key,
        model=resolved_model,
        default_temperature=temperature,
        default_max_tokens=max_tokens,
        base_url=resolved_base_url,
        provider_name=provider,
    )


def create_embedding_client(
    provider: str = "openai",
    model: str | None = None,
    dimensions: int | None = None,
    api_key: str | None = None,
    fallback_provider: str | None = None,
) -> EmbeddingPort:
    """
    Factory to create an embedding client for the specified provider.

    If the provider doesn't support embeddings (e.g., DeepSeek), it will
    automatically fall back to `fallback_provider` or Gemini.

    Args:
        provider: Primary provider name.
        model: Override the embedding model name.
        dimensions: Override the embedding dimensions.
        api_key: API key (falls back to env variable).
        fallback_provider: Provider to use if primary has no embedding support.

    Returns:
        An EmbeddingPort-compatible client.
    """
    provider = provider.lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'.")

    config = PROVIDERS[provider]

    # Fallback if provider has no embedding model
    if config.default_embedding_model is None:
        fallback = fallback_provider or "gemini"
        logger.warning(
            f"Provider '{provider}' has no embedding API. "
            f"Falling back to '{fallback}' for embeddings."
        )
        return create_embedding_client(
            provider=fallback,
            model=model,
            dimensions=dimensions,
        )

    resolved_key = api_key or os.environ.get(config.env_key_name, "")
    resolved_model = model or config.default_embedding_model
    resolved_dims = dimensions or config.default_embedding_dimensions

    logger.info(
        f"Creating embedding client: provider={provider}, model={resolved_model}"
    )

    return OpenAIEmbeddingClient(
        api_key=resolved_key,
        model=resolved_model,
        dimensions=resolved_dims,
        base_url=config.base_url,
        provider_name=provider,
    )
