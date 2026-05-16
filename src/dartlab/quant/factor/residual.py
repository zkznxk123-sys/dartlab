"""잔여수익 분석 — 팩터 제거 후 잔여 모멘텀.

학술 근거: Blitz, Huij, Martens (2011) — Residual Momentum.
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def calcResidual(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """잔여 모멘텀/알파 — FF5 팩터 설명 제거 후 고유 신호.

    Capabilities:
        Fama-French 5 팩터 (MKT/SMB/HML/RMW/CMA) 회귀로 종목 일별 수익을 분해한 뒤, 잔차
        시계열로 6 개월·1 개월 잔여 모멘텀, 고유 변동성, 잔여 알파/Sharpe, 팩터 R² 를 산출.
        시장/스타일이 설명하지 못하는 종목 고유 신호를 한 dict 로 노출.

    Parameters
    ----------
    stockCode : str
        종목코드 (KR 6 자리 또는 US ticker).
    market : str, default "auto"
        "KR" | "US" | "auto" (자동 감지).
    **kwargs
        benchmark : str | None — 벤치마크 명시 override
        benchmarkMode : str — "market" (default) | "sector" | "style" | "auto"
        start/end : str — 기간 윈도우

    Returns
    -------
    dict
        stockCode : str — 입력 echo
        market : str — 해석된 시장
        residualMomentum6m : float — 6 개월 잔여 모멘텀 (%, 연환산)
        residualMomentum1m : float — 1 개월 잔여 모멘텀 (%, 연환산)
        idiosyncraticVol : float — 고유 변동성 (%, 연환산)
        residualAlpha : float — 잔여 알파 (%, 연환산)
        residualSharpe : float — alpha / vol (배)
        factorRSquared : float — 팩터 모델 R² (0~1)
        residualVerdict : str — "positive_alpha" | "negative_alpha" | "neutral"
        데이터 부족 시 {**result, "error": str} 반환.

    Raises
    ------
    없음 (오류는 dict["error"] 로 반환).

    Example
    -------
    >>> r = calcResidual("005930", market="KR")
    >>> r["residualVerdict"], r["residualAlpha"]
    ('positive_alpha', 8.4)

    Guide
    -----
    R² 가 높으면 (>0.7) 종목 수익의 대부분이 팩터로 설명 — alpha 신호 약함. R² 가 낮으면
    (<0.3) 고유성 강하지만 OLS 노이즈도 클 수 있음. residualSharpe 만 단독 인용 금지.

    SeeAlso
    -------
    - ``dartlab.quant.factor.value.calcValue`` : 가치 팩터 신호
    - ``dartlab.quant.factor.quality.calcQuality`` : 퀄리티 팩터 신호
    - ``dartlab.quant.factor.calc.decomposeFactor`` : FF5 분해 본체

    Requires
    --------
    - L1 gather: 주가 OHLCV (60 거래일 이상)
    - 벤치마크 OHLCV (benchmarkMode 에 맞춰 자동 선택)

    AIContext
    ---------
    팩터 설명 후에도 남는 "고유 신호" 의 진입점. positive_alpha 면 다른 알파 축 (모멘텀/감성)
    교차 확인 권장. R² 매우 낮으면 답변에 "표본 노이즈 가능" 명시.
    """
    market = resolveMarket(stockCode, market)
    benchmark = kwargs.pop("benchmark", None)
    benchmarkMode = kwargs.pop("benchmarkMode", "market")
    result: dict = {"stockCode": stockCode, "market": market}

    from dartlab.quant.factor.calc import decomposeFactor

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

    from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

    bench, benchmark_meta = fetchBenchmarkOhlcv(
        stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
        start=kwargs.get("start"),
        end=kwargs.get("end"),
        returnMeta=True,
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
