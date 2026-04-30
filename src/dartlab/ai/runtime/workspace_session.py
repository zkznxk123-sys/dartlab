"""Request-local session state for the workspace-native AI agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class Observation:
    id: str
    source: str
    target: str | None = None
    metric: str | None = None
    value: Any | None = None
    unit: str | None = None
    observedDate: str | None = None
    collectedAt: str | None = None
    period: str | None = None
    universe: str | None = None
    basis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_empty(asdict(self))


@dataclass
class Execution:
    id: str
    code: str
    stdout: str
    stderr: str
    returncode: int
    durationMs: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return _drop_empty(
            {
                "id": self.id,
                "ok": self.ok,
                "durationMs": self.durationMs,
                "returncode": self.returncode,
                "stdout": self.stdout[:4000],
                "stderr": self.stderr[:2000],
                "code": self.code[:4000],
            }
        )


@dataclass
class AgentSession:
    question: str
    workspaceRoot: Path
    dataRoot: Path
    currentDate: str = field(default_factory=lambda: date.today().isoformat())
    observations: list[Observation] = field(default_factory=list)
    executions: list[Execution] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    visuals: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    finalAnswer: str = ""
    verified: bool = False
    verificationIssues: list[str] = field(default_factory=list)
    _seq: int = 0

    def next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq:04d}"

    def record_trace(self, phase: str, payload: dict[str, Any]) -> None:
        self.trace.append({"phase": phase, **_json_safe(payload)})

    def add_limit(self, message: str) -> None:
        if message and message not in self.limits:
            self.limits.append(message)

    def add_observation(self, **kwargs: Any) -> Observation:
        item = Observation(
            id=self.next_id("obs"),
            collectedAt=datetime.now().isoformat(timespec="seconds"),
            **kwargs,
        )
        self.observations.append(item)
        return item

    def response_meta(self) -> dict[str, Any]:
        pack_events = [event.get("pack") for event in self.trace if isinstance(event.get("pack"), dict)]
        latest_pack = next((event for event in reversed(pack_events) if event), {})
        process_ids: list[str] = []
        for event in self.trace:
            for process_id in event.get("processMapIds") or []:
                if process_id not in process_ids:
                    process_ids.append(str(process_id))
        pack_hit_count = sum(int(event.get("packHits") or 0) for event in self.trace)
        return {
            "agent": {
                "mode": "workspace_native",
                "currentDate": self.currentDate,
                "workspaceRoot": str(self.workspaceRoot),
                "dataRoot": str(self.dataRoot),
                "observationCount": len(self.observations),
                "executionCount": len(self.executions),
                "artifactCount": len(self.artifacts),
                "visualCount": len(self.visuals),
                "verified": self.verified,
                "verificationIssues": list(self.verificationIssues),
                "packVersion": latest_pack.get("schemaVersion"),
                "packSourceHash": latest_pack.get("sourceHash"),
                "packHitCount": pack_hit_count,
                "selectedProcess": process_ids[:5],
                "visualValidity": {
                    "visualCount": len(self.visuals),
                    "valid": "degenerate_visual" not in self.verificationIssues,
                },
                "trace": self.trace[-40:],
            }
        }


def _drop_empty(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _json_safe(value: Any) -> Any:
    try:
        import polars as pl

        if isinstance(value, pl.DataFrame):
            return value.to_dicts()
    except ImportError:
        pass
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
