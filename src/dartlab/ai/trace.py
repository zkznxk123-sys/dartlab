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
        """이벤트 1 건 누적 — kind + data dict + 자동 timestamp."""
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
        """T11-4 — 5 패스 완료 시 finishedAt 기록. dumpToJson 전 호출."""
        if self.finishedAt is None:
            self.finishedAt = dt.datetime.now(dt.UTC).isoformat()

    def toDict(self) -> dict[str, Any]:
        """직렬화 가능 dict 변환 — JSON dump 또는 외부 evidence flow 입력."""
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
        """5 패스 trace 를 JSON line 형식으로 저장.

        Args:
            filePath: 저장 경로. None 이면 `_defaultTraceDir() / {sessionId}.json`.
        Returns:
            실제 저장된 Path.
        Example:
            >>> collector = AuditCollector(question="삼성전자 분석")
            >>> collector.observe("BRIEF", {"intent": "ratio_analysis"})
            >>> collector.markFinished()
            >>> path = collector.dumpToJson()
            >>> path.exists()
            True
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
        """저장된 trace JSON 을 AuditCollector 로 복원 — ref circularity 분석 입력."""
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
