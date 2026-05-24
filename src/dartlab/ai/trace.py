"""Audit and progress capture hooks for AI streams.

T11-4 — 5 패스 trace 완전 dump + JSON 저장. ref circularity 가드 (T11-3) 가 본
collector dump 를 입력으로 DFS 순환 검사.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def installProgressCapture() -> None:
    """Install progress capture hooks.

    The new engine exposes progress through Agent Gateway events, so the server
    bootstrap hook is intentionally idempotent and side-effect free.
    """

    return None


def _defaultTraceDir() -> Path:
    """trace dump 기본 디렉터리 — `data/_trace/` (gitignored, 로컬 디버그 전용).

    환경변수 `DARTLAB_TRACE_DIR` 로 override 가능. 외부 사고 시 PII 노출
    회피 위해 사용자 명시 경로만 사용 권장.
    """
    custom = os.getenv("DARTLAB_TRACE_DIR")
    if custom:
        return Path(custom)
    return Path.cwd() / "data" / "_trace"


@dataclass
class AuditCollector:
    """In-memory audit collector used by server streaming adapters.

    T11-4 보강: sessionId / startedAt / finishedAt 메타 + dumpToJson / loadFromJson
    저장 round-trip. 5 패스 events (BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST) 가
    observe() 로 시간 순서 누적.
    """

    question: str = ""
    stockCode_hint: str | None = None
    provider: str | None = None
    model: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    # T11-4 메타
    sessionId: str = field(default_factory=lambda: str(uuid.uuid4()))
    startedAt: str = field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())
    finishedAt: str | None = None

    def observe(self, kind: str, data: dict[str, Any] | None = None) -> None:
        """이벤트 1 건 누적 — kind + data dict + 자동 timestamp (T10-4).

        Capabilities:
            5 패스 (BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST) 이벤트 누적. 호출
            마다 UTC ISO timestamp 자동 부착.

        Args:
            kind: 이벤트 분류 (대문자 5 패스 권장).
            data: 이벤트 페이로드 dict (refUsed / refProduced / message 등).

        AIContext:
            T11-4 워크벤치 trace 핵심 메서드. metrics workflow grep 가능.
        """
        self.events.append(
            {
                "kind": kind,
                "data": dict(data or {}),
                "at": dt.datetime.now(dt.UTC).isoformat(),
            }
        )

    def flush(self) -> None:
        """no-op — 서버 어댑터 호환용 hook (실제 flush 없음)."""
        return None

    def markFinished(self) -> None:
        """5 패스 완료 시 finishedAt 기록 (T11-4 / T10-4).

        Capabilities:
            dumpToJson 전 호출 강제. idempotent — 이미 기록됐으면 no-op.

        AIContext:
            세션 종료 시점 추적. metrics workflow 가 duration 계산.
        """
        if self.finishedAt is None:
            self.finishedAt = dt.datetime.now(dt.UTC).isoformat()

    def toDict(self) -> dict[str, Any]:
        """직렬화 가능 dict 변환 (T10-4).

        Returns:
            sessionId / question / stockCodeHint / provider / model / startedAt
            / finishedAt / events 8 필드 dict.

        SeeAlso:
            dumpToJson: 파일 저장.
        """
        return {
            "sessionId": self.sessionId,
            "question": self.question,
            "stockCodeHint": self.stockCode_hint,
            "provider": self.provider,
            "model": self.model,
            "startedAt": self.startedAt,
            "finishedAt": self.finishedAt,
            "events": list(self.events),
        }

    def dumpToJson(self, filePath: str | Path | None = None) -> Path:
        """5 패스 trace 를 JSON 형식으로 저장 (T10-4).

        Capabilities:
            AuditCollector 의 이벤트 + 메타를 JSON 파일로 직렬화. refCircularity
            check (T11-3) 의 입력.

        Args:
            filePath: 저장 경로. None 이면 `_defaultTraceDir() / {sessionId}.json`.

        Returns:
            실제 저장된 Path.

        Example:
            >>> collector = AuditCollector(question="삼성전자 분석")
            >>> collector.observe("BRIEF", {"intent": "ratio_analysis"})
            >>> collector.markFinished()
            >>> path = collector.dumpToJson()

        Guide:
            DARTLAB_TRACE_DIR env 로 default dir override 가능. PII 우려 시
            사용자 명시 경로만 사용.

        SeeAlso:
            loadFromJson: round-trip 복원.
            markFinished: 완료 시점 기록.
            refCircularityCheck (T11-3): 순환 감지.

        Requires:
            쓰기 권한.

        AIContext:
            T11-4 워크벤치 trace. ref circularity audit (T11-3) 의 입력.

        Raises:
            OSError: 디스크 쓰기 실패.
        """
        if filePath is None:
            outputPath = _defaultTraceDir() / f"{self.sessionId}.json"
        else:
            outputPath = Path(filePath)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        self.markFinished()
        outputPath.write_text(json.dumps(self.toDict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return outputPath

    @classmethod
    def loadFromJson(cls, filePath: str | Path) -> AuditCollector:
        """저장된 trace JSON 을 AuditCollector 로 복원 (T10-4).

        Capabilities:
            dumpToJson 산출물 round-trip 복원. ref circularity audit (T11-3) 의
            대표 입력 — 저장된 trace 후처리 가능.

        Args:
            filePath: 복원 대상 JSON 경로.

        Returns:
            새 AuditCollector 인스턴스 (events + 메타 복원).

        Example:
            >>> collector = AuditCollector.loadFromJson("data/_trace/abc.json")
            >>> len(collector.events)
            12

        SeeAlso:
            dumpToJson / refCircularityCheck (T11-3).

        Requires:
            파일 존재 + JSON 형식 정상.

        AIContext:
            T11-4 trace round-trip. 외부 audit tool 이 trace 분석.

        Raises:
            FileNotFoundError / json.JSONDecodeError.
        """
        data = json.loads(Path(filePath).read_text(encoding="utf-8"))
        collector = cls(
            question=data.get("question", ""),
            stockCode_hint=data.get("stockCodeHint"),
            provider=data.get("provider"),
            model=data.get("model"),
            events=list(data.get("events", [])),
        )
        collector.sessionId = data.get("sessionId", collector.sessionId)
        collector.startedAt = data.get("startedAt", collector.startedAt)
        collector.finishedAt = data.get("finishedAt")
        return collector
