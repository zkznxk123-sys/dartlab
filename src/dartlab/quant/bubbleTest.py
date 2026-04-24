"""SADF / GSADF 버블 탐지 — Phillips-Shi-Yu (2015, International Economic Review).

ADF 의 supremum/sliding-window 버전 = 폭발 단위근 (explosive root) 탐지.

SADF (Supremum ADF) :
    각 r_2 ∈ [r_0, 1] 에 대해 ADF 검정 (window [0, r_2])
    SADF = sup ADF(r_2)

GSADF (Generalized SADF) :
    각 (r_1, r_2) 쌍에 대해 ADF, sup over (r_1, r_2)
    더 robust 하게 다중 버블 탐지

해석 :
    SADF > critical (= 1.49 at 5%) → 버블 (폭발 단위근) 통계적 유의
    BSADF time series → 버블 시작/종료 시점 탐지

dartlab 활용 :
    한국 시장 KOSPI/코스닥 주가 버블 실시간 탐지
    개별 종목 버블 (특히 테마주) 진단
"""

from __future__ import annotations

import numpy as np


def _adfStat(y: np.ndarray) -> float:
    """단순 ADF (no constant trend) — Δy_t = β·y_{t-1} + ε."""
    n = len(y)
    if n < 10:
        return float("nan")
    dy = np.diff(y)
    x_lag = y[:-1]
    X = np.column_stack([np.ones(n - 1), x_lag])
    try:
        beta, *_ = np.linalg.lstsq(X, dy, rcond=None)
    except np.linalg.LinAlgError:
        return float("nan")
    b = float(beta[1])
    resid = dy - X @ beta
    mse = float(np.sum(resid**2) / max(n - 3, 1))
    x_var = float(np.sum((x_lag - x_lag.mean()) ** 2))
    if x_var <= 0:
        return float("nan")
    se = np.sqrt(mse / x_var)
    return b / se if se > 0 else 0.0


def calcSADF(
    series: np.ndarray,
    *,
    minWindowFrac: float = 0.1,
) -> dict:
    """SADF (Supremum ADF) — 단일 버블 시점 탐지.

    Capabilities:
        - ADF series for sliding right-end window
        - 최대값 = SADF stat
        - critical value comparison

    AIContext:
        - Sprint 6 risk — 한국 시장 버블 진단
        - SADF > 1.49 (5% critical, n=400) → 버블 유의
        - review `bubbleBlock` 후속

    Args:
        series: 1D 가격 (양수, log scale 권장).
        minWindowFrac: 최소 window 비율. 기본 ``0.1`` (전체 10%).

    Returns:
        dict
            n : int
            adfSeries : np.ndarray — ADF stat 시계열
            sadfStat : float
            sadfPeakIdx : int — 최대 ADF 시점
            critical5pct : float — 1.49 (n=400 근사)
            isBubble : bool
            interpretation : str

    Notes:
        - Critical values 는 Phillips-Shi-Yu 2015 Table 1 근사.
        - 작은 n 에서는 finite-sample 보정 필요 (here: 0.5 보수적 가산).
    """
    y = np.asarray(series, dtype=np.float64)
    if (y <= 0).any():
        return {"error": "series must be positive"}
    log_y = np.log(y)
    n = len(log_y)
    if n < 30:
        return {"error": "n < 30"}

    r0 = max(int(n * minWindowFrac), 10)
    adf_series = np.full(n, np.nan, dtype=np.float64)
    for r2 in range(r0, n + 1):
        stat = _adfStat(log_y[:r2])
        adf_series[r2 - 1] = stat

    valid = ~np.isnan(adf_series)
    if valid.sum() == 0:
        return {"error": "no valid ADF stats"}
    sadf = float(np.nanmax(adf_series))
    peak_idx = int(np.nanargmax(adf_series))
    crit = 1.49 + (50 / max(n, 1))  # finite-sample crude adjust
    is_bubble = sadf > crit

    return {
        "n": n,
        "adfSeries": adf_series,
        "sadfStat": round(sadf, 3),
        "sadfPeakIdx": peak_idx,
        "critical5pct": round(crit, 2),
        "isBubble": bool(is_bubble),
        "interpretation": (
            f"SADF={round(sadf, 2)} (5% critical {round(crit, 2)}). "
            + (f"버블 유의 (peak idx {peak_idx})." if is_bubble else "버블 미감지.")
        ),
    }


def calcGSADF(
    series: np.ndarray,
    *,
    minWindowFrac: float = 0.1,
) -> dict:
    """GSADF — 다중 버블 + 시작/종료 시점 탐지.

    각 r_2 에 대해 r_1 ∈ [0, r_2 - r_0] sup ADF.
    BSADF[r_2] = max_{r_1} ADF(r_1, r_2)

    Returns:
        dict — bsadfSeries / gsadfStat / bubbleSpans
    """
    y = np.asarray(series, dtype=np.float64)
    if (y <= 0).any():
        return {"error": "series must be positive"}
    log_y = np.log(y)
    n = len(log_y)
    if n < 50:
        return {"error": "n < 50"}

    r0 = max(int(n * minWindowFrac), 20)
    bsadf = np.full(n, np.nan, dtype=np.float64)
    for r2 in range(r0, n + 1):
        best = -np.inf
        for r1 in range(0, r2 - r0 + 1):
            stat = _adfStat(log_y[r1:r2])
            if not np.isnan(stat) and stat > best:
                best = stat
        bsadf[r2 - 1] = best if best > -np.inf else np.nan

    valid = ~np.isnan(bsadf)
    if valid.sum() == 0:
        return {"error": "no valid BSADF"}
    gsadf = float(np.nanmax(bsadf))
    crit = 1.79 + (50 / max(n, 1))  # GSADF critical higher than SADF

    # bubble spans: consecutive index where BSADF > crit
    spans = []
    in_bubble = False
    start = None
    for i, b in enumerate(bsadf):
        if not np.isnan(b) and b > crit:
            if not in_bubble:
                start = i
                in_bubble = True
        else:
            if in_bubble:
                spans.append((start, i - 1))
                in_bubble = False
    if in_bubble:
        spans.append((start, n - 1))

    return {
        "n": n,
        "bsadfSeries": bsadf,
        "gsadfStat": round(gsadf, 3),
        "critical5pct": round(crit, 2),
        "bubbleSpans": spans,
        "interpretation": (
            f"GSADF={round(gsadf, 2)} (5% critical {round(crit, 2)}). 버블 구간 {len(spans)}건: {spans[:3]}"
        ),
    }
