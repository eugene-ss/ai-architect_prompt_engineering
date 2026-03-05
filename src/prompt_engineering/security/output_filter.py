"""Output-side content filtering: indirect injection detection and PII redaction."""

from __future__ import annotations

import re

_OUTPUT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\[SYSTEM\]", re.I),
    re.compile(r"<\|im_start\|>system", re.I),
    re.compile(r"<\|endoftext\|>", re.I),
    re.compile(r"ignore\s+previous\s+instructions", re.I),
    re.compile(r"(fetch|curl|wget|http[s]?://)\s*['\"]?https?://", re.I),
]

_PII_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
]

def filter_output(text: str) -> tuple[str, list[str]]:
    """Redact PII and strip indirect-injection markers from LLM output.

    Returns ``(filtered_text, list_of_findings)``.
    """
    findings: list[str] = []

    for pat in _PII_PATTERNS:
        if pat.search(text):
            findings.append(f"PII: {pat.pattern}")
            text = pat.sub("[REDACTED]", text)

    for pat in _OUTPUT_INJECTION_PATTERNS:
        if pat.search(text):
            findings.append(f"Output injection: {pat.pattern}")
            text = pat.sub("[FILTERED]", text)

    return text, findings
