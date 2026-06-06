"""Event Study 공용 계산.

analysis와 quant가 함께 쓰는 CAR/BHAR 계산을 L1.5 synth에 둔다.
"""

from __future__ import annotations

import numpy as np


def _marketModel(stockReturns: np.ndarray, marketReturns: np.ndarray) -> tuple[float, float, float]:
    """OLS alpha, beta, residual sigma."""
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
    """Cumulative Abnormal Return - MacKinlay event-study 표준."""
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
    """Buy-and-Hold Abnormal Return."""
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
