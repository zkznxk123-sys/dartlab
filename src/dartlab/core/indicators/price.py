"""Price-shape and support/resistance helpers.

Capabilities:
    - Pivot points, rolling linear regression, and ZigZag pivot extraction.

Args:
    Functions accept aligned NumPy price arrays and optional lookback/threshold settings.

Returns:
    Price-shape arrays or tuple outputs aligned to input length.

Example:
    >>> value, slope, rsq = vlinearRegression(close, period=20)

Guide:
    Keep direct price-geometry helpers here rather than mixing them into trend or momentum.

SeeAlso:
    ``channels`` for envelope levels and ``trend`` for moving-average direction.

Requires:
    NumPy price arrays with sufficient history.

AIContext:
    Higher layers use these primitives for support/resistance and price-shape context.

LLM Specifications:
    AntiPatterns: Do not label companies, fetch quotes, or run screen ranking here.
    OutputSchema: NDArray[np.float64] or tuple outputs with input-series length.
    Prerequisites: Caller supplies sorted, cleaned price arrays.
    Freshness: Pure calculation; no freshness policy inside this module.
    Dataflow: price arrays -> price-shape formula -> vectorized arrays.
    TargetMarkets: Any price series where pivots/regression are meaningful.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray


def vpivotPoints(
    high: NDArray[np.float64],
    low: NDArray[np.float64],
    close: NDArray[np.float64],
) -> Tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    """Compute classic pivot points from previous period."""
    n = len(close)
    pp = np.full(n, np.nan, dtype=np.float64)
    r1 = np.full(n, np.nan, dtype=np.float64)
    r2 = np.full(n, np.nan, dtype=np.float64)
    r3 = np.full(n, np.nan, dtype=np.float64)
    s1 = np.full(n, np.nan, dtype=np.float64)
    s2 = np.full(n, np.nan, dtype=np.float64)
    s3 = np.full(n, np.nan, dtype=np.float64)
    for i in range(1, n):
        p = (high[i - 1] + low[i - 1] + close[i - 1]) / 3
        pp[i] = p
        r1[i] = 2 * p - low[i - 1]
        s1[i] = 2 * p - high[i - 1]
        r2[i] = p + (high[i - 1] - low[i - 1])
        s2[i] = p - (high[i - 1] - low[i - 1])
        r3[i] = high[i - 1] + 2 * (p - low[i - 1])
        s3[i] = low[i - 1] - 2 * (high[i - 1] - p)
    return pp, r1, r2, r3, s1, s2, s3


def vlinearRegression(
    close: NDArray[np.float64],
    period: int = 20,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute rolling linear regression value, slope, and r-squared."""
    n = len(close)
    value = np.full(n, np.nan, dtype=np.float64)
    slope = np.full(n, np.nan, dtype=np.float64)
    rsq = np.full(n, np.nan, dtype=np.float64)
    x = np.arange(period, dtype=np.float64)
    xmean = x.mean()
    xvar = np.sum((x - xmean) ** 2)
    for i in range(period - 1, n):
        y = close[i - period + 1 : i + 1]
        ymean = y.mean()
        cov = np.sum((x - xmean) * (y - ymean))
        b = cov / xvar if xvar > 0 else 0
        a = ymean - b * xmean
        value[i] = a + b * (period - 1)
        slope[i] = b
        yhat = a + b * x
        ss_res = np.sum((y - yhat) ** 2)
        ss_tot = np.sum((y - ymean) ** 2)
        rsq[i] = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return value, slope, rsq


def vzigzag(close: NDArray[np.float64], threshold: float = 5.0) -> NDArray[np.float64]:
    """Compute ZigZag pivot series."""
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)
    result[0] = close[0]
    lastPivot = close[0]
    lastIdx = 0
    direction = 0
    for i in range(1, n):
        change = (close[i] - lastPivot) / lastPivot * 100 if lastPivot > 0 else 0
        if direction == 0:
            if abs(change) >= threshold:
                direction = 1 if change > 0 else -1
                result[i] = close[i]
                lastPivot = close[i]
                lastIdx = i
        elif direction == 1:
            if close[i] > lastPivot:
                result[lastIdx] = np.nan
                result[i] = close[i]
                lastPivot = close[i]
                lastIdx = i
            elif change <= -threshold:
                direction = -1
                result[i] = close[i]
                lastPivot = close[i]
                lastIdx = i
        else:
            if close[i] < lastPivot:
                result[lastIdx] = np.nan
                result[i] = close[i]
                lastPivot = close[i]
                lastIdx = i
            elif change >= threshold:
                direction = 1
                result[i] = close[i]
                lastPivot = close[i]
                lastIdx = i
    return result
