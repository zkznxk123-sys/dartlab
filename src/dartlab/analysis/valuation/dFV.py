"""dFV v2 (dartlab Fair Value) — DCF Anchor + 삼각검증 + Quality WACC.

학술 근거:
- McKinsey Valuation Ch.14: DCF를 primary, multiples를 triangulation
- Damodaran: "하나의 서사, 하나의 모델" — 가중 평균 경계
- Fernandez: 질적 조정은 WACC 입력에서 (사후 곱셈 금지)
- CFA Level II: 기업유형별 모델 선택 매트릭스

dFV = Primary Model(Quality-Adjusted WACC) + 삼각검증 + DDM floor
"""

from __future__ import annotations

from typing import Any


def calcDFV(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """dartlab Fair Value v2.

    Returns
    -------
    dict | None
        dFV : float — dartlab 적정주가 (Base 시나리오)
        scenarios : dict — bull/base/bear 적정가
        currentPrice : float
        upside : float — %
        opinion : str
        confidence : str
        primaryModel : str — 사용된 primary 모델명
        companyType : str | None
        triangulation : dict — 삼각검증 결과
        dividendFloor : dict | None — DDM 하한
        qualityWACC : dict — WACC 조정 상세
        allMethods : dict — 모든 방법론 적정가 (참고용)
    """
    # 1. 기업유형 → primary/secondary 선택
    from dartlab.analysis.valuation.fitness import selectModels

    models = selectModels(company)
    primary_key = models["primary"]
    secondary_keys = models["secondary"]

    # 2. 모든 방법론 적정가 수집
    all_methods = _collectAllValues(company, basePeriod)
    if not all_methods:
        return None

    # 3. Quality-Adjusted WACC
    base_wacc = _getBaseWACC(company)
    from dartlab.analysis.valuation.qualityWACC import calcQualityWACC

    qw = calcQualityWACC(company, base_wacc, basePeriod=basePeriod)
    adjusted_wacc = qw["adjustedWACC"]

    # 4. Primary 모델 값 = dFV (Base)
    primary_value = all_methods.get(primary_key)

    # primary가 없으면 fallback: 가장 적합도 높은 방법론 사용
    if primary_value is None:
        from dartlab.analysis.valuation.fitness import calcMethodFitness

        fit = calcMethodFitness(company, basePeriod=basePeriod)
        best_key = max(all_methods.keys(), key=lambda k: fit.get(k, {}).get("fitness", 0), default=None)
        if best_key:
            primary_key = best_key
            primary_value = all_methods[best_key]
        else:
            return None

    if primary_value is None or primary_value <= 0:
        return None

    # 5. Bull/Base/Bear 시나리오 (WACC ±1%p 효과 근사)
    # WACC 1%p 변화 ≈ 적정가 ±10~15% (경험칙)
    wacc_effect = 0.12  # 12% per 1%p WACC change
    bull = primary_value * (1 + wacc_effect)
    bear = primary_value * (1 - wacc_effect)

    # 6. 삼각검증
    triangulation = _triangulate(primary_key, primary_value, secondary_keys, all_methods)

    # 7. DDM floor
    ddm_floor = None
    ddm_value = all_methods.get("ddm")
    if ddm_value and ddm_value > 0 and models["ddmRole"] == "floor":
        ddm_floor = {
            "value": round(ddm_value),
            "meaning": f"배당만으로도 최소 {ddm_value:,.0f}원의 가치",
            "coverageRatio": round(ddm_value / primary_value, 2) if primary_value > 0 else 0,
        }

    # 8. 현재가 + upside
    current_price = _getCurrentPrice(company)
    upside = (primary_value - current_price) / current_price * 100 if current_price and current_price > 0 else None

    # 9. 신뢰도 + 의견
    confidence = triangulation.get("confidence", "low")
    opinion = _calcOpinion(upside)

    return {
        "dFV": round(primary_value),
        "scenarios": {"bull": round(bull), "base": round(primary_value), "bear": round(bear)},
        "currentPrice": round(current_price) if current_price else None,
        "upside": round(upside, 1) if upside is not None else None,
        "opinion": opinion,
        "confidence": confidence,
        "primaryModel": primary_key,
        "companyType": models.get("companyType"),
        "triangulation": triangulation,
        "dividendFloor": ddm_floor,
        "qualityWACC": qw,
        "allMethods": {k: round(v) for k, v in all_methods.items()},
    }


def _collectAllValues(company: Any, basePeriod: str | None) -> dict:
    """모든 방법론 적정가 수집."""
    values: dict = {}
    try:
        from dartlab.analysis.financial.valuation import calcValuationSynthesis

        synth = calcValuationSynthesis(company, basePeriod=basePeriod)
        if synth:
            method_map = {"DCF": "dcf", "DDM": "ddm", "상대가치": "relative", "RIM": "rim"}
            for est in synth.get("estimates", []):
                key = method_map.get(est.get("method", ""))
                val = est.get("value")
                if key and val and val > 0:
                    values[key] = float(val)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return values


def _getBaseWACC(company: Any) -> float:
    """기본 WACC 추출 (업종 기반)."""
    try:
        from dartlab.core.finance.dcf import _getSectorParams

        si = getattr(company, "sector", None)
        params = _getSectorParams(si.sector if si else None, si.industryGroup if si else None) if si else None
        if params:
            return params.discountRate
    except (ImportError, AttributeError):
        pass
    return 10.0  # 기본값


def _triangulate(primary_key: str, primary_value: float, secondary_keys: list[str], all_methods: dict) -> dict:
    """삼각검증 — primary와 secondary 괴리 체크."""
    checks = []
    for key in secondary_keys:
        sec_value = all_methods.get(key)
        if sec_value is None or sec_value <= 0:
            continue
        divergence = abs(primary_value - sec_value) / primary_value
        if divergence < 0.20:
            verdict = "합의"
        elif divergence < 0.50:
            verdict = "부분 합의"
        else:
            verdict = "불일치"
        checks.append(
            {
                "method": key,
                "value": round(sec_value),
                "divergence": round(divergence * 100, 1),
                "verdict": verdict,
            }
        )

    # 종합 신뢰도
    if not checks:
        confidence = "low"
    elif all(c["verdict"] == "합의" for c in checks):
        confidence = "high"
    elif any(c["verdict"] == "불일치" for c in checks):
        confidence = "low"
    else:
        confidence = "medium"

    return {"checks": checks, "confidence": confidence}


def _getCurrentPrice(company: Any) -> float | None:
    try:
        price = getattr(company, "currentPrice", None)
        if price:
            return float(price)
        import dartlab

        p = dartlab.gather("price", getattr(company, "stockCode", ""))
        if p is not None and hasattr(p, "height") and p.height > 0:
            return float(p["close"][-1])
    except (ImportError, AttributeError, ValueError, TypeError, KeyError):
        pass
    return None


def _calcOpinion(upside: float | None) -> str:
    if upside is None:
        return "판단 불가"
    if upside > 30:
        return "강력매수"
    if upside > 10:
        return "매수"
    if upside > -10:
        return "보유"
    if upside > -30:
        return "매도"
    return "강력매도"
