"""Trace and audit utilities for Ask Workbench."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditCollector:
    """Small server-side audit collector for kernel events."""

    question: str = ""
    stockCode_hint: str | None = None
    provider: str | None = None
    model: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def observe(self, kind: str, data: dict[str, Any]) -> None:
        self.events.append({"kind": kind, "data": data})

    def flush(self) -> None:
        path = _audit_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            packet = {
                "question": self.question,
                "stockCodeHint": self.stockCode_hint,
                "provider": self.provider,
                "model": self.model,
                "events": self.events,
            }
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(packet, ensure_ascii=False) + "\n")
        except OSError:
            return


def installProgressCapture() -> None:
    """Compatibility no-op; progress is now emitted as kernel trace events."""


def _audit_path() -> Path | None:
    import os

    raw = os.environ.get("DARTLAB_AI_AUDIT_JSONL")
    if not raw:
        return None
    return Path(raw)
