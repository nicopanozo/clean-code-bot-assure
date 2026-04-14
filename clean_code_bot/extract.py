"""Extract a single fenced code block from model output."""

from __future__ import annotations

import re


def extract_primary_code_fence(text: str) -> str:
    """
    Return code inside the first ```lang ... ``` fence.

    If no fence is found, return stripped raw text (best-effort).
    """
    pattern = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?\s*\n(.*?)```", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return text.strip()
    return match.group(1).rstrip("\n")
