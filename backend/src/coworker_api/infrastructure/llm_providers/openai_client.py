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
    _MAX_CONTINUATION_CALLS = 2
    _CONTINUE_PROMPT = (
        "Continue exactly from where you stopped. "
        "Do not repeat previous text. Complete the answer."
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
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
            resolved_temperature = (
                temperature if temperature is not None else self._default_temperature
            )
            resolved_max_tokens = (
                max_tokens if max_tokens is not None else self._default_max_tokens
            )

            parts: list[str] = []
            final_finish_reason = ""
            for attempt in range(self._MAX_CONTINUATION_CALLS + 1):
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=resolved_temperature,
                    max_tokens=resolved_max_tokens,
                )

                choice = response.choices[0]
                content_piece = choice.message.content or ""
                finish_reason = getattr(choice, "finish_reason", "") or ""
                final_finish_reason = finish_reason
                parts.append(content_piece)

                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
                logger.debug(
                    "LLM response chunk generated: provider=%s model=%s finish_reason=%s "
                    "prompt_tokens=%s completion_tokens=%s chars=%s attempt=%s",
                    self._provider_name,
                    self._model,
                    finish_reason or "unknown",
                    prompt_tokens,
                    completion_tokens,
                    len(content_piece),
                    attempt + 1,
                )

                if finish_reason != "length":
                    break

                if attempt >= self._MAX_CONTINUATION_CALLS:
                    logger.warning(
                        "LLM response may be truncated after continuation attempts: "
                        "provider=%s model=%s",
                        self._provider_name,
                        self._model,
                    )
                    break

                if not content_piece.strip():
                    logger.warning(
                        "LLM returned empty chunk with finish_reason=length; aborting continuation"
                    )
                    break

                messages.append({"role": "assistant", "content": content_piece})
                messages.append({"role": "user", "content": self._CONTINUE_PROMPT})

            content = "".join(parts).strip()
            if not content:
                logger.warning(
                    "LLM returned empty content: provider=%s model=%s finish_reason=%s",
                    self._provider_name,
                    self._model,
                    final_finish_reason or "unknown",
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
