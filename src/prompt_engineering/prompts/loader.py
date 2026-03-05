"""Prompt file loader.

Loads MD prompt files from the prompts/ directory.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent

def load_prompt(reference: str) -> str:
    """Load a prompt from a file reference.

    Args:
        reference: Either a ``file:`` prefixed path relative to the prompts
            directory, or a relative path.
    """
    if reference.startswith("file:"):
        reference = reference[len("file:"):]
    path = _PROMPTS_DIR / reference
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")
