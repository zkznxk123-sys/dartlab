"""Survival Probability × Going-Concern 가중 SSOT.

Damodaran, *The Dark Side of Valuation* Ch.4 — 부실 위험이 있는 기업은
going-concern 가치(DCF/RIM)를 pSurvival 로 가중하고, 청산가치를 잔여 가중치로 더한다:

    Value = GoingConcern × pSurvival + Liquidation × (1 - pSurvival)

credit ↔ valuation 은 L2 상호 import 금지 → 이 모듈이 **중립 SSOT** 역할.
양쪽 엔진 모두 여기만 import.

입력:
- credit 엔진이 계산한 CHS 12M PD (probability) 또는
- CHS 원본 feature dict 를 넘기면 내부에서 계산
- 둘 다 없으면 pSurvival=1.0 (Mature Stable 회귀 불변 보장)

출력: 순수 dict — 해석 문장 없음.
"""

from __future__ import annotations

from typing import Any

from dartlab.credit.chsModel import CHSResult, calcCHS

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
