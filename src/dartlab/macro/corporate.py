"""매크로 기업집계 분석 — scan finance.parquet 기반 독자 매크로 지표.

전종목 재무제표를 집계하여 매크로 사이클을 bottom-up으로 포착한다.
Bloomberg/FactSet 유료 서비스에서나 가능한 기능을 dartlab scan 데이터로 무료 제공.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

import os

import polars as pl

from dartlab.core.finance.corporateAggregate import (
    aggregateEarningsCycle,
    leverageCycle,
    ponziRatio,
)

_SCAN_CACHE: dict[str, pl.DataFrame] = {}


def _load_scan_finance(market: str) -> pl.DataFrame | None:
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


def analyze_corporate(*, market: str = "KR", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """기업집계 매크로 분석.

    전종목 재무제표(scan/finance.parquet)를 집계하여
    이익 사이클, Ponzi 비율, 레버리지 사이클을 bottom-up으로 산출한다.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR"). 기본 "KR".
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.
    overrides : dict | None
        AI 가정 교체.

    Returns
    -------
    dict
        market : str — 시장 코드
        earningsCycle : dict | None — 이익 사이클
            periods : list[str] — 분석 기간 리스트
            totalOperatingIncome : list[float] — 기간별 영업이익 합계 (원 또는 달러)
            yoyChanges : list[float | None] — 기간별 YoY 변화율 (%)
            currentDirection : str — 현재 방향 ("expanding" | "contracting" | "stable")
            currentLabel : str — 한글 레이블
            companyCount : int — 분석 대상 기업 수
            description : str — 해설
        ponziRatio : dict | None — Ponzi 비율 (이자비용 > 영업이익 기업 비중)
            periods : list[str] — 분석 기간 리스트
            ratios : list[float] — 기간별 Ponzi 비율 (0~1)
            currentRatio : float — 최신 Ponzi 비율 (0~1)
            trend : str — 추세 ("rising" | "falling" | "stable")
            trendLabel : str — 한글 레이블
            description : str — 해설
        leverageCycle : dict | None — 레버리지 사이클
            periods : list[str] — 분석 기간 리스트
            medianDebtRatio : list[float] — 기간별 중앙값 부채비율 (%)
            currentLevel : float — 최신 중앙값 부채비율 (%)
            trend : str — 추세 ("deleveraging" | "leveraging" | "stable")
            trendLabel : str — 한글 레이블
            description : str — 해설
        description : str | None — 데이터 부재 시 안내 메시지
    """
    result: dict = {"market": market.upper()}

    df = _load_scan_finance(market)
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
