"""데이터 커버리지/신뢰도 점수."""

from __future__ import annotations


def calcCoverageScore(
    *,
    hasFinance: bool = False,
    hasDocs: bool = False,
    hasInsight: bool = False,
    hasMarket: bool = False,
    hasValuation: bool = False,
    hasForecast: bool = False,
    hasEsg: bool = False,
    hasSectorKpis: bool = False,
    hasRisk: bool = False,
    hasPeer: bool = False,
    hasNarrative: bool = False,
) -> float:
    """0~1 커버리지 점수.

    Parameters
    ----------
    hasFinance : bool
        재무제표 존재 여부.
    hasDocs : bool
        공시문서 존재 여부.
    hasInsight : bool
        인사이트 분석 존재 여부.
    hasMarket : bool
        시장 데이터 존재 여부.
    hasValuation : bool
        밸류에이션 존재 여부.
    hasForecast : bool
        예측 데이터 존재 여부.
    hasEsg : bool
        ESG 데이터 존재 여부.
    hasSectorKpis : bool
        섹터 KPI 존재 여부.
    hasRisk : bool
        리스크 분석 존재 여부.
    hasPeer : bool
        피어 분석 존재 여부.
    hasNarrative : bool
        서술 분석 존재 여부.

    Returns
    -------
    float
        커버리지 점수 (0.0~1.0).
    """
    weights = {
        "finance": (hasFinance, 0.18),
        "insight": (hasInsight, 0.15),
        "valuation": (hasValuation, 0.13),
        "market": (hasMarket, 0.10),
        "forecast": (hasForecast, 0.08),
        "risk": (hasRisk, 0.08),
        "peer": (hasPeer, 0.06),
        "docs": (hasDocs, 0.06),
        "esg": (hasEsg, 0.05),
        "sectorKpis": (hasSectorKpis, 0.05),
        "narrative": (hasNarrative, 0.06),
    }
    score = sum(w for available, w in weights.values() if available)
    return round(min(score, 1.0), 2)
