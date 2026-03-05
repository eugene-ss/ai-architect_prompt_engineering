"""Async Azure OpenAI client with retry."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from prompt_engineering.config import AppSettings

logger = logging.getLogger(__name__)

class LLMResponse:

    def __init__(self, raw: dict[str, Any], latency_ms: float) -> None:
        self.raw = raw
        self.latency_ms = latency_ms

    @property
    def content(self) -> str:
        choices = self.raw.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        choices = self.raw.get("choices", [])
        if not choices:
            return []
        return choices[0].get("message", {}).get("tool_calls") or []

    @property
    def usage(self) -> dict[str, int]:
        return self.raw.get("usage", {})

    @property
    def finish_reason(self) -> str:
        choices = self.raw.get("choices", [])
        if not choices:
            return "unknown"
        return choices[0].get("finish_reason", "unknown")


class LLMClient:
    """
    URL pattern::

        POST {ENDPOINT_URL}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions
             ?api-version={API_VERSION}
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._url = settings.completions_url
        self._headers = {
            "Content-Type": "application/json",
            "api-key": settings.OPENAI_API_KEY.get_secret_value(),
        }
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._settings.REQUEST_TIMEOUT_SECONDS),
                limits=httpx.Limits(
                    max_connections=self._settings.MAX_CONCURRENT_REQUESTS,
                    max_keepalive_connections=20,
                ),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> LLMResponse:
        """Send a chat-completion request with automatic retry."""
        return await self._chat_with_retry(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )

    @retry(
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def _chat_with_retry(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | None,
    ) -> LLMResponse:
        client = await self._ensure_client()
        body: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice

        logger.debug("LLM request to %s (msgs=%d)", self._url, len(messages))
        t0 = time.perf_counter()
        resp = await client.post(self._url, json=body, headers=self._headers)
        latency_ms = (time.perf_counter() - t0) * 1000

        resp.raise_for_status()
        data = resp.json()
        finish = data.get("choices", [{}])[0].get("finish_reason")
        logger.debug("LLM response in %.0f ms  finish=%s", latency_ms, finish)
        return LLMResponse(raw=data, latency_ms=latency_ms)
