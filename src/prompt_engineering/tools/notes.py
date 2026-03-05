"""Tool for lesson planning and progress tracking."""

from __future__ import annotations

from typing import Any

from prompt_engineering.tools.base import BaseTool

class NotesTool(BaseTool):
    def __init__(self) -> None:
        self._notes: str = ""

    @property
    def name(self) -> str:
        return "notes_tool"

    @property
    def description(self) -> str:
        return (
            "Notes tool for lesson planning and progress tracking. "
            "Use action='write' to replace, 'append' to add, or 'read' to retrieve."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["write", "append", "read"],
                    "description": "write = overwrite, append = add to end, read = return current notes.",
                },
                "content": {"type": "string", "description": "Text to write or append.", "default": ""},
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "read")
        content = kwargs.get("content", "")
        if action == "write":
            self._notes = content
            return self._json({"status": "ok", "action": "write", "length": len(self._notes)})
        elif action == "append":
            self._notes += "\n" + content if self._notes else content
            return self._json({"status": "ok", "action": "append", "length": len(self._notes)})
        else:
            return self._json({"notes": self._notes if self._notes else "(empty)"})