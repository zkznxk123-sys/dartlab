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
from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays

# ── 공분산 추정 ──────────────────────────────────────────


def _ledoit_wolf_shrinkage(returns: np.ndarray) -> tuple[np.ndarray, float]:
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


def _activeset_minvar(cov: np.ndarray, max_iter: int = 50) -> np.ndarray:
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
    for _ in range(max_iter):
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


def _activeset_tangency(mu_excess: np.ndarray, cov: np.ndarray, max_iter: int = 50) -> np.ndarray:
    """Long-only max Sharpe (Tangency) via active-set."""
    n = cov.shape[0]

    if n <= 12:
        best_w = None
        best_sr = -np.inf
        for mask in range(1, 1 << n):
            idx = [i for i in range(n) if mask & (1 << i)]
            mu_sub = mu_excess[idx]
            sub = cov[np.ix_(idx, idx)]
            try:
                inv = np.linalg.inv(sub)
            except np.linalg.LinAlgError:
                inv = np.linalg.pinv(sub)
            w_sub = inv @ mu_sub
            s = w_sub.sum()
            if s == 0:
                continue
            w_sub = w_sub / s
            if (w_sub < -1e-10).any():
                continue
            ret = float(w_sub @ mu_sub)
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
    for _ in range(max_iter):
        sub = cov[np.ix_(active, active)]
        mu_sub = mu_excess[active]
        try:
            inv = np.linalg.inv(sub)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(sub)
        w_sub = inv @ mu_sub
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


