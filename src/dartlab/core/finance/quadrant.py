"""Bridgewater-style Growth × Inflation 4-Quadrant regime classifier.

Dalio (2018) "Principles for Navigating Big Debt Crises"
Ilmanen (2011) "Expected Returns" Ch.17

Growth↑ + Inflation↑ = reflation    → 원자재, EM 주식, TIPS
Growth↑ + Inflation↓ = goldilocks   → 선진국 주식, 크레딧
Growth↓ + Inflation↑ = stagflation  → 금, TIPS, 현금
Growth↓ + Inflation↓ = deflation    → 장기 국채, 투자등급채
"""

from __future__ import annotations

# ── 자산배분 매핑 (Bridgewater All Weather 원리) ──

_ASSET_MAP: dict[str, dict[str, str]] = {
    "reflation": {
        "equity": "overweight",
        "bond": "underweight",
        "commodity": "overweight",
        "gold": "neutral",
        "tips": "overweight",
        "cash": "underweight",
    },
    "goldilocks": {
        "equity": "overweight",
        "bond": "neutral",
        "commodity": "neutral",
        "gold": "underweight",
        "tips": "underweight",
        "cash": "underweight",
    },
    "stagflation": {
        "equity": "underweight",
        "bond": "underweight",
        "commodity": "overweight",
        "gold": "overweight",
        "tips": "overweight",
        "cash": "overweight",
    },
    "deflation": {
        "equity": "underweight",
        "bond": "overweight",
        "commodity": "underweight",
        "gold": "neutral",
        "tips": "underweight",
        "cash": "neutral",
    },
}

_LABELS: dict[str, str] = {
    "reflation": "리플레이션",
    "goldilocks": "골디락스",
    "stagflation": "스태그플레이션",
    "deflation": "디플레이션",
}

_DESCRIPTIONS: dict[str, str] = {
    "reflation": "성장 가속 + 물가 상승 — 원자재·EM 주식·TIPS 유리, 명목채 불리",
    "goldilocks": "성장 가속 + 물가 안정 — 선진국 주식·크레딧 최적, 금·원자재 불리",
    "stagflation": "성장 둔화 + 물가 상승 — 금·TIPS·현금 방어, 주식·채권 불리",
    "deflation": "성장 둔화 + 물가 하락 — 장기 국채 최적, 주식·원자재 불리",
}


def classifyQuadrant(
    growth_signal: float,
    inflation_signal: float,
    *,
    growth_threshold: float = 0.0,
    inflation_threshold: float = 0.0,
) -> dict:
    """Growth × Inflation 2×2 → 4체제 판별.

    Args:
        growth_signal: ISM PMI - 50 (양수=확장, 음수=수축) 또는 IP YoY
        inflation_signal: CPI YoY 3M 변화 (양수=상승 모멘텀, 음수=하락)
        growth_threshold: 성장 판별 임계값 (기본 0)
        inflation_threshold: 인플레 판별 임계값 (기본 0)

    Returns:
        dict with quadrant, labels, asset implications, confidence
    """
    growth_rising = growth_signal > growth_threshold
    inflation_rising = inflation_signal > inflation_threshold

    if growth_rising and inflation_rising:
        quadrant = "reflation"
    elif growth_rising and not inflation_rising:
        quadrant = "goldilocks"
    elif not growth_rising and inflation_rising:
        quadrant = "stagflation"
    else:
        quadrant = "deflation"

    # 신뢰도: 신호 강도 기반
    g_strength = abs(growth_signal)
    i_strength = abs(inflation_signal)
    if g_strength > 5.0 and i_strength > 0.5:
        confidence = "high"
    elif g_strength > 2.0 or i_strength > 0.3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "quadrant": quadrant,
        "quadrantLabel": _LABELS[quadrant],
        "growth": "rising" if growth_rising else "falling",
        "growthSignal": round(growth_signal, 2),
        "inflation": "rising" if inflation_rising else "falling",
        "inflationSignal": round(inflation_signal, 2),
        "assetImplication": _ASSET_MAP[quadrant],
        "confidence": confidence,
        "description": _DESCRIPTIONS[quadrant],
    }
