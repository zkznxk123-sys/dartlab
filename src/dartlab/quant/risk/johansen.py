"""Johansen 다변량 공적분 검정 + VECM — Johansen (1988, 1991).

Engle-Granger 가 2변수 한정인 반면, Johansen 은 k 개 변수 공적분 rank 동시 추정.

VAR(p) :
    ΔY_t = Π Y_{t-1} + Σ Γ_i ΔY_{t-i} + ε_t

Π = αβ^T (rank r ≤ k 의 cointegrating space)
β^T Y_t = stationary spreads (r 개)

검정 :
    Trace test : H_0: rank(Π) ≤ r vs H_1: rank > r
    -T · Σ_{i=r+1}^k ln(1 - λ_i)

dartlab 활용 :
    3+ 자산 페어 트레이딩 (예: KOSPI200 sector 3사 공적분)
    pairsTrading.py 의 자연스러운 확장
"""

from __future__ import annotations

import numpy as np

# Johansen Trace test critical values (Osterwald-Lenum 1992) — k=1..5, no trend
_TRACE_CRIT_5PCT = {
    1: 3.84,
    2: 12.32 + 3.84,  # for r ≤ 0 in k=2
    # 다중 rank 별 정확 critical = OL Table 1 — 단순화 위해 first row 만 사용
}

# 더 정확한 critical values (OL 1992 Table 1, "no constant" specification)
_TRACE_CRIT_TABLE = {
    # k: [r=0 critical, r=1, r=2, ...]
    1: [3.84],
    2: [12.32, 3.84],
    3: [24.28, 12.32, 3.84],
    4: [40.17, 24.28, 12.32, 3.84],
    5: [60.06, 40.17, 24.28, 12.32, 3.84],
}


def johansenTest(Y: np.ndarray, *, lag: int = 1) -> dict:
    """Johansen 공적분 trace test.

    Capabilities:
        - k 개 변수의 공적분 rank 추정 (0 ≤ r ≤ k)
        - 각 가설 r 의 trace stat + 5% critical
        - β (cointegrating vectors) + α (loading) 추정
        - Engle-Granger 보다 powerful (다변량 동시)

    AIContext:
        - Sprint 6 risk — 3+ 자산 공적분 페어 트레이딩
        - calcPairs (Engle-Granger) 의 multi-asset 확장

    Args:
        Y: T × k 시계열 매트릭스 (k ≤ 5).
        lag: VAR lag order. 기본 ``1`` (= VECM lag 0).

    Returns:
        dict
            k : int
            t : int
            traceStats : np.ndarray — [r=0, r=1, ..., r=k-1] trace statistics
            critical5pct : list[float]
            cointRank : int — 추정 rank (5% level)
            beta : np.ndarray — k × cointRank cointegrating vectors
            eigenvalues : np.ndarray
            interpretation : str
    """
    Y = np.asarray(Y, dtype=np.float64)
    if Y.ndim != 2:
        return {"error": "Y must be 2D (T × k)"}
    T, k = Y.shape
    if k > 5:
        return {"error": "k > 5 not supported (critical table)"}
    if T < k * 20:
        return {"error": f"T ({T}) too small for k={k}"}

    # ΔY_t (T-1)
    dY = np.diff(Y, axis=0)
    Y_lag = Y[:-1]

    # If lag > 1, include ΔY_{t-1}, ..., ΔY_{t-lag+1} as regressors
    if lag > 1:
        regressors = []
        for ll in range(1, lag):
            regressors.append(np.roll(dY, ll, axis=0))
        Z = np.column_stack(regressors)[lag - 1 :]
        dY_eff = dY[lag - 1 :]
        Y_lag_eff = Y_lag[lag - 1 :]
    else:
        Z = None
        dY_eff = dY
        Y_lag_eff = Y_lag

    # Concentrate out Z by regression
    if Z is not None and Z.shape[0] > 0:
        ZtZ_inv = np.linalg.inv(Z.T @ Z + np.eye(Z.shape[1]) * 1e-8)
        proj = np.eye(Z.shape[0]) - Z @ ZtZ_inv @ Z.T
        R0 = proj @ dY_eff
        R1 = proj @ Y_lag_eff
    else:
        R0 = dY_eff
        R1 = Y_lag_eff

    n = R0.shape[0]
    S00 = (R0.T @ R0) / n
    S01 = (R0.T @ R1) / n
    S10 = (R1.T @ R0) / n
    S11 = (R1.T @ R1) / n

    # Generalized eigenvalue problem: |λ S11 - S10 S00^-1 S01| = 0
    try:
        S00_inv = np.linalg.inv(S00 + np.eye(k) * 1e-10)
        S11_inv_sqrt = np.linalg.cholesky(S11 + np.eye(k) * 1e-10)
        # Standard form: M = S11^{-1/2} S10 S00^-1 S01 S11^{-1/2}
        # eigvals λ_i ≤ 1
        try:
            inv_chol = np.linalg.inv(S11_inv_sqrt)
        except np.linalg.LinAlgError:
            return {"error": "S11 inversion failed"}
        M = inv_chol @ S10 @ S00_inv @ S01 @ inv_chol.T
        eig_vals, eig_vecs = np.linalg.eigh(M)
        # 내림차순 정렬
        order = eig_vals.argsort()[::-1]
        eig_vals = np.clip(eig_vals[order], 0, 1 - 1e-12)
        eig_vecs = eig_vecs[:, order]
    except np.linalg.LinAlgError:
        return {"error": "eigendecomposition failed"}

    # Trace stats
    trace_stats = np.zeros(k)
    for r in range(k):
        trace_stats[r] = -n * np.sum(np.log(1 - eig_vals[r:]))

    crit = _TRACE_CRIT_TABLE.get(k, [3.84] * k)

    # cointRank: 첫 번째 r 인데 trace_stats[r] ≤ critical[r] (수락)
    coint_rank = 0
    for r in range(k):
        if trace_stats[r] > crit[r]:
            coint_rank = r + 1
        else:
            break

    # β (cointegrating vectors) = S11^{-1/2} eig_vecs[:, :coint_rank]
    beta = inv_chol.T @ eig_vecs[:, :coint_rank] if coint_rank > 0 else np.zeros((k, 0))

    return {
        "k": k,
        "t": int(n),
        "traceStats": np.round(trace_stats, 3),
        "critical5pct": [round(c, 2) for c in crit],
        "cointRank": int(coint_rank),
        "beta": beta,
        "eigenvalues": np.round(eig_vals, 4),
        "interpretation": (
            f"k={k}, T={int(n)}, cointRank={coint_rank}. "
            f"trace stats {np.round(trace_stats, 1).tolist()} vs critical {[round(c, 1) for c in crit]}. "
            + (f"{coint_rank} 개 공적분 관계 발견." if coint_rank > 0 else "공적분 없음.")
        ),
    }


