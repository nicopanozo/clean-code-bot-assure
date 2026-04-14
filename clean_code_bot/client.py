"""OpenAI-compatible chat client (OpenAI + Groq)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass(frozen=True)
class LlmConfig:
    provider: str  # "openai" | "groq"
    model: str
    api_key: str
    base_url: str | None = None


def load_llm_config_from_env() -> LlmConfig:
    provider = (os.getenv("CLEAN_CODE_BOT_PROVIDER") or "openai").strip().lower()
    if provider not in {"openai", "groq"}:
        raise ValueError('CLEAN_CODE_BOT_PROVIDER must be "openai" or "groq".')

    if provider == "groq":
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            raise ValueError("GROQ_API_KEY is required when CLEAN_CODE_BOT_PROVIDER=groq.")
        model = os.getenv("CLEAN_CODE_BOT_MODEL", "llama-3.3-70b-versatile").strip()
        return LlmConfig(
            provider=provider,
            model=model,
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
        )

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENAI_API_KEY is required when CLEAN_CODE_BOT_PROVIDER=openai (default).")
    model = os.getenv("CLEAN_CODE_BOT_MODEL", "gpt-4o-mini").strip()
    return LlmConfig(provider=provider, model=model, api_key=key, base_url=None)


def chat_completion(*, system: str, user: str, temperature: float = 0.2) -> str:
    cfg = load_llm_config_from_env()
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    resp = client.chat.completions.create(
        model=cfg.model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    choice = resp.choices[0].message.content
    if not choice:
        raise RuntimeError("Empty completion from model.")
    return choice
