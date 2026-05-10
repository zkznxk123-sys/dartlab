"""Mean-CVaR Portfolio Optimization — Rockafellar-Uryasev (2000).

Mean-Variance 의 부족: variance 는 양/음 변동 동등 페널티. 실무는 *손실* 만 회피.

CVaR (Conditional Value at Risk) :
    CVaR_α(R) = E[ R | R ≤ VaR_α ]

Rockafellar-Uryasev (2000) Linear Programming 으로 해결.

dartlab 단순화 (numpy-only) :
    Sample-based scenario CVaR 최적화 — historical returns sample 사용,
    가중평균 손실 분포의 left tail expected value 최소화.

대안: optimizeMeanVar (variance 기반) — 정상 분포 가정 잘 안 맞을 때 CVaR 우위.
"""

from __future__ import annotations

import numpy as np


def optimizeMeanCVaR(
    returns: np.ndarray,
    *,
    alpha: float = 0.05,
    targetReturn: float | None = None,
    longOnly: bool = True,
    maxWeight: float = 0.25,
) -> dict:
    """Mean-CVaR 최적화 — Rockafellar-Uryasev sample-based.

    Capabilities:
        - 샘플 시나리오 기반 CVaR 최소화 (95% / 99% tail 평균 손실)
        - long-only + max weight 제약
        - target return constraint (optional)
        - numpy-only (cvxpy 의존 없이 projected gradient + barrier)

    AIContext:
        - Sprint 5 portfolio — variance 대체 risk metric
        - dartlab 판단 서사: "VaR 5% 일 때 CVaR -3.2% — 평균 -2% 손실 허용"

    Args:
        returns: T × N 일별 수익률 매트릭스 (N 종목, T 관측).
        alpha: tail 비율. 기본 ``0.05`` (95% CVaR).
        targetReturn: 최소 기대수익률 (일별). None 이면 무제약 (min CVaR).
        longOnly: long-only 강제.
        maxWeight: 단일 종목 max 비중. 기본 ``0.25``.

    Returns:
        dict
            weights : np.ndarray — 최적 비중 (합=1)
            expectedReturn : float — 일별 (annualized × 252)
            cvar : float — α-CVaR (음수, 손실)
            var : float — α-VaR
            interpretation : str

    Notes:
        - Projected Gradient + soft barrier — 정확한 LP 아님, 근사. cvxpy 미사용.
        - 결과는 sample CVaR (overfit 위험). out-of-sample 검증 필수.
    """
    R = np.asarray(returns, dtype=np.float64)
    if R.ndim != 2 or R.shape[1] < 2:
        return {"error": "returns must be T × N with N ≥ 2"}
    T, N = R.shape
    if T < 30:
        return {"error": "T < 30 — too few scenarios"}

    mu = R.mean(axis=0)

    # 초기화: Equal Weight
    w = np.ones(N) / N

    def cvar(weights: np.ndarray) -> float:
        """cvar — TODO 한국어 동작 설명."""
        port = R @ weights
        var_thresh = np.quantile(port, alpha)
        tail = port[port <= var_thresh]
        return -float(tail.mean()) if len(tail) > 0 else 0.0

    # Projected gradient descent (단순)
    lr = 0.005
    n_iter = 500
    best_w = w.copy()
    best_obj = float("inf")

    for _it in range(n_iter):
        eps = 1e-5
        port = R @ w
        var_thresh = np.quantile(port, alpha)
        tail_mask = port <= var_thresh

        # gradient of CVaR ≈ -mean(R[tail_mask], axis=0)
        if tail_mask.sum() > 0:
            grad = -R[tail_mask].mean(axis=0)
        else:
            grad = -mu

        # target return constraint (penalty)
        if targetReturn is not None and (w @ mu < targetReturn):
            grad -= 2.0 * (targetReturn - w @ mu) * mu

        w = w - lr * grad
        # project: long-only + max weight + sum=1
        w = np.clip(w, 0 if longOnly else -maxWeight, maxWeight)
        s = w.sum()
        if s > 0:
            w = w / s
        else:
            w = np.ones(N) / N

        obj = cvar(w)
        if obj < best_obj:
            best_obj = obj
            best_w = w.copy()

    port = R @ best_w
    var_thresh = float(np.quantile(port, alpha))
    tail = port[port <= var_thresh]
    cvar_val = float(tail.mean()) if len(tail) > 0 else 0.0
    exp_ret = float(best_w @ mu)

    return {
        "weights": best_w,
        "expectedReturn": round(exp_ret, 6),
        "expectedReturnAnnual": round(exp_ret * 252, 4),
        "cvar": round(cvar_val, 6),
        "cvarAnnual": round(cvar_val * np.sqrt(252), 4),
        "var": round(var_thresh, 6),
        "alpha": alpha,
        "n": N,
        "interpretation": (
            f"N={N}, T={T}, α={alpha} → CVaR={round(cvar_val * 100, 2)}% (일별), "
            f"VaR={round(var_thresh * 100, 2)}%, 기대수익 연 {round(exp_ret * 252 * 100, 1)}%."
        ),
    }
