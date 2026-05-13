"""Volume and money-flow indicators.

Capabilities:
    - OBV, MFI, Elder Ray, Force Index, VWAP, ADL, Chaikin, EMV, NVI, PVI, and PVT.

Args:
    Functions accept aligned NumPy price and volume arrays.

Returns:
    Volume-pressure arrays, or tuples where the indicator naturally has multiple lines.

Example:
    >>> obv = vobv(close, volume)

Guide:
    Use this module when the formula requires volume or money-flow information.

SeeAlso:
    ``momentum`` for price-only oscillators and ``trend`` for EMA smoothing.

Requires:
    Price and volume arrays with the same length and order.

AIContext:
    Quant layers use this module to confirm price signals with participation/flow data.

LLM Specifications:
    AntiPatterns: Do not fetch volume, infer market sessions, or call provider endpoints.
    OutputSchema: NDArray[np.float64] or tuple outputs aligned to input length.
    Prerequisites: Caller supplies cleaned price and volume arrays.
    Freshness: Pure calculation; output freshness equals input freshness.
    Dataflow: price/volume arrays -> volume formula -> pressure arrays.
    TargetMarkets: Markets with meaningful volume data.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from dartlab.synth.indicators.trend import vema


def vobv(close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute On Balance Volume."""
    n = len(close)
    obv = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]
    return obv


def vmfi(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    volume: NDArray[np.float64],
    period: int = 14,
) -> NDArray[np.float64]:
    """Compute Money Flow Index."""
    tp = (high + low + close) / 3
    mf = tp * volume
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)
    for i in range(period, n):
        pos = 0.0
        neg = 0.0
        for j in range(i - period + 1, i + 1):
            if tp[j] > tp[j - 1]:
                pos += mf[j]
            elif tp[j] < tp[j - 1]:
                neg += mf[j]
        result[i] = 100.0 if neg == 0 else 100.0 - 100.0 / (1.0 + pos / neg)
    return result


def velderRay(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    period: int = 13,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute Elder Ray bull and bear power."""
    ema = vema(close, period)
    bull = high - ema
    bear = low - ema
    return bull, bear


def vforceIndex(close: NDArray[np.float64], volume: NDArray[np.float64], period: int = 13) -> NDArray[np.float64]:
    """Compute EMA-smoothed Force Index."""
    n = len(close)
    raw = np.zeros(n, dtype=np.float64)
    raw[1:] = (close[1:] - close[:-1]) * volume[1:]
    return vema(raw, period)


def vvwap(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    volume: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute cumulative VWAP."""
    tp = (high + low + close) / 3
    cumTPV = np.cumsum(tp * volume)
    cumV = np.cumsum(volume)
    result = np.where(cumV > 0, cumTPV / cumV, np.nan)
    return result.astype(np.float64)


def vadl(
    close: NDArray[np.float64], high: NDArray[np.float64], low: NDArray[np.float64], volume: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Compute Accumulation/Distribution Line."""
    n = len(close)
    adl = np.zeros(n, dtype=np.float64)
    for i in range(n):
        hl = high[i] - low[i]
        if hl > 0:
            mfm = ((close[i] - low[i]) - (high[i] - close[i])) / hl
            adl[i] = (adl[i - 1] if i > 0 else 0) + mfm * volume[i]
        else:
            adl[i] = adl[i - 1] if i > 0 else 0
    return adl


def vchaikin(
    close: NDArray[np.float64],
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    volume: NDArray[np.float64],
    fastPeriod: int = 3,
    slowPeriod: int = 10,
) -> NDArray[np.float64]:
    """Compute Chaikin Oscillator."""
    adl = vadl(close, high, low, volume)
    return vema(adl, fastPeriod) - vema(adl, slowPeriod)


def vemv(
    high: NDArray[np.float64], low: NDArray[np.float64], volume: NDArray[np.float64], period: int = 14
) -> NDArray[np.float64]:
    """Compute Ease of Movement."""
    n = len(high)
    raw = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        hl = high[i] - low[i]
        if hl > 0 and volume[i] > 0:
            dm = ((high[i] + low[i]) / 2) - ((high[i - 1] + low[i - 1]) / 2)
            box = volume[i] / hl
            raw[i] = dm / box if box > 0 else 0
    return vema(raw, period)


def vnvi(close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute Negative Volume Index."""
    n = len(close)
    nvi = np.full(n, 1000.0, dtype=np.float64)
    for i in range(1, n):
        if volume[i] < volume[i - 1] and close[i - 1] > 0:
            nvi[i] = nvi[i - 1] * (1 + (close[i] - close[i - 1]) / close[i - 1])
        else:
            nvi[i] = nvi[i - 1]
    return nvi


def vpvi(close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute Positive Volume Index."""
    n = len(close)
    pvi = np.full(n, 1000.0, dtype=np.float64)
    for i in range(1, n):
        if volume[i] > volume[i - 1] and close[i - 1] > 0:
            pvi[i] = pvi[i - 1] * (1 + (close[i] - close[i - 1]) / close[i - 1])
        else:
            pvi[i] = pvi[i - 1]
    return pvi


def vpvt(close: NDArray[np.float64], volume: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute Price Volume Trend."""
    n = len(close)
    pvt = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if close[i - 1] > 0:
            pvt[i] = pvt[i - 1] + volume[i] * (close[i] - close[i - 1]) / close[i - 1]
        else:
            pvt[i] = pvt[i - 1]
    return pvt
