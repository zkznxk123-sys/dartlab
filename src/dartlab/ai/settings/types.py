"""Core AI configuration types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """Provider connection settings used by setup/profile code."""

    provider: str = "dartlab"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None
