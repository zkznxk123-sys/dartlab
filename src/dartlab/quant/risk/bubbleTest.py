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
    """SADF (Supremum ADF) — 단일 버블 시점 탐지 (Phillips-Shi-Yu 2015).

    Capabilities:
        가격 시계열의 log 변환 후 sliding right-end window 로 ADF 통계량을 계산하고 최댓값을
        SADF stat 으로 사용. 5% critical value (1.49, n=400 근사) 대비 초과 여부로 버블 유의성
        판정 + 피크 시점 반환. 단일 버블에 특화.

    Parameters
    ----------
    series : np.ndarray
        1D 가격 시계열 (양수, log scale 권장). 모든 값 > 0 필요 (음수/0 입력 시 error).
    minWindowFrac : float, default 0.1
        최소 window 비율 (전체의 10%). 너무 작으면 ADF 분포 왜곡.

    Returns
    -------
    dict
        n : int — 시계열 길이
        adfSeries : np.ndarray — sliding window ADF stat 시계열 (앞부분 NaN)
        sadfStat : float — ADF series 최댓값 (SADF)
        sadfPeakIdx : int — 최대 ADF 시점 (버블 피크)
        critical5pct : float — 5% critical value (n 보정 후)
        isBubble : bool — sadfStat > critical5pct 여부
        interpretation : str — 한 줄 해석 문장
        잘못된 입력 시 {"error": str}.

    Raises
    ------
    없음 (오류는 dict["error"]).

    Example
    -------
    >>> import numpy as np
    >>> prices = np.exp(np.cumsum(np.random.normal(0.001, 0.02, 200)))
    >>> r = calcSADF(prices)
    >>> r["isBubble"], r["sadfStat"]
    (False, 0.42)

    Guide
    -----
    Phillips-Shi-Yu 2015 Table 1 critical values 사용. finite-sample 보정으로 작은 n 에서
    +50/n 보수 가산. 단일 버블만 탐지 — 다중 버블/시작-종료 시점은 calcGSADF 사용.

    SeeAlso
    -------
    - ``dartlab.quant.risk.bubbleTest.calcGSADF`` : 다중 버블 + 시작/종료 spans
    - ``dartlab.quant.risk.tailrisk.calcTailrisk`` : 꼬리 위험

    Requires
    --------
    - 시계열 길이 ≥ 30
    - 모든 가격 > 0 (log 변환 가능)

    AIContext
    ---------
    "지금 거품 같은데" 정성적 답변의 1 차 검증. isBubble True 면 sadfPeakIdx 시점을 함께 인용해
    "X 일 전 피크" 식 시점 답변. False 면 단일 버블 미감지 — calcGSADF 로 후속 검증 권장.
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
    """GSADF — 다중 버블 + 시작/종료 시점 탐지 (Phillips-Shi-Yu 2015).

    Capabilities:
        각 right-end r_2 에서 left-end r_1 을 [0, r_2-r_0] 범위로 sweep 하며 ADF 최대를 BSADF
        sequence 로 누적, 5% critical 초과 구간을 bubbleSpans 로 묶어 반환. 다중 버블·여러
        episode 의 정확한 시작/종료 시점을 단일 호출로.

    Parameters
    ----------
    series : np.ndarray
        1D 가격 시계열 (양수). log 자동 변환.
    minWindowFrac : float, default 0.1
        최소 window 비율.

    Returns
    -------
    dict
        n : int — 시계열 길이
        bsadfSeries : np.ndarray — BSADF stat 시계열
        gsadfStat : float — bsadf 최댓값
        critical5pct : float — 5% critical (n 보정)
        bubbleSpans : list[tuple[int,int]] — [(start_idx, end_idx), ...] 5% 초과 구간
        interpretation : str
        잘못된 입력 시 {"error": str}.

    Raises
    ------
    없음 (오류는 dict["error"]).

    Example
    -------
    >>> r = calcGSADF(prices)
    >>> r["bubbleSpans"]
    [(120, 145), (200, 215)]

    Guide
    -----
    SADF 가 "전체 시계열 중 단일 버블" 만 잡는다면 GSADF 는 multi-episode 감지에 강함. 한
    series 안의 여러 버블·진정 사이클 분석에 적합.

    SeeAlso
    -------
    - ``dartlab.quant.risk.bubbleTest.calcSADF`` : 단일 버블

    Requires
    --------
    - 시계열 길이 ≥ 50
    - 모든 가격 > 0

    AIContext
    ---------
    여러 버블 시점을 나열한 답변에 사용. bubbleSpans 빈 리스트면 "거품 감지 없음" 명시.
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
