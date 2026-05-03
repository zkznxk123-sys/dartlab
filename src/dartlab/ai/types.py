"""Small provider compatibility types for the Ask Workbench boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None

    def merge(self, overrides: dict[str, Any]) -> LLMConfig:
        values = asdict(self)
        values.update({key: value for key, value in overrides.items() if key in values and value is not None})
        return LLMConfig(**values)


@dataclass(frozen=True)
class LLMResponse:
    content: str = ""
    raw: dict[str, Any] | None = None
    answer: str = ""
    provider: str = ""
    model: str = ""
    context_tables: list[str] | None = None
    usage: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.answer and not self.content:
            object.__setattr__(self, "content", self.answer)
        elif self.content and not self.answer:
            object.__setattr__(self, "answer", self.content)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResponse:
    answer: str
    provider: str
    model: str
    tool_calls: list[ToolCall]
    context_tables: list[str] | None = None
    usage: dict[str, int] | None = None
    finish_reason: str = "stop"
