"""Orchestrates validation → LLM → extraction."""

from __future__ import annotations

from pathlib import Path

from clean_code_bot.client import chat_completion
from clean_code_bot.cot import build_prompt_bundle
from clean_code_bot.extract import extract_primary_code_fence
from clean_code_bot.security import assert_safe_path, validate_and_sanitize_source


def infer_language_hint(path: Path | None) -> str:
    if path is None:
        return "unknown (infer from code)"
    suffix = path.suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
    }
    return mapping.get(suffix, suffix.lstrip(".") or "unknown")


def refactor_source(text: str, *, path: Path | None = None, temperature: float = 0.2) -> str:
    if path is not None:
        assert_safe_path(path)

    validation = validate_and_sanitize_source(text, path=path)
    if not validation.ok or validation.sanitized is None:
        raise ValueError(validation.message)

    bundle = build_prompt_bundle(
        language_hint=infer_language_hint(path),
        user_code=validation.sanitized,
    )
    raw = chat_completion(system=bundle.system, user=bundle.user, temperature=temperature)
    return extract_primary_code_fence(raw)
