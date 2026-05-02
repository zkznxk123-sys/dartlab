"""Core contracts for the Ask Workbench Kernel.

This module is the type boundary for the new AI engine.  It deliberately does
not import the legacy AI package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

RefKind = Literal[
    "doc",
    "tool",
    "capability",
    "skill",
    "knowledge",
    "dataset",
    "date",
    "execution",
    "table",
    "value",
    "visual",
    "verify",
    "web",
]
ActionName = Literal[
    "search_reference",
    "read_context",
    "inspect_dataset",
    "run_python",
    "compile_visual",
    "finalize_answer",
]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:10]}"


@dataclass(frozen=True)
class WorkbenchTask:
    id: str
    question: str
    actions: list[ActionName] = field(
        default_factory=lambda: ["search_reference", "read_context", "inspect_dataset", "run_python", "compile_visual", "finalize_answer"]
    )
    release_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "numbersRequireRefs": True,
            "datesRequireRefs": True,
            "answerClaimsRequireRefs": True,
            "visualsRequireEvidence": True,
            "failedExecutionCannotBeHidden": True,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Ref:
    id: str
    kind: RefKind
    source: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    data: dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "data": self.data, "createdAt": self.created_at}


@dataclass(frozen=True)
class AnswerDraft:
    answer: str
    evidence_refs: list[str] = field(default_factory=list)
    material_claims: list[dict[str, Any]] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    visual_refs: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    issues: list[dict[str, Any]] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResultBundle:
    answer: str
    artifacts: list[dict[str, Any]]
    refs: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    verification: dict[str, Any]
    visuals: list[dict[str, Any]]
    limits: list[str]
    response_meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "artifacts": self.artifacts,
            "refs": self.refs,
            "trace": self.trace,
            "verification": self.verification,
            "visuals": self.visuals,
            "limits": self.limits,
            "responseMeta": self.response_meta,
        }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
