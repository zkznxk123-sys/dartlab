"""Canonical AI tool contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from dartlab.ai.contracts import Ref


@dataclass(frozen=True)
class ToolSpec:
    """LLM tool 정의 — name + description + inputSchema + MCP hint 4 종."""

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
        """ToolSpec 모든 필드 → dict 직렬화 (frozen dataclass 안전 변환)."""
        return asdict(self)

    @property
    def parameters(self) -> dict[str, Any]:
        """OpenAI-style compatibility alias for legacy tool callers."""
        return self.inputSchema


@dataclass
class ToolResult:
    """tool 실행 결과 — ok + summary + refs (Ref list) + data + error."""

    ok: bool
    summary: str
    refs: list[Ref] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def toDict(self) -> dict[str, Any]:
        """refs 의 Ref 도 dict 로 평탄화한 직렬화 형태."""
        return {
            "ok": self.ok,
            "summary": self.summary,
            "refs": [ref.toDict() for ref in self.refs],
            "data": self.data,
            "error": self.error,
        }
