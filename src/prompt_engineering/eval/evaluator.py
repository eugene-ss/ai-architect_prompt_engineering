"""Side-by-side prompt version comparison."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from prompt_engineering.config import VERSION_MAP
from prompt_engineering.eval.metrics import EvaluationScores, MetricEvaluator
from prompt_engineering.prompts.loader import load_prompt
from prompt_engineering.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class VersionResult:
    version: str
    query: str
    response: str
    scores: EvaluationScores

@dataclass
class ComparisonReport:
    results: list[VersionResult] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        by_version: dict[str, list[EvaluationScores]] = {}
        for r in self.results:
            by_version.setdefault(r.version, []).append(r.scores)
        out: dict[str, Any] = {}
        for version, scores in by_version.items():
            n = len(scores)
            out[version] = {
                "avg_relevance": round(sum(s.relevance for s in scores) / n, 2),
                "avg_coherence": round(sum(s.coherence for s in scores) / n, 2),
                "avg_completeness": round(sum(s.completeness for s in scores) / n, 2),
                "avg_actionability": round(sum(s.actionability for s in scores) / n, 2),
                "avg_composite": round(sum(s.composite_score for s in scores) / n, 2),
                "safety_pass_rate": round(sum(1 for s in scores if s.is_safe) / n, 2),
                "avg_latency_ms": round(sum(s.latency_ms for s in scores) / n, 1),
                "num_queries": n,
            }
        return out

class PromptEvaluator:
    """Compare prompt versions by running test queries and scoring results."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client
        self._metric = MetricEvaluator(llm_client)

    async def evaluate_version(self, version: str, query: str) -> VersionResult:
        prompt_file = VERSION_MAP.get(version)
        if not prompt_file:
            raise ValueError(f"Unknown version '{version}'. Available: {list(VERSION_MAP.keys())}")
        system_prompt = load_prompt(prompt_file)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}]
        resp = await self._llm.chat(messages=messages, temperature=0.3, max_tokens=4096)
        scores = await self._metric.evaluate(
            query=query, response=resp.content, latency_ms=resp.latency_ms,
            token_count=resp.usage.get("total_tokens", 0),
        )
        return VersionResult(version=version, query=query, response=resp.content, scores=scores)

    async def compare(self, test_queries: list[str], versions: list[str] | None = None) -> ComparisonReport:
        versions = versions or list(VERSION_MAP.keys())
        report = ComparisonReport()
        for version in versions:
            for query in test_queries:
                logger.info("Evaluating %s with query: %s", version, query[:60])
                report.results.append(await self.evaluate_version(version, query))
        return report
