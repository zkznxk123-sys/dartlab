"""CounterfactualPanel — 런타임 what-if (Phase 10 G4).

사용자/AI 가 "만약 WACC +1%p 면?" 물으면 review 가 즉시 재계산.
기존 calc 재사용 → 83초 타임아웃 우회.
"""

from __future__ import annotations

from typing import Any


# 지원 what-if 키 — dFV overrides 와 매핑
_SUPPORTED_KEYS: dict[str, str] = {
    "wacc": "할인율 (%)",
    "terminalGrowth": "영구 성장률 (%)",
    "growthRates": "고속 성장률 (list[%])",
    "marginPath": "영업이익률 경로 (list[%])",
    "reinvestmentPath": "재투자율 경로 (list[%])",
    "pSurvival": "생존 확률 (0~1)",
    "liquidationDiscount": "청산 할인 (0~1)",
    "countryCode": "국가 코드 (CRP 조정)",
}


def runCounterfactual(
    company: Any,
    *,
    overrides: dict,
    basePeriod: str | None = None,
) -> dict:
    """what-if 시나리오 실행 → baseline vs scenario 비교.

    Parameters
    ----------
    company : Company
    overrides : dict — dFV override 키 (_SUPPORTED_KEYS 참고)
    basePeriod : 기준 기간

    Returns
    -------
    dict
        baseline : {dFV, primaryModel}
        scenario : {dFV, primaryModel, overrides_applied}
        delta_abs : float
        delta_pct : float
        narrative : str
    """
    try:
        from dartlab.analysis.valuation.dFV import calcDFV
    except ImportError:
        return {"error": "dFV 모듈 접근 불가"}

    invalid = [k for k in overrides if k not in _SUPPORTED_KEYS]
    if invalid:
        return {
            "error": f"지원 안 되는 key: {invalid}",
            "supported": list(_SUPPORTED_KEYS.keys()),
        }

    base = calcDFV(company, basePeriod=basePeriod)
    if not base or not base.get("dFV"):
        return {"error": "baseline dFV 계산 실패"}

    scenario = calcDFV(company, basePeriod=basePeriod, overrides=overrides)
    if not scenario or not scenario.get("dFV"):
        return {"error": "scenario dFV 계산 실패", "overrides": overrides}

    base_dfv = base["dFV"]
    sc_dfv = scenario["dFV"]
    delta_abs = sc_dfv - base_dfv
    delta_pct = delta_abs / base_dfv * 100 if base_dfv else 0

    applied_parts = [f"{k}={v}" for k, v in overrides.items()]
    narrative = (
        f"What-if ({', '.join(applied_parts)}) → "
        f"dFV {base_dfv:,.0f} → {sc_dfv:,.0f} "
        f"({'+' if delta_pct >= 0 else ''}{delta_pct:.1f}%)"
    )

    return {
        "baseline": {"dFV": base_dfv, "primaryModel": base.get("primaryModel")},
        "scenario": {
            "dFV": sc_dfv,
            "primaryModel": scenario.get("primaryModel"),
            "overrides_applied": overrides,
        },
        "delta_abs": round(delta_abs, 0),
        "delta_pct": round(delta_pct, 2),
        "narrative": narrative,
    }


def runSensitivityGrid(
    company: Any,
    *,
    key: str,
    values: list[float],
    basePeriod: str | None = None,
) -> list[dict]:
    """한 변수의 여러 값에 대해 dFV 반응 — 민감도 그리드.

    Parameters
    ----------
    key : dFV override 키 (wacc, terminalGrowth 등)
    values : 테스트할 값 리스트

    Returns
    -------
    list[dict] — [{value, dFV, delta_pct_vs_baseline}, ...]
    """
    if key not in _SUPPORTED_KEYS:
        return []

    try:
        from dartlab.analysis.valuation.dFV import calcDFV
    except ImportError:
        return []

    base = calcDFV(company, basePeriod=basePeriod)
    if not base or not base.get("dFV"):
        return []
    base_dfv = base["dFV"]

    grid = []
    for v in values:
        result = calcDFV(company, basePeriod=basePeriod, overrides={key: v})
        if result and result.get("dFV"):
            dfv = result["dFV"]
            delta_pct = (dfv - base_dfv) / base_dfv * 100 if base_dfv else 0
            grid.append({"value": v, "dFV": dfv, "delta_pct": round(delta_pct, 2)})
        else:
            grid.append({"value": v, "dFV": None, "delta_pct": None})

    return grid
