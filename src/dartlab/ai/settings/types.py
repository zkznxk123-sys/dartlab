"""Core AI configuration types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """Provider connection settings used by setup/profile code."""

    provider: str = "dartlab"
    model: str | None = None
    apiKey: str | None = None
    baseUrl: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    systemPrompt: str | None = None
