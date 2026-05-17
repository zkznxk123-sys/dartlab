"""quant/portfolio/optimize.py 고급 최적화 분리 — HRP + Active Exposure + Constrained MV.

optimize.py 752 줄 분할. HRP (hierarchical + recursive + allocateERC 약 165 줄) +
Active Exposure (holdingsToFactorExposure + riskBudgetByFactor + activeExposure 약 115 줄)
+ Constrained MV (_projectSimplexBoxSectors + constrainedMinVariance 약 120 줄) 합 400 줄.
optimize.py 의 facade (공분산 추정 · MVO · 단순 RP · _buildReturns) 책임 유지.

BC: portfolio.optimize 모듈에서 모든 심볼 import 가능 (re-export).
"""

from __future__ import annotations

import logging

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def _hierarchicalCluster(dist: np.ndarray, n: int) -> list[int]:
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


def _recursiveBisection(weights: np.ndarray, cov: np.ndarray, order: list[int]):
    """Recursive bisection for HRP weights."""
    if len(order) <= 1:
        return

    mid = len(order) // 2
    left = order[:mid]
    right = order[mid:]

    var_left = _clusterVariance(cov, left)
    var_right = _clusterVariance(cov, right)

    alpha = 1 - var_left / (var_left + var_right) if (var_left + var_right) > 0 else 0.5

    for i in left:
        weights[i] *= alpha
    for i in right:
        weights[i] *= 1 - alpha

    _recursiveBisection(weights, cov, left)
    _recursiveBisection(weights, cov, right)


