"""Built-in AI tools — KnowledgeDB 직접 접근.

경험 자산화 순환의 "읽기" 경로. 블로그 + AI 과거 분석을 tool 로 노출.
AI 가 자율 판단 ("이 회사 전에 본 적 있나?") 으로 호출 — 떠먹이기 아님.
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
    AI 가 "이 회사 전에 분석한 적 있나?" 자율 판단 후 호출.

    Returns:
        {narrative, strengths, weaknesses, keyMetrics, dataAsOf, source} 또는 None
    """
    try:
        from dartlab.ai.persistence import KnowledgeDB
    except ImportError:
        return None

    try:
        db = KnowledgeDB.get()
    except (OSError, RuntimeError):
        return None

    # 블로그 (source="blog") 우선 시도
    rec = db.get_insight(stockCode, source="blog")
    if rec is None:
        rec = db.get_insight(stockCode)
    return _recordToDict(rec)


def sectorInsights(sector: str, limit: int = 3) -> list[dict[str, Any]]:
    """동종 업계 과거 분석 서사 조회 (교차 학습).

    AI 가 "이 업종에서 전에 어떤 패턴 발견했나?" 자율 판단 후 호출.
    매크로/섹터 질문에 특히 유용.

    Returns:
        list of {narrative, strengths, weaknesses, keyMetrics, stockCode, corpName}
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


# ── AITool 정의 ──────────────────────────────────────────


def _builtinTools() -> list:
    """buildTools() 가 append 할 built-in tool 리스트."""
    from dartlab.ai.tools import AITool

    return [
        AITool(
            name="pastInsight",
            description=(
                "특정 회사 과거 분석 서사 조회 (블로그 우선 → AI 축적). "
                "AI 가 분석 전 이 회사에 대해 이미 아는 게 있는지 확인하는 경험 조회."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "stockCode": {"type": "string", "description": "종목코드 (예: '005930', 'AAPL')"},
                },
                "required": ["stockCode"],
                "additionalProperties": False,
            },
            handler=pastInsight,
        ),
        AITool(
            name="sectorInsights",
            description=("동종 업계 과거 분석 서사 목록 (교차 학습). 업종 단위 패턴 파악 — 매크로/섹터 질문에 유용."),
            parameters={
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "업종명 (예: '반도체', '식품')"},
                    "limit": {"type": "integer", "description": "상위 N개 (기본 3)", "minimum": 1, "maximum": 20},
                },
                "required": ["sector"],
                "additionalProperties": False,
            },
            handler=sectorInsights,
        ),
    ]
