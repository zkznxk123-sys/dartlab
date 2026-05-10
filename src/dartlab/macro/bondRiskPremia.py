"""Cochrane-Piazzesi (2005) Bond Risk Premia Factor.

선도금리의 tent-shaped 선형 결합 → 단일 팩터.
이 팩터로 2-5년 만기 채권의 초과수익률을 R²=0.44로 예측.
경기역행적: 불황기에 팩터 상승 → 기대 초과수익 상승 → 채권 매수 기회.

Cochrane & Piazzesi (2005) "Bond Risk Premia", AER.
계수: Table 2 (1964-2003, annual data).
"""

from __future__ import annotations

import math

# CP (2005) Table 2 계수 — 1Y~5Y 선도금리에 대한 가중치
# tent-shaped: 중간 만기(3Y)에서 최대, 양쪽으로 하락
_CP_GAMMA = [-2.14, 0.81, 3.00, 0.80, -2.08]
_CP_INTERCEPT = -3.38  # 상수항


def forwardRatesFromSpot(spotRates: dict[int, float]) -> list[float]:
    """현물 수익률 → 1Y~5Y 선도금리 계산.

    Args:
        spot_rates: {만기(년): 수익률(%)} — 최소 {1, 2, 3, 4, 5} 필요

    Returns:
        [f(0,1), f(1,2), f(2,3), f(3,4), f(4,5)] — 5개 선도금리 (%)
    """
    forwards = []
    for n in range(1, 6):
        if n == 1:
            forwards.append(spotRates[1])
        else:
            y_n = spotRates[n]
            y_n1 = spotRates[n - 1]
            # f(n-1, n) = n*y(n) - (n-1)*y(n-1)
            fwd = n * y_n - (n - 1) * y_n1
            forwards.append(fwd)
    return forwards


def cochranePiazzesiFactor(forwardRates: list[float]) -> dict:
    """CP 단일 팩터 계산 + 해석.

    Args:
        forward_rates: [f(0,1), f(1,2), f(2,3), f(3,4), f(4,5)] — 5개 선도금리 (%)

    Returns:
        dict with cpFactor, expectedExcessReturn, zone, description
    """
    if len(forwardRates) < 5:
        return {}

    # CP factor = intercept + γ₁f₁ + γ₂f₂ + γ₃f₃ + γ₄f₄ + γ₅f₅
    cp = _CP_INTERCEPT
    for gamma, fwd in zip(_CP_GAMMA, forwardRates[:5]):
        if fwd is None or math.isnan(fwd):
            return {}
        cp += gamma * fwd

    # CP factor ≈ 기대 초과수익률 (%p, 연율)
    # 양수 = 채권 초과수익 기대, 음수 = 채권 불리
    if cp > 2.0:
        zone, zone_label = "high", "높음"
        desc = "채권 기대초과수익 높음 — 장기채 매수 유리 (경기 우려 반영)"
    elif cp > 0.5:
        zone, zone_label = "normal", "보통"
        desc = "채권 기대초과수익 정상 범위"
    elif cp > -0.5:
        zone, zone_label = "low", "낮음"
        desc = "채권 기대초과수익 낮음 — 장기채 초과수익 제한적"
    else:
        zone, zone_label = "negative", "음수"
        desc = "채권 기대초과수익 음수 — 장기채 underweight"

    return {
        "cpFactor": round(cp, 3),
        "expectedExcessReturn": round(cp, 2),
        "zone": zone,
        "zoneLabel": zone_label,
        "description": desc,
    }
