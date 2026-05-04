"""Canonical AI tool contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from dartlab.ai.contracts import Ref


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    inputSchema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    ok: bool
    summary: str
    refs: list[Ref] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": self.summary,
            "refs": [ref.to_dict() for ref in self.refs],
            "data": self.data,
            "error": self.error,
        }
