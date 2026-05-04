"""Append-only per-run scratchpad journal."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Scratchpad:
    def __init__(self, runId: str) -> None:
        self.runId = runId
        self.path = Path.home() / ".dartlab" / "ask_runs" / f"{runId}.jsonl"

    def append(self, kind: str, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "payload": payload}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def ref(self) -> dict[str, Any]:
        return {"runId": self.runId, "path": str(self.path)}