def _build_returns(stockCodes: list[str]) -> tuple[np.ndarray | None, list[str]]:
    """종목별 OHLCV를 순차 수집하여 수익률 행렬 구성."""
    all_rets = []
    valid_codes = []
    for code in stockCodes:
        ohlcv = fetch_ohlcv(code)
        if isEmptyDf(ohlcv):
            continue
        arr = ohlcv_to_arrays(ohlcv)
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

    returns, codes = _build_returns(stockCodes)
    if returns is None:
        return {**result, "error": f"수익률 데이터 부족 ({len(codes)}종목)"}

    len(codes)
    mu = np.mean(returns, axis=0) * 252

    if covEstimator == "ledoit_wolf":
        cov_d, delta = _ledoit_wolf_shrinkage(returns)
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
    w_mv = _activeset_minvar(cov)
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
    mu_excess = mu - riskFree
    w_tan = _activeset_tangency(mu_excess, cov)
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
    >>> from dartlab.quant.portfolio import optimizeRiskParity
    >>> optimizeRiskParity(["005930", "000660", "035720"])"""
    result: dict = {"stockCodes": stockCodes}

    if len(stockCodes) < 2:
        w = {stockCodes[0]: 1.0} if stockCodes else {}
        return {**result, "weights": w, "info": "2종목 이상 필요"}

    returns, codes = _build_returns(stockCodes)
    if returns is None:
        return {**result, "error": "수익률 데이터 부족"}

    n = len(codes)
    cov = np.cov(returns.T) * 252
    corr = np.corrcoef(returns.T)

    # 1. 거리 행렬
    dist = np.sqrt(0.5 * (1 - corr))

    # 2. Single-linkage clustering (numpy)
    order = _hierarchical_cluster(dist, n)

    # 3. Recursive bisection
    weights = np.ones(n)
    _recursive_bisection(weights, cov, order)
    weights /= weights.sum()

    # Risk contribution
    port_var = float(weights @ cov @ weights)
    rc = weights * (cov @ weights) / max(port_var, 1e-12)

    result["weights"] = {codes[i]: round(float(weights[i]), 4) for i in range(n)}
    result["riskContribution"] = {codes[i]: round(float(rc[i]), 4) for i in range(n)}
    result["clusterOrder"] = [codes[i] for i in order]
    return result


def _hierarchical_cluster(dist: np.ndarray, n: int) -> list[int]:
    """Single-linkage agglomerative clustering → quasi-diagonal leaf order.

    Lopez de Prado (2016) HRP의 1단계: 거리 행렬에서 가장 가까운 두 점/클러스터를
    반복적으로 병합(single linkage = 최소 거리)하고 leaf 순서를 반환.
    """
    if n <= 1:
        return list(range(n))

    # active cluster id → leaves
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    active: list[int] = list(range(n))
    next_id = n

    # 동적 거리 행렬 (cluster_id → cluster_id → dist)
    d: dict[int, dict[int, float]] = {i: {} for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i != j:
                d[i][j] = float(dist[i, j])

    while len(active) > 1:
        # 가장 가까운 두 active cluster 탐색
        best_a = best_b = -1
        best_dd = np.inf
        for ai, a in enumerate(active):
            for b in active[ai + 1 :]:
                dd = d[a][b]
                if dd < best_dd:
                    best_dd = dd
                    best_a, best_b = a, b

        # 병합
        new_id = next_id
        next_id += 1
        members[new_id] = members[best_a] + members[best_b]
        active.remove(best_a)
        active.remove(best_b)

        # 새 cluster의 거리 = 단일연결(=min)
        d[new_id] = {}
        for c in active:
            new_d = min(d[best_a][c], d[best_b][c])
            d[new_id][c] = new_d
            d[c][new_id] = new_d
        active.append(new_id)

    return members[next_id - 1]


def _recursive_bisection(weights: np.ndarray, cov: np.ndarray, order: list[int]):
    """Recursive bisection for HRP weights."""
    if len(order) <= 1:
        return

    mid = len(order) // 2
    left = order[:mid]
    right = order[mid:]

    var_left = _cluster_variance(cov, left)
    var_right = _cluster_variance(cov, right)

    alpha = 1 - var_left / (var_left + var_right) if (var_left + var_right) > 0 else 0.5

    for i in left:
        weights[i] *= alpha
    for i in right:
        weights[i] *= 1 - alpha

    _recursive_bisection(weights, cov, left)
    _recursive_bisection(weights, cov, right)


def _cluster_variance(cov: np.ndarray, indices: list[int]) -> float:
    """클러스터의 역분산 가중 분산."""
    sub_cov = cov[np.ix_(indices, indices)]
    n = len(indices)
    if n == 1:
        return float(sub_cov[0, 0])
    # 역분산 가중
    ivp = 1 / np.diag(sub_cov)
    ivp /= ivp.sum()
    return float(ivp @ sub_cov @ ivp)


def allocateERC(stockCodes: list[str], *, market: str = "auto", **kwargs) -> dict:
    """리스크 버짓팅 — Equal Risk Contribution (Maillard et al. 2010).

    모든 종목의 리스크 기여도가 동일(1/N)이 되도록 가중치를 반복 조정.
    역분산 가중의 확장으로, 상관관계까지 고려한 균등 리스크 배분.

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
        converged : bool — 수렴 여부
        targetRC : float — 목표 리스크 기여도 (%, 1/N)

    Examples
    --------
    >>> from dartlab.quant.portfolio import allocateERC
    >>> allocateERC(["005930", "000660", "035720"])"""
    result: dict = {"stockCodes": stockCodes}

    if len(stockCodes) < 2:
        w = {stockCodes[0]: 1.0} if stockCodes else {}
        return {**result, "weights": w, "info": "2종목 이상 필요"}

    returns, codes = _build_returns(stockCodes)
    if returns is None:
        return {**result, "error": "수익률 데이터 부족"}

    n = len(codes)
    cov = np.cov(returns.T) * 252
    target_rc = 1.0 / n

    # 초기: 동일 가중
    w = np.ones(n) / n

    converged = False
    for _ in range(200):
        sigma_w = cov @ w
        port_var = float(w @ sigma_w)
        if port_var < 1e-12:
            break
        rc = w * sigma_w / port_var

        # 조정
        adj = target_rc / (rc + 1e-12)
        w_new = w * adj
        w_new = np.clip(w_new, 1e-6, None)
        w_new /= w_new.sum()

        if np.max(np.abs(w_new - w)) < 1e-8:
            converged = True
            w = w_new
            break
        w = w_new

    # 최종 risk contribution
    sigma_w = cov @ w
    port_var = float(w @ sigma_w)
    rc = w * sigma_w / max(port_var, 1e-12)

    result["weights"] = {codes[i]: round(float(w[i]), 4) for i in range(n)}
    result["riskContribution"] = {codes[i]: round(float(rc[i]), 4) for i in range(n)}
    result["converged"] = converged
    result["targetRC"] = round(target_rc, 4)
    return result


# ══════════════════════════════════════════════════════════════════════
# Grinold Ch.3-4 — Holdings Decomposition (Factor Exposure + Risk Budget)
# ══════════════════════════════════════════════════════════════════════


def holdingsToFactorExposure(
    weights: dict[str, float],
    factorLoadings: dict[str, dict[str, float]],
) -> dict[str, float]:
    """포트폴리오 weights × 종목별 loadings → 포트폴리오 factor exposure.

    Grinold Ch.3 기반. 각 종목의 팩터 로딩에 가중치를 곱하여
    포트폴리오 전체의 팩터별 노출도를 산출한다.

    Parameters
    ----------
    weights : dict[str, float]
        종목별 가중치 (종목코드 → 비중).
    factorLoadings : dict[str, dict[str, float]]
        종목별 팩터 로딩 (종목코드 → {팩터명: 로딩값}).

    Returns
    -------
    dict[str, float]
        팩터별 포트폴리오 노출도 (팩터명 → 노출값).

    Examples
    --------
    >>> holdingsToFactorExposure(
    ...     {"005930": 0.6, "000660": 0.4},
    ...     {"005930": {"value": 0.3, "size": 0.8}, "000660": {"value": 0.7, "size": 0.2}},
    ... )"""
    exposure: dict[str, float] = {}
    for stock, w in weights.items():
        loadings = factorLoadings.get(stock)
        if not loadings:
            continue
        for fname, ld in loadings.items():
            exposure[fname] = exposure.get(fname, 0.0) + w * ld
    return {k: float(v) for k, v in exposure.items()}


def riskBudgetByFactor(
    portfolioExposure: dict[str, float],
    factorCov: dict[tuple[str, str], float],
    factorNames: list[str],
) -> dict:
    """팩터별 리스크 기여도 (Grinold Ch.3).

    portfolio variance = e^T × Σ × e;
    risk contribution_k = e_k × (Σ × e)_k / σ_p².
    """
    k = len(factorNames)
    if k == 0:
        return {"totalVariance": 0.0, "marginalContrib": {}, "pctContrib": {}}
    e = np.array([portfolioExposure.get(f, 0.0) for f in factorNames], dtype=float)
    Sigma = np.zeros((k, k), dtype=float)
    for i, fi in enumerate(factorNames):
        for j, fj in enumerate(factorNames):
            v = factorCov.get((fi, fj)) or factorCov.get((fj, fi)) or 0.0
            Sigma[i, j] = v
    Se = Sigma @ e
    total_var = float(e @ Se)
    if total_var <= 0:
        return {
            "totalVariance": total_var,
            "marginalContrib": {f: 0.0 for f in factorNames},
            "pctContrib": {f: 0.0 for f in factorNames},
        }
    marginal = {f: float(Se[i]) for i, f in enumerate(factorNames)}
    pct = {f: float(e[i] * Se[i] / total_var) for i, f in enumerate(factorNames)}
    return {"totalVariance": total_var, "marginalContrib": marginal, "pctContrib": pct}


def activeExposure(
    portfolioWeights: dict[str, float],
    benchmarkWeights: dict[str, float],
    factorLoadings: dict[str, dict[str, float]],
) -> dict[str, float]:
    """액티브 익스포저 = 포트 노출 − 벤치 노출 (Grinold Ch.4).

    포트폴리오와 벤치마크의 팩터 노출도 차이를 계산하여
    액티브 베팅 방향과 크기를 파악한다.

    Parameters
    ----------
    portfolioWeights : dict[str, float]
        포트폴리오 종목별 가중치.
    benchmarkWeights : dict[str, float]
        벤치마크 종목별 가중치.
    factorLoadings : dict[str, dict[str, float]]
        종목별 팩터 로딩 (종목코드 → {팩터명: 로딩값}).

    Returns
    -------
    dict[str, float]
        팩터별 액티브 노출도 (팩터명 → 포트−벤치 차이).
        양수 = 포트폴리오가 해당 팩터에 오버웨이트.

    Examples
    --------
    >>> activeExposure(
    ...     {"005930": 0.5}, {"005930": 0.3},
    ...     {"005930": {"value": 0.5}},
    ... )"""
    stocks = set(portfolioWeights) | set(benchmarkWeights)
    active = {s: portfolioWeights.get(s, 0.0) - benchmarkWeights.get(s, 0.0) for s in stocks}
    return holdingsToFactorExposure(active, factorLoadings)


# ══════════════════════════════════════════════════════════════════════
# Grinold Ch.13 — Constrained Min-Variance (Projected Gradient + Dykstra)
# ══════════════════════════════════════════════════════════════════════
#
# cvxpy 의존 금지. numpy 직접 구현.


def _projectSimplexBoxSectors(
    w: np.ndarray,
    *,
    boxMin: float,
    boxMax: float,
    sectorMemberships: dict[int, list[int]] | None,
    sectorCaps: dict[int, float] | None,
    innerIter: int = 50,
) -> np.ndarray:
    """Σw=1, box, sector cap 동시 투영 — Dykstra 반복 투영."""
    n = w.size
    p = np.clip(w, boxMin, boxMax)
    for _ in range(innerIter):
        old = p.copy()
        gap = 1.0 - p.sum()
        if abs(gap) > 1e-12:
            p = p + gap / n
        p = np.clip(p, boxMin, boxMax)
        if sectorMemberships and sectorCaps:
            for sid, idx in sectorMemberships.items():
                cap = sectorCaps.get(sid)
                if cap is None or not idx:
                    continue
                s = p[idx].sum()
                if s > cap:
                    p[idx] = p[idx] * (cap / s)
        if float(np.linalg.norm(p - old)) < 1e-10:
            break
    total = p.sum()
    if total > 0:
        p = p / total
    return p


def constrainedMinVariance(
    cov: np.ndarray,
    *,
    boxMin: float = 0.0,
    boxMax: float = 1.0,
    sectorMemberships: dict[int, list[int]] | None = None,
    sectorCaps: dict[int, float] | None = None,
    maxIter: int = 500,
    tol: float = 1e-8,
) -> dict:
    """제약 Min-Variance (Grinold Ch.13) — Projected Gradient.

    min w^T Σ w s.t. Σw=1, w ∈ [boxMin, boxMax], sector caps.
    """
    S = np.asarray(cov, dtype=float)
    n = S.shape[0]
    if n == 0:
        return {"weights": np.array([]), "variance": 0.0, "converged": True, "iterations": 0}
    w = np.ones(n) / n
    eigmax = float(np.linalg.eigvalsh(S).max()) if n > 0 else 1.0
    if eigmax <= 0:
        eigmax = 1.0
    step = 1.0 / (2.0 * eigmax)
    prev = w.copy()
    converged = False
    it = 0
    for it in range(maxIter):
        grad = 2.0 * S @ w
        w_new = w - step * grad
        w_new = _projectSimplexBoxSectors(
            w_new,
            boxMin=boxMin,
            boxMax=boxMax,
            sectorMemberships=sectorMemberships,
            sectorCaps=sectorCaps,
        )
        diff = float(np.linalg.norm(w_new - prev))
        prev = w_new.copy()
        w = w_new
        if diff < tol:
            converged = True
            break
    return {
        "weights": w,
        "variance": float(w @ S @ w),
        "converged": converged,
        "iterations": it + 1,
    }


def factorExposureConstraint(
    weights: np.ndarray,
    factorLoadings: np.ndarray,
    factorLimits: np.ndarray,
) -> dict:
    """팩터 익스포저 제약 체크 — |exposure| ≤ limit 위반 탐지.

    Grinold Ch.13 제약 최적화의 사후 검증. 포트폴리오 가중치에
    팩터 로딩을 곱한 노출도가 한도를 초과하는 팩터를 식별한다.

    Parameters
    ----------
    weights : np.ndarray
        포트폴리오 가중치 벡터 (N,).
    factorLoadings : np.ndarray
        팩터 로딩 행렬 (N × K), N=종목수, K=팩터수.
    factorLimits : np.ndarray
        팩터별 노출 한도 벡터 (K,).

    Returns
    -------
    dict
        exposure : np.ndarray — 팩터별 노출도 벡터 (K,)
        breaches : list[int] — 한도 초과 팩터 인덱스 목록
        compliant : bool — 모든 팩터가 한도 이내이면 True

    Examples
    --------
    >>> factorExposureConstraint(
    ...     np.array([0.5, 0.5]),
    ...     np.array([[0.3, 0.1], [0.7, 0.2]]),
    ...     np.array([0.6, 0.2]),
    ... )"""
    w = np.asarray(weights, dtype=float)
    L = np.asarray(factorLoadings, dtype=float)
    lim = np.asarray(factorLimits, dtype=float)
    exp = L.T @ w
    breaches = [int(i) for i in range(len(exp)) if abs(exp[i]) > lim[i]]
    return {"exposure": exp, "breaches": breaches, "compliant": len(breaches) == 0}