def _clusterVariance(cov: np.ndarray, indices: list[int]) -> float:
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
    >>> from dartlab.quant.portfolio.optimize import allocateERC
    >>> allocateERC(["005930", "000660", "035720"])

    Capabilities:
        - cov 매트릭스 기반 반복 조정으로 모든 종목의 risk contribution = 1/N 수렴
        - 200 회 반복 cap + max(weight 변동) < 1e-8 수렴 판정

    Guide:
        Maillard et al. 2010 표준 ERC. 단순 1/N 보다 변동성 큰 종목 underweight,
        상관관계 작은 종목 overweight.

    When:
        Portfolio 리스크 균등 배분 + AI "변동성 균형" 답변.

    How:
        ``_buildReturns`` → cov annualize → iterative w 조정 → 수렴 또는 200 회 cap.

    Requires:
        ``stockCodes`` ≥ 2 + ``_buildReturns`` 가 ``returns`` 매트릭스 반환.

    Raises:
        없음 — 데이터 부족 시 ``{"error": ...}``.

    SeeAlso:
        - optimize.allocateRiskParity : 단순 역변동성 (상관 무시)
        - constrainedMinVariance : 제약 최소분산

    AIContext:
        "리스크를 균등 배분하면" 답변 시 weights + riskContribution 인용.
    """
    from dartlab.quant.portfolio.optimize import _buildReturns

    result: dict = {"stockCodes": stockCodes}

    if len(stockCodes) < 2:
        w = {stockCodes[0]: 1.0} if stockCodes else {}
        return {**result, "weights": w, "info": "2종목 이상 필요"}

    returns, codes = _buildReturns(stockCodes)
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
    ... )

    Capabilities:
        - 종목 weights × loadings 누적 → 팩터별 합산 노출도 dict
        - 로딩 부재 종목 skip (방어적 join)

    Guide:
        Grinold-Kahn Active Portfolio Management Ch.3 표준 분해. ERC/Min-Var weights
        의 팩터 해석에 필수.

    When:
        포트 팩터 분해 + AI "포트는 value/size 어디에 베팅" 답변.

    How:
        weights 순회 → loadings 매칭 → 누적 dict.

    Requires:
        weights/factorLoadings 의 종목 코드 키 일치.

    Raises:
        없음.

    SeeAlso:
        - riskBudgetByFactor : 팩터별 risk contribution
        - activeExposure : 벤치 대비 액티브 노출

    AIContext:
        "포트는 어느 팩터에 베팅" 답변 시 exposure dict 의 top key 인용.
    """
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

    Capabilities:
        - 팩터 노출 e × cov Σ × e → totalVariance + marginal contribution + pct contribution
        - 대칭 cov key 자동 처리 (fi,fj) 또는 (fj,fi)

    Args:
        portfolioExposure: 팩터별 포트 노출 ``{factorName: exposure}``.
        factorCov: 팩터 cov ``{(fi,fj): cov}``.
        factorNames: 팩터 순서 list.

    Returns:
        dict — totalVariance/marginalContrib/pctContrib.

    Guide:
        Grinold-Kahn Ch.3 risk budgeting 표준. pctContrib 합 = 1. 단일 팩터가 50%+ 이면
        집중 베팅.

    When:
        팩터 위험 분해 + AI "어느 팩터가 위험 주범" 답변.

    How:
        e/Σ 매트릭스 구성 → Se 계산 → totalVariance + per-factor contribution.

    Requires:
        portfolioExposure 와 factorCov 의 팩터 이름 일치.

    Raises:
        없음.

    Example:
        >>> r = riskBudgetByFactor({"value": 0.3}, {("value","value"): 0.04}, ["value"])
        >>> r["totalVariance"]
        0.0036

    SeeAlso:
        - holdingsToFactorExposure : exposure 산출
        - activeExposure : 액티브 노출

    AIContext:
        "리스크는 어느 팩터에서" 답변에 pctContrib top 인용.
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
    ... )

    Capabilities:
        - 포트 weights − 벤치 weights → active weights → ``holdingsToFactorExposure`` 결합
        - 종목 union 으로 한쪽에만 있는 종목도 액티브 베팅으로 포함

    Guide:
        Grinold-Kahn Ch.4 Active Management 표준. |active exposure| 큰 팩터 = 베팅 방향.

    When:
        벤치마크 대비 active risk 분해 + AI 액티브 베팅 답변.

    How:
        union(portfolio, benchmark) 종목 → diff weights → factor 결합.

    Requires:
        portfolio/benchmark/loadings 종목 키 정합.

    Raises:
        없음.

    SeeAlso:
        - holdingsToFactorExposure : 베이스
        - riskBudgetByFactor : 액티브 리스크 기여

    AIContext:
        "벤치 대비 어디에 베팅했나" 답변 시 양수 / 음수 active exposure 인용.
    """
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

    Capabilities:
        - Projected Gradient + Dykstra 반복 투영으로 cvxpy 없이 제약 Min-Var 해결
        - Σw=1 + box [min, max] + sector cap 동시 제약 만족

    Args:
        cov: cov 매트릭스 (N×N).
        boxMin: 종목별 최소 비중. 기본 ``0.0``.
        boxMax: 종목별 최대 비중. 기본 ``1.0``.
        sectorMemberships: ``{sectorId: [stockIdx...]}`` 매핑.
        sectorCaps: ``{sectorId: maxWeight}``.
        maxIter: 최대 반복. 기본 ``500``.
        tol: 수렴 임계. 기본 ``1e-8``.

    Returns:
        dict — weights/variance/converged/iterations.

    Guide:
        Grinold-Kahn Ch.13 표준. cvxpy 없이 numpy 만 → wheel 슬림화. sector cap 미사용
        시 box-Min-Var 와 동일.

    When:
        제약 포트 최적화 + AI "min variance 포트" 답변.

    How:
        grad = 2Σw → projected step → Dykstra 투영 → 수렴/maxIter.

    Requires:
        cov 가 양의 정부호 (또는 양의 준정부호) NxN.

    Raises:
        없음 — 빈 cov 시 empty result.

    Example:
        >>> r = constrainedMinVariance(cov, boxMax=0.3)
        >>> r["converged"]
        True

    SeeAlso:
        - allocateERC : risk parity
        - optimize.minVariance : 비제약

    AIContext:
        "Min-Variance 포트는 어떻게" 답변 시 weights + 종목별 cap 인용.
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
    ... )

    Capabilities:
        - exposure = L^T × w → |exposure| 가 factorLimits 초과하는 팩터 인덱스 식별
        - 사후 제약 검증 (constrainedMinVariance 결과 sanity check)

    Guide:
        Grinold-Kahn Ch.13 제약 최적화의 검증 단계. compliant=False 면 weights 재최적화.

    When:
        포트 제약 검증 + AI 팩터 베팅 한도 답변.

    How:
        L.T @ w → |.| vs lim 비교 → 초과 인덱스 누적.

    Requires:
        weights/factorLoadings/factorLimits 차원 정합 (N, NxK, K).

    Raises:
        없음.

    SeeAlso:
        - constrainedMinVariance : 사전 최적화
        - holdingsToFactorExposure : exposure dict 버전

    AIContext:
        "팩터 한도 위반" 답변 시 breaches 인덱스 + exposure 인용.
    """
    w = np.asarray(weights, dtype=float)
    L = np.asarray(factorLoadings, dtype=float)
    lim = np.asarray(factorLimits, dtype=float)
    exp = L.T @ w
    breaches = [int(i) for i in range(len(exp)) if abs(exp[i]) > lim[i]]
    return {"exposure": exp, "breaches": breaches, "compliant": len(breaches) == 0}
