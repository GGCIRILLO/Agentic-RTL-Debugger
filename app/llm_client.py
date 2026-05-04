"""Thin LLM client that supports OpenAI and Anthropic.

Usage:
    from app.llm_client import LLMClient
    client = LLMClient()
    response = await client.chat(messages)
"""

from __future__ import annotations

import json
import logging

from app.config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Async LLM client façade."""

    def __init__(self) -> None:
        self.provider = config.llm_provider
        self.model = config.llm_model

    async def chat(self, messages: list[dict]) -> dict:
        """Send messages and return the parsed JSON body of the assistant reply."""
        if self.provider == "openai":
            return await self._openai_chat(messages)
        if self.provider == "anthropic":
            return await self._anthropic_chat(messages)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _openai_chat(self, messages: list[dict]) -> dict:
        from openai import AsyncOpenAI  # lazy import

        client = AsyncOpenAI(api_key=config.openai_api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        logger.debug("OpenAI raw response: %s", content)
        return json.loads(content)

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    async def _anthropic_chat(self, messages: list[dict]) -> dict:
        import anthropic  # lazy import

        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        user_messages = [m for m in messages if m["role"] != "system"]

        client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_msg,
            messages=user_messages,  # type: ignore[arg-type]
        )
        content = response.content[0].text if response.content else "{}"
        logger.debug("Anthropic raw response: %s", content)
        return json.loads(content)
