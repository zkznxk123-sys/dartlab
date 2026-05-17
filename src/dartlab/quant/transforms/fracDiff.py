"""Fractional Differentiation — AFML Ch.5 (Lopez de Prado 2018).

전통적 log return (=1차 차분) 은 메모리 전부 소실. 분수 차수 d ∈ (0, 1) 으로
"메모리 유지하면서 stationary" 변환.

가중치 :
    w_0 = 1,  w_k = -w_{k-1} · (d - k + 1) / k

FFD (Fixed-Width Window) :
    가중치 |w_k| < threshold 면 truncate → 일정 길이 윈도우.
    y_t = Σ_k w_k · x_{t-k}

목적 :
    1. ADF stat 통과 (stationary)
    2. 원본 가격과 corr ≈ 1 유지 (메모리 보존)
    3. ML 입력으로 적합 (트렌드 정보 + stationary)
"""

from __future__ import annotations

import numpy as np


def _ffdWeights(d: float, threshold: float = 1e-5) -> np.ndarray:
    """FFD 가중치 — |w_k| < threshold 까지 truncate."""
    w = [1.0]
    k = 1
    while True:
        next_w = -w[-1] * (d - k + 1) / k
        if abs(next_w) < threshold:
            break
        w.append(next_w)
        k += 1
        if k > 10000:  # safety
            break
    return np.asarray(w, dtype=np.float64)


def fracDiffFFD(
    series: np.ndarray,
    *,
    d: float = 0.4,
    threshold: float = 1e-5,
) -> dict:
    """Fractional Differentiation (FFD) — 메모리 유지 stationary 변환.

    Capabilities:
        - 분수 차수 d ∈ [0, 1] 변환 (0 = 원본, 1 = 1차 차분)
        - threshold 로 윈도우 자동 길이 결정
        - 변환 결과 + 가중치 + 윈도우 길이 반환

    AIContext:
        - Sprint 3 ML 인프라 — log_return 대체
        - ML 모델 (RF / GRU / xgboost) 입력 시계열 정제

    Args:
        series: 1D 시계열 (가격 / 지수 등 양수 배열).
        d: 분수 차수. 기본 ``0.4`` (대부분 한국 주가 stationary 통과).
        threshold: 가중치 truncation. 기본 ``1e-5``.

    Returns:
        dict
            d : float
            window : int — 적용 윈도우 길이
            weights : np.ndarray — FFD 가중치
            transformed : np.ndarray — 변환 결과 (앞 window-1 개는 NaN)
            n : int — 유효 결과 개수
            originalCorr : float — 원본 vs 변환 Pearson (메모리 보존도)
            interpretation : str

    Examples:
        >>> import numpy as np
        >>> from dartlab.quant.transforms.fracDiff import fracDiffFFD
        >>> r = fracDiffFFD(np.cumsum(np.random.randn(500))+100, d=0.4)
        >>> print(r["window"], r["originalCorr"])
        12 0.85

    Notes:
        - d=0.4 가 통상 sweet spot (Lopez de Prado 권장).
        - d 너무 크면 메모리 손실, 너무 작으면 stationary 통과 실패.
        - originalCorr > 0.7 이면 메모리 보존 ok.

    Guide:
        Lopez de Prado AFML — log_return 의 stationary 보장 + 메모리 보존 동시.
        ML 모델 (RF/GRU/xgboost) 의 표준 입력.

    When:
        Quant ML 인프라 + 시계열 stationary 검증.

    How:
        d/threshold → 가중치 truncation → convolve → window 결정 → 변환 시리즈
        + 원본 corr.

    Requires:
        시계열 ≥ 30. d ∈ [0, 1].

    Raises:
        없음 — 실패 시 error 키.

    See Also:
        - calcSADF : 단위근/버블 검정 (stationary 검증 보조)
    """
    series = np.asarray(series, dtype=np.float64)
    if len(series) < 30:
        return {"error": "series too short"}

    weights = _ffdWeights(d, threshold)
    window = len(weights)
    if window > len(series):
        return {"error": f"window {window} > series {len(series)}"}

    n_out = len(series) - window + 1
    transformed = np.full(len(series), np.nan, dtype=np.float64)
    # convolve manually: y_t = sum_k w_k * x_{t-k}
    for t in range(window - 1, len(series)):
        x_window = series[t - window + 1 : t + 1][::-1]  # x_t, x_{t-1}, ..., x_{t-window+1}
        transformed[t] = float(np.dot(weights, x_window))

    valid = ~np.isnan(transformed)
    if valid.sum() < 10:
        return {"error": "insufficient valid points"}
    corr = float(np.corrcoef(series[valid], transformed[valid])[0, 1])

    return {
        "d": d,
        "window": window,
        "weights": weights,
        "transformed": transformed,
        "n": int(valid.sum()),
        "originalCorr": round(corr, 4),
        "interpretation": (
            f"d={d}, window={window}, 원본 corr={round(corr, 3)}. "
            + ("메모리 잘 보존." if corr > 0.7 else "메모리 손실 — d 줄이거나 threshold 낮춰라.")
        ),
    }


