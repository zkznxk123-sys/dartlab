"""Price channel and band indicators.

Capabilities:
    - Bollinger, Keltner, Donchian, percent-B, and bandwidth calculations.

Args:
    Functions accept aligned NumPy high/low/close arrays plus channel periods and
    multipliers.

Returns:
    Channel arrays or tuples of upper/middle/lower arrays aligned to input length.

Example:
    >>> upper, middle, lower = vbollinger(close, period=20)

Guide:
    Put price-envelope formulas here. Do not mix them into trend or volatility modules.

SeeAlso:
    ``trend`` for averages and ``volatility`` for ATR inputs.

Requires:
    NumPy arrays with sufficient history for rolling windows.

AIContext:
    L2 strategies can inspect price location inside bands through this stable L1.5 API.

LLM Specifications:
    AntiPatterns: Do not scan symbols, rank companies, or materialize DataFrames here.
    OutputSchema: NDArray[np.float64] or tuple[upper, middle, lower].
    Prerequisites: Caller supplies aligned OHLC arrays and chosen parameters.
    Freshness: Pure calculation; no data freshness side effects.
    Dataflow: OHLC arrays -> channel formula -> envelope arrays.
    TargetMarkets: Any OHLC market series.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray

from dartlab.core.indicators.trend import vema, vsma
from dartlab.core.indicators.volatility import vatr


def vbollinger(
    close: NDArray[np.float64], period: int = 20, std: float = 2.0
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute Bollinger upper, middle, and lower bands."""
    n = len(close)
    middle = vsma(close, period)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)
    for i in range(period - 1, n):
        window = close[i - period + 1 : i + 1]
        stdDev = np.std(window, ddof=0)
        upper[i] = middle[i] + std * stdDev
        lower[i] = middle[i] - std * stdDev
    return upper, middle, lower


def vkeltner(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
    period: int = 20,
    atrPeriod: int = 10,
    multiplier: float = 2.0,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute Keltner upper, middle, and lower channels."""
    middle = vema(close, period)
    atr = vatr(high, low, close, atrPeriod)
    upper = middle + multiplier * atr
    lower = middle - multiplier * atr
    return upper, middle, lower


def vdonchian(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    period: int = 20,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute Donchian upper, middle, and lower channels."""
    n = len(high)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)
    for i in range(period - 1, n):
        upper[i] = np.max(high[i - period + 1 : i + 1])
        lower[i] = np.min(low[i - period + 1 : i + 1])
    middle = (upper + lower) / 2
    return upper, middle, lower


def vbollingerPercentB(close: NDArray[np.float64], period: int = 20, std: float = 2.0) -> NDArray[np.float64]:
    """Compute Bollinger percent B."""
    upper, _, lower = vbollinger(close, period, std)
    rng = upper - lower
    result = np.where(rng > 0, (close - lower) / rng, np.nan)
    return result.astype(np.float64)


def vbollingerWidth(close: NDArray[np.float64], period: int = 20, std: float = 2.0) -> NDArray[np.float64]:
    """Compute Bollinger bandwidth."""
    upper, middle, lower = vbollinger(close, period, std)
    result = np.where(middle > 0, (upper - lower) / middle, np.nan)
    return result.astype(np.float64)
