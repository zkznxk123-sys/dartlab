"""DartLab AI 공통 타입 SSOT.

Provider compatibility (LLMConfig / LLMResponse / ToolCall / ToolResponse) +
contracts re-export (Ref / TraceEvent / WorkbenchTask / AnswerDraft / VerificationResult).
새 import 는 본 파일 경로 사용. 옛 `from dartlab.ai.contracts import Ref` 도 호환.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# contracts re-export — Phase D 점진 통합. 점진 마이그레이션 시 옛 경로 폐기.
from .contracts import (  # noqa: F401
    AnswerDraft,
    Ref,
    TraceEvent,
    VerificationResult,
    WorkbenchTask,
)


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
