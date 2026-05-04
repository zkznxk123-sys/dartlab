"""Public contracts for the DartLab research engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Ref:
    """Evidence reference produced by the research graph."""

    id: str
    kind: str
    title: str
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceEvent:
    """Internal research event.

    Only Agent Gateway may translate this object into public UI events.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "data": self.data, "ts": self.ts}


@dataclass(frozen=True)
class WorkbenchTask:
    """Compatibility task object for old callers that still import it."""

    question: str
    intent: str = "research"
    selectedSkillIds: list[str] = field(default_factory=list)
    requiredEvidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnswerDraft:
    """Compatibility answer draft used by verification tests and adapters."""

    text: str
    evidenceRefs: list[str] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationResult:
    """Ref-based answer verification result."""

    ok: bool
    refId: str
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
