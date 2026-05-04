"""Async LLM client supporting Ollama (local), OpenAI, and Anthropic.

Ollama is the default provider. It exposes an OpenAI-compatible REST API
at /v1/chat/completions, so we reuse AsyncOpenAI with a custom base_url —
no extra SDK needed.

JSON robustness
---------------
Local models do not guarantee well-formed JSON the way the OpenAI
response_format={"type": "json_object"} does.  _parse_json() applies a
three-stage extraction strategy:
  1. Direct json.loads on the full response.
  2. Regex extraction of the first {...} block (handles markdown fences).
  3. Raises ValueError so the caller can retry or surface the error to
     Temporal, which will handle the activity retry policy.

Usage:
    from app.llm_client import LLMClient
    client = LLMClient()
    data = await client.chat(messages)   # returns dict
"""

from __future__ import annotations

import json
import logging
import re

from app.config import config

logger = logging.getLogger(__name__)

# Matches the first JSON object in the string, including nested braces.
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json(raw: str) -> dict:
    """Extract a JSON object from raw LLM output using a robust multi-stage strategy.

    Args:
        raw: The raw text string returned by the LLM.

    Returns:
        A dictionary parsed from the JSON found in the raw text.

    Raises:
        ValueError: If no valid JSON object could be extracted or parsed 
            after checking both the full string and the first {...} block.
    """
    raw = raw.strip()

    # Stage 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Stage 2: extract first {...} block
    m = _JSON_BLOCK_RE.search(raw)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Found JSON-like block but failed to parse: {exc}\nBlock: {m.group()[:300]}"
            ) from exc

    raise ValueError(
        f"No JSON object found in LLM output.\nRaw (first 400 chars): {raw[:400]}"
    )


class LLMClient:
    """Async LLM client facade supporting ollama, openai, and anthropic."""

    def __init__(self) -> None:
        self.provider = config.llm_provider
        self.model = config.llm_model

    async def chat(self, messages: list[dict]) -> dict:
        """Send messages and return the parsed JSON body of the assistant reply.

        This method abstracts away the provider-specific logic and ensures 
        that the response is always returned as a structured dictionary.

        Args:
            messages: A list of chat message dictionaries (role, content).

        Returns:
            A dictionary containing the JSON response from the model.

        Raises:
            ValueError: If the response cannot be parsed as JSON after
                all extraction attempts, or if the provider is unsupported.
                The caller (activity) should let this propagate so Temporal 
                can retry according to the activity retry policy.
        """
        logger.debug(
            "LLM chat: provider=%s model=%s messages=%d",
            self.provider, self.model, len(messages),
        )
        if self.provider == "ollama":
            return await self._ollama_chat(messages)
        if self.provider == "openai":
            return await self._openai_chat(messages)
        if self.provider == "anthropic":
            return await self._anthropic_chat(messages)
        raise ValueError(f"Unsupported LLM provider: {self.provider!r}")

    # ------------------------------------------------------------------
    # Ollama  (OpenAI-compatible local endpoint)
    # ------------------------------------------------------------------

    async def _ollama_chat(self, messages: list[dict]) -> dict:
        """Call the Ollama REST API reusing the OpenAI SDK with a custom base_url.

        Args:
            messages: A list of chat message dictionaries.

        Returns:
            The parsed JSON response as a dictionary.
        """
        from openai import AsyncOpenAI  # lazy import

        client = AsyncOpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama",
        )
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.0,
        )
        raw = response.choices[0].message.content or "{}"
        logger.debug("Ollama raw response (first 500): %s", raw[:500])
        return _parse_json(raw)

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
        raw = response.choices[0].message.content or "{}"
        logger.debug("OpenAI raw response (first 500): %s", raw[:500])
        return _parse_json(raw)

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
        raw = response.content[0].text if response.content else "{}"
        logger.debug("Anthropic raw response (first 500): %s", raw[:500])
        return _parse_json(raw)
