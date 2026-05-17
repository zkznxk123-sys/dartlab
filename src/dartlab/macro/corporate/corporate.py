"""매크로 기업집계 분석 — scan finance.parquet 기반 독자 매크로 지표.

전종목 재무제표를 집계하여 매크로 사이클을 bottom-up으로 포착한다.
Bloomberg/FactSet 유료 서비스에서나 가능한 기능을 dartlab scan 데이터로 무료 제공.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

import os

import polars as pl

from dartlab.macro.corporate.corporateAggregate import (
    aggregateEarningsCycle,
    leverageCycle,
    ponziRatio,
)

_SCAN_CACHE: dict[str, pl.DataFrame] = {}


def _loadScanFinance(market: str) -> pl.DataFrame | None:
    """scan/finance.parquet 로드. 모듈 레벨 캐시로 반복 호출 최적화.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR").
        KR → ``data/dart/scan/finance.parquet``,
        US → ``data/edgar/scan/finance.parquet``.

    Returns
    -------
    pl.DataFrame | None
        전종목 재무제표 집계 DataFrame.
        주요 컬럼: stockCode, period, operatingIncome, totalDebt,
        totalEquity, interestExpense 등.
        파일이 없으면 None.
    """
    key = market.upper()
    if key in _SCAN_CACHE:
        return _SCAN_CACHE[key]

    if key == "KR":
        paths = [
            os.path.join("data", "dart", "scan", "finance.parquet"),
            os.path.join(os.path.expanduser("~"), ".dartlab", "data", "dart", "scan", "finance.parquet"),
        ]
    else:
        paths = [
            os.path.join("data", "edgar", "scan", "finance.parquet"),
            os.path.join(os.path.expanduser("~"), ".dartlab", "data", "edgar", "scan", "finance.parquet"),
        ]

    for p in paths:
        if os.path.exists(p):
            df = pl.read_parquet(p)
            _SCAN_CACHE[key] = df
            return df

    try:
        from dartlab.core.dataLoader import loadScanFinance

        df = loadScanFinance(market=market)
        if df is not None:
            _SCAN_CACHE[key] = df
        return df
    except (ImportError, KeyError, ValueError, TypeError, OSError):
        return None


def analyzeCorporate(*, market: str = "KR", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """기업집계 매크로 분석.

    Capabilities:
        scan/finance.parquet 전종목 재무제표 → bottom-up 집계 → 영업이익 사이클
        + Ponzi 비율 (이자 > 영업이익 기업 비중) + 레버리지 사이클 (중앙값
        부채비율). 매크로 top-down 보완.

    Args:
        market: 시장 코드 ``"US"`` | ``"KR"``. 기본 ``"KR"``.
        asOf: 기준일 (YYYY-MM-DD). None 이면 최신.
        overrides: AI 가정 교체. 현재 미사용 (forward-compat).

    Returns:
        dict — market/earningsCycle(periods/totalOperatingIncome/yoyChanges/
        currentDirection/companyCount)/ponziRatio(periods/ratios/currentRatio/
        trend)/leverageCycle(periods/medianDebtRatio/trend)/description.

    Example:
        >>> r = analyzeCorporate(market="KR")
        >>> r["earningsCycle"]["currentDirection"]
        'expanding'

    Guide:
        ponziRatio > 0.2 = 위험 (Ponzi finance 기업 비중 ↑). leverageCycle
        trend "leveraging" + earningsCycle "contracting" 동시 = 매크로 부채 사이클
        피크 신호.

    When:
        ``analyzeSummary`` corporate 보조축 + AI 한국 기업 매크로 답변.

    How:
        _loadScanFinance (parquet) → aggregateEarningsCycle + ponziRatio +
        leverageCycle 3 함수 호출 → dict 합성.

    Requires:
        scan/finance.parquet (dartlab collect --scan 또는 downloadAll('scan')).

    Raises:
        없음 — parquet 없으면 description 안내 메시지 반환.

    See Also:
        - aggregateEarningsCycle : 영업이익 집계
        - ponziRatio : Ponzi finance 비율
        - leverageCycle : 부채비율 사이클

    AIContext:
        earningsCycle.currentLabel + ponziRatio.currentRatio + leverageCycle.
        trendLabel 3 필드 인용으로 한 단락 답변.

    LLM Specifications:
        AntiPatterns:
            - 시장="US" 호출 (KR scan 한정. US 미준비)
            - parquet 없는데 결과 단정 (description 메시지 확인 필수)
            - currentDirection 만 인용 + ponzi/leverage 무시
        OutputSchema:
            ``{market, earningsCycle, ponziRatio, leverageCycle, description}``.
        Prerequisites: scan/finance.parquet (Q 별 분기 재무제표 약 2500 사 × N
            분기).
        Freshness: 분기 (실적 발표 직후).
        Dataflow: parquet → 3 집계 함수 → dict.
        TargetMarkets: KR (메인). US 미지원.
    """
    result: dict = {"market": market.upper()}

    df = _loadScanFinance(market)
    if df is None or len(df) == 0:
        result["earningsCycle"] = None
        result["ponziRatio"] = None
        result["leverageCycle"] = None
        result["description"] = "scan/finance.parquet 없음 — dartlab collect --scan 또는 downloadAll('scan') 필요"
        return result

    # 이익 사이클
    try:
        ec = aggregateEarningsCycle(df)
        result["earningsCycle"] = {
            "periods": ec.periods,
            "totalOperatingIncome": ec.totalOperatingIncome,
            "yoyChanges": ec.yoyChanges,
            "currentDirection": ec.currentDirection,
            "currentLabel": ec.currentLabel,
            "companyCount": ec.companyCount,
            "description": ec.description,
        }
    except (KeyError, ValueError, TypeError, OSError):
        result["earningsCycle"] = None

    # Ponzi 비율
    try:
        pr = ponziRatio(df)
        result["ponziRatio"] = {
            "periods": pr.periods,
            "ratios": pr.ratios,
            "currentRatio": pr.currentRatio,
            "trend": pr.trend,
            "trendLabel": pr.trendLabel,
            "description": pr.description,
        }
    except (KeyError, ValueError, TypeError, OSError):
        result["ponziRatio"] = None

    # 레버리지 사이클
    try:
        lc = leverageCycle(df)
        result["leverageCycle"] = {
            "periods": lc.periods,
            "medianDebtRatio": lc.medianDebtRatio,
            "currentLevel": lc.currentLevel,
            "trend": lc.trend,
            "trendLabel": lc.trendLabel,
            "description": lc.description,
        }
    except (KeyError, ValueError, TypeError, OSError):
        result["leverageCycle"] = None

    return result
