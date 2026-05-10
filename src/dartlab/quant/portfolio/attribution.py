"""Brinson 성과귀속 — 종목선정 / 비중 / 타이밍 분해.

학술 근거:
- Brinson, Hood, Beebower (1986): Determinants of Portfolio Performance
- Brinson, Singer, Beebower (1991): 후속 (BHB)
- Karnosky-Singer (1994): 통화 효과 분해 (비통화 부분만 본 모듈에서)

표준 BHB 분해:
    Active Return = Allocation Effect + Selection Effect + Interaction

Allocation: (w_p - w_b) × R_b   ← 섹터/그룹 가중치 차이
Selection : w_b × (R_p - R_b)   ← 같은 그룹 내 종목 선정
Interaction: (w_p - w_b) × (R_p - R_b)  ← 두 효과의 교호

각 그룹(섹터/팩터/지역) 별로 산출 후 합산.
"""

from __future__ import annotations

import numpy as np


def brinsonAttribution(
    portfolioWeights: np.ndarray,
    benchmarkWeights: np.ndarray,
    portfolioReturns: np.ndarray,
    benchmarkReturns: np.ndarray,
    groupLabels: list[str] | None = None,
) -> dict:
    """BHB Brinson-Hood-Beebower 성과귀속.

    Args:
        portfolio_weights: 그룹별 포트 가중치 (합=1)
        benchmark_weights: 그룹별 벤치 가중치 (합=1)
        portfolio_returns: 그룹별 포트 수익률
        benchmark_returns: 그룹별 벤치 수익률
        group_labels: 그룹 이름 (선택)

    Returns:
        dict — totalActive, allocation, selection, interaction +
               그룹별 분해 표.
    """
    wp = np.asarray(portfolioWeights, dtype=float)
    wb = np.asarray(benchmarkWeights, dtype=float)
    rp = np.asarray(portfolioReturns, dtype=float)
    rb = np.asarray(benchmarkReturns, dtype=float)
    n = len(wp)
    if not (len(wb) == len(rp) == len(rb) == n):
        return {"error": "길이 불일치"}

    portfolio_total = float(wp @ rp)
    benchmark_total = float(wb @ rb)
    active = portfolio_total - benchmark_total

    alloc = (wp - wb) * rb
    sel = wb * (rp - rb)
    inter = (wp - wb) * (rp - rb)

    labels = groupLabels if groupLabels else [f"g{i}" for i in range(n)]
    rows = []
    for i in range(n):
        rows.append(
            {
                "group": labels[i],
                "wPort": round(float(wp[i]), 4),
                "wBench": round(float(wb[i]), 4),
                "rPort": round(float(rp[i]), 4),
                "rBench": round(float(rb[i]), 4),
                "allocation": round(float(alloc[i]), 4),
                "selection": round(float(sel[i]), 4),
                "interaction": round(float(inter[i]), 4),
            }
        )

    return {
        "portfolioReturn": round(portfolio_total, 4),
        "benchmarkReturn": round(benchmark_total, 4),
        "activeReturn": round(active, 4),
        "totalAllocation": round(float(alloc.sum()), 4),
        "totalSelection": round(float(sel.sum()), 4),
        "totalInteraction": round(float(inter.sum()), 4),
        "byGroup": rows,
    }


def timingEffect(
    weightsHistory: np.ndarray,
    returnsHistory: np.ndarray,
    avgWeights: np.ndarray,
) -> float:
    """Timing effect — 가중치 변화가 수익률과 일치했는가.

    timing = Σ_t (w_t - w̄) × r_t

    weights_history: (T, N) 시점별 가중치
    returns_history: (T, N) 시점별 수익률
    avg_weights: (N,) 평균 가중치 (보통 정책 가중치)

    양수면 timing 능력 있음 (rebalancing이 수익률 방향과 일치).
    """
    W = np.asarray(weightsHistory, dtype=float)
    R = np.asarray(returnsHistory, dtype=float)
    avg = np.asarray(avgWeights, dtype=float)
    deviation = W - avg
    contribution = np.sum(deviation * R, axis=1)
    return float(contribution.sum())


# 0.10 BC 깸 — snake_case alias 제거. brinsonAttribution / timingEffect 만 SSOT.
