"""
OpenAI-Compatible LLM Client — Implements LLMPort.

Works with ANY provider that exposes an OpenAI-compatible API:
  - OpenAI (default)
  - Google Gemini (via generativelanguage.googleapis.com)
  - DeepSeek (via api.deepseek.com)
  - Zhipu AI / GLM (via open.bigmodel.cn)

Just change the `base_url` and `api_key`.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from coworker_api.domain.ports import LLMPort
from coworker_api.domain.exceptions import LLMConnectionError

logger = logging.getLogger(__name__)


class OpenAIClient(LLMPort):
    """
    OpenAI-compatible LLM adapter.

    Supports any provider with a chat completions API by setting `base_url`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        default_temperature: float = 0.7,
        default_max_tokens: int = 1024,
        base_url: str | None = None,
        provider_name: str = "openai",
    ):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens
        self._provider_name = provider_name

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a text completion."""
        messages = self._build_messages(system_prompt, prompt)
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature or self._default_temperature,
                max_tokens=max_tokens or self._default_max_tokens,
            )
            content = response.choices[0].message.content or ""
            logger.debug(
                "LLM response generated",
                extra={
                    "provider": self._provider_name,
                    "model": self._model,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            )
            return content
        except Exception as e:
            logger.error(f"{self._provider_name} API call failed", exc_info=True)
            raise LLMConnectionError(f"{self._provider_name} API error: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming text completion, yielding chunks."""
        messages = self._build_messages(system_prompt, prompt)
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature or self._default_temperature,
                max_tokens=max_tokens or self._default_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"{self._provider_name} streaming failed", exc_info=True)
            raise LLMConnectionError(f"{self._provider_name} streaming error: {e}") from e

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict]:
        """Build the messages array."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages
