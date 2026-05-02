"""Small provider compatibility types for the Ask Workbench boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class LLMResponse:
    content: str
    raw: dict[str, Any] | None = None
