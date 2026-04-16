"""KnowledgeDB 경험 자산 조회 — 모듈 레벨 함수.

역할 (Phase 16 C3): **READ 전용** — 종목/섹터별 과거 판단 조회.
저장/갱신 경로는 `ai/context/playbook.py` (WRITE: delta merge).

dartlab.pastInsight(stockCode) / dartlab.sectorInsights(sector) 로 노출.
AI tool 자동 등록 경로 (`_autoDiscover`) 가 dartlab.__all__ 순회 시 자동 포함.

사상 (src/dartlab/ai/README.md §7 경험 자산화 순환):
- 사람 (블로그) + AI (응답) 가 쌓은 서사·bullet 이 KnowledgeDB 에 보존
- 떠먹이기 아님 — AI 가 자율 판단 ("이 회사 전에 본 적 있나?") 으로 호출
- 블로그 (검증 프리미엄) 우선, 없으면 AI 축적 fallback
"""

from __future__ import annotations

from typing import Any


def _recordToDict(rec: Any) -> dict[str, Any] | None:
    """InsightRecord → dict 변환. dataclass 또는 namedtuple 모두 지원."""
    if rec is None:
        return None
    if hasattr(rec, "_asdict"):
        return rec._asdict()
    if hasattr(rec, "__dict__"):
        return {k: v for k, v in rec.__dict__.items() if not k.startswith("_")}
    if isinstance(rec, dict):
        return rec
    return {"value": str(rec)}


def pastInsight(stockCode: str) -> dict[str, Any] | None:
    """특정 회사의 과거 분석 서사 조회.

    우선순위: 블로그 (사람 검증 프리미엄) → AI 축적.
    AI 가 분석 전 "이 회사 전에 본 적 있나?" 자율 판단 후 호출.

    Args:
        stockCode: 종목코드 (예: '005930', 'AAPL')

    Returns:
        dict — narrative / strengths / weaknesses / keyMetrics / dataAsOf / source.
        None — 과거 분석 없음.
    """
    try:
        from dartlab.ai.persistence import KnowledgeDB
    except ImportError:
        return None

    try:
        db = KnowledgeDB.get()
    except (OSError, RuntimeError):
        return None

    rec = db.get_insight(stockCode, source="blog")
    if rec is None:
        rec = db.get_insight(stockCode)
    return _recordToDict(rec)


def sectorInsights(sector: str, limit: int = 3) -> list[dict[str, Any]]:
    """동종 업계 과거 분석 서사 목록 (교차 학습).

    AI 가 "이 업종에서 전에 어떤 패턴 발견했나?" 자율 판단 후 호출.
    매크로/섹터 질문에 특히 유용.

    Args:
        sector: 업종명 (예: '반도체', '식품')
        limit: 상위 N개 (기본 3)

    Returns:
        list — 각 항목: narrative / strengths / weaknesses / keyMetrics / stockCode / corpName.
    """
    try:
        from dartlab.ai.persistence import KnowledgeDB
    except ImportError:
        return []

    try:
        db = KnowledgeDB.get()
    except (OSError, RuntimeError):
        return []

    records = db.get_sector_insights(sector, limit=limit)
    return [d for d in (_recordToDict(r) for r in records) if d is not None]
