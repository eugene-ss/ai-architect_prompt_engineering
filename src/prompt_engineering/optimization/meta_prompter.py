"""Meta-prompting: use an LLM to refine a prompt."""

from __future__ import annotations

from dataclasses import dataclass

from prompt_engineering.services.llm_client import LLMClient

_META_SYSTEM = (
    "You are a principal prompt engineer. Your goal is to take an existing "
    "prompt and make it as clear, specific, and actionable as possible for an "
    "AI assistant. Preserve the original intent but improve structure, "
    "add missing guardrails, and ensure the output format is well-defined."
)

_META_USER = """\
Here is my current prompt:

---
{prompt}
---

Please refine this prompt to make it even more clear and actionable for an AI assistant.
Specifically:
1. Improve the overall structure (use numbered sections or bullet points).
2. Add specific output-format instructions where missing.
3. Include quality constraints (accuracy, tone, cultural sensitivity).
4. Add pedagogical best practices if applicable (spaced repetition, scaffolding).
5. Ensure the prompt is self-contained.

Return ONLY the refined prompt text, no commentary.
"""

@dataclass
class MetaPromptResult:
    original_prompt: str
    refined_prompt: str
    test_query: str | None = None
    original_response: str | None = None
    refined_response: str | None = None

class MetaPrompter:
    """Uses an LLM to refine prompts and optionally A/B-test the results."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    async def refine(self, prompt: str) -> str:
        """Ask the LLM to improve *prompt* for clarity and actionability."""
        messages = [
            {"role": "system", "content": _META_SYSTEM},
            {"role": "user", "content": _META_USER.format(prompt=prompt)},
        ]
        resp = await self._llm.chat(messages=messages, temperature=0.3, max_tokens=2048)
        return resp.content.strip()

    async def refine_and_test(self, prompt: str, test_query: str) -> MetaPromptResult:
        """Refine the prompt then A/B-test both versions with *test_query*."""
        refined = await self.refine(prompt)

        async def _test(system: str) -> str:
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": test_query}]
            return (await self._llm.chat(messages=msgs, temperature=0.3, max_tokens=4096)).content.strip()

        original_response = await _test(prompt)
        refined_response = await _test(refined)
        return MetaPromptResult(
            original_prompt=prompt,
            refined_prompt=refined,
            test_query=test_query,
            original_response=original_response,
            refined_response=refined_response,
        )