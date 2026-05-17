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

    Capabilities:
        - 이전 봉 fast ≤ slow + 현봉 fast > slow 시 1 마크
        - NaN 게이팅으로 워밍업 구간 자동 제외

    Args:
        fast: 빠른 지표 배열.
        slow: 느린 지표 배열.

    Returns:
        NDArray[np.int8] — 1=상향 돌파 시점, 0=없음.

    Guide:
        SMA·MACD·DI± 크로스 등의 발현 시점 marker. 신호 양방향 필요시 ``vcross``.

    When:
        Strategy DSL crossover rule + AI 진입 시점 답변.

    How:
        ``np.roll`` 로 이전 봉 비교 → boolean mask → int8 배열.

    Requires:
        ``fast/slow`` 길이 동일 + numpy float64.

    Raises:
        없음 — NaN 은 자동 skip.

    Example:
        >>> vcrossover(fast, slow)
        array([0, 0, 1, 0, 0], dtype=int8)

    See Also:
        - vcrossunder : 하향 버전
        - vcross : 양방향 동시
        - vgoldenCross : 골든크로스 wrapper

    AIContext:
        Strategy 진입 시점 답변 시 mark된 인덱스의 ``date`` 인용.
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

    Capabilities:
        - 이전 봉 fast ≥ slow + 현봉 fast < slow 시 -1 마크
        - NaN 게이팅 + 첫 봉 자동 skip

    Args:
        fast: 빠른 지표 배열.
        slow: 느린 지표 배열.

    Returns:
        NDArray[np.int8] — -1=하향 돌파 시점, 0=없음.

    Guide:
        데드크로스 류 청산 시점 marker. 양방향 동시 마킹은 ``vcross``.

    When:
        Strategy DSL exit rule + AI 청산 시점 답변.

    How:
        ``np.roll`` prev → boolean mask → ``signals[mask] = -1``.

    Requires:
        ``fast/slow`` 길이 동일 + numpy float64.

    Raises:
        없음.

    Example:
        >>> vcrossunder(fast, slow)
        array([ 0,  0, -1,  0,  0], dtype=int8)

    See Also:
        - vcrossover : 상향 버전
        - vcross : 양방향
        - vTrendFilter : 추세 필터

    AIContext:
        AI 청산 시점 답변 시 -1 마크 인덱스 인용.
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

    Capabilities:
        - vcrossover + vcrossunder 동시 마크 (단일 패스)
        - NaN/첫봉 안전 처리

    Args:
        fast: 빠른 지표 배열.
        slow: 느린 지표 배열.

    Returns:
        NDArray[np.int8] — +1=상향, -1=하향, 0=없음.

    Guide:
        ``vgoldenCross``·``vmacdSignal``·``vrsiSignal`` 등 모든 양방향 cross 의 기반 helper.

    When:
        Strategy DSL 양방향 시그널 + AI 전환 시점 답변.

    How:
        ``np.roll`` prev → 두 boolean mask 합 → int8 매핑.

    Requires:
        길이 동일 numpy float64.

    Raises:
        없음.

    Example:
        >>> vcross(fast, slow)
        array([0, 1, 0, -1, 0], dtype=int8)

    See Also:
        - vcrossover / vcrossunder : 단방향
        - vgoldenCross / vmacdSignal : 응용 wrapper

    AIContext:
        양방향 전환점 인용 (강세→약세 또는 반대) 답변 시 사용.
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

    Capabilities:
        - 이전 봉 RSI ≤ 30 + 현봉 > 30 → +1 (과매도 탈출)
        - 이전 봉 RSI ≥ 70 + 현봉 < 70 → -1 (과매수 반전)

    Args:
        rsi: RSI 값 배열 (0~100).
        oversold: 과매도 임계값. 기본 ``30.0``.
        overbought: 과매수 임계값. 기본 ``70.0``.

    Returns:
        NDArray[np.int8] — +1/0/-1.

    Guide:
        Wilder 1978 RSI 표준 임계 30/70. 변동성 종목 = 20/80, 추세 종목 = 40/60 권장.

    When:
        Mean reversion strategy + AI overbought/oversold 답변.

    How:
        ``np.roll`` prev → 두 boolean mask → ``signals[mask] = ±1``.

    Requires:
        ``synth.indicators.vrsi`` 등으로 사전 계산된 rsi 배열.

    Raises:
        없음.

    Example:
        >>> vrsiSignal(rsi)
        array([0, 1, 0, 0, -1], dtype=int8)

    See Also:
        - synth.indicators.vrsi : RSI 계산
        - vbollingerSignal : 다른 mean reversion

    AIContext:
        AI 가 "과매도 시점" 답변 시 +1 mark 인덱스의 날짜·RSI 값 인용.
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

    Capabilities:
        - 이전 close ≤ lower + 현 close > lower → +1 (하단 반등)
        - 현 close ≥ upper → -1 (상단 접촉)

    Args:
        close: 종가 배열.
        period: SMA 기간. 기본 ``20``.
        std: 표준편차 배수. 기본 ``2.0``.

    Returns:
        NDArray[np.int8] — +1/0/-1.

    Guide:
        Bollinger 1980 표준. 표준편차 배수 = 2.0 (95% 통계) 범용. 횡보장 mean reversion.

    When:
        Mean reversion strategy + AI 변동성 밴드 답변.

    How:
        ``vbollinger`` → upper/lower 배열 → 두 mask → int8.

    Requires:
        close 길이 ≥ period.

    Raises:
        없음.

    Example:
        >>> vbollingerSignal(close, 20, 2.0)
        array([0, 1, 0, -1, 0], dtype=int8)

    See Also:
        - synth.indicators.vbollinger : 밴드 계산
        - vrsiSignal : 다른 mean reversion

    AIContext:
        "볼린저 하단 매수 시점" 답변 시 +1 mark 의 close + lower 값 인용.
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

    Capabilities:
        - close > 이전 N 일 최고가 → +1 (상방 돌파)
        - close < 이전 N 일 최저가 → -1 (하방 돌파)
        - Donchian channel breakout = Turtle Trading 표준

    Args:
        high: 고가 배열.
        low: 저가 배열.
        close: 종가 배열.
        period: 채널 룩백 기간. 기본 ``20``.

    Returns:
        NDArray[np.int8] — +1/0/-1.

    Guide:
        Dennis-Eckhardt 1983 Turtle System. period 20 = 단기, 55 = 중기 (S1/S2).
        Trend-following 표준 진입.

    When:
        Trend strategy breakout + AI 신고가 답변.

    How:
        for i ∈ [period, n): hh/ll 계산 → close 비교 → signals[i] 설정.

    Requires:
        high/low/close 같은 길이 + ≥ period.

    Raises:
        없음 — 짧으면 0 배열.

    Example:
        >>> vbreakoutSignal(h, l, c, 20)
        array([0, 0, 1, 0, -1], dtype=int8)

    See Also:
        - vAtrTrailingStop : 진입 후 stop
        - strategy.styles.breakout : 사용처

    AIContext:
        "20 일 신고가 돌파" 류 답변 시 +1 mark 의 close + hh 인용.
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

    Capabilities:
        - True Range + Wilder smoothing 으로 ATR 시계열 계산
        - Chandelier Exit: 진입 이후 최고가 - multiplier × ATR (위로만 trailing)

    Args:
        close: 종가 시계열.
        high: 고가 시계열.
        low: 저가 시계열.
        atrPeriod: ATR 계산 기간. 기본 ``14``.
        multiplier: ATR 배수. 기본 ``3.0`` (Chandelier 표준).

    Returns:
        NDArray[np.float64] — 각 시점의 trailing stop price (np.nan = 미정).

    Guide:
        Wilder 1978 + Chandelier Exit (LeBeau-Lucas 1999). multiplier 2.5 = tight,
        4.0 = loose. 변동성 종목 = loose, 추세 종목 = tight 권장.

    When:
        Risk management strategy + AI 손절 레벨 답변.

    How:
        True Range → Wilder smoothing → 진입 이후 highest high - mult × ATR.

    Requires:
        close/high/low 같은 길이 + ≥ atrPeriod + 1.

    Raises:
        없음 — 짧으면 nan 배열.

    Example:
        >>> stop = vAtrTrailingStop(c, h, l, 14, 3.0)
        >>> stop[-1]
        72400.0

    See Also:
        - vVolatilityScaledStop : sigma 기반 stop
        - vbreakoutSignal : 진입 시그널

    AIContext:
        "손절 레벨" 답변 시 stop 시계열 최신값 인용.
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

    Capabilities:
        - 일별 log return 표준편차 σ 계산 + close × (1 - mult × σ) 시계열
        - 변동성 ↑ → stop 거리 자동 확대

    Args:
        close: 종가 시계열.
        lookback: 변동성 lookback. 기본 ``20`` 일.
        multiplier: σ 배수. 기본 ``2.0``.

    Returns:
        NDArray[np.float64] — stop level price 시계열 (np.nan = 미정).

    Guide:
        Carver 2015 Systematic Trading 표준. ATR 기반 (``vAtrTrailingStop``) 보다 단순 +
        log-return 표준편차 기반이라 다양한 자산에 호환.

    When:
        Volatility targeting strategy + AI 동적 손절 답변.

    How:
        ``np.diff(np.log(close))`` → rolling std → close × (1 - mult × σ).

    Requires:
        close 길이 ≥ lookback + 1.

    Raises:
        없음.

    Example:
        >>> stop = vVolatilityScaledStop(c, 20, 2.0)
        >>> stop[-1]
        70800.0

    See Also:
        - vAtrTrailingStop : ATR Chandelier
        - quant.portfolio.sizing : volatility target sizing

    AIContext:
        AI 가 "변동성 기반 동적 손절" 류 답변 시 σ + stop 값 인용.
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

    Capabilities:
        - ADX < 임계 → 약한 추세로 판단 → 신호 0 으로 제거
        - 매수는 close > sma 동시 만족, 매도는 close < sma 동시 만족 시만 통과

    Args:
        close: 종가 배열.
        sma: SMA 배열 (추세 방향 판별).
        adx: ADX 배열 (추세 강도 판별).
        signals: 원본 매수/매도 신호 배열.
        adxThreshold: ADX 임계값. 기본 ``25.0``. 이상이면 강한 추세.

    Returns:
        NDArray[np.int8] — 필터링된 신호. ADX < 임계값이면 0.

    Guide:
        Wilder 1978 ADX. 25 = 추세 형성 기준. 횡보장 false signal 제거에 효과적.

    When:
        Trend-following strategy 강건성 보강 + AI 잡음 제거 답변.

    How:
        valid (NaN 제외) + (adx ≥ threshold) → close-sma 방향 확인 → ±1 통과.

    Requires:
        close/sma/adx/signals 같은 길이.

    Raises:
        없음.

    Example:
        >>> filtered = vTrendFilter(c, sma, adx, signals, 25.0)
        >>> int(filtered.sum())
        12

    See Also:
        - synth.indicators.vadx : ADX 계산
        - vgoldenCross : 원본 cross signal

    AIContext:
        "추세 약할 때 매매 잡음" 류 답변 시 필터 전후 시그널 수 비교 인용.
    """
    n = len(close)
    filtered = np.zeros(n, dtype=np.int8)
    valid = ~np.isnan(sma) & ~np.isnan(adx)
    strong = valid & (adx >= adxThreshold)
    filtered[(strong) & (signals == 1) & (close > sma)] = 1
    filtered[(strong) & (signals == -1) & (close < sma)] = -1
    return filtered
