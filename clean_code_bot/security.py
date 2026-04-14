"""Input validation and sanitization to reduce prompt-injection risk."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Tunable limits — adjust for your environment / model context window.
MAX_INPUT_BYTES = 256_000  # ~250 KiB of source
MAX_LINES = 8_000

# Patterns often used in indirect prompt injection in "data" channels.
_INJECTION_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?is)\b(ignore|disregard)\b.{0,80}\b(previous|prior|above)\b.{0,40}\b(instructions?|prompt|system)\b"
    ),
    re.compile(r"(?is)\b(you are now|new instructions?|override)\b"),
    # Role markers at line start (avoid matching phrases like "file system:").
    re.compile(r"(?im)^\s*(system|assistant)\s*[:>]"),
    re.compile(r"(?is)<\s*/?\s*system\s*>"),
    re.compile(r"(?is)\b(secret|password|api[_-]?key|token)\b.{0,40}\b(is|are|=|:)\b"),
)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating user-supplied source text."""

    ok: bool
    message: str
    sanitized: str | None = None


def _strip_control_chars(text: str) -> str:
    # Remove NUL and most C0 controls except common whitespace.
    return "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ord(ch) >= 32)


def validate_and_sanitize_source(text: str, *, path: Path | None = None) -> ValidationResult:
    """
    Validate size and scan for high-risk injection phrasing.

    Defense in depth (not a cryptographic guarantee):
    - Hard caps on bytes/lines.
    - Neutral framing is applied later in the prompt template.
    - Suspicious phrases are flagged so the operator can abort or review.
    """
    if not text or not text.strip():
        return ValidationResult(False, "Input is empty.")

    raw_bytes = len(text.encode("utf-8", errors="strict"))
    if raw_bytes > MAX_INPUT_BYTES:
        return ValidationResult(
            False,
            f"Input too large ({raw_bytes} bytes). Limit is {MAX_INPUT_BYTES} bytes.",
        )

    line_count = text.count("\n") + 1
    if line_count > MAX_LINES:
        return ValidationResult(
            False,
            f"Input has too many lines ({line_count}). Limit is {MAX_LINES}.",
        )

    cleaned = _strip_control_chars(text)

    lowered = cleaned.lower()
    for pat in _INJECTION_HINT_PATTERNS:
        if pat.search(lowered):
            hint = path.as_posix() if path else "stdin"
            return ValidationResult(
                False,
                "Possible prompt-injection patterns detected in the source. "
                f"Review file {hint} and remove meta-instructions embedded in code/comments, "
                "or split the file.",
            )

    return ValidationResult(True, "OK", sanitized=cleaned)


def assert_safe_path(path: Path) -> None:
    """Ensure path is a normal file path (no obvious traversal)."""
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        raise ValueError(f"Invalid path: {path}") from exc
    if not resolved.is_file():
        raise ValueError(f"Not a file: {resolved}")
