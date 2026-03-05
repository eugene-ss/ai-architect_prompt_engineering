"""ReAct agent with integrated self-reflection.

Implements the Thought -> Action -> Observation -> (Reflection) loop.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from prompt_engineering.config import AgentProfile
from prompt_engineering.prompts.loader import load_prompt
from prompt_engineering.services.llm_client import LLMClient, LLMResponse
from prompt_engineering.tools.base import BaseTool

logger = logging.getLogger(__name__)

class MessageHistory:
    def __init__(self) -> None:
        self._msgs: list[dict[str, Any]] = []

    def add_system(self, content: str) -> None:
        self._msgs.append({"role": "system", "content": content})

    def add_user(self, content: str) -> None:
        self._msgs.append({"role": "user", "content": content})

    def add_assistant(
        self, content: str | None = None, tool_calls: list[dict] | None = None
    ) -> None:
        msg: dict[str, Any] = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._msgs.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._msgs.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._msgs)

@dataclass
class AgentAnswer:
    """Final output of a ReAct run."""

    answer: str
    turns_used: int
    tools_used: int
    total_latency_ms: float
    reflections: list[str] = field(default_factory=list)
    trajectory: list[dict[str, Any]] = field(default_factory=list)

class ReActAgent:
    """ReAct agent with self-reflection after every tool turn.

    ReAct loop:
      1. Inject budget message
      2. Call LLM
      3. If tool_calls  -> execute tools, optionally self-reflect
      4. If no tool_calls -> agent is done, break
      5. Repeat until max_turns or agent finishes
    """

    def __init__(
        self,
        llm_client: LLMClient,
        profile: AgentProfile,
        tools: list[BaseTool],
    ) -> None:
        self._llm = llm_client
        self._profile = profile
        self._tools: dict[str, BaseTool] = {t.name: t for t in tools}
        self._history = MessageHistory()

        self._reflection_prompt: str | None = None
        if profile.enable_self_reflection:
            self._reflection_prompt = load_prompt(profile.self_reflection_prompt_file)

    @property
    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_tool() for t in self._tools.values()]

    async def run(self, query: str, *, system_prompt: str | None = None) -> AgentAnswer:
        if system_prompt is None:
            system_prompt = load_prompt(self._profile.system_prompt_file)

        self._history = MessageHistory()
        self._history.add_system(system_prompt)
        self._history.add_user(query)

        tool_budget = self._profile.tool_budget
        tools_used = 0
        reflections: list[str] = []
        trajectory: list[dict[str, Any]] = []
        t0 = time.perf_counter()

        for turn in range(self._profile.max_turns):
            logger.info("--- Turn %d ---", turn)

            if tool_budget <= 0:
                self._history.add_user(
                    "You have used all your tool calls. "
                    "Please provide your final answer now."
                )

            response = await self._call_llm()
            tool_calls = self._parse_tool_calls(response)

            if tool_calls and tool_budget > 0:
                self._history.add_assistant(
                    content=response.content, tool_calls=response.tool_calls
                )
                for tc in tool_calls:
                    result = await self._execute_tool(tc["name"], tc["arguments"])
                    self._history.add_tool_result(tc["id"], result)
                    trajectory.append({
                        "turn": turn,
                        "tool": tc["name"],
                        "input": tc["arguments"],
                        "output_preview": result[:500],
                    })
                    tools_used += 1
                    tool_budget -= 1

                if self._reflection_prompt and tool_budget > 0:
                    reflection = await self._reflect(turn, tool_budget)
                    if reflection:
                        self._history.add_user(
                            f"[Self-Reflection]\n{reflection}\n\nContinue with your next step."
                        )
                        reflections.append(reflection)
            else:
                if response.content:
                    self._history.add_assistant(content=response.content)
                break
        else:
            logger.warning("Agent reached max_turns (%d) without finishing", self._profile.max_turns)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        final_text = self._extract_final_answer() or (
            "I was unable to produce a complete answer within the allotted turns."
        )
        return AgentAnswer(
            answer=final_text,
            turns_used=turn + 1,
            tools_used=tools_used,
            total_latency_ms=elapsed_ms,
            reflections=reflections,
            trajectory=trajectory,
        )

    async def _call_llm(self) -> LLMResponse:
        return await self._llm.chat(
            messages=self._history.messages,
            temperature=self._profile.llm_config.temperature,
            max_tokens=self._profile.llm_config.max_tokens,
            tools=self._tool_schemas if self._tools else None,
        )

    async def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        tool = self._tools.get(tool_name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        logger.info("Tool call: %s", tool_name)
        try:
            return await tool.execute(**tool_input)
        except Exception as exc:
            logger.warning("Tool error on %s: %s", tool_name, exc)
            return json.dumps({"error": str(exc)})

    def _parse_tool_calls(self, response: LLMResponse) -> list[dict[str, Any]]:
        parsed: list[dict[str, Any]] = []
        for tc in response.tool_calls:
            func = tc.get("function", {})
            args_raw = func.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            parsed.append({"id": tc.get("id", ""), "name": func.get("name", ""), "arguments": args})
        return parsed

    async def _reflect(self, turn: int, tool_budget_remaining: int) -> str:
        """Produce a self-reflection by calling the LLM with the reflection prompt."""
        user_msg = (
            f"{self._reflection_prompt}\n\n"
            f"Current turn: {turn + 1}. Tool calls remaining: {tool_budget_remaining}."
        )
        messages = self._history.messages + [{"role": "user", "content": user_msg}]
        try:
            response = await self._llm.chat(messages=messages, temperature=0.2, max_tokens=512)
            text = response.content.strip()
            logger.info("Self-reflection completed for turn %d", turn)
            return text
        except Exception:
            logger.exception("Self-reflection failed at turn %d", turn)
            return ""

    def _extract_final_answer(self) -> str:
        for msg in reversed(self._history.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                return msg["content"]
        return ""
