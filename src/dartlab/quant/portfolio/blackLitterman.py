"""Black-Litterman Portfolio Allocation — Black & Litterman (1992).

Mean-Variance 의 약점: μ 추정 noise → weights 극단화 + estimation error 폭증.

BL 해결 :
    1. *Equilibrium prior* μ_eq = δ · Σ · w_market (시장 균형 implied return)
    2. *Investor views* P · μ = q + ε,  ε ~ N(0, Ω)
    3. *Posterior* μ_BL = ((τΣ)^-1 + P^T Ω^-1 P)^-1 · ((τΣ)^-1 μ_eq + P^T Ω^-1 q)
    4. 사후 μ_BL → Mean-Variance 최적화

dartlab 사용 예시 :
    분석 엔진 판단 ("삼성전자 향후 1년 수익률 +15%") → view 로 입력.
    시장 시총 가중 prior + 분석 view 결합 → 포트폴리오.
"""

from __future__ import annotations

import numpy as np


def blackLittermanPosterior(
    *,
    cov: np.ndarray,
    marketWeights: np.ndarray,
    P: np.ndarray | None = None,
    q: np.ndarray | None = None,
    omega: np.ndarray | None = None,
    riskAversion: float = 2.5,
    tau: float = 0.05,
) -> dict:
    """Black-Litterman posterior expected returns.

    Capabilities:
        - Equilibrium implied return + investor views → posterior μ
        - View confidence (Ω) 자동 계산 (P τΣ P^T 비례)
        - 사후 평균 + 분산 둘다 반환

    AIContext:
        - Sprint 5 portfolio — dartlab 판단 서사 → view 로 직결
        - 시장 합의 + 사용자/AI view 합리적 결합

    Args:
        cov: N × N 종목 공분산 (Σ).
        marketWeights: 시장 시총 가중 (N,). 합=1.
        P: K × N view picking matrix (K 개의 view). None 이면 view 없음 (= prior).
        q: K × 1 view 기대수익 벡터. None 이면 0.
        omega: K × K view 신뢰도 (None 이면 P τΣ P^T 의 대각).
        riskAversion: δ (Sharpe slope). 기본 ``2.5``.
        tau: prior 신뢰도 스케일. 기본 ``0.05``.

    Returns:
        dict
            muEq : np.ndarray — implied equilibrium return
            muBL : np.ndarray — posterior expected return
            covBL : np.ndarray — posterior covariance (사후)
            weights : np.ndarray — μ_BL 기반 tangency portfolio
            interpretation : str

    Guide:
        Black-Litterman (1992) — 시장 합의 + view 합리적 결합. K=1 단순 view 부터
        K=N 풀 view 까지. riskAversion δ ≈ 2~3 (S&P 가정).

    When:
        Portfolio + AI view 기반 최적화 답변.

    How:
        equilibrium μ_eq = δΣw_mkt → view P/q/Ω 결합 → posterior μ_BL + cov_BL
        → tangency weights.

    Requires:
        cov N×N + marketWeights N (합=1). view 옵션.

    Raises:
        없음 — shape mismatch 시 error 키.

    Example:
        >>> r = blackLittermanPosterior(cov=cov, marketWeights=w)
        >>> r["weights"].sum()
        1.0

    See Also:
        - optimizeNCO : cluster 기반
        - optimizeMeanCVaR : CVaR 최소화
    """
    Sigma = np.asarray(cov, dtype=np.float64)
    w_mkt = np.asarray(marketWeights, dtype=np.float64)
    N = Sigma.shape[0]
    if Sigma.shape != (N, N) or w_mkt.shape != (N,):
        return {"error": "shape mismatch"}

    # Equilibrium implied return
    mu_eq = riskAversion * Sigma @ w_mkt

    if P is None or q is None:
        mu_bl = mu_eq
        cov_bl = Sigma * (1 + tau)
    else:
        P = np.asarray(P, dtype=np.float64)
        q = np.asarray(q, dtype=np.float64).reshape(-1)
        K = P.shape[0]
        if Omega := omega is not None:
            Omega = np.asarray(omega, dtype=np.float64)
        else:
            # default: diag(P τΣ P^T) — view 별 신뢰도 prior σ 비례
            Omega = np.diag(np.diag(P @ (tau * Sigma) @ P.T))
            Omega += np.eye(K) * 1e-8

        # Posterior
        tau_sig_inv = np.linalg.inv(tau * Sigma)
        omega_inv = np.linalg.inv(Omega)
        # M = (τΣ)^-1 + P^T Ω^-1 P
        M = tau_sig_inv + P.T @ omega_inv @ P
        # μ_BL = M^-1 ((τΣ)^-1 μ_eq + P^T Ω^-1 q)
        rhs = tau_sig_inv @ mu_eq + P.T @ omega_inv @ q
        mu_bl = np.linalg.solve(M, rhs)
        cov_bl = Sigma + np.linalg.inv(M)

    # Tangency portfolio: w = (δ Σ)^-1 μ
    try:
        w_unscaled = np.linalg.solve(riskAversion * cov_bl, mu_bl)
    except np.linalg.LinAlgError:
        w_unscaled = w_mkt

    # Long-only project + sum=1
    w = np.clip(w_unscaled, 0, None)
    if w.sum() > 0:
        w = w / w.sum()
    else:
        w = w_mkt

    return {
        "muEq": mu_eq,
        "muBL": mu_bl,
        "covBL": cov_bl,
        "weights": w,
        "n": N,
        "interpretation": (
            f"BL posterior μ ({N}종목), prior implied {round(float(mu_eq.mean() * 252 * 100), 2)}% → "
            f"posterior {round(float(mu_bl.mean() * 252 * 100), 2)}% (annualized 평균)."
        ),
    }


def buildSimpleViews(
    stockCodes: list[str],
    viewSpec: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """간단한 absolute view 빌더.

    예시 :
        viewSpec = {"005930": 0.15, "000660": -0.05}
        → P = [[1, 0, 0, ...], [0, 1, 0, ...]] (코드 인덱스 위치만 1)
        → q = [0.15, -0.05]

    Args:
        stockCodes: 전체 코드 순서.
        viewSpec: {stockCode: 연 기대수익률}.

    Returns:
        (P, q) — view picking matrix + 기대수익 벡터.
    """
    code_idx = {c: i for i, c in enumerate(stockCodes)}
    K = len(viewSpec)
    N = len(stockCodes)
    P = np.zeros((K, N), dtype=np.float64)
    q = np.zeros(K, dtype=np.float64)
    for k, (code, ret) in enumerate(viewSpec.items()):
        if code in code_idx:
            P[k, code_idx[code]] = 1.0
            # convert annual to daily
            q[k] = ret / 252
    return P, q
