"""통계 primitive SSOT — zscore · winsorize · percentileRank · rolling.

L1.5 synth 본체 — analysis · credit · macro · quant · industry 5 엔진 + scan 가
공통으로 호출하는 단순 통계 도구. numpy 배열 또는 list[float] 처리.

수치 안정성 원칙:
- NaN/None/빈 배열 → 보수적 fallback (zeros, 원본 그대로 등) 또는 명시 ValueError
- ddof=1 표본 표준편차 기본 (Polars/Pandas 호환)
- rolling 함수는 길이 부족 시 앞자리 NaN 으로 채움

순수 numpy. 외부 의존성 0.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

ArrayLike = np.ndarray | Sequence[float | None]


def _toArray(values: ArrayLike) -> np.ndarray:
    """입력 → numpy float 배열. None/NaN 보존."""
    arr = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=float)
    return arr


def zscore(values: ArrayLike, *, ddof: int = 1) -> np.ndarray:
    """표준화 — (x - mean) / std.

    Args:
        values: 1D array-like. NaN 은 mean/std 계산에서 무시되지만 결과 위치에는 NaN 유지.
        ddof: Delta degrees of freedom. 표본 표준편차 1 (기본), 모분산 0.

    Returns:
        np.ndarray — 입력과 동일 길이. std 가 0 또는 NaN 이면 모두 0.

    Example:
        >>> zscore([1.0, 2.0, 3.0, 4.0, 5.0])
        array([-1.26491106, -0.63245553,  0.        ,  0.63245553,  1.26491106])
    """
    arr = _toArray(values)
    if arr.size == 0:
        return arr
    mean = np.nanmean(arr)
    std = np.nanstd(arr, ddof=ddof)
    if not np.isfinite(std) or std == 0:
        return np.zeros_like(arr)
    return (arr - mean) / std


def winsorize(values: ArrayLike, *, lower: float = 0.01, upper: float = 0.99) -> np.ndarray:
    """양 끝단 분위수 cap — 이상치 영향 제한.

    Args:
        values: 1D array-like. NaN 은 분위수 계산에서 무시 + cap 영향 0 (그대로 NaN).
        lower: 하단 분위수 (0.0 ~ 0.5). 기본 1 %.
        upper: 상단 분위수 (0.5 ~ 1.0). 기본 99 %.

    Returns:
        np.ndarray — 입력과 동일 길이. lower/upper 분위수로 cap 된 값.

    Raises:
        ValueError: lower >= upper 또는 범위 밖.

    Example:
        >>> winsorize([1.0, 2.0, 3.0, 4.0, 100.0], lower=0.0, upper=0.8)
        array([1. , 2. , 3. , 4. , 4. ])
    """
    if not (0.0 <= lower < upper <= 1.0):
        raise ValueError(f"invalid bounds lower={lower}, upper={upper}")
    arr = _toArray(values)
    if arr.size == 0:
        return arr
    lo = float(np.nanquantile(arr, lower))
    hi = float(np.nanquantile(arr, upper))
    return np.clip(arr, lo, hi)


def percentileRank(values: ArrayLike, *, target: float | None = None) -> np.ndarray | float:
    """분위 순위 — 각 값이 전체 중 몇 분위인지 (0.0 ~ 1.0).

    Args:
        values: 1D array-like 기준 분포. NaN 은 무시.
        target: 단일 값 분위. None 이면 입력 각 원소의 분위 배열 반환.

    Returns:
        target 지정 시 float (0.0 ~ 1.0). 미지정 시 동일 길이 np.ndarray.
        분포 비어있으면 NaN (target) 또는 빈 배열.

    Example:
        >>> percentileRank([10, 20, 30, 40, 50], target=25)
        0.4
        >>> percentileRank([10, 20, 30, 40, 50])
        array([0. , 0.25, 0.5 , 0.75, 1.  ])
    """
    arr = _toArray(values)
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return float("nan") if target is not None else np.array([], dtype=float)
    sorted_valid = np.sort(valid)
    if target is not None:
        rank = float(np.searchsorted(sorted_valid, target, side="right")) / float(sorted_valid.size)
        return max(0.0, min(1.0, rank))
    # 입력 각 원소의 분위 (NaN 은 NaN 유지)
    out = np.full_like(arr, np.nan)
    for i, v in enumerate(arr):
        if np.isfinite(v):
            out[i] = float(np.searchsorted(sorted_valid, v, side="right")) / float(sorted_valid.size)
    return out


def rollingMean(values: ArrayLike, *, period: int) -> np.ndarray:
    """이동평균 — 길이 period 윈도우.

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=1). 길이 부족 영역은 NaN.

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN.

    Raises:
        ValueError: period < 1.
    """
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    arr = _toArray(values)
    n = arr.size
    if n == 0:
        return arr
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = arr[i - period + 1 : i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.mean(window))
    return out


def rollingStd(values: ArrayLike, *, period: int, ddof: int = 1) -> np.ndarray:
    """이동 표준편차 — 길이 period 윈도우.

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=2).
        ddof: Delta degrees of freedom (표본 1, 모분산 0).

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN.

    Raises:
        ValueError: period < 2.
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    arr = _toArray(values)
    n = arr.size
    if n == 0:
        return arr
    out = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = arr[i - period + 1 : i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=ddof))
    return out


def rollingZScore(values: ArrayLike, *, period: int) -> np.ndarray:
    """rolling z-score — (x - rollingMean) / rollingStd.

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=2).

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN. std=0 위치는 0.
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    arr = _toArray(values)
    n = arr.size
    if n == 0:
        return arr
    m = rollingMean(arr, period=period)
    s = rollingStd(arr, period=period)
    out = np.full(n, np.nan)
    for i in range(n):
        if np.isfinite(arr[i]) and np.isfinite(m[i]) and np.isfinite(s[i]):
            out[i] = 0.0 if s[i] == 0 else (arr[i] - m[i]) / s[i]
    return out


def normalize(values: ArrayLike, *, method: str = "zscore") -> np.ndarray:
    """선택 정규화 — zscore / minmax / rank.

    Args:
        values: 1D array-like.
        method: ``"zscore"`` (default), ``"minmax"`` (0~1 스케일), ``"rank"`` (분위 0~1).

    Returns:
        np.ndarray — 입력과 동일 길이.

    Raises:
        ValueError: 지원하지 않는 method.
    """
    if method == "zscore":
        return zscore(values)
    if method == "minmax":
        arr = _toArray(values)
        if arr.size == 0:
            return arr
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            return arr
        mn = float(np.min(valid))
        mx = float(np.max(valid))
        if mx == mn:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn)
    if method == "rank":
        result = percentileRank(values)
        if isinstance(result, np.ndarray):
            return result
        # target=None 분기는 항상 ndarray 반환
        return np.asarray([result], dtype=float)
    raise ValueError(f"unknown method: {method!r} (expected zscore/minmax/rank)")
