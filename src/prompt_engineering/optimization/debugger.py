"""Prompt debugging: analyse a poorly performing prompt, then refine it."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from prompt_engineering.eval.metrics import strip_json_fences
from prompt_engineering.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_ANALYSIS_SYSTEM = (
    "You are an expert prompt engineer. Your task is to analyse a given prompt "
    "and identify specific weaknesses that would cause a language model to "
    "produce low-quality output."
)

_ANALYSIS_USER = """\
Here is the prompt to analyse:

---
{prompt}
---

Identify weaknesses and return a JSON object:
{{"missing_context": [...], "ambiguity_issues": [...], "specificity_gaps": [...], \
"overall_quality_score": <1-10>, "improvement_suggestions": [...]}}

Return ONLY the JSON object, no other text.
"""

_REFINE_SYSTEM = (
    "You are an expert prompt engineer. Rewrite the given prompt to fix all "
    "identified issues while keeping the original intent intact."
)

_REFINE_USER = """\
Original prompt:
---
{original_prompt}
---

Identified issues:
{issues_json}

Produce an improved prompt that adds all missing context, eliminates ambiguity, \
increases specificity, and maintains a clear professional tone.

Return ONLY the improved prompt text, no commentary.
"""

@dataclass
class PromptAnalysis:
    missing_context: list[str] = field(default_factory=list)
    ambiguity_issues: list[str] = field(default_factory=list)
    specificity_gaps: list[str] = field(default_factory=list)
    overall_quality_score: int = 0
    improvement_suggestions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

class PromptDebugger:
    """Two-step pipeline: analyse -> refine a prompt."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def analyse(self, prompt: str) -> PromptAnalysis:
        """Identify weaknesses in *prompt* using LLM-based analysis."""
        messages = [
            {"role": "system", "content": _ANALYSIS_SYSTEM},
            {"role": "user", "content": _ANALYSIS_USER.format(prompt=prompt)},
        ]
        resp = await self._llm.chat(messages=messages, temperature=0.2, max_tokens=1024)
        text = strip_json_fences(resp.content)
        try:
            data: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Could not parse analysis JSON – returning raw text")
            return PromptAnalysis(raw={"raw_text": text})
        return PromptAnalysis(
            missing_context=data.get("missing_context", []),
            ambiguity_issues=data.get("ambiguity_issues", []),
            specificity_gaps=data.get("specificity_gaps", []),
            overall_quality_score=data.get("overall_quality_score", 0),
            improvement_suggestions=data.get("improvement_suggestions", []),
            raw=data,
        )

    async def refine(self, original_prompt: str, analysis: PromptAnalysis) -> str:
        """Produce an improved prompt based on the analysis."""
        issues = json.dumps(analysis.raw or {"suggestions": analysis.improvement_suggestions}, indent=2)
        messages = [
            {"role": "system", "content": _REFINE_SYSTEM},
            {"role": "user", "content": _REFINE_USER.format(original_prompt=original_prompt, issues_json=issues)},
        ]
        resp = await self._llm.chat(messages=messages, temperature=0.3, max_tokens=2048)
        return resp.content.strip()

    async def debug_and_optimize(self, prompt: str) -> tuple[PromptAnalysis, str]:
        """Full pipeline: analyse then refine."""
        analysis = await self.analyse(prompt)
        refined = await self.refine(prompt, analysis)
        return analysis, refined
