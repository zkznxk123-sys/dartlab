"""벡터화 신호 발생기 — 순수 NumPy 구현.

tradix에서 이식. int8 배열 반환: 1=매수, -1=매도, 0=신호없음.

신호 9개:
    vcrossover, vcrossunder, vcross,
    vgoldenCross, vrsiSignal, vmacdSignal,
    vbollingerSignal, vbreakoutSignal, vTrendFilter
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from dartlab.synth.indicators import vbollinger, vmacd, vsma


def vcrossover(fast: NDArray[np.float64], slow: NDArray[np.float64]) -> NDArray[np.int8]:
    """상향 돌파 감지. 1=크로스오버, 0=없음.

    Parameters
    ----------
    fast : NDArray[np.float64]
        빠른 지표 배열.
    slow : NDArray[np.float64]
        느린 지표 배열.

    Returns
    -------
    NDArray[np.int8]
        1=상향 돌파 시점, 0=없음.
    """
    n = len(fast)
    signals = np.zeros(n, dtype=np.int8)
    prevFast = np.roll(fast, 1)
    prevSlow = np.roll(slow, 1)
    cross = (prevFast <= prevSlow) & (fast > slow)
    cross[0] = False
    cross = cross & ~np.isnan(fast) & ~np.isnan(slow) & ~np.isnan(prevFast) & ~np.isnan(prevSlow)
    signals[cross] = 1
    return signals


def vcrossunder(fast: NDArray[np.float64], slow: NDArray[np.float64]) -> NDArray[np.int8]:
    """하향 돌파 감지. -1=크로스언더, 0=없음.

    Parameters
    ----------
    fast : NDArray[np.float64]
        빠른 지표 배열.
    slow : NDArray[np.float64]
        느린 지표 배열.

    Returns
    -------
    NDArray[np.int8]
        -1=하향 돌파 시점, 0=없음.
    """
    n = len(fast)
    signals = np.zeros(n, dtype=np.int8)
    prevFast = np.roll(fast, 1)
    prevSlow = np.roll(slow, 1)
    cross = (prevFast >= prevSlow) & (fast < slow)
    cross[0] = False
    cross = cross & ~np.isnan(fast) & ~np.isnan(slow) & ~np.isnan(prevFast) & ~np.isnan(prevSlow)
    signals[cross] = -1
    return signals


def vcross(fast: NDArray[np.float64], slow: NDArray[np.float64]) -> NDArray[np.int8]:
    """양방향 돌파. +1=상향, -1=하향, 0=없음.

    Parameters
    ----------
    fast : NDArray[np.float64]
        빠른 지표 배열.
    slow : NDArray[np.float64]
        느린 지표 배열.

    Returns
    -------
    NDArray[np.int8]
        +1=상향 돌파, -1=하향 돌파, 0=없음.
    """
    n = len(fast)
    signals = np.zeros(n, dtype=np.int8)
    prevFast = np.roll(fast, 1)
    prevSlow = np.roll(slow, 1)
    valid = ~np.isnan(fast) & ~np.isnan(slow) & ~np.isnan(prevFast) & ~np.isnan(prevSlow)
    valid[0] = False
    signals[(valid) & (prevFast <= prevSlow) & (fast > slow)] = 1
    signals[(valid) & (prevFast >= prevSlow) & (fast < slow)] = -1
    return signals


def vgoldenCross(close: NDArray[np.float64], fast: int = 10, slow: int = 30) -> NDArray[np.int8]:
    """골든크로스(+1) / 데스크로스(-1).

    Parameters
    ----------
    close : NDArray[np.float64]
        종가 배열.
    fast : int
        단기 SMA 기간 (기본 10).
    slow : int
        장기 SMA 기간 (기본 30).

    Returns
    -------
    NDArray[np.int8]
        +1=골든크로스, -1=데드크로스, 0=없음.

    Example:
        >>> vgoldenCross(close, 10, 30)
        array([0, 0, 1, 0, ..., -1, 0])

    Requires:
        close 가 numpy array + slow + fast ≥ 2.

    Raises:
        없음.
    """
    return vcross(vsma(close, fast), vsma(close, slow))


def vrsiSignal(rsi: NDArray[np.float64], oversold: float = 30.0, overbought: float = 70.0) -> NDArray[np.int8]:
    """RSI 과매도 회복(+1) / 과매수 반전(-1).

    Parameters
    ----------
    rsi : NDArray[np.float64]
        RSI 값 배열 (0~100).
    oversold : float
        과매도 임계값 (기본 30.0).
    overbought : float
        과매수 임계값 (기본 70.0).

    Returns
    -------
    NDArray[np.int8]
        +1=과매도 탈출 매수, -1=과매수 이탈 매도, 0=없음.
    """
    n = len(rsi)
    signals = np.zeros(n, dtype=np.int8)
    prevRsi = np.roll(rsi, 1)
    valid = ~np.isnan(rsi) & ~np.isnan(prevRsi)
    valid[0] = False
    signals[(valid) & (prevRsi <= oversold) & (rsi > oversold)] = 1
    signals[(valid) & (prevRsi >= overbought) & (rsi < overbought)] = -1
    return signals


def vmacdSignal(close: NDArray[np.float64], fast: int = 12, slow: int = 26, signal: int = 9) -> NDArray[np.int8]:
    """MACD/Signal 크로스.

    Example:
        >>> vmacdSignal(close)
        array([0, 0, 1, ..., -1, 0])

    Requires:
        close 가 numpy array.

    Raises:
        없음.

    Parameters
    ----------
    close : NDArray[np.float64]
        종가 배열.
    fast : int
        MACD 빠른 EMA 기간 (기본 12).
    slow : int
        MACD 느린 EMA 기간 (기본 26).
    signal : int
        시그널선 EMA 기간 (기본 9).

    Returns
    -------
    NDArray[np.int8]
        +1=MACD 상향 돌파, -1=하향 돌파, 0=없음.
    """
    macdLine, signalLine, _ = vmacd(close, fast, slow, signal)
    return vcross(macdLine, signalLine)


def vbollingerSignal(close: NDArray[np.float64], period: int = 20, std: float = 2.0) -> NDArray[np.int8]:
    """볼린저밴드 하단 반등(+1) / 상단 돌파(-1).

    Parameters
    ----------
    close : NDArray[np.float64]
        종가 배열.
    period : int
        볼린저밴드 SMA 기간 (기본 20).
    std : float
        표준편차 배수 (기본 2.0).

    Returns
    -------
    NDArray[np.int8]
        +1=하단 반등 매수, -1=상단 접촉 매도, 0=없음.
    """
    upper, _, lower = vbollinger(close, period, std)
    n = len(close)
    signals = np.zeros(n, dtype=np.int8)
    prevClose = np.roll(close, 1)
    prevLower = np.roll(lower, 1)
    valid = ~np.isnan(upper) & ~np.isnan(lower)
    valid[0] = False
    signals[(valid) & (prevClose <= prevLower) & (close > lower)] = 1
    signals[(valid) & (close >= upper)] = -1
    return signals


def vbreakoutSignal(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    period: int = 20,
) -> NDArray[np.int8]:
    """채널 돌파 (Turtle Trading). 상방(+1) / 하방(-1).

    Parameters
    ----------
    high : NDArray[np.float64]
        고가 배열.
    low : NDArray[np.float64]
        저가 배열.
    close : NDArray[np.float64]
        종가 배열.
    period : int
        채널 룩백 기간 (기본 20).

    Returns
    -------
    NDArray[np.int8]
        +1=상방 돌파, -1=하방 돌파, 0=없음.
    """
    n = len(close)
    signals = np.zeros(n, dtype=np.int8)
    for i in range(period, n):
        hh = np.max(high[i - period : i])
        ll = np.min(low[i - period : i])
        if close[i] > hh:
            signals[i] = 1
        elif close[i] < ll:
            signals[i] = -1
    return signals


def vAtrTrailingStop(
    close: NDArray[np.float64],
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    atrPeriod: int = 14,
    multiplier: float = 3.0,
) -> NDArray[np.float64]:
    """ATR 기반 trailing stop level 시계열.

    매수 포지션 진입 후 추적용 stop level. close가 stop 아래로 떨어지면 손절.
    학술 근거: Wilder (1978) New Concepts in Technical Trading Systems — ATR.
    실무: Chandelier Exit (LeBeau & Lucas 1999).

    Args:
        close, high, low: OHLC 시계열
        atrPeriod: ATR 계산 기간 (기본 14)
        multiplier: ATR 배수 (기본 3.0 — Chandelier 표준)

    Returns:
        각 시점의 trailing stop price (np.nan = stop 미정)
    """
    n = len(close)
    stop = np.full(n, np.nan)
    if n < atrPeriod + 1:
        return stop

    # True Range
    prev_close = np.roll(close, 1)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    tr[0] = high[0] - low[0]

    # Wilder smoothing
    atr = np.full(n, np.nan)
    atr[atrPeriod - 1] = float(np.mean(tr[:atrPeriod]))
    for i in range(atrPeriod, n):
        atr[i] = (atr[i - 1] * (atrPeriod - 1) + tr[i]) / atrPeriod

    # Chandelier: highest high since entry − multiplier × ATR
    for i in range(atrPeriod, n):
        hh = float(np.max(high[max(0, i - atrPeriod) : i + 1]))
        candidate = hh - multiplier * atr[i]
        if i == atrPeriod or np.isnan(stop[i - 1]):
            stop[i] = candidate
        else:
            # trailing: stop은 한 방향으로만 (위로) 움직임
            stop[i] = max(stop[i - 1], candidate) if close[i] > stop[i - 1] else candidate

    return stop


def vVolatilityScaledStop(
    close: NDArray[np.float64],
    lookback: int = 20,
    multiplier: float = 2.0,
) -> NDArray[np.float64]:
    """변동성 기반 stop distance — close에서 multiplier × σ 만큼 아래.

    sigma는 lookback일 일별 log return 표준편차. 학술: Carver (2015) Systematic
    Trading. 보유 자산 변동성에 따라 stop 거리를 동적 조정.

    Args:
        close: 종가 시계열
        lookback: 변동성 lookback (기본 20일)
        multiplier: σ 배수 (기본 2.0)

    Returns:
        stop level price 시계열
    """
    n = len(close)
    stop = np.full(n, np.nan)
    if n < lookback + 1:
        return stop
    log_ret = np.diff(np.log(close))
    for i in range(lookback, n):
        sigma = float(np.std(log_ret[i - lookback : i], ddof=1))
        stop[i] = float(close[i] * (1 - multiplier * sigma))
    return stop


def vTrendFilter(
    close: NDArray[np.float64],
    sma: NDArray[np.float64],
    adx: NDArray[np.float64],
    signals: NDArray[np.int8],
    adxThreshold: float = 25.0,
) -> NDArray[np.int8]:
    """ADX 추세 필터. 약한 추세 신호 제거.

    Parameters
    ----------
    close : NDArray[np.float64]
        종가 배열.
    sma : NDArray[np.float64]
        SMA 배열 (추세 방향 판별).
    adx : NDArray[np.float64]
        ADX 배열 (추세 강도 판별).
    signals : NDArray[np.int8]
        원본 매수/매도 신호 배열.
    adxThreshold : float
        ADX 임계값 (기본 25.0). 이상이면 강한 추세.

    Returns
    -------
    NDArray[np.int8]
        필터링된 신호. ADX < 임계값이면 0으로 제거.
    """
    n = len(close)
    filtered = np.zeros(n, dtype=np.int8)
    valid = ~np.isnan(sma) & ~np.isnan(adx)
    strong = valid & (adx >= adxThreshold)
    filtered[(strong) & (signals == 1) & (close > sma)] = 1
    filtered[(strong) & (signals == -1) & (close < sma)] = -1
    return filtered
