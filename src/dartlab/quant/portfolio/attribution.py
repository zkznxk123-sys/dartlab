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

    Capabilities:
        - 그룹별 가중·수익률 → allocation/selection/interaction 3 효과 분해 (Brinson 1986)
        - byGroup 표 + totalActive 일관성 (allocation + selection + interaction)

    Args:
        portfolioWeights: 그룹별 포트 가중치 (합=1).
        benchmarkWeights: 그룹별 벤치 가중치 (합=1).
        portfolioReturns: 그룹별 포트 수익률.
        benchmarkReturns: 그룹별 벤치 수익률.
        groupLabels: 그룹 이름 (선택). 미지정 시 ``g0..gN``.

    Returns:
        dict — portfolioReturn/benchmarkReturn/activeReturn/totalAllocation/totalSelection/totalInteraction/byGroup.

    Guide:
        Brinson-Hood-Beebower 1986. 가중치 효과 (allocation) 가 종목 선정 효과 (selection)
        대비 어디서 가치 만드는지 식별. PM 평가의 표준.

    When:
        포트 성과 귀속 + AI "성과 어디서 왔나" 답변.

    How:
        그룹별 active = (wp-wb)×rb + wb×(rp-rb) + (wp-wb)×(rp-rb).

    Requires:
        4 array 길이 정합.

    Raises:
        없음 — 길이 불일치 시 ``{"error": "길이 불일치"}``.

    Example:
        >>> brinsonAttribution(wp, wb, rp, rb)["totalSelection"]
        0.013

    See Also:
        - timingEffect : 시점 효과
        - portfolio.allocateERC : 가중 결정

    AIContext:
        "포트의 성과는 종목선정 vs 섹터 베팅" 답변에 selection/allocation 인용.
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

    Capabilities:
        - 시점별 (w_t - w̄) × r_t 누적 → market timing 능력 단일 스칼라
        - 양수 = timing 좋음, 음수 = 잘못 타이밍

    Args:
        weightsHistory: (T, N) 시점별 가중치 매트릭스.
        returnsHistory: (T, N) 시점별 수익률 매트릭스.
        avgWeights: (N,) 평균 가중치 (보통 정책 가중치).

    Returns:
        float — timing 효과 스칼라.

    Guide:
        BHB 후속 (1991). rebalancing 의 가치 정량화. 음수면 매수 후 하락 / 매도 후 상승
        반복 (잘못 타이밍).

    When:
        Portfolio 시점 효과 평가 + AI "타이밍 잘했나" 답변.

    How:
        deviation = W - avg → ⊙ R 으로 시점별 기여 → sum.

    Requires:
        W/R 차원 (T,N) 정합 + avg (N,).

    Raises:
        없음.

    Example:
        >>> timingEffect(W, R, avg)
        0.018

    See Also:
        - brinsonAttribution : BHB 분해
        - portfolio.optimize : 가중 결정

    AIContext:
        "rebalancing 가치" 답변 시 양/음 + 크기 인용.
    """
    W = np.asarray(weightsHistory, dtype=float)
    R = np.asarray(returnsHistory, dtype=float)
    avg = np.asarray(avgWeights, dtype=float)
    deviation = W - avg
    contribution = np.sum(deviation * R, axis=1)
    return float(contribution.sum())


# 0.10 BC 깸 — snake_case alias 제거. brinsonAttribution / timingEffect 만 SSOT.
