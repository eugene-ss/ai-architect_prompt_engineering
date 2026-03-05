"""Batch processor for concurrent LLM request execution.

Designed when LLM providers introduce native batch
endpoints, the ``_execute_single`` method can be swapped to use a batch API
without changing the caller interface.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from prompt_engineering.services.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)

@dataclass
class ChatRequest:
    """Single chat-completion request."""

    messages: list[dict[str, Any]]
    temperature: float = 0.3
    max_tokens: int = 4096
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result for one item in a batch."""

    index: int
    request: ChatRequest
    response: LLMResponse | None = None
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        return self.response is not None


class BatchProcessor:
    """Process multiple LLM requests concurrently."""

    def __init__(
        self,
        client: LLMClient,
        max_concurrency: int | None = None,
    ) -> None:
        self._client = client
        concurrency = max_concurrency or client._settings.MAX_CONCURRENT_REQUESTS
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _execute_single(
        self, index: int, request: ChatRequest
    ) -> BatchResult:
        async with self._semaphore:
            try:
                resp = await self._client.chat(
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    tools=request.tools,
                    tool_choice=request.tool_choice,
                )
                return BatchResult(index=index, request=request, response=resp)
            except Exception as exc:
                logger.warning("Batch item %d failed: %s", index, exc)
                return BatchResult(index=index, request=request, error=exc)

    async def run(self, requests: list[ChatRequest]) -> list[BatchResult]:
        """Execute all requests concurrently and return results.

        Failed requests are captured in ``BatchResult.error``, one failure does not abort the entire batch.
        """
        if not requests:
            return []

        logger.info(
            "Batch: processing %d requests (concurrency=%d)",
            len(requests),
            self._semaphore._value,
        )
        t0 = time.perf_counter()

        tasks = [
            self._execute_single(i, req) for i, req in enumerate(requests)
        ]
        results = await asyncio.gather(*tasks)
        results_sorted = sorted(results, key=lambda r: r.index)

        elapsed = (time.perf_counter() - t0) * 1000
        ok_count = sum(1 for r in results_sorted if r.ok)
        logger.info(
            "Batch complete: %d/%d succeeded in %.0f ms",
            ok_count,
            len(requests),
            elapsed,
        )
        return results_sorted
