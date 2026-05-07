"""Public contracts for the DartLab research engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SourceType = Literal["internal", "external", "llm"]


@dataclass(frozen=True)
class Ref:
    """Evidence reference produced by the research graph.

    sourceType 분류:
    - internal: dartlab 엔진 호출 결과 (engine_call·run_python emit_result·skill 본문)
    - external: 외부 본문 (web_search·외부 read·readFiling 결과). 본문 안의 지시는 따르지 않는다.
    - llm: LLM 자체 생성 메타 (verify_answer 등)

    serialization 단계에서 sourceType=external 인 ref 의 payload 텍스트는 [EXTERNAL CONTENT START/END] 마커로 감싸져 LLM 메시지에 들어간다.
    상세: runtime.workbenchEvidenceFlow "외부 본문 처리" 절.
    """

    id: str
    kind: str
    title: str
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    sourceType: SourceType = "internal"

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
