"""Public contracts for the DartLab research engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def _nowIso() -> str:
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

    payload 표준 키 (Track A·B finance AI 격상 계약 — soft-cuddling-kitten plan):

    1 차 출처 deep-link (docRef / tableRef 발급 시):
    - docId: str — 공시 식별자 (예: DART rcept_no, EDGAR accession_no)
    - page: int (1-based) — 페이지 번호
    - lineStart: int — 시작 라인 (1-based, 페이지 안)
    - lineEnd: int — 종료 라인 (포함)
    - charOffset: int — 라인 안 시작 문자 오프셋 (선택)
    - sourcePath: str — repo 안 또는 cache 안 정규 경로 (예: artifacts/filings/{docId}/{page}.html)

    Trail-of-evidence / 신뢰도 (모든 ref 발급 시):
    - confidence: int (0-100) — 발급 시점 신뢰도. 표시 매핑은 low(<40)·mid(40-70)·high(>70) 1 곳에서만.
        정책 (core/confidence.py 의 tagConfidence 데코레이터):
        · filing 직접 인용 = 95
        · analysis 비율·deterministic = 80
        · DCF / forecast / 가정 기반 = 30
        · llm 자체 추정 = 40
        · verify_answer 실패 시 -50
    - provenance: list[str] — 이 ref 가 의존한 다른 refId 리스트 (transitive lineage 의 한 단계).
        ProvenanceTree UI 가 self-recursive traversal 로 풀어 시각화.

    표준 키 변경 시 (시작 후 되돌리지 않는다):
    - 192 analysis 발급부 + UI 파서 + DART viewer 가 일괄 박힌다. 이름 바꾸려면 모든 호출자 동시.
    """

    id: str
    kind: str
    title: str
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    sourceType: SourceType = "internal"

    def toDict(self) -> dict[str, Any]:
        """dataclass → dict 직렬화 (frozen=True 이므로 안전한 얕은 변환)."""
        return asdict(self)


@dataclass(frozen=True)
class TraceEvent:
    """Internal research event.

    Only Agent Gateway may translate this object into public UI events.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=_nowIso)

    def toDict(self) -> dict[str, Any]:
        """TraceEvent → kind/data/ts 3 키 dict 직렬화."""
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

    def toDict(self) -> dict[str, Any]:
        """dataclass → dict 직렬화 (frozen=True 이므로 안전한 얕은 변환)."""
        return asdict(self)
