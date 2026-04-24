"""Multiple Testing Adjustment — Harvey-Liu-Zhu (2016) + White Reality Check.

전략 다수 검정 시 false discovery 폭증. dartlab 30+ 검증 스타일 + N 알파 universe →
Sharpe 의 multiplicative adjustment 필수.

학술 :
    - Harvey, Liu, Zhu (2016, Review of Financial Studies) — Haircut Sharpe
    - White (2000, Econometrica) — Reality Check bootstrap p-value
    - Hansen (2005) — Stepwise SPA (Superior Predictive Ability)
"""

from __future__ import annotations

import numpy as np


def haircutSharpe(
    sharpe: float,
    *,
    nTests: int,
    nObs: int,
    method: str = "bonferroni",
) -> dict:
    """Sharpe 다중 테스트 보정 — Harvey-Liu-Zhu 2016.

    Capabilities:
        - Bonferroni / Holm / BHY (Benjamini-Hochberg-Yekutieli) 3종
        - haircut Sharpe = 보정 후 t-stat / √(years) × √252
        - 통과 여부 (5% 유의)

    AIContext:
        - Sprint 7 거버넌스 — DSR + HLZ 결합으로 strategy 진정성 검증
        - dartlab 8 검증 스타일 + N alpha = 실제 32+ 동시 testing → 보정 필수

    Args:
        sharpe: 관측 annualized Sharpe.
        nTests: 동시 검정한 전략 수.
        nObs: 관측 일수 (= 일별 시계열 길이).
        method: ``"bonferroni"`` | ``"holm"`` | ``"bhy"``.

    Returns:
        dict
            tStat : float — 원본 t-stat (= sharpe × √(nObs/252))
            adjustedAlpha : float — 5% / nTests 등
            criticalT : float — 보정 후 critical t
            haircutSharpe : float — adjusted t / √(years) × √252
            haircutPct : float — 원본 대비 손실 (%)
            isSignificant : bool
            method : str
            interpretation : str

    Notes:
        - HLZ 원논문은 Bayesian re-weighting — 본 함수는 frequentist 단순화 (Bonferroni).
        - DSR (Bailey-Lopez 2014) 와 결합 권장 — DSR 은 within-strategy 다중 시도, HLZ 는 between-strategy.
    """
    if nObs < 30 or nTests < 1:
        return {"error": "invalid input"}

    years = nObs / 252
    t_stat = sharpe * np.sqrt(years)

    # adjusted α
    if method == "bonferroni":
        alpha_adj = 0.05 / nTests
    elif method == "holm":
        # 가장 유의한 1순위만 → Bonferroni 와 동일
        alpha_adj = 0.05 / nTests
    elif method == "bhy":
        # Benjamini-Hochberg-Yekutieli FDR
        c_n = sum(1 / k for k in range(1, nTests + 1))
        alpha_adj = 0.05 / (nTests * c_n)
    else:
        return {"error": f"method {method} unknown"}

    # 양측 critical t (정규 inverse CDF, statistics 표준 라이브러리)
    from statistics import NormalDist

    # 양측 검정: P(|Z| > crit) = α  →  P(Z > crit) = α/2
    crit_t = float(NormalDist().inv_cdf(1 - alpha_adj / 2))

    # haircut: t_stat 가 critical 이상이면 그대로, 아니면 비율 축소
    if abs(t_stat) >= crit_t:
        haircut_sharpe = sharpe
        haircut_pct = 0.0
        sig = True
    else:
        ratio = abs(t_stat) / crit_t
        haircut_sharpe = sharpe * ratio
        haircut_pct = (1 - ratio) * 100
        sig = False

    return {
        "tStat": round(t_stat, 3),
        "adjustedAlpha": round(alpha_adj, 6),
        "criticalT": round(crit_t, 3),
        "haircutSharpe": round(haircut_sharpe, 3),
        "haircutPct": round(haircut_pct, 1),
        "isSignificant": bool(sig),
        "method": method,
        "interpretation": (
            f"Sharpe {sharpe:+.2f} → haircut {round(haircut_sharpe, 2):+.2f} "
            f"({round(haircut_pct, 0):.0f}% 손실, {nTests} tests {method}). "
            + ("유의." if sig else "비유의 — false discovery 가능.")
        ),
    }


def realityCheck(
    strategyReturns: list[np.ndarray],
    benchmarkReturns: np.ndarray,
    *,
    nBootstrap: int = 1000,
    blockLength: int = 10,
) -> dict:
    """White Reality Check (2000) — bootstrap-based 다중 전략 우위 검정.

    H_0: 모든 전략의 평균 excess 수익 ≤ 0 vs H_1: 최소 1개 > 0.
    Stationary bootstrap (Politis-Romano) 으로 p-value 추정.

    Capabilities:
        - 다수 전략 동시 검정 (data snooping bias 보정)
        - bootstrap distribution of max excess Sharpe

    Args:
        strategyReturns: list of T-array (각 전략 수익).
        benchmarkReturns: T-array (벤치마크).
        nBootstrap: bootstrap iterations. 기본 ``1000``.
        blockLength: stationary bootstrap mean block length. 기본 ``10``.

    Returns:
        dict
            nStrategies : int
            t : int
            maxExcessMean : float — 최대 평균 excess
            pValue : float — Reality Check p
            isSignificant : bool — p < 0.05
            interpretation : str
    """
    bench = np.asarray(benchmarkReturns, dtype=np.float64)
    excess = []
    for s in strategyReturns:
        s_arr = np.asarray(s, dtype=np.float64)
        if len(s_arr) != len(bench):
            return {"error": "length mismatch"}
        excess.append(s_arr - bench)

    excess_mat = np.column_stack(excess)  # T × M
    T, M = excess_mat.shape
    if T < 30:
        return {"error": "T < 30"}

    obs_max = float(np.max(excess_mat.mean(axis=0)))

    # stationary bootstrap
    rng = np.random.default_rng(42)
    p_block = 1 / blockLength
    boot_max = np.zeros(nBootstrap)
    for b in range(nBootstrap):
        # demeaned bootstrap (Politis-Romano stationary)
        idx = np.zeros(T, dtype=np.int32)
        cur = rng.integers(0, T)
        for t in range(T):
            idx[t] = cur
            if rng.random() < p_block:
                cur = rng.integers(0, T)
            else:
                cur = (cur + 1) % T
        boot_sample = excess_mat[idx]
        # subtract obs mean for null distribution
        boot_centered = boot_sample - excess_mat.mean(axis=0)
        boot_max[b] = float(np.max(boot_centered.mean(axis=0) + excess_mat.mean(axis=0).max()))

    # p-value: P(boot_max ≥ obs_max)
    p_val = float((boot_max >= obs_max).mean())

    return {
        "nStrategies": M,
        "t": T,
        "maxExcessMean": round(obs_max, 5),
        "pValue": round(p_val, 4),
        "isSignificant": bool(p_val < 0.05),
        "nBootstrap": nBootstrap,
        "interpretation": (
            f"M={M} strategies, T={T}, max excess mean={round(obs_max, 4)}. "
            f"Reality Check p={round(p_val, 3)}. "
            + ("최소 1 전략 진정한 alpha." if p_val < 0.05 else "data snooping 가능 — 진정 alpha 미증명.")
        ),
    }
