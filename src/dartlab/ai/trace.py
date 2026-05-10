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
        """observe — TODO 한국어 동작 설명."""
        self.events.append({"kind": kind, "data": dict(data or {})})

    def flush(self) -> None:
        """flush — TODO 한국어 동작 설명."""
        return None
