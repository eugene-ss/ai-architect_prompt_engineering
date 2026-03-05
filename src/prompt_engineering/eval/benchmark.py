"""Benchmark runner with JSON persistence for trend analysis."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_engineering.eval.evaluator import ComparisonReport, PromptEvaluator

logger = logging.getLogger(__name__)

class BenchmarkRunner:
    """Run evaluations and persist results for trend analysis."""

    def __init__(self, evaluator: PromptEvaluator, output_dir: str | Path = "outputs/benchmarks") -> None:
        self._evaluator = evaluator
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def run(
        self, test_queries: list[str], versions: list[str] | None = None, run_label: str | None = None
    ) -> ComparisonReport:
        report = await self._evaluator.compare(test_queries, versions)
        self._save(report, run_label)
        return report

    def _save(self, report: ComparisonReport, label: str | None) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"{label}_{ts}" if label else ts
        path = self._output_dir / f"benchmark_{name}.json"
        data: dict[str, Any] = {
            "timestamp": ts,
            "summary": report.summary(),
            "results": [
                {
                    "version": r.version, "query": r.query,
                    "response_preview": r.response[:500], "scores": r.scores.to_dict(),
                }
                for r in report.results
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Benchmark saved to %s", path)
        return path
