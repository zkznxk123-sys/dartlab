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
    """표준화 — (x - mean) / std. 횡단면 또는 시계열 z-score 산출.

    Capabilities:
        - NaN-safe (NaN 위치 유지, mean/std 계산에서 제외)
        - std=0 또는 NaN 시 보수적 fallback (zeros)
        - 표본 표준편차 (ddof=1) 기본, 모분산 (ddof=0) 옵션

    Args:
        values: 1D array-like. NaN 은 mean/std 계산에서 무시되지만 결과 위치에는 NaN 유지.
        ddof: Delta degrees of freedom. 표본 표준편차 1 (기본), 모분산 0.

    Returns:
        np.ndarray — 입력과 동일 길이. std 가 0 또는 NaN 이면 모두 0.

    Example:
        >>> zscore([1.0, 2.0, 3.0, 4.0, 5.0])
        array([-1.26491106, -0.63245553,  0.        ,  0.63245553,  1.26491106])

    Guide:
        횡단면 비교 (peer 간 또는 sector 내 회사 비교) 또는 단발 정규화에 사용.
        시계열의 rolling 정규화는 `rollingZScore` 호출.

    SeeAlso:
        - `winsorize`: 이상치 cap 후 z-score 가 안정적
        - `percentileRank`: 분위 순위로 동일 목적
        - `rollingZScore`: 시계열 윈도우 정규화

    Requires:
        numpy

    AIContext:
        AI 가 정규화 결과를 비교 도구로 인용 시 std=0 케이스 (모든 값 동일) 면
        모두 0 반환 — "차이 없음" 으로 해석. 입력 분포에 따라 의미가 달라짐을 유의.

    LLM Specifications:
        AntiPatterns: 단일 값 (size=1) 에 zscore 호출 — std 정의 불가, 0 반환.
        OutputSchema: np.ndarray, dtype=float64, NaN 가능.
        Prerequisites: 입력 길이 >= 2 권장 (size=1 시 zeros, size=0 시 빈 배열).
        Freshness: stateless — 입력 시점에만 의존.
        Dataflow: list/np.ndarray → np.ndarray (변환 없음, identity 보존 X).
        TargetMarkets: 도메인 무관 — peer 비교 · factor 표준화 · 횡단면 분석 일반.
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

    Capabilities:
        - numpy linear interpolation 기반 분위수 (보편 표준)
        - lower=0 또는 upper=1 시 한 쪽만 cap
        - NaN 보존 (분위수 계산에서 제외)

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
        array([ 1. ,  2. ,  3. ,  4. , 23.2])  # 0.8 분위 = 23.2 (linear interp)

    Guide:
        이상치 영향이 큰 회귀/zscore 직전 호출 권장. 일반적 cutoff 는 (0.01, 0.99)
        또는 (0.05, 0.95). financial peer 비교에서는 종종 (0.025, 0.975).

    SeeAlso:
        - `zscore`: winsorize 결과를 받아 표준화하는 패턴
        - `percentileRank`: rank-based 정규화 (이상치 영향 자동 제어)

    Requires:
        numpy

    AIContext:
        AI 가 winsorize 결과 인용 시 cap 된 값은 "원본" 이 아님을 명시. 보존된 NaN
        위치는 인용 가능하나 cap 된 위치는 "조정값" 라벨 권장.

    LLM Specifications:
        AntiPatterns: lower>=upper 호출 (ValueError); 빈 배열에 호출 가능하나 결과도 빈 배열.
        OutputSchema: np.ndarray, dtype=float64, 길이 == 입력.
        Prerequisites: lower < upper, 모두 [0.0, 1.0] 내.
        Freshness: stateless.
        Dataflow: list/np.ndarray → np.ndarray (분위수 cap 적용).
        TargetMarkets: factor analysis · 회귀 전처리 · peer 비교 (이상치 흔한 도메인).
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

    Capabilities:
        - target 지정 → float 반환 (단일 값 분위 조회)
        - target 미지정 → 입력 각 원소의 분위 배열
        - "rank/n" 방식 (searchsorted side="right" → 강한 inequality)

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
        array([0.2, 0.4, 0.6, 0.8, 1. ])

    Guide:
        zscore 이상치 영향 회피용. peer 분포에서 회사 위치 표시·factor 비교에 적합.
        target=None 모드는 입력 각 원소의 분위를 한 번에 계산.

    SeeAlso:
        - `zscore`: 분포가 정규분포 가정될 때
        - `winsorize`: 이상치 cap 후 zscore 가 더 안정적
        - `normalize(method="rank")`: 본 함수와 동일 (rank 정규화)

    Requires:
        numpy

    AIContext:
        AI 가 percentile 결과 인용 시 "상위 X%" vs "X 분위" 의미 구분. searchsorted
        side="right" 기준이라 동일 값들은 더 높은 분위 받음 (보수적 인용 권장).

    LLM Specifications:
        AntiPatterns: 빈 입력에 target 지정 → NaN; target 없이 빈 입력 → 빈 배열.
        OutputSchema: target 시 float [0.0, 1.0], 미지정 시 np.ndarray.
        Prerequisites: 입력 size >= 1 권장.
        Freshness: stateless.
        Dataflow: list/np.ndarray → float|np.ndarray (target 분기).
        TargetMarkets: peer 비교 · factor screening · 회사 ranking 일반.
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

    Capabilities:
        - 윈도우 내 NaN 1 개라도 있으면 결과 NaN (보수적)
        - 앞자리 (period-1) 개는 NaN 으로 padding
        - period=1 시 입력과 동일 결과

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=1). 길이 부족 영역은 NaN.

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN.

    Raises:
        ValueError: period < 1.

    Example:
        >>> rollingMean([1.0, 2.0, 3.0, 4.0], period=2)
        array([nan, 1.5, 2.5, 3.5])

    Guide:
        시계열 평활화 · trend 산출 · 이동평균 크로스 신호. period 는 도메인에 맞춰
        (예: 일별 가격 20/60/120, 분기별 매출 4).

    SeeAlso:
        - `rollingStd`: 동일 윈도우 표준편차
        - `rollingZScore`: rollingMean / rollingStd 결합

    Requires:
        numpy

    AIContext:
        AI 가 평활화 결과 인용 시 앞자리 NaN 위치는 "데이터 부족" 으로 명시.
        윈도우 NaN 보수 처리로 sparse 데이터에서는 결과 NaN 다수 가능.

    LLM Specifications:
        AntiPatterns: period > 입력 길이 호출 → 모두 NaN (오류 아님).
        OutputSchema: np.ndarray, dtype=float64, 길이 == 입력.
        Prerequisites: period >= 1.
        Freshness: stateless.
        Dataflow: list/np.ndarray → np.ndarray.
        TargetMarkets: 시계열 분석 (가격 · macro 시계열 · 실적 분기).
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

    Capabilities:
        - 윈도우 내 NaN 1 개라도 있으면 NaN (보수적)
        - 앞자리 (period-1) 개는 NaN padding
        - ddof=1 표본 (Polars/Pandas 호환) 기본, ddof=0 모분산

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=2).
        ddof: Delta degrees of freedom (표본 1, 모분산 0).

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN.

    Raises:
        ValueError: period < 2.

    Example:
        >>> rollingStd([1.0, 2.0, 3.0, 4.0, 5.0], period=3)
        array([nan, nan, 1. , 1. , 1. ])

    Guide:
        시계열 변동성 산출. 가격 시계열의 realized volatility, 매출 변동성 등.
        rollingZScore 의 분모로도 사용됨.

    SeeAlso:
        - `rollingMean`: 동일 윈도우 평균
        - `rollingZScore`: 결합 z-score

    Requires:
        numpy

    AIContext:
        AI 가 변동성 결과 인용 시 ddof 차이를 명시. 표본 1 (default) 는 N-1 분모,
        모분산 0 은 N 분모 — 인용 매체에 따라 다름.

    LLM Specifications:
        AntiPatterns: period=1 호출 (ValueError); period 가 너무 큼 → 모두 NaN.
        OutputSchema: np.ndarray, dtype=float64, 길이 == 입력.
        Prerequisites: period >= 2, ddof in {0, 1} 권장.
        Freshness: stateless.
        Dataflow: list/np.ndarray → np.ndarray.
        TargetMarkets: 변동성 분석 · realized vol · 시계열 risk.
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

    Capabilities:
        - 시계열 윈도우 내 정규화 — 추세 제거 후 표준화
        - 윈도우 std=0 위치는 0 (모든 값 동일)
        - 앞 (period-1) 개는 NaN padding

    Args:
        values: 1D array-like.
        period: 윈도우 크기 (>=2).

    Returns:
        np.ndarray — 입력과 동일 길이. 앞 (period-1) 개는 NaN. std=0 위치는 0.

    Raises:
        ValueError: period < 2.

    Example:
        >>> rollingZScore([1.0, 2.0, 3.0, 4.0, 5.0], period=3)[2:]
        array([1., 1., 1.])

    Guide:
        시계열의 "정상 범위 대비 현재 위치" 신호. 가격/매출 z-score 임계값
        (예: |z|>2 = 이상) 트리거 생성에 사용.

    SeeAlso:
        - `zscore`: 전체 분포 기준 단일 정규화
        - `rollingMean` · `rollingStd`: 본 함수의 구성 블록

    Requires:
        numpy

    AIContext:
        AI 가 신호 트리거 인용 시 window size 명시 필수 (예: "20일 z-score").
        std=0 케이스 (모든 값 동일) 는 0 반환 — 신호 무효 의미.

    LLM Specifications:
        AntiPatterns: 단순 z-score 가 충분한 경우 (분포 stable) 에 호출 — 본 함수는
        시계열용. percentile 가 적합한 경우 (분포 비대칭) 에 호출 — percentileRank 권장.
        OutputSchema: np.ndarray, dtype=float64, 길이 == 입력.
        Prerequisites: period >= 2, len(values) >= period 권장.
        Freshness: stateless.
        Dataflow: list/np.ndarray → np.ndarray.
        TargetMarkets: 시계열 신호 · realized vol z · 가격 momentum 트리거.
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

    Capabilities:
        - 3 method (zscore/minmax/rank) — 도메인에 맞춰 선택
        - 모든 method 가 동일 길이 np.ndarray 반환
        - constant 입력 (max=min) 시 zeros 반환 (minmax)

    Args:
        values: 1D array-like.
        method: ``"zscore"`` (default), ``"minmax"`` (0~1 스케일), ``"rank"`` (분위 0~1).

    Returns:
        np.ndarray — 입력과 동일 길이.

    Raises:
        ValueError: 지원하지 않는 method.

    Example:
        >>> normalize([10.0, 20.0, 30.0], method="minmax")
        array([0. , 0.5, 1. ])
        >>> normalize([100, 200, 300], method="rank")
        array([0.33..., 0.67..., 1.  ])

    Guide:
        - zscore: 평균=0 기준 비교. 정규분포 가정.
        - minmax: [0, 1] 절대 스케일. visualization · ML feature scaling.
        - rank: 이상치 영향 0. 분위 비교 우선 도메인 (peer ranking).

    SeeAlso:
        - `zscore`: zscore method 의 단독 호출
        - `percentileRank`: rank method 의 단독 호출

    Requires:
        numpy

    AIContext:
        AI 가 method 결정 시: 정규분포 가정 가능 → zscore; 절대 범위 필요 → minmax;
        이상치 多 → rank. 인용 시 method 명시 권장.

    LLM Specifications:
        AntiPatterns: 미지원 method 호출 (ValueError); 입력 모두 동일값에 minmax 호출 → zeros (의미 X).
        OutputSchema: np.ndarray, dtype=float64, 길이 == 입력.
        Prerequisites: method ∈ {"zscore", "minmax", "rank"}.
        Freshness: stateless.
        Dataflow: list/np.ndarray → np.ndarray (method 분기 후 zscore/minmax/percentileRank 호출).
        TargetMarkets: 정규화 일반 — ML feature · 비교 · 시각화.
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
