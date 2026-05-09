"""잔여수익 분석 — 팩터 제거 후 잔여 모멘텀.

학술 근거: Blitz, Huij, Martens (2011) — Residual Momentum.
"""

from __future__ import annotations

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant._helpers import fetchOhlcv, ohlcvToArrays, resolve_market


def calcResidual(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """팩터 제거 후 잔여 모멘텀/알파.

    FF5 회귀에서 팩터 설명을 제거한 잔여 수익으로 모멘텀·알파·Sharpe 를 산출한다.

    Parameters
    ----------
    stockCode : str
        종목코드.
    market : str
        "KR" | "US" | "auto". 기본 "auto".

    Returns
    -------
    dict
        stockCode : str — 종목코드
        market : str — 시장
        residualMomentum6m : float — 6개월 잔여 모멘텀 (%, 연환산)
        residualMomentum1m : float — 1개월 잔여 모멘텀 (%, 연환산)
        idiosyncraticVol : float — 고유 변동성 (%, 연환산)
        residualAlpha : float — 잔여 알파 (%, 연환산)
        residualSharpe : float — 잔여 Sharpe = alpha / vol (배)
        factorRSquared : float — 팩터 모델 R² (비율)
        residualVerdict : str — "positive_alpha" | "negative_alpha" | "neutral"
    """
    market = resolve_market(stockCode, market)
    benchmark = kwargs.pop("benchmark", None)
    benchmarkMode = kwargs.pop("benchmarkMode", "market")
    result: dict = {"stockCode": stockCode, "market": market}

    from dartlab.quant.factor import decomposeFactor

    fr = decomposeFactor(stockCode, market=market, benchmark=benchmark, benchmarkMode=benchmarkMode)
    if "error" in fr:
        return {**result, "error": fr["error"]}

    ohlcv = fetchOhlcv(stockCode)
    if isEmptyDf(ohlcv):
        return {**result, "error": "주가 데이터 없음"}

    close = ohlcvToArrays(ohlcv).get("close")
    if close is None or len(close) < 60:
        return {**result, "error": "데이터 부족"}

    sr = np.diff(np.log(close))

    from dartlab.quant.benchmark import fetch_benchmark_ohlcv

    bench, benchmark_meta = fetch_benchmark_ohlcv(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        start=kwargs.get("start"),
        end=kwargs.get("end"),
        return_meta=True,
    )
    if bench is None:
        return {**result, "error": "벤치마크 없음"}
    bc = ohlcvToArrays(bench).get("close")
    br = np.diff(np.log(bc))

    ml = min(len(sr), len(br))
    sr, br = sr[-ml:], br[-ml:]

    beta = fr.get("MKT", {}).get("loading", 1.0)
    alpha_d = fr.get("alpha", 0) / 252
    predicted = alpha_d + beta * br
    residuals = sr - predicted

    n = len(residuals)
    rm6 = float(np.mean(residuals[-min(126, n) :]) * 252)
    rm1 = float(np.mean(residuals[-min(22, n) :]) * 252)
    iv = float(np.std(residuals) * np.sqrt(252))
    ra = float(np.mean(residuals) * 252)
    rs = ra / iv if iv > 0 else 0

    result["residualMomentum6m"] = round(rm6, 4)
    result["residualMomentum1m"] = round(rm1, 4)
    result["idiosyncraticVol"] = round(iv, 4)
    result["residualAlpha"] = round(ra, 4)
    result["residualSharpe"] = round(float(rs), 4)
    result["factorRSquared"] = fr.get("rSquared", 0)
    result["benchmarkUsed"] = benchmark_meta
    result["residualVerdict"] = "positive_alpha" if ra > 0.05 else "negative_alpha" if ra < -0.05 else "neutral"
    return result
