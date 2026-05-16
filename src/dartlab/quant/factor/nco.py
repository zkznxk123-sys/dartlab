"""Nested Clustered Optimization — AFML Ch.16 (Lopez de Prado 2018).

기존 Mean-Variance: estimation noise → 극단 weights.
HRP (Hierarchical Risk Parity) 개선 + intra-cluster optimization 결합 = NCO.

알고리즘 :
    1. 상관행렬 → distance = sqrt(0.5 (1 - ρ))
    2. Single-linkage hierarchical clustering
    3. Top-k clusters 분리 (예: 5)
    4. 각 cluster 내부: Markowitz tangency
    5. Cluster 간: HRP recursive bisection (변동성 가중)
    6. 최종 weights = w_intra × w_inter

dartlab 활용 :
    - 30+ 종목 large universe optimization
    - 단일 cov matrix 의 unstable inverse 회피
    - HRP 단독 (existing) 보다 expected return 정보 활용
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger(__name__)


def _distMatrix(corr: np.ndarray) -> np.ndarray:
    """상관 → 유클리드 distance (Lopez de Prado 표준)."""
    d = np.sqrt(0.5 * np.clip(1 - corr, 0, 2))
    np.fill_diagonal(d, 0)
    return d


def _hierarchicalClusters(dist: np.ndarray, k: int) -> list[list[int]]:
    """Single-linkage hierarchical clustering → k clusters.

    NumPy 단순 구현 (scipy 없이).
    """
    n = dist.shape[0]
    clusters: list[list[int]] = [[i] for i in range(n)]
    work_dist = dist.copy()
    np.fill_diagonal(work_dist, np.inf)

    while len(clusters) > k:
        # 가장 가까운 cluster 쌍 찾기
        min_idx = np.unravel_index(np.argmin(work_dist), work_dist.shape)
        i, j = min_idx
        if i > j:
            i, j = j, i
        # merge j into i
        clusters[i] = clusters[i] + clusters[j]
        clusters.pop(j)
        # update distances: single linkage = min
        new_d = np.minimum(work_dist[i], work_dist[j])
        new_d[i] = np.inf
        work_dist[i] = new_d
        work_dist[:, i] = new_d
        work_dist = np.delete(work_dist, j, axis=0)
        work_dist = np.delete(work_dist, j, axis=1)
        np.fill_diagonal(work_dist, np.inf)

    return clusters


def _intraClusterWeights(covSub: np.ndarray, muSub: np.ndarray | None) -> np.ndarray:
    """Cluster 내부: Markowitz tangency (μ 있으면) 또는 minimum variance."""
    n = covSub.shape[0]
    try:
        inv = np.linalg.inv(covSub + np.eye(n) * 1e-8)
    except np.linalg.LinAlgError:
        return np.ones(n) / n

    if muSub is not None:
        w = inv @ muSub
    else:
        w = inv @ np.ones(n)
    w = np.clip(w, 0, None)  # long-only
    if w.sum() > 0:
        return w / w.sum()
    return np.ones(n) / n


def optimizeNCO(
    cov: np.ndarray,
    *,
    mu: np.ndarray | None = None,
    nClusters: int = 5,
    longOnly: bool = True,
) -> dict:
    """Nested Clustered Optimization — AFML Ch.16 표준.

    Capabilities:
        - 종목 universe 자동 cluster 분할 (single-linkage)
        - Cluster 내부 tangency, cluster 간 risk parity 결합
        - HRP 단독 (allocateERC) 보다 μ 정보 활용

    AIContext:
        - Sprint 5 portfolio — 30+ 종목 universe 안정 최적화
        - estimation error 의 condition number explosion 회피

    Args:
        cov: N × N 공분산.
        mu: 기대수익률 (N,). None 이면 cluster 내부도 min-var.
        nClusters: cluster 개수. 기본 ``5``.
        longOnly: long-only (기본 True).

    Returns:
        dict
            weights : np.ndarray — 최종 비중 (합=1)
            clusters : list[list[int]] — 각 cluster 의 종목 인덱스
            intraWeights : list[np.ndarray] — cluster 내부 비중
            interWeights : np.ndarray — cluster 간 비중
            interpretation : str

    Guide:
        Lopez de Prado AFML Ch.16 — 30+ universe 에서 mean-variance 의 conditional
        number explosion 회피. nClusters 4~6 권장.

    When:
        대형 universe portfolio optimization + AI 30+ 종목 안정 비중 답변.

    How:
        cov → corr → distance → single-linkage cluster → cluster 내부 tangency/
        min-var + cluster 간 risk parity → 최종 weights.

    Requires:
        cov 가 양의 준정칙 N×N (N ≥ nClusters).

    Raises:
        없음 — shape mismatch 시 error 키.

    Example:
        >>> r = optimizeNCO(cov, nClusters=5)
        >>> r["weights"].sum()
        1.0

    See Also:
        - allocateERC : HRP 단순화
        - blackLittermanPosterior : 뷰 + prior 결합
    """
    Sigma = np.asarray(cov, dtype=np.float64)
    N = Sigma.shape[0]
    if Sigma.shape != (N, N) or N < nClusters:
        return {"error": "shape mismatch or too few stocks"}

    # 1. correlation → distance
    diag = np.sqrt(np.diag(Sigma))
    diag = np.where(diag < 1e-10, 1e-10, diag)
    corr = Sigma / np.outer(diag, diag)
    np.fill_diagonal(corr, 1)

    dist = _distMatrix(corr)

    # 2. clustering
    clusters = _hierarchicalClusters(dist, nClusters)

    # 3. intra-cluster tangency
    intra_weights = []
    for c in clusters:
        c_sub = Sigma[np.ix_(c, c)]
        m_sub = mu[c] if mu is not None else None
        w_intra = _intraClusterWeights(c_sub, m_sub)
        intra_weights.append(w_intra)

    # 4. inter-cluster: variance per cluster (HRP-style)
    cluster_vars = np.zeros(len(clusters))
    for i, (c, w_in) in enumerate(zip(clusters, intra_weights)):
        c_sub = Sigma[np.ix_(c, c)]
        cluster_vars[i] = float(w_in @ c_sub @ w_in)

    inv_var = 1 / np.where(cluster_vars > 0, cluster_vars, np.inf)
    inter_weights = inv_var / inv_var.sum() if inv_var.sum() > 0 else np.ones(len(clusters)) / len(clusters)

    # 5. final
    final = np.zeros(N)
    for c, w_in, w_inter in zip(clusters, intra_weights, inter_weights):
        for k, idx in enumerate(c):
            final[idx] = w_inter * w_in[k]

    if longOnly:
        final = np.clip(final, 0, None)
    if final.sum() > 0:
        final = final / final.sum()

    return {
        "weights": final,
        "clusters": clusters,
        "intraWeights": intra_weights,
        "interWeights": inter_weights,
        "n": N,
        "nClusters": nClusters,
        "interpretation": (
            f"NCO N={N}, {nClusters} clusters. "
            f"클러스터 변동성 {[round(float(v) ** 0.5, 4) for v in cluster_vars]}. "
            "HRP 안정성 + tangency μ 결합."
        ),
    }
