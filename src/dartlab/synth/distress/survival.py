"""Survival Probability × Going-Concern 가중 SSOT.

Damodaran, *The Dark Side of Valuation* Ch.4 — 부실 위험이 있는 기업은
going-concern 가치(DCF/RIM)를 pSurvival 로 가중하고, 청산가치를 잔여 가중치로 더한다:

    Value = GoingConcern × pSurvival + Liquidation × (1 - pSurvival)

L1.5 synth/distress 본체 — credit ↔ analysis 양쪽 엔진이 동일 경로로 호출.

입력:
- credit 엔진이 계산한 CHS 12M PD (probability) 또는
- CHS 원본 feature dict 를 넘기면 내부에서 계산
- 둘 다 없으면 pSurvival=1.0 (Mature Stable 회귀 불변 보장)

출력: 순수 dict — 해석 문장 없음.
"""

from __future__ import annotations

from typing import Any

from dartlab.synth.distress.chsModel import CHSResult, calcCHS

# Damodaran 권고 — 청산 시 공정가치 할인
_DEFAULT_LIQUIDATION_DISCOUNT = 0.25


def calcSurvivalWeight(
    *,
    probability: float | None = None,
    zone: str | None = None,
    chsFeatures: dict[str, Any] | None = None,
    horizonYears: int = 10,
    liquidationDiscount: float | None = None,
) -> dict[str, Any]:
    """Dark Side of Valuation Ch.4 — Going-Concern × Survival 가중 계산.

    Capabilities:
        - 3 source 우선순위: probability > chsFeatures > zone > safe_default
        - liquidationDiscount [0, 0.7] 자동 clamp (overflow 방어)
        - hazard 미주입 시 safe_default (~0.5% 연 hazard, pSurvival ≈ 0.95)
        - source 라벨로 어떤 입력 사용됐는지 투명 추적

    Parameters
    ----------
    probability : CHS 12M 부도확률 (0.0~1.0). 지정 시 annualHazard 로 직접 사용.
    zone : CHS zone hint ("safe"/"watch"/"distress"). probability 없을 때 보조.
    chsFeatures : CHS 원본 입력 (netIncome, totalLiabilities 등). 지정 시 calcCHS 호출.
    horizonYears : 누적 생존 계산 기간 (Damodaran 권고 10년).
    liquidationDiscount : 청산 시 book value 할인율 (0.0~1.0). None → 기본 0.25.

    Returns
    -------
    dict
        pSurvival : float — 0.0~1.0 (horizon 년 누적 생존확률)
        pDefault : float — 1 - pSurvival
        annualHazard : float — 연간 부도 확률 (12M PD)
        liquidationDiscount : float — 적용된 청산 할인
        horizonYears : int
        source : str — "chs_probability" | "chs_features" | "zone_default" | "safe_default"

    Guide:
        DCF/RIM 등 going-concern 모델 결과를 가중치로 묶을 때 사용.
        source 라벨로 입력 신뢰도 추적: chs_probability > chs_features > zone > safe.

    SeeAlso:
        - `applySurvivalWeight`: going-concern + liquidation 가중 합산 함수
        - `calcCHS`: CHS 모델로 probability 산출
        - `extractChsFeatures`: company → CHS 입력 dict

    Requires:
        synth.distress.chsModel (calcCHS, CHSResult)

    AIContext:
        결과 인용 시 source 라벨도 함께 명시 — safe_default 인 경우 "데이터 부족
        가정치" 표기 필수. 청산할인은 도메인별 다름 (제조 0.25, IT 0.40 권장).

    LLM Specifications:
        AntiPatterns: probability 와 chsFeatures 동시 지정 — probability 가 우선,
        chsFeatures 무시됨 (silent). horizonYears < 1 호출 — max(1, n) 으로 보정.
        OutputSchema: dict(pSurvival/pDefault/annualHazard/liquidationDiscount/horizonYears/source).
        Prerequisites: probability ∈ [0, 1] 또는 zone ∈ {safe, watch, distress}.
        Freshness: stateless — chsFeatures 시점에만 의존.
        Dataflow: hazard 입력 → (1-hazard)^horizon → pSurvival.
        TargetMarkets: 부실 위험 노출 회사 valuation. 안정기업 (safe_default) 도 호출 가능 (보수 유지).
    """
    discount = _DEFAULT_LIQUIDATION_DISCOUNT if liquidationDiscount is None else float(liquidationDiscount)
    # 청산 할인 유효 범위 [0, 0.7]
    if discount < 0:
        discount = 0.0
    elif discount > 0.7:
        discount = 0.7

    hazard: float | None = None
    source = "safe_default"

    if probability is not None:
        hazard = float(max(0.0, min(1.0, probability)))
        source = "chs_probability"
    elif chsFeatures:
        try:
            result = calcCHS(
                **{
                    k: chsFeatures.get(k)
                    for k in (
                        "netIncome",
                        "totalLiabilities",
                        "cash",
                        "totalAssets",
                        "marketCap",
                        "equityVolatility",
                        "marketTotal",
                        "excessReturn",
                        "stockPrice",
                    )
                }
            )
        except TypeError:
            result = None
        if isinstance(result, CHSResult):
            hazard = float(max(0.0, min(1.0, result.probability)))
            source = "chs_features"

    if hazard is None and zone:
        zone_map = {"safe": 0.005, "watch": 0.03, "distress": 0.12}
        hazard = zone_map.get(zone.lower())
        if hazard is not None:
            source = "zone_default"

    if hazard is None:
        hazard = 0.005  # Mature Stable 근사 — pSurvival ≈ 0.95 over 10Y
        source = "safe_default"

    p_survival = (1.0 - hazard) ** max(1, int(horizonYears))

    return {
        "pSurvival": round(p_survival, 4),
        "pDefault": round(1.0 - p_survival, 4),
        "annualHazard": round(hazard, 4),
        "liquidationDiscount": round(discount, 4),
        "horizonYears": int(horizonYears),
        "source": source,
    }


