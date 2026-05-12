"""기존 기술적 분석 코드를 축 인터페이스로 래핑.

indicators, signals, verdict, beta, divergence를 새 축 체계에 연결.
기존 analyzer.py, extended.py의 함수를 그대로 호출한다.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv


class _OHLCVWrapper:
    """OHLCV를 이미 보유한 경량 래퍼 — extended.py의 _fetchOhlcv 캐시 호환."""

    def __init__(self, stockCode: str, ohlcv, market: str = "KR"):
        self.stockCode = stockCode
        self.currency = "KRW" if market == "KR" else "USD"
        self._cache = {"_quant_ohlcv": ohlcv}


def _getOhlcv(stockCode: str, **kwargs):
    """OHLCV fetch + 검증."""
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return None, {"error": f"{stockCode} 주가 데이터 없음"}
    return ohlcv, None


# ── 축 함수들 ────────────────────────────────────────────


def calcIndicators(stockCode: str, **kwargs: Any) -> Any:
    """45개 기술적 지표 DataFrame — OHLCV 기반 보조지표 일괄 산출.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    **kwargs
        fetchOhlcv 전달 인자 (start, market 등).

    Returns
    -------
    pl.DataFrame
        date : date — 거래일
        close : float — 종가 (원)
        sma20 : float — 20일 단순이동평균 (원)
        sma60 : float — 60일 단순이동평균 (원)
        rsi : float — RSI 14일 (%)
        macd : float — MACD 값
        adx : float — ADX (%)
        atr : float — ATR 14일 (원)
        bbUpper : float — 볼린저밴드 상단 (원)
        bbLower : float — 볼린저밴드 하단 (원)
        기타 보조지표 컬럼 포함 (총 45개).
    dict
        error 발생 시 {"error": str}.

    Examples
    --------
    >>> c.quant("indicators")"""
    ohlcv, err = _getOhlcv(stockCode, **kwargs)
    if err:
        return err
    from dartlab.quant.signal.analyzer import enrichWithIndicators

    return enrichWithIndicators(ohlcv)


def calcSignals(stockCode: str, **kwargs: Any) -> Any:
    """최근 20일 매매 신호 요약 — 골든크로스·RSI·MACD·볼린저.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    **kwargs
        fetchOhlcv 전달 인자 (start, market 등).

    Returns
    -------
    dict
        signals : dict
            goldenCross : int — 20일간 골든/데드크로스 누적 (양=매수, 음=매도)
            rsiSignal : int — RSI 신호 누적
            macdSignal : int — MACD 신호 누적
            bollingerSignal : int — 볼린저 신호 누적
        signalSummary : dict
            bullish : int — 매수 신호 건수 (건)
            bearish : int — 매도 신호 건수 (건)
        recentEvents : list[dict] — 최근 10개 이벤트
            date : str — 발생일
            type : str — 신호 유형
            direction : str — "매수" | "매도"
    dict
        error 발생 시 {"error": str}.

    Examples
    --------
    >>> c.quant("signals")"""
    ohlcv, err = _getOhlcv(stockCode, **kwargs)
    if err:
        return err
    from dartlab.quant.screen.extended import calcTechnicalSignals

    market = resolveMarket(stockCode, kwargs.pop("market", "auto"))
    wrapper = _OHLCVWrapper(stockCode, ohlcv, market)
    return calcTechnicalSignals(wrapper)


def calcVerdict(stockCode: str, **kwargs: Any) -> dict:
    """종합 기술적 판단 — 강세/중립/약세 + 주요 보조지표 스냅샷.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    **kwargs
        fetchOhlcv 전달 인자 (start, market 등).

    Returns
    -------
    dict
        verdict : str — "강세" | "중립" | "약세"
        score : int — 종합 점수 (점, −5 ~ +5)
        rsi : float — RSI 14일 (%)
        adx : float — ADX (%)
        aboveSma20 : bool — 종가가 20일선 위인지
        aboveSma60 : bool — 종가가 60일선 위인지
        bbPosition : float — 볼린저밴드 내 위치 (%, 0=하단, 100=상단)
        signals : dict — 개별 신호 점수
    dict
        error 발생 시 {"error": str}.

    Examples
    --------
    >>> c.quant("verdict")"""
    benchmark = kwargs.pop("benchmark", None)
    benchmarkMode = kwargs.pop("benchmarkMode", "market")
    ohlcv, err = _getOhlcv(stockCode, **kwargs)
    if err:
        return err
    from dartlab.quant.signal.analyzer import technicalVerdict

    market = resolveMarket(stockCode, kwargs.pop("market", "auto"))
    return technicalVerdict(
        ohlcv,
        stockCode=stockCode,
        market=market,
        benchmark=benchmark,
        benchmarkMode=benchmarkMode,
    )


def calcBeta(stockCode: str, **kwargs: Any) -> dict:
    """시장 베타 + CAPM 기대수익률 + 상대강도.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    **kwargs
        fetchOhlcv 전달 인자 (start, market 등).

    Returns
    -------
    dict
        value : float — 베타 계수 (배)
        r2 : float — 결정계수 (%, 0~100)
        capmExpected : float — CAPM 기대수익률 (%)
        relativeStrength : float — 벤치마크 대비 상대강도 (배)
        interpretation : str — 베타 해석 문장
    dict
        error 발생 시 {"error": str}.

    Examples
    --------
    >>> c.quant("beta")"""
    benchmark = kwargs.pop("benchmark", None)
    benchmarkMode = kwargs.pop("benchmarkMode", "market")
    ohlcv, err = _getOhlcv(stockCode, **kwargs)
    if err:
        return err
    from dartlab.quant.screen.extended import calcMarketBeta

    market = resolveMarket(stockCode, kwargs.pop("market", "auto"))
    wrapper = _OHLCVWrapper(stockCode, ohlcv, market)
    if benchmark:
        wrapper.benchmark = benchmark
    wrapper.benchmarkMode = benchmarkMode
    return calcMarketBeta(wrapper)


def calcDivergence(stockCode: str, **kwargs: Any) -> dict:
    """재무-기술적 괴리 진단 — 재무 등급 vs 기술적 판단 교차검증.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    **kwargs
        fetchOhlcv 전달 인자 (start, market 등).

    Returns
    -------
    dict
        financialGrade : str | None — 재무 스코어카드 등급 ("A+" ~ "D")
        technicalVerdict : str | None — "강세" | "중립" | "약세"
        technicalScore : int — 기술적 종합 점수 (점)
        divergence : str — 괴리 유형 ("순풍" | "괴리" | "위험" 등)
        diagnosis : str — 진단 메시지
        matrix : str — 2×3 매트릭스 키 ("good_bullish" 등)
    dict
        error 발생 시 {"error": str}.

    Examples
    --------
    >>> c.quant("divergence")"""
    ohlcv, err = _getOhlcv(stockCode, **kwargs)
    if err:
        return err
    from dartlab.quant.screen.extended import calcFundamentalDivergence

    market = resolveMarket(stockCode, kwargs.pop("market", "auto"))
    wrapper = _OHLCVWrapper(stockCode, ohlcv, market)
    return calcFundamentalDivergence(wrapper)