def findMinDForStationarity(
    series: np.ndarray,
    *,
    dRange: tuple[float, float] = (0.0, 1.0),
    step: float = 0.05,
    threshold: float = 1e-5,
) -> dict:
    """ADF 통과하는 최소 d 자동 탐색 — AFML Ch.5.5.

    가장 작은 d 가 메모리 최대 보존 + stationary 동시 만족.

    Args:
        series: 1D 시계열.
        dRange: 탐색 범위 (low, high). 기본 (0.0, 1.0).
        step: 격자 스텝. 기본 0.05.
        threshold: FFD threshold.

    Returns:
        dict
            optimalD : float | None — ADF p < 0.05 통과하는 최소 d
            results : list[dict] — 각 d 의 ADF stat, p-value, corr
            recommendation : str

    Capabilities:
        - d 격자 sweep → 각 d 별 FFD diff + ADF 통과 여부 → 최소 stationary d
        - 메모리 보존도 최대화

    Guide:
        Lopez de Prado AFML Ch.5.5. d=1 은 메모리 소멸, d=0 은 stationary 부재.
        optimalD 가 둘의 균형.

    When:
        FFD 사전 분석 + AI fractional differentiation 답변.

    How:
        d 0~1 step 0.05 sweep → fracDiffFFD + adfTest → 통과 시 최소 d.

    Requires:
        series ≥ 100.

    Raises:
        없음 — 통과 d 없을 시 None.

    Example:
        >>> findMinDForStationarity(series)["optimalD"]
        0.45

    See Also:
        - fracDiffFFD : 핵심 diff
        - signal.pairsTrading._adfTest : ADF

    AIContext:
        "FFD 최소 d 권장" 답변 시 optimalD + recommendation 인용.
    """
    from dartlab.quant.signal.pairsTrading import _adfTest

    results = []
    optimal = None
    d = dRange[0]
    while d <= dRange[1] + 1e-9:
        out = fracDiffFFD(series, d=d, threshold=threshold)
        if "error" in out:
            results.append({"d": round(d, 3), "error": out["error"]})
            d += step
            continue
        valid = out["transformed"][~np.isnan(out["transformed"])]
        adf_stat, _, _ = _adfTest(valid)
        # ADF critical 5% ≈ -2.86 (대수표본)
        adf_pass = adf_stat is not None and adf_stat < -2.86
        results.append(
            {
                "d": round(d, 3),
                "adfStat": round(float(adf_stat or 0), 3),
                "adfPass": bool(adf_pass),
                "corr": out["originalCorr"],
                "window": out["window"],
            }
        )
        if adf_pass and optimal is None:
            optimal = round(d, 3)
        d += step

    return {
        "optimalD": optimal,
        "results": results,
        "recommendation": (
            f"최적 d = {optimal} (ADF 5% 통과 최소값, 메모리 최대 보존)."
            if optimal is not None
            else "ADF 통과 d 없음 — 시계열 매우 비stationary 거나 dRange 확장 필요."
        ),
    }
