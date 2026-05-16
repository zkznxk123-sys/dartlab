"""Event Study — Cumulative Abnormal Return (CAR) + Buy-and-Hold AR (BHAR).

학술 :
    - MacKinlay (1997, Journal of Economic Literature) — Event Study 방법론 표준
    - Brown & Warner (1985) — abnormal return 통계 검정

방법 :
    1. Estimation window (이벤트 -120 ~ -30 일) → 시장 모델 추정 α + β
    2. Event window (-5 ~ +5 일 등) → 실제 - 예측 = AR_t
    3. CAR = Σ AR_t (event window 합)
    4. BHAR = Π (1 + R_actual) - Π (1 + R_expected)

dartlab 활용 :
    - DART 공시 (실적 / 자본변동 / M&A) 후 abnormal drift 측정
    - 공시 유형 × regime 별 CAR distribution
    - PEAD 검증 (실적 발표 후 60~90일 drift)
"""

from __future__ import annotations

import numpy as np


def _marketModel(stockReturns: np.ndarray, marketReturns: np.ndarray) -> tuple[float, float, float]:
    """OLS α, β, σ_residual."""
    if len(stockReturns) < 20 or len(marketReturns) != len(stockReturns):
        return 0.0, 1.0, 0.01
    X = np.column_stack([np.ones(len(marketReturns)), marketReturns])
    try:
        beta, *_ = np.linalg.lstsq(X, stockReturns, rcond=None)
    except np.linalg.LinAlgError:
        return 0.0, 1.0, 0.01
    a, b = float(beta[0]), float(beta[1])
    resid = stockReturns - X @ beta
    sigma = float(resid.std(ddof=2))
    return a, b, max(sigma, 1e-6)


def calcCAR(
    stockReturns: np.ndarray,
    marketReturns: np.ndarray,
    *,
    eventIdx: int,
    estimationWindow: tuple[int, int] = (-120, -30),
    eventWindow: tuple[int, int] = (-5, 5),
) -> dict:
    """Cumulative Abnormal Return — MacKinlay (1997) 표준.

    Capabilities:
        - 시장 모델 (Sharpe-Lintner) 으로 expected return 추정
        - event window 동안 abnormal return 합 (CAR)
        - t-stat (CAR / SCAR_se) 통계 유의성

    AIContext:
        - Sprint 4 dartlab Korea-Native — DART 공시 자동 event study
        - story `eventStudyBlock` 후속 (공시 유형 × 평균 CAR)

    Args:
        stockReturns: 일별 종목 수익률 (전체 시계열).
        marketReturns: 일별 시장 수익률 (같은 길이).
        eventIdx: 이벤트 발생 일자 인덱스.
        estimationWindow: (시작, 끝) eventIdx 상대. 기본 (-120, -30).
        eventWindow: 기본 (-5, +5) — t-5 ~ t+5.

    Returns:
        dict
            eventIdx : int
            alpha / beta / sigma : float — 시장 모델 추정
            ar : np.ndarray — event window AR
            car : float — CAR
            scar : float — standardized CAR (= CAR / sqrt(L * sigma^2))
            tStat : float
            isSignificant : bool — |t| > 1.96
            interpretation : str

    Guide:
        MacKinlay (1997) event study 표준. estimationWindow (-120, -30) +
        eventWindow (-5, +5) 표준. |t| > 1.96 = 5% 유의.

    When:
        Quant event study + AI 공시 영향 답변.

    How:
        estimation window 에서 α/β 회귀 → eventWindow expected return →
        abnormal return → CAR + t-stat.

    Requires:
        stockReturns + marketReturns 동일 길이 + eventIdx 가 window 안.

    Raises:
        없음 — window out of range 시 error 키.

    Example:
        >>> r = calcCAR(stockR, marketR, eventIdx=120)
        >>> r["car"]
        0.045

    See Also:
        - calcEventSignal : 공시 이벤트 분류
        - labelTripleBarrier : ML 라벨링
    """
    n = len(stockReturns)
    est_lo = eventIdx + estimationWindow[0]
    est_hi = eventIdx + estimationWindow[1]
    ev_lo = eventIdx + eventWindow[0]
    ev_hi = eventIdx + eventWindow[1]
    if est_lo < 0 or ev_hi >= n:
        return {"error": "window out of range"}

    s_est = np.asarray(stockReturns[est_lo : est_hi + 1], dtype=np.float64)
    m_est = np.asarray(marketReturns[est_lo : est_hi + 1], dtype=np.float64)
    alpha, beta, sigma = _marketModel(s_est, m_est)

    s_ev = np.asarray(stockReturns[ev_lo : ev_hi + 1], dtype=np.float64)
    m_ev = np.asarray(marketReturns[ev_lo : ev_hi + 1], dtype=np.float64)
    expected = alpha + beta * m_ev
    ar = s_ev - expected
    car = float(ar.sum())
    L = len(ar)
    scar = car / (sigma * np.sqrt(L)) if sigma > 0 else 0.0

    return {
        "eventIdx": eventIdx,
        "alpha": round(alpha, 5),
        "beta": round(beta, 3),
        "sigma": round(sigma, 5),
        "ar": ar,
        "car": round(car, 4),
        "carPct": round(car * 100, 2),
        "scar": round(scar, 3),
        "tStat": round(scar, 3),
        "isSignificant": bool(abs(scar) > 1.96),
        "windowL": L,
        "interpretation": (
            f"event idx {eventIdx}, CAR {round(car * 100, 2)}% (L={L}d), "
            f"t={round(scar, 2)}. " + ("유의 abnormal drift." if abs(scar) > 1.96 else "통계 비유의.")
        ),
    }


def calcBHAR(
    stockReturns: np.ndarray,
    marketReturns: np.ndarray,
    *,
    eventIdx: int,
    holdWindow: int = 60,
) -> dict:
    """Buy-and-Hold Abnormal Return — Barber & Lyon (1997).

    BHAR = Π_t (1+R_stock) − Π_t (1+R_market)

    장기 holdWindow 에 적합 (장기 drift 검정).

    Args:
        stockReturns: 종목 일별 수익률.
        marketReturns: 시장.
        eventIdx: 이벤트 시점.
        holdWindow: 후속 보유 일수. 기본 ``60`` (3개월).

    Returns:
        dict — bhar, bhar_stock, bhar_market, interpretation
    """
    n = len(stockReturns)
    hi = eventIdx + holdWindow
    if hi >= n:
        return {"error": "window out of range"}
    s = stockReturns[eventIdx + 1 : hi + 1]
    m = marketReturns[eventIdx + 1 : hi + 1]
    if len(s) < 5:
        return {"error": "too few obs"}
    bhar_s = float(np.prod(1 + s) - 1)
    bhar_m = float(np.prod(1 + m) - 1)
    bhar = bhar_s - bhar_m
    return {
        "eventIdx": eventIdx,
        "holdWindow": holdWindow,
        "bharStock": round(bhar_s * 100, 2),
        "bharMarket": round(bhar_m * 100, 2),
        "bhar": round(bhar * 100, 2),
        "interpretation": (
            f"event {eventIdx} 후 {holdWindow}일 BHAR {round(bhar * 100, 2)}% "
            f"(종목 {round(bhar_s * 100, 1)}%, 시장 {round(bhar_m * 100, 1)}%)."
        ),
    }
