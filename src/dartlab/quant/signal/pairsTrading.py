"""공적분 기반 페어 트레이딩 — Engle-Granger 2단계 검정.

학술 근거: Engle & Granger (1987), Gatev et al. (2006).
"""

from __future__ import annotations

import logging

import numpy as np

from dartlab.quant.screen.dataAccess import fetchOhlcv, loadScanParquet, ohlcvToArrays
from dartlab.synth.scanBridge import extractAnnualConsolidated, getAccountValue, isEdgarSchema

log = logging.getLogger(__name__)

# ADF 임계값 (Dickey-Fuller, n→∞)
_ADF_CRITICAL = {"1%": -3.43, "5%": -2.86, "10%": -2.57}


def calcPairs(*, market: str = "KR", stockCode: str | None = None, **kwargs) -> dict:
    """공적분 기반 페어 탐색.

    자산 상위 종목 간 Engle-Granger ADF 검정으로 공적분 페어를 탐색한다.

    Parameters
    ----------
    market : str
        시장. 기본 "KR".
    stockCode : str | None
        특정 종목 포함 시 해당 종목을 페어 후보에 강제 포함.

    Returns
    -------
    dict
        market : str — 시장
        pairs : list[dict] — ADF 통계량 기준 정렬된 페어 (최대 10개)
            stockA : str, stockB : str,
            adfStat : float — ADF 검정 통계량,
            cointegrated : str — "1%" | "5%" | "10%" | "no",
            halfLife : float | None — 평균 회귀 반감기 (일),
            spreadZ : float — 현재 스프레드 z-score (배),
            dataPoints : int — 공통 관측치 수
        totalPairsTested : int — 검정한 총 페어 수
        cointegratedPairs : int — 공적분 성립 페어 수
        stocksUsed : list[str] — 분석에 사용된 종목 코드
    """
    result: dict = {"market": market}

    # 자산 상위 5종목 선정 (finance.parquet)
    top_codes = _getTopStocks(market, n=5)
    if not top_codes:
        return {**result, "error": "종목 리스트 확보 실패"}

    if stockCode and stockCode not in top_codes:
        top_codes = [stockCode] + top_codes[:4]

    # OHLCV 수집 (순차, 메모리 안전)
    prices: dict[str, np.ndarray] = {}
    for code in top_codes:
        ohlcv = fetchOhlcv(code)
        if ohlcv is not None and not ohlcv.is_empty():
            arr = ohlcvToArrays(ohlcv)
            if "close" in arr and len(arr["close"]) >= 60:
                prices[code] = np.log(arr["close"])

    codes = list(prices.keys())
    if len(codes) < 2:
        return {**result, "error": f"가격 데이터 부족 ({len(codes)}종목)"}

    # 모든 페어 ADF 검정
    pairs = []
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            pa, pb = prices[a], prices[b]
            ml = min(len(pa), len(pb))
            if ml < 60:
                continue
            spread = pa[-ml:] - pb[-ml:]

            adf_stat, beta, half_life = _adfTest(spread)
            if adf_stat is None:
                continue

            # 현재 스프레드 z-score
            z = (spread[-1] - np.mean(spread)) / max(np.std(spread), 1e-10)

            coint = "no"
            for level, cv in _ADF_CRITICAL.items():
                if adf_stat < cv:
                    coint = level
                    break

            pairs.append(
                {
                    "stockA": a,
                    "stockB": b,
                    "adfStat": round(float(adf_stat), 4),
                    "cointegrated": coint,
                    "halfLife": round(float(half_life), 1) if half_life and half_life > 0 else None,
                    "spreadZ": round(float(z), 4),
                    "dataPoints": ml,
                }
            )

    pairs.sort(key=lambda x: x["adfStat"])
    result["pairs"] = pairs[:10]
    result["totalPairsTested"] = len(pairs)
    result["cointegratedPairs"] = sum(1 for p in pairs if p["cointegrated"] != "no")
    result["stocksUsed"] = codes
    return result


def _adfTest(spread: np.ndarray) -> tuple[float | None, float, float]:
    """ADF 검정 (numpy OLS).

    ΔX_t = α + β·X_{t-1} + ε
    t_stat = β / SE(β)
    half_life = -ln(2) / ln(1 + β)
    """
    n = len(spread)
    if n < 30:
        return None, 0, 0

    dx = np.diff(spread)
    x_lag = spread[:-1]

    # OLS: dx = α + β·x_lag
    X = np.column_stack([np.ones(n - 1), x_lag])
    try:
        beta = np.linalg.lstsq(X, dx, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None, 0, 0

    b = float(beta[1])
    resid = dx - X @ beta
    mse = float(np.sum(resid**2) / (n - 3))
    x_var = float(np.sum((x_lag - np.mean(x_lag)) ** 2))
    if x_var == 0:
        return None, 0, 0

    se = np.sqrt(mse / x_var)
    t_stat = b / se if se > 0 else 0

    hl = -np.log(2) / np.log(1 + b) if b < 0 and b > -1 else 0

    return float(t_stat), b, float(hl)


def _getTopStocks(market: str, n: int = 5) -> list[str]:
    """finance.parquet에서 자산 상위 N종목 — scanBridge 경유."""
    import polars as pl

    lf = loadScanParquet("finance", market)
    if lf is None:
        return []

    try:
        full = lf.collect(engine="streaming")
    except (KeyError, ValueError, TypeError, AttributeError):
        return []

    annual = extractAnnualConsolidated(full)
    if annual.is_empty():
        return []

    edgar = isEdgarSchema(annual)
    yearCol = "fy" if edgar else "bsns_year"
    yr = annual.get_column(yearCol).sort(descending=True).to_list()[0]
    latest = annual.filter(pl.col(yearCol) == yr)

    assets_map = getAccountValue(latest, "자산총계")
    if not assets_map:
        return []

    stocks = sorted(assets_map.items(), key=lambda x: -x[1])
    return [s[0] for s in stocks[:n]]
