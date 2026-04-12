"""dFV (dartlab Fair Value) — 4엔진 통합 적정주가.

기존 DCF/RIM/DDM/상대가치를 "참고용 도구"로 두고,
각 방법론의 적합도(fitness) 가중 합산 + 질적 조정(quality adjustment)으로
dartlab만의 종합 적정주가를 산출한다.

dFV = Σ(방법론i × 적합도i) / Σ(적합도i) × (1 + 질적조정)
"""

from __future__ import annotations

from typing import Any


def calcDFV(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """dartlab Fair Value — 4엔진 통합 적정주가.

    Returns
    -------
    dict | None
        dFV : float — dartlab 적정주가
        currentPrice : float
        upside : float — %
        opinion : str — 강력매수/매수/보유/매도/강력매도
        confidence : str — high/medium/low
        confidenceInterval : list[float] — [하한, 상한]
        methods : dict — 방법론별 value/fitness/weight
        qualityAdjustment : float
        adjustmentFactors : list[dict]
    """
    # 1. 기존 방법론 적정가 수집
    methods = _collectMethodValues(company, basePeriod)
    if not methods:
        return None

    # 2. 적합도 산출
    from dartlab.analysis.valuation.fitness import calcMethodFitness

    fitness = calcMethodFitness(company, basePeriod=basePeriod)

    # 3. 적합도 가중 합산
    weighted_sum = 0.0
    fitness_sum = 0.0
    method_details = {}

    for key, value in methods.items():
        if value is None:
            continue
        fit = fitness.get(key, {}).get("fitness", 0.5)
        weighted_sum += value * fit
        fitness_sum += fit
        method_details[key] = {
            "value": round(value),
            "fitness": fit,
            "fitnessReason": fitness.get(key, {}).get("reason", ""),
            "weight": 0,  # 나중에 계산
        }

    if fitness_sum == 0:
        return None

    raw_value = weighted_sum / fitness_sum

    # 가중치 비율 역산
    for key in method_details:
        fit = method_details[key]["fitness"]
        method_details[key]["weight"] = round(fit / fitness_sum, 2)

    # 4. 질적 조정
    from dartlab.analysis.valuation.qualityAdjustment import calcQualityAdjustment

    qa = calcQualityAdjustment(company, basePeriod=basePeriod)
    total_adj = qa.get("totalAdjustment", 0)
    adjusted_value = raw_value * (1 + total_adj)

    # 5. 현재가 + upside
    current_price = _getCurrentPrice(company)
    if current_price and current_price > 0:
        upside = (adjusted_value - current_price) / current_price * 100
    else:
        upside = None

    # 6. 컨피던스 구간 (방법론간 σ 기반)
    values = [v for v in methods.values() if v is not None]
    if len(values) >= 2:
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        sigma = var**0.5
        ci_low = adjusted_value - sigma
        ci_high = adjusted_value + sigma
    else:
        ci_low = adjusted_value * 0.85
        ci_high = adjusted_value * 1.15

    # 7. 신뢰도 등급
    confidence = _calcConfidence(fitness_sum, values)

    # 8. 의견
    opinion = _calcOpinion(upside)

    return {
        "dFV": round(adjusted_value),
        "currentPrice": round(current_price) if current_price else None,
        "upside": round(upside, 1) if upside is not None else None,
        "opinion": opinion,
        "confidence": confidence,
        "confidenceInterval": [round(ci_low), round(ci_high)],
        "methods": method_details,
        "qualityAdjustment": total_adj,
        "adjustmentFactors": qa.get("factors", []),
        "rawAverage": round(raw_value),
    }


def _collectMethodValues(company: Any, basePeriod: str | None) -> dict:
    """기존 4개 방법론의 적정가(주당) 수집."""
    values: dict = {}

    # DCF
    try:
        from dartlab.analysis.valuation.valuation import calcValuationSynthesis

        synth = calcValuationSynthesis(company, basePeriod=basePeriod)
        if synth:
            dcf = synth.get("dcf", {})
            if dcf and dcf.get("perShareValue"):
                values["dcf"] = float(dcf["perShareValue"])
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # RIM
    try:
        from dartlab.analysis.valuation.residualIncome import calcRIM

        rim = calcRIM(company, basePeriod=basePeriod)
        if rim:
            iv = getattr(rim, "intrinsicValue", None)
            if iv is None and isinstance(rim, dict):
                iv = rim.get("intrinsicValue")
            if iv and iv > 0:
                values["rim"] = float(iv)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # DDM
    try:
        from dartlab.analysis.valuation.valuation import calcValuationSynthesis

        synth = calcValuationSynthesis(company, basePeriod=basePeriod)
        if synth:
            ddm = synth.get("ddm", {})
            if ddm and ddm.get("perShareValue"):
                values["ddm"] = float(ddm["perShareValue"])
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # 상대가치
    try:
        from dartlab.analysis.valuation.valuation import calcValuationSynthesis

        synth = calcValuationSynthesis(company, basePeriod=basePeriod)
        if synth:
            rel = synth.get("relative", {})
            if rel and rel.get("fairValue"):
                values["relative"] = float(rel["fairValue"])
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    return values


def _getCurrentPrice(company: Any) -> float | None:
    """현재 주가 조회."""
    try:
        price = getattr(company, "currentPrice", None)
        if price:
            return float(price)
        # gather 경로
        import dartlab

        p = dartlab.gather("price", getattr(company, "stockCode", ""))
        if p is not None and hasattr(p, "height") and p.height > 0:
            return float(p["close"][-1])
    except (ImportError, AttributeError, ValueError, TypeError, KeyError):
        pass
    return None


def _calcConfidence(fitness_sum: float, values: list[float]) -> str:
    """신뢰도 등급."""
    if len(values) < 2:
        return "low"

    mean = sum(values) / len(values)
    if mean == 0:
        return "low"

    cv = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5 / abs(mean)

    if fitness_sum > 2.5 and cv < 0.20:
        return "high"
    elif fitness_sum > 1.5 and cv < 0.40:
        return "medium"
    return "low"


def _calcOpinion(upside: float | None) -> str:
    """upside 기반 투자 의견."""
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
