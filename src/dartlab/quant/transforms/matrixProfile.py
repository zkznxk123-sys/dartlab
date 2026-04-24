"""Matrix Profile — 시계열 유사 패턴 탐색 (Yeh & Mueen 2016, ICDM).

Matrix Profile P[i] = 시계열 T 의 부분수열 T[i:i+m] 과 다른 모든 부분수열 사이의
**최소 z-normalized Euclidean 거리**.

작은 P[i] = 매우 유사 패턴 존재 (= motif), 큰 P[i] = 이상치 (discord).

dartlab 활용 :
    - 과거 유사 차트 검색 (현재 시점 패턴이 과거 어디서 발생했는지)
    - Anomaly detection (discord = 이상 가격 패턴)
    - Regime change 탐지 (motif 패턴 빈도 급변)

NumPy-only STAMP 알고리즘 (Scrimp 미적용 — 단순/안정).
"""

from __future__ import annotations

import numpy as np


def _slidingWindows(series: np.ndarray, m: int) -> np.ndarray:
    """Stride trick — series → (n-m+1, m) windows."""
    n = len(series)
    return np.lib.stride_tricks.sliding_window_view(series, m)


def _zNormalize(arr: np.ndarray) -> np.ndarray:
    mean = arr.mean(axis=-1, keepdims=True)
    std = arr.std(axis=-1, ddof=0, keepdims=True)
    std = np.where(std < 1e-10, 1.0, std)
    return (arr - mean) / std


def computeMatrixProfile(
    series: np.ndarray,
    *,
    window: int = 30,
    excludeFraction: float = 0.5,
) -> dict:
    """Matrix Profile (단변량, NumPy-only STAMP).

    Capabilities:
        - 시계열 부분수열 길이 m 의 최소 z-normalized 유클리드 거리 시리즈
        - motif (가장 유사) / discord (가장 이상) 자동 식별
        - Anomaly score / similar pattern indices

    AIContext:
        - Sprint 3 ML 인프라 — 유사 차트 검색 (dartlab killer feature)
        - calcStrategySnapshot 의 retrospective 패턴 기반 진입 신호 source

    Args:
        series: 1D 시계열 (가격 / 지수).
        window: 부분수열 길이 m. 기본 ``30`` (1개월 거래일).
        excludeFraction: 자기 자신과의 trivial match 제외 비율 (m × frac). 기본 ``0.5``.

    Returns:
        dict
            window : int
            n : int — 부분수열 개수 (= len(series) - window + 1)
            profile : np.ndarray — 각 i 의 최소 거리
            profileIdx : np.ndarray — 각 i 의 가장 유사한 j
            motif : tuple[int, int, float] — (i, j, dist) 가장 가까운 두 부분수열
            discord : tuple[int, float] — (i, dist) 가장 큰 거리 (이상치)
            interpretation : str

    Examples:
        >>> import numpy as np
        >>> from dartlab.quant.transforms.matrixProfile import computeMatrixProfile
        >>> s = np.cumsum(np.random.randn(500))
        >>> r = computeMatrixProfile(s, window=20)
        >>> print(r["motif"])
        (123, 280, 0.87)

    Notes:
        - O(n²·m) — n=1000 / m=30 → 약 30M 연산, 1초 미만.
        - z-normalize 로 패턴 매칭 (절대값 무관).
        - 더 빠른 알고리즘 (STOMP/SCRIMP) 은 후속.
    """
    series = np.asarray(series, dtype=np.float64)
    n_raw = len(series)
    if n_raw < window * 2:
        return {"error": f"series ({n_raw}) < 2*window ({window * 2})"}

    windows = _slidingWindows(series, window)
    n = windows.shape[0]
    z_windows = _zNormalize(windows)

    excl = max(1, int(window * excludeFraction))
    profile = np.full(n, np.inf, dtype=np.float64)
    profile_idx = np.zeros(n, dtype=np.int32)

    # STAMP: 각 i 에 대해 모든 j 와 거리 계산 (vectorized)
    for i in range(n):
        # z-norm Euclidean^2 = 2*m*(1 - corr)
        d = np.linalg.norm(z_windows - z_windows[i], axis=1)
        # exclude trivial neighborhood
        lo = max(0, i - excl)
        hi = min(n, i + excl + 1)
        d[lo:hi] = np.inf
        j = int(np.argmin(d))
        profile[i] = float(d[j])
        profile_idx[i] = j

    # motif = global min
    motif_i = int(np.argmin(profile))
    motif_j = int(profile_idx[motif_i])
    motif_d = float(profile[motif_i])
    # discord = global max (excluding inf)
    finite = profile[np.isfinite(profile)]
    if len(finite) == 0:
        return {"error": "no finite profile values"}
    max_d = finite.max()
    discord_i = int(np.argmax(np.where(np.isfinite(profile), profile, -1)))

    return {
        "window": window,
        "n": int(n),
        "profile": profile,
        "profileIdx": profile_idx,
        "motif": (motif_i, motif_j, round(motif_d, 4)),
        "discord": (discord_i, round(float(max_d), 4)),
        "interpretation": (
            f"window={window}, n={n} 부분수열. "
            f"가장 유사 패턴: t={motif_i} ↔ t={motif_j} (거리 {round(motif_d, 3)}). "
            f"가장 이상 패턴: t={discord_i} (거리 {round(float(max_d), 3)})."
        ),
    }


def findSimilarPatterns(
    series: np.ndarray,
    queryStart: int,
    *,
    window: int = 30,
    topK: int = 5,
    excludeFraction: float = 0.5,
) -> dict:
    """현재 (또는 지정) 시점의 패턴과 가장 유사한 과거 시점 top-K.

    Args:
        series: 전체 시계열.
        queryStart: 쿼리 시작 index. ``len(series) - window`` = 최근 패턴.
        window: 부분수열 길이.
        topK: 상위 유사도 개수.
        excludeFraction: 자기 근방 trivial 제외.

    Returns:
        dict
            queryRange : tuple[int, int]
            window : int
            topK : list[tuple[int, float]] — (start_idx, distance) 거리 오름차순
            interpretation : str
    """
    series = np.asarray(series, dtype=np.float64)
    n_raw = len(series)
    if queryStart + window > n_raw:
        return {"error": "queryStart + window exceeds series length"}

    windows = _slidingWindows(series, window)
    z_windows = _zNormalize(windows)
    z_query = z_windows[queryStart]
    d = np.linalg.norm(z_windows - z_query, axis=1)

    excl = max(1, int(window * excludeFraction))
    lo = max(0, queryStart - excl)
    hi = min(len(d), queryStart + excl + 1)
    d[lo:hi] = np.inf

    top_idx = np.argsort(d)[:topK]
    top_pairs = [(int(i), round(float(d[i]), 4)) for i in top_idx if np.isfinite(d[i])]

    return {
        "queryRange": (int(queryStart), int(queryStart + window)),
        "window": window,
        "topK": top_pairs,
        "interpretation": (
            f"쿼리 t={queryStart}~{queryStart + window} 와 가장 유사한 과거 패턴 top-{len(top_pairs)}: {top_pairs[:3]}"
        ),
    }
