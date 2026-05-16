"""포트폴리오 최적화 — MVO + HRP + 리스크 버짓팅.

학술 근거:
- Markowitz (1952): Portfolio Selection
- Ledoit & Wolf (2003): Honey, I Shrunk the Sample Covariance Matrix
- Lopez de Prado (2016): Hierarchical Risk Parity
- Maillard et al. (2010): Equal Risk Contribution
"""

from __future__ import annotations

import logging

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.portfolio._optimizeAdvanced import _hierarchicalCluster, _recursiveBisection
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays

# ── 공분산 추정 ──────────────────────────────────────────


def _ledoitWolfShrinkage(returns: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf (2003) 공분산 수축.

    sample covariance를 (1-δ)*sample + δ*target 으로 수축.
    target = 평균 분산 × 단위행렬 (constant correlation 단순화).

    Returns:
        (shrunk_cov, delta) — annualized 아님 (호출자가 ×252)
    """
    t, n = returns.shape
    sample = np.cov(returns.T, ddof=1)

    # target: μ × I, μ = 평균 대각
    mu = float(np.trace(sample) / n)
    target = mu * np.eye(n)

    # 분자: π = Σ Var(x_i x_j)
    centered = returns - returns.mean(axis=0)
    pi_mat = np.zeros((n, n))
    for k in range(t):
        z = np.outer(centered[k], centered[k]) - sample
        pi_mat += z * z
    pi_mat /= t
    pi = float(pi_mat.sum())

    # 분모: γ = ||sample - target||²_F
    gamma = float(np.sum((sample - target) ** 2))

    if gamma <= 0:
        delta = 0.0
    else:
        kappa = pi / gamma
        delta = max(0.0, min(1.0, kappa / t))

    shrunk = (1 - delta) * sample + delta * target
    return shrunk, delta


# ── Active-set QP (long-only) ────────────────────────────


def _activesetMinvar(cov: np.ndarray, maxIter: int = 50) -> np.ndarray:
    """Long-only Min-Variance via active-set algorithm.

    음수 가중치가 발생하면 그 자산을 active set에서 제거하고 재계산. 수렴 보장.
    종목 수가 작으면(≤12) enumeration으로 globally optimal 보장.
    """
    n = cov.shape[0]

    if n <= 12:
        # Enumeration: 모든 비공집합에서 unconstrained 풀고 최선 선택
        best_w = None
        best_var = np.inf
        for mask in range(1, 1 << n):
            idx = [i for i in range(n) if mask & (1 << i)]
            sub = cov[np.ix_(idx, idx)]
            try:
                inv = np.linalg.inv(sub)
            except np.linalg.LinAlgError:
                inv = np.linalg.pinv(sub)
            ones = np.ones(len(idx))
            w_sub = inv @ ones / (ones @ inv @ ones)
            if (w_sub < -1e-10).any():
                continue
            var = float(w_sub @ sub @ w_sub)
            if var < best_var:
                best_var = var
                w = np.zeros(n)
                for k, i in enumerate(idx):
                    w[i] = w_sub[k]
                best_w = w
        return best_w if best_w is not None else (np.ones(n) / n)

    # n > 12: iterative active-set
    active = list(range(n))
    for _ in range(maxIter):
        sub = cov[np.ix_(active, active)]
        try:
            inv = np.linalg.inv(sub)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(sub)
        ones = np.ones(len(active))
        w_sub = inv @ ones / (ones @ inv @ ones)
        # 가장 음수인 항목을 active에서 제거
        if (w_sub < -1e-10).any():
            worst = active[int(np.argmin(w_sub))]
            active.remove(worst)
            if not active:
                break
            continue
        w = np.zeros(n)
        for k, i in enumerate(active):
            w[i] = w_sub[k]
        return w
    return np.ones(n) / n


def _activesetTangency(muExcess: np.ndarray, cov: np.ndarray, maxIter: int = 50) -> np.ndarray:
    """Long-only max Sharpe (Tangency) via active-set."""
    n = cov.shape[0]

    if n <= 12:
        best_w = None
        best_sr = -np.inf
        for mask in range(1, 1 << n):
            idx = [i for i in range(n) if mask & (1 << i)]
            muSub = muExcess[idx]
            sub = cov[np.ix_(idx, idx)]
            try:
                inv = np.linalg.inv(sub)
            except np.linalg.LinAlgError:
                inv = np.linalg.pinv(sub)
            w_sub = inv @ muSub
            s = w_sub.sum()
            if s == 0:
                continue
            w_sub = w_sub / s
            if (w_sub < -1e-10).any():
                continue
            ret = float(w_sub @ muSub)
            risk = float(np.sqrt(w_sub @ sub @ w_sub))
            if risk <= 0 or ret <= 0:
                continue
            sr = ret / risk
            if sr > best_sr:
                best_sr = sr
                w = np.zeros(n)
                for k, i in enumerate(idx):
                    w[i] = w_sub[k]
                best_w = w
        return best_w if best_w is not None else (np.ones(n) / n)

    # n > 12: iterative
    active = list(range(n))
    for _ in range(maxIter):
        sub = cov[np.ix_(active, active)]
        muSub = muExcess[active]
        try:
            inv = np.linalg.inv(sub)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(sub)
        w_sub = inv @ muSub
        s = w_sub.sum()
        if s != 0:
            w_sub = w_sub / s
        if (w_sub < -1e-10).any():
            worst = active[int(np.argmin(w_sub))]
            active.remove(worst)
            if not active:
                break
            continue
        w = np.zeros(n)
        for k, i in enumerate(active):
            w[i] = w_sub[k]
        return w
    return np.ones(n) / n


log = logging.getLogger(__name__)


def _buildReturns(stockCodes: list[str]) -> tuple[np.ndarray | None, list[str]]:
    """종목별 OHLCV를 순차 수집하여 수익률 행렬 구성."""
    all_rets = []
    valid_codes = []
    for code in stockCodes:
        ohlcv = fetchOhlcv(code)
        if isEmptyDf(ohlcv):
            continue
        arr = ohlcvToArrays(ohlcv)
        close = arr.get("close")
        if close is None or len(close) < 30:
            continue
        rets = np.diff(np.log(close))
        all_rets.append(rets)
        valid_codes.append(code)
        del ohlcv  # 메모리 해제

    if len(valid_codes) < 2:
        return None, valid_codes

    # 길이 맞추기
    min_len = min(len(r) for r in all_rets)
    matrix = np.column_stack([r[-min_len:] for r in all_rets])
    return matrix, valid_codes


def optimizeMeanVar(
    stockCodes: list[str],
    *,
    market: str = "auto",
    riskFree: float = 0.0,
    covEstimator: str = "sample",
    **kwargs,
) -> dict:
    """Markowitz 평균-분산 최적화 — long-only Min-Variance + Tangency.

    Args:
        stockCodes: 종목 리스트.
        market: "KR" | "US" | "auto".
        riskFree: 연환산 무위험수익률 (Tangency excess return 계산).
        covEstimator: "sample" | "ledoit_wolf" — 다종목/단기표본에서 ledoit_wolf 권장.

    Returns:
        dict — minVariance, tangency 각각 weights/expectedReturn/risk/sharpe.

    Note:
        - Long-only QP를 active-set 알고리즘으로 정확히 풀이 (clip+renorm 아님).
        - 종목 ≤ 12: enumeration으로 globally optimal.
        - 종목 > 12: iterative active-set.
        - Tangency Sharpe는 (μ - rf) / σ.
    """
    result: dict = {"stockCodes": stockCodes}

    if len(stockCodes) < 2:
        w = {stockCodes[0]: 1.0} if stockCodes else {}
        return {**result, "minVariance": {"weights": w}, "info": "2종목 이상 필요"}

    returns, codes = _buildReturns(stockCodes)
    if returns is None:
        return {**result, "error": f"수익률 데이터 부족 ({len(codes)}종목)"}

    len(codes)
    mu = np.mean(returns, axis=0) * 252

    if covEstimator == "ledoit_wolf":
        cov_d, delta = _ledoitWolfShrinkage(returns)
        cov = cov_d * 252
        result["covShrinkage"] = round(float(delta), 4)
    else:
        cov = np.cov(returns.T, ddof=1) * 252

    result["validStocks"] = codes
    result["dataPoints"] = int(returns.shape[0])
    result["covEstimator"] = covEstimator
    result["riskFree"] = round(float(riskFree), 4)
    if returns.shape[0] < 60:
        result["dataAdequacy"] = "low"
    else:
        result["dataAdequacy"] = "ok"

    # Min-Variance via active-set
    w_mv = _activesetMinvar(cov)
    ret_mv = float(w_mv @ mu)
    risk_mv = float(np.sqrt(w_mv @ cov @ w_mv))
    sharpe_mv = (ret_mv - riskFree) / risk_mv if risk_mv > 0 else 0

    result["minVariance"] = {
        "weights": {c: round(float(w), 4) for c, w in zip(codes, w_mv)},
        "expectedReturn": round(ret_mv, 4),
        "risk": round(risk_mv, 4),
        "sharpe": round(sharpe_mv, 4),
    }

    # Tangency via active-set (excess returns)
    muExcess = mu - riskFree
    w_tan = _activesetTangency(muExcess, cov)
    ret_t = float(w_tan @ mu)
    risk_t = float(np.sqrt(w_tan @ cov @ w_tan))
    sharpe_t = (ret_t - riskFree) / risk_t if risk_t > 0 else 0

    result["tangency"] = {
        "weights": {c: round(float(w), 4) for c, w in zip(codes, w_tan)},
        "expectedReturn": round(ret_t, 4),
        "risk": round(risk_t, 4),
        "sharpe": round(sharpe_t, 4),
    }

    return result


def optimizeRiskParity(stockCodes: list[str], *, market: str = "auto", **kwargs) -> dict:
    """HRP — 계층적 리스크 패리티 (Lopez de Prado 2016).

    상관행렬 기반 거리로 계층 클러스터링한 뒤, recursive bisection으로
    역분산 가중치를 배분한다. 공분산 추정 오류에 강건.

    Parameters
    ----------
    stockCodes : list[str]
        종목코드 리스트 (2개 이상).
    market : str
        "KR" | "US" | "auto".

    Returns
    -------
    dict
        stockCodes : list[str] — 입력 종목 리스트
        weights : dict[str, float] — 종목별 배분 비중 (%, 합=1)
        riskContribution : dict[str, float] — 종목별 리스크 기여도 (%, 합≈1)
        clusterOrder : list[str] — 클러스터링 leaf 순서

    Examples
    --------
    >>> from dartlab.quant.portfolio.optimize import optimizeRiskParity
    >>> optimizeRiskParity(["005930", "000660", "035720"])"""
    result: dict = {"stockCodes": stockCodes}

    if len(stockCodes) < 2:
        w = {stockCodes[0]: 1.0} if stockCodes else {}
        return {**result, "weights": w, "info": "2종목 이상 필요"}

    returns, codes = _buildReturns(stockCodes)
    if returns is None:
        return {**result, "error": "수익률 데이터 부족"}

    n = len(codes)
    cov = np.cov(returns.T) * 252
    corr = np.corrcoef(returns.T)

    # 1. 거리 행렬
    dist = np.sqrt(0.5 * (1 - corr))

    # 2. Single-linkage clustering (numpy)
    order = _hierarchicalCluster(dist, n)

    # 3. Recursive bisection
    weights = np.ones(n)
    _recursiveBisection(weights, cov, order)
    weights /= weights.sum()

    # Risk contribution
    port_var = float(weights @ cov @ weights)
    rc = weights * (cov @ weights) / max(port_var, 1e-12)

    result["weights"] = {codes[i]: round(float(weights[i]), 4) for i in range(n)}
    result["riskContribution"] = {codes[i]: round(float(rc[i]), 4) for i in range(n)}
    result["clusterOrder"] = [codes[i] for i in order]
    return result


# ── HRP + Active Exposure + Constrained MV → _optimizeAdvanced.py 분리 ──

from dartlab.quant.portfolio._optimizeAdvanced import (  # noqa: E402, F401
    activeExposure,
    allocateERC,
    constrainedMinVariance,
    holdingsToFactorExposure,
    riskBudgetByFactor,
)