def calcVECM(Y: np.ndarray, *, lag: int = 1, cointRank: int | None = None) -> dict:
    """VECM — Johansen 공적분 + 단기 조정 동학 (α, β, spreads).

    Capabilities:
        다변량 시계열 Y 를 Johansen test 로 공적분 rank 자동 추정 후, 적응 loadings (α) 와
        공적분 벡터 (β), 정상 spread 시계열 (β^T Y) 을 산출. 페어 트레이딩·환율-금리 균형
        분석·구조방정식 추정에 사용.

    Parameters
    ----------
    Y : np.ndarray
        T × k 다변량 시계열 (T 행, k 변수).
    lag : int, default 1
        VAR lag 수.
    cointRank : int | None, default None
        공적분 rank 명시. None 이면 johansenTest 자동 추정.

    Returns
    -------
    dict
        beta : np.ndarray — k × r 공적분 벡터
        alpha : np.ndarray — k × r 적응 loadings
        spreads : np.ndarray — T × r 정상 spread 시계열
        cointRank : int — 사용된 rank
        interpretation : str — 평균 회귀 속도 + spread variance 요약
        rank=0 또는 johansen 오류 시 {"error": str}.

    Raises
    ------
    없음 (오류는 dict["error"]).

    Example
    -------
    >>> r = calcVECM(Y, lag=2)
    >>> r["cointRank"], r["interpretation"]
    (1, 'VECM rank=1. 평균 회귀 속도 (α 평균) = 0.082, ...')

    Guide
    -----
    ΔY_t = αβ^T Y_{t-1} + Σ Γ ΔY_{t-i} + ε 의 1 차 근사. α 작을수록 회귀 느림. spread 의
    표준편차가 작으면 페어 트레이드 후보 (mean-reverting strong).

    See Also:
        - ``dartlab.quant.risk.johansen.johansenTest`` : 공적분 rank 검정
        - ``dartlab.quant.risk.bubbleTest.calcGSADF`` : 비정상성 (버블) 진단

    When:
        페어 트레이딩 + 환율-금리 균형 진단 + AI 균형 관계 답변.

    How:
        johansenTest → β/α 추정 → spreads = β^T Y → 평균 회귀 속도 평가.

    Requires:
        시계열 T > 50 + 변수 간 공적분 가능성 (단위근 변수).

    AIContext
    ---------
    "두 시계열이 균형 관계 있나" 답변에 사용. cointRank>0 이면 균형 존재 + α 크기로 회귀 속도
    인용. rank=0 = 균형 없음으로 답변하고 단변량 추세 분석으로 전환.
    """
    Y = np.asarray(Y, dtype=np.float64)
    jr = johansenTest(Y, lag=lag)
    if "error" in jr:
        return jr

    r = cointRank if cointRank is not None else jr["cointRank"]
    if r == 0:
        return {"error": "no cointegration — VECM 불가"}

    beta = jr["beta"][:, :r] if jr["beta"].shape[1] >= r else jr["beta"]
    spreads = Y @ beta  # T × r

    # α 추정: ΔY_t = α (β^T Y_{t-1}) + ε  → OLS
    dY = np.diff(Y, axis=0)
    z = Y[:-1] @ beta  # T-1 × r
    # α (k × r) = (Z^T Z)^-1 Z^T ΔY  의 transpose
    try:
        ZTZ_inv = np.linalg.inv(z.T @ z + np.eye(r) * 1e-10)
        alpha = (ZTZ_inv @ z.T @ dY).T  # k × r
    except np.linalg.LinAlgError:
        alpha = np.zeros((Y.shape[1], r))

    return {
        "beta": beta,
        "alpha": alpha,
        "spreads": spreads,
        "cointRank": r,
        "interpretation": (
            f"VECM rank={r}. 평균 회귀 속도 (α 평균) = "
            f"{round(float(np.mean(np.abs(alpha))), 4)}, "
            f"spread variance ratio = {round(float(np.std(spreads, axis=0).mean()), 4)}"
        ),
    }
