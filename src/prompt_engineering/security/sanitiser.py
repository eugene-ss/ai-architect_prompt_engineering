"""Input sanitizing and prompt-injection detection."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_INPUT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts?)", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?new\s+(ai|assistant|system)", re.I),
    re.compile(r"disregard\s+(all\s+)?(system|safety)\s+(prompt|message|instruction)", re.I),
    re.compile(r"override\s+(your|the)\s+(system|safety)", re.I),
    re.compile(r"pretend\s+you\s+(are|have)\s+no\s+(rules|restrictions)", re.I),
    re.compile(r"\bDAN\b.*\bjailbreak\b", re.I),
    re.compile(r"forget\s+(everything|all)\s+(you\s+)?(know|were\s+told)", re.I),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+(guidelines|guardrails)", re.I),
    re.compile(r"(system|developer)\s*prompt\s*[:=]", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"respond\s+only\s+with\s+(yes|no|true|false)", re.I),
    re.compile(r"repeat\s+(the|your)\s+(system|initial)\s+(prompt|instructions)", re.I),
    re.compile(r"translate\s+(the\s+)?(above|system)\s+(prompt|text)\s+to", re.I),
]

def detect_prompt_injection(text: str) -> list[str]:
    """Return matched injection-pattern descriptions on *input* (empty = clean)."""
    return [p.pattern for p in _INPUT_INJECTION_PATTERNS if p.search(text)]


def sanitise_input(text: str, *, max_length: int = 10_000) -> str:
    """Strip control chars, enforce length, and block injection attempts.

    Raises ``ValueError`` if injection patterns are found.
    """
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)[:max_length]
    injections = detect_prompt_injection(cleaned)
    if injections:
        logger.warning("Prompt-injection attempt: %s", injections)
        raise ValueError("Input rejected: potential prompt-injection detected.")
    return cleaned