def applySurvivalWeight(
    goingConcernValue: float | None,
    bookEquity: float | None,
    survival: dict[str, Any] | None,
) -> dict[str, Any]:
    """Going-Concern + Liquidation 가중 합산.

    Capabilities:
        - going-concern × pSurvival + liquidation × (1-pSurvival) 합산
        - survival=None 시 pSurvival=1 (going-concern 그대로, 안전 fallback)
        - bookEquity None/<=0 시 liquidation None (going-concern × pSurvival 만)
        - uplift 보고 (조정 후 변화율 %p)

    Parameters
    ----------
    goingConcernValue : DCF/RIM/DDM 등 primary 가치 (주당 또는 전체). 단위 호출자 관리.
    bookEquity : 장부 자본 (liquidation base). 단위는 goingConcernValue 와 동일해야 함.
    survival : calcSurvivalWeight 결과 dict. None 이면 pSurvival=1 로 처리.

    Returns
    -------
    dict
        adjustedValue : float | None — 가중 합산 결과
        goingConcernWeight : float — pSurvival
        liquidationValue : float | None — bookEquity × (1 - discount)
        liquidationWeight : float — 1 - pSurvival
        pSurvival : float
        uplift : float | None — (adjusted / goingConcern - 1), 단위 %p

    Guide:
        DCF 의 minimum-value floor 효과. distress 회사일수록 liquidation 비중 ↑.
        제조업 0.25, IT 0.40 청산할인이 통상. 호출자가 단위 일관성 책임.

    SeeAlso:
        - `calcSurvivalWeight`: pSurvival 산출 (본 함수 입력 생성)
        - `calcCHS`: PD 산출

    Requires:
        stdlib only

    AIContext:
        adjustedValue 인용 시 uplift 부호 명시 (양수 = liquidation 보호 효과,
        음수 = 청산가치가 going-concern 보다 낮음 — 흔치 않음).

    LLM Specifications:
        AntiPatterns: bookEquity 음수 입력 — None 처리 (liquidation=None).
        OutputSchema: dict(adjustedValue/goingConcernWeight/liquidationValue/
            liquidationWeight/pSurvival/uplift).
        Prerequisites: 단위 일관성 (goingConcernValue 와 bookEquity 동일 단위).
        Freshness: stateless.
        Dataflow: goingConcern + liquidation + pSurvival → 가중 합산.
        TargetMarkets: distress/turnaround valuation. 안정기업도 pSurvival=1 안전 동작.
    """
    if survival is None:
        survival = {"pSurvival": 1.0, "liquidationDiscount": _DEFAULT_LIQUIDATION_DISCOUNT}

    p = float(survival.get("pSurvival", 1.0))
    discount = float(survival.get("liquidationDiscount", _DEFAULT_LIQUIDATION_DISCOUNT))

    liquidation = None
    if bookEquity is not None and bookEquity > 0:
        liquidation = bookEquity * (1.0 - discount)

    adjusted: float | None = None
    uplift: float | None = None
    if goingConcernValue is not None:
        liq_part = (liquidation or 0.0) * (1.0 - p)
        adjusted = goingConcernValue * p + liq_part
        if goingConcernValue != 0:
            uplift = round((adjusted / goingConcernValue - 1.0) * 100, 2)

    return {
        "adjustedValue": adjusted,
        "goingConcernWeight": round(p, 4),
        "liquidationValue": liquidation,
        "liquidationWeight": round(1.0 - p, 4),
        "pSurvival": round(p, 4),
        "uplift": uplift,
    }
