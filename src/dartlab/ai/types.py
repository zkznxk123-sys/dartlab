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
    """LLM 호출 설정 — provider/model/apiKey/baseUrl/temperature 통합."""

    provider: str | None = None
    model: str | None = None
    apiKey: str | None = None
    baseUrl: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    systemPrompt: str | None = None

    def merge(self, overrides: dict[str, Any]) -> LLMConfig:
        """기존 필드 위에 None 이 아닌 overrides 만 덮어쓴 새 LLMConfig."""
        values = asdict(self)
        values.update({key: value for key, value in overrides.items() if key in values and value is not None})
        return LLMConfig(**values)


@dataclass(frozen=True)
class LLMResponse:
    """LLM 응답 — content + provider + model + usage (answer alias 호환)."""

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
    """LLM 응답의 tool 호출 한 건 — id + 함수명 + arguments dict."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResponse:
    """tool calling 모드 응답 — answer + toolCalls list + finish_reason."""

    answer: str
    provider: str
    model: str
    toolCalls: list[ToolCall]
    context_tables: list[str] | None = None
    usage: dict[str, int] | None = None
    finish_reason: str = "stop"
