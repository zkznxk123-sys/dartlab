"""분석 메모리 저장소 — KnowledgeDB 단일 DB 위임.

Company 객체(200~500MB)는 저장하지 않는다.
stockCode + 시점 + 질문 요약 + 결과 요약만 저장하여 메모리 안전.

내부적으로 KnowledgeDB(ai_knowledge.db)의 executions 테이블을 사용한다.
공개 API(saveAnalysis, recallForStock, toPromptContext)는 기존과 동일.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# 싱글턴 인스턴스
_instance: AnalysisMemory | None = None


@dataclass(frozen=True)
class MemoryRecord:
    """저장된 분석 기록."""

    stockCode: str
    question: str
    questionType: str
    resultSummary: str
    timestamp: float
    grade: str | None = None
    keyMetrics: str = ""


class AnalysisMemory:
    """KnowledgeDB 위임 분석 히스토리 저장소."""

    def __init__(self) -> None:
        self._db = None

    def _ensureDb(self):
        """lazy init — KnowledgeDB 싱글턴에 위임."""
        if self._db is not None:
            return self._db
        from dartlab.ai.persistence.knowledge_db import KnowledgeDB

        self._db = KnowledgeDB.get()
        return self._db

    def saveAnalysis(
        self,
        stockCode: str,
        question: str,
        questionType: str = "",
        resultSummary: str = "",
        grade: str | None = None,
        keyMetrics: str = "",
    ) -> None:
        """분석 결과 저장.

        keyMetrics: 핵심 수치 구조화 문자열 (예: "ROE=12.3%|영업이익률=8.9%|등급=dCR-AA+")
        """
        try:
            db = self._ensureDb()
            db.save_execution(
                stock_code=stockCode,
                question=question,
                question_type=questionType,
                result_summary=resultSummary,
                grade=grade or "",
                key_metrics=keyMetrics,
            )
        except (ImportError, OSError) as e:
            log.warning("분석 메모리 저장 실패: %s", e)

    def recallForStock(
        self,
        stockCode: str,
        limit: int = 5,
        decayDays: int = 90,
    ) -> list[MemoryRecord]:
        """종목별 최근 분석 기록 조회 (시간 감쇠 적용)."""
        try:
            db = self._ensureDb()
            rows = db.recall_for_stock(stockCode, limit=limit, decay_days=decayDays)
            return [
                MemoryRecord(
                    stockCode=r["stock_code"] or "",
                    question=r["question"],
                    questionType=r["question_type"] or "",
                    resultSummary=r["result_summary"] or "",
                    timestamp=r["timestamp"],
                    grade=r["grade"] or None,
                    keyMetrics=r["key_metrics"] or "",
                )
                for r in rows
            ]
        except (ImportError, OSError):
            return []

    def toPromptContext(self, stockCode: str) -> str:
        """이전 분석 기록을 프롬프트용 텍스트로 변환.

        keyMetrics가 있으면 핵심 수치를 포함하여 멀티턴 참조 가능.
        """
        records = self.recallForStock(stockCode)
        if not records:
            return ""
        lines = ["## 이전 분석 기록"]
        for r in records:
            import datetime

            dt = datetime.datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            grade_str = f" [등급: {r.grade}]" if r.grade else ""
            lines.append(f"- **{dt}** ({r.questionType}){grade_str}: {r.question}")
            if r.keyMetrics:
                lines.append(f"  {r.keyMetrics}")
            elif r.resultSummary:
                lines.append(f"  -> {r.resultSummary[:200]}")
        return "\n".join(lines)

    def close(self) -> None:
        """연결 종료."""
        self._db = None


def getMemory() -> AnalysisMemory:
    """싱글턴 메모리 인스턴스."""
    global _instance
    if _instance is None:
        _instance = AnalysisMemory()
    return _instance
