"""Audit and progress capture hooks for AI streams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def installProgressCapture() -> None:
    """Install progress capture hooks.

    The new engine exposes progress through Agent Gateway events, so the server
    bootstrap hook is intentionally idempotent and side-effect free.
    """

    return None


@dataclass
class AuditCollector:
    """In-memory audit collector used by server streaming adapters."""

    question: str = ""
    stockCode_hint: str | None = None
    provider: str | None = None
    model: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def observe(self, kind: str, data: dict[str, Any] | None = None) -> None:
        """이벤트 1 건 누적 (in-memory) — kind + data dict."""
        self.events.append({"kind": kind, "data": dict(data or {})})

    def flush(self) -> None:
        """no-op — 서버 어댑터 호환용 hook (실제 flush 없음)."""
        return None
