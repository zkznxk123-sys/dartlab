"""Bridgewater-style Growth × Inflation 4-Quadrant regime classifier.

Dalio (2018) "Principles for Navigating Big Debt Crises"
Ilmanen (2011) "Expected Returns" Ch.17

Growth↑ + Inflation↑ = reflation    → 원자재, EM 주식, TIPS
Growth↑ + Inflation↓ = goldilocks   → 선진국 주식, 크레딧
Growth↓ + Inflation↑ = stagflation  → 금, TIPS, 현금
Growth↓ + Inflation↓ = deflation    → 장기 국채, 투자등급채

L1.5 synth SSOT — macro/summary, macro/cycle, quant 가 소비.
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
    growthSignal: float,
    inflationSignal: float,
    *,
    growthThreshold: float = 0.0,
    inflationThreshold: float = 0.0,
) -> dict:
    """Bridgewater 4-Quadrant (Growth × Inflation) regime 판별.

    Capabilities:
        성장 시그널 × 인플레 시그널 2 축을 임계값 기준으로 부호 비교하여
        4 체제 (reflation/goldilocks/stagflation/deflation) 중 하나를
        선택하고 자산배분 권고 + 강도 기반 confidence 를 함께 반환.

    Args:
        growthSignal: 성장 모멘텀. ISM PMI - 50 또는 IP YoY 권장. 양수=확장.
        inflationSignal: 인플레 모멘텀. CPI YoY 의 3M 변화 권장. 양수=가속.
        growthThreshold: 성장 부호 판정 임계. 기본 ``0.0`` (PMI 50 기준).
        inflationThreshold: 인플레 부호 판정 임계. 기본 ``0.0``.

    Returns:
        dict with keys:
            - ``quadrant`` (str): ``"reflation"``/``"goldilocks"``/
              ``"stagflation"``/``"deflation"``
            - ``quadrantLabel`` (str): 한국어 라벨
            - ``growth``/``inflation`` (str): ``"rising"``/``"falling"``
            - ``growthSignal``/``inflationSignal`` (float): 입력 시그널 (rounded)
            - ``assetImplication`` (dict): 6 자산군 over/neutral/underweight
            - ``confidence`` (str): ``"high"``/``"medium"``/``"low"``
              (strength 기반)
            - ``description`` (str): 체제 설명 한 줄

    Raises:
        없음.

    Example:
        >>> r = classifyQuadrant(growthSignal=3.5, inflationSignal=0.4)
        >>> r["quadrant"]
        'reflation'
        >>> r["assetImplication"]["commodity"]
        'overweight'

    Guide:
        Dalio (2018) "Principles for Navigating Big Debt Crises", Ilmanen
        (2011) "Expected Returns" Ch.17 기반. 본 함수는 단일 시점 분류이며
        체제 전환은 ``macro.cycles.macroCycle.classifyCycle`` 와 결합 권장.

    SeeAlso:
        - ``dartlab.macro.cycles.macroCycle.classifyCycle``
        - ``dartlab.synth.portfolioMapping.regimeToAllocation``

    Requires:
        없음 (순수 함수).

    AIContext:
        confidence="low" 시 4 체제 라벨 단독 인용 금지. 동일 분기 PMI/CPI
        모멘텀이 약하면 체제 전환 직전 가능성이 높아 macro/summary 와
        cross-check 가 필요.

    LLM Specifications:
        AntiPatterns:
            - threshold 를 0 이외로 설정한 결과를 default 인 양 인용 금지.
            - assetImplication 의 over/neutral/underweight 는 정성 권고이지
              구체 비중 (%) 이 아니다.
        OutputSchema:
            ``{quadrant, quadrantLabel, growth, growthSignal, inflation,
            inflationSignal, assetImplication, confidence, description}``.
        Prerequisites:
            growthSignal, inflationSignal 둘 다 finite float.
        Freshness:
            입력 시그널의 freshness 에 따름 (보통 월간 갱신).
        Dataflow:
            (g, i) → sign(g - g_thr), sign(i - i_thr) → quadrant 키
            → _ASSET_MAP/_LABELS/_DESCRIPTIONS 룩업.
        TargetMarkets: Global (US/KR/EM 공통, ISM PMI 또는 KR PMI 권장).
    """
    growth_rising = growthSignal > growthThreshold
    inflation_rising = inflationSignal > inflationThreshold

    if growth_rising and inflation_rising:
        quadrant = "reflation"
    elif growth_rising and not inflation_rising:
        quadrant = "goldilocks"
    elif not growth_rising and inflation_rising:
        quadrant = "stagflation"
    else:
        quadrant = "deflation"

    g_strength = abs(growthSignal)
    i_strength = abs(inflationSignal)
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
        "growthSignal": round(growthSignal, 2),
        "inflation": "rising" if inflation_rising else "falling",
        "inflationSignal": round(inflationSignal, 2),
        "assetImplication": _ASSET_MAP[quadrant],
        "confidence": confidence,
        "description": _DESCRIPTIONS[quadrant],
    }
