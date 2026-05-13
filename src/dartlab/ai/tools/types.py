"""Canonical AI tool contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from dartlab.ai.contracts import Ref


@dataclass(frozen=True)
class ToolSpec:
    """ToolSpec — TODO 한국어 클래스 설명."""

    name: str
    description: str
    inputSchema: dict[str, Any]
    # MCP Tool Annotations — 외부 LLM 의 도구 안전성 / 재실행 가능성 / 외부 의존 판단 힌트.
    # 모두 default None — 기존 plugin 이 ToolSpec 직접 인스턴스화해도 호환.
    # 매핑 시 None 인 hint 는 ToolAnnotations 에서 빠지고 LLM 이 추론하도록 둠.
    readOnlyHint: bool | None = None
    destructiveHint: bool | None = None
    idempotentHint: bool | None = None
    openWorldHint: bool | None = None

    def toDict(self) -> dict[str, Any]:
        """toDict — TODO 한국어 동작 설명."""
        return asdict(self)

    @property
    def parameters(self) -> dict[str, Any]:
        """OpenAI-style compatibility alias for legacy tool callers."""
        return self.inputSchema


@dataclass
class ToolResult:
    """ToolResult — TODO 한국어 클래스 설명."""

    ok: bool
    summary: str
    refs: list[Ref] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def toDict(self) -> dict[str, Any]:
        """toDict — TODO 한국어 동작 설명."""
        return {
            "ok": self.ok,
            "summary": self.summary,
            "refs": [ref.toDict() for ref in self.refs],
            "data": self.data,
            "error": self.error,
        }
