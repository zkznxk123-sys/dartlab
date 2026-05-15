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

# Phase 12 A1: Smart Primary Selector — override 감응성 매트릭스.
# override 가 들어올 때 primary 가 무감각 모델이면 감응 모델로 자동 전환.
_MODEL_SENSITIVITY: dict[str, set[str]] = {
    "dcf": {"wacc", "terminalGrowth", "growthRates", "countryCode"},
    "dcf2stage": {
        "wacc",
        "terminalGrowth",
        "growthRates",
        "marginPath",
        "reinvestmentPath",
        "countryCode",
    },
    "ddm": {"terminalGrowth"},
    "rim": {"wacc", "countryCode"},
    "relative": set(),  # PER/PBR — override 무감각
    "relativeSurvival": set(),
    "liquidation": {"liquidationValue", "liquidationDiscount"},
}

_SELECTOR_IGNORE = {"primaryModel", "lifeCyclePhase", "companyType", "pSurvival", "impliedERP", "bottomUpBeta"}


def _selectPrimaryWithOverrides(
    selected: str,
    allMethods: dict,
    overrides: dict,
) -> tuple[str, str | None]:
    """override 가 실제 영향 주는 primary 자동 선택.

    Returns
    -------
    (primary_key, reason) — reason not None 이면 자동 전환됨.
    """
    if not overrides:
        return selected, None
    ov_keys = {k for k in overrides if k not in _SELECTOR_IGNORE and not k.startswith("_")}
    if not ov_keys:
        return selected, None

    sensitivities = _MODEL_SENSITIVITY.get(selected, set())
    if sensitivities & ov_keys:
        return selected, None  # 현재 primary 이미 감응

    # 감응 대안 모델 중 값 있는 것 선택
    for cand in ("dcf2stage", "dcf", "rim", "ddm"):
        if cand in allMethods and allMethods[cand] and allMethods[cand] > 0:
            cand_sens = _MODEL_SENSITIVITY.get(cand, set())
            if cand_sens & ov_keys:
                return cand, f"{selected}→{cand} (override {sorted(ov_keys)} 반영)"
    return selected, None


def _dfvEarlyDispatch(company: Any, basePeriod: str | None, ov: dict) -> dict | None:
    """금융업/지주사 자동 분기 — Bank Excess Return / SOTP NAV.

    Returns
    -------
    dict | None
        Bank DFV (isFinancialCompany) 또는 Holding SOTP (upside |≤100%|)
        valid result. 해당 없으면 None (일반 dispatch 진행).
    """
    try:
        from dartlab.analysis.valuation.bankDFV import calcBankDFV, isFinancialCompany

        if isFinancialCompany(company):
            bank_result = calcBankDFV(company, basePeriod=basePeriod, overrides=ov)
            if bank_result and bank_result.get("dFV"):
                return bank_result
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    try:
        from dartlab.analysis.financial.companyType import _checkHolding
        from dartlab.analysis.valuation.sotp import calcHoldingDFV

        if _checkHolding(company):
            sotp_result = calcHoldingDFV(company, basePeriod=basePeriod, overrides=ov)
            if sotp_result and sotp_result.get("dFV"):
                up = sotp_result.get("upside")
                if up is None or abs(up) <= 100:
                    return sotp_result
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return None


def _dfvCheckRelativeExtreme(
    company: Any,
    primaryKey: str,
    primaryValue: float,
    secondaryKeys: list,
    allMethods: dict,
) -> tuple[str, float]:
    """primary=relative 가 현재가 ±150% 이탈 시 secondary 중 현재가 근접 모델로 교체.

    Returns
    -------
    tuple[str, float]
        (new_primary_key, new_primary_value). 정상 범위면 그대로 반환.
    """
    if primaryKey not in ("relative", "relativeSurvival"):
        return primaryKey, primaryValue
    try:
        cp = _getCurrentPrice(company)
        if not (cp and cp > 0):
            return primaryKey, primaryValue
        ratio = primaryValue / cp
        if not (ratio > 2.5 or ratio < 0.4):
            return primaryKey, primaryValue
        sec_candidates: list[tuple[str, float, float]] = []
        for sk in secondaryKeys:
            sv = allMethods.get(sk)
            if sv and sv > 0:
                sec_candidates.append((sk, sv, abs(sv / cp - 1.0)))
        if sec_candidates:
            sec_candidates.sort(key=lambda x: x[2])
            return sec_candidates[0][0], sec_candidates[0][1]
    except (AttributeError, ValueError, TypeError, ZeroDivisionError):
        pass
    return primaryKey, primaryValue


def _dfvApplyGoingConcern(out: dict, goingConcern: float | None, survival: dict | None) -> None:
    """Going concern + Survival 가중 결과를 out 에 in-place 추가."""
    if goingConcern is not None:
        out["goingConcernValue"] = round(goingConcern)
    if survival is not None:
        out["survival"] = {
            "pSurvival": survival.get("pSurvival"),
            "liquidationValue": round(survival["liquidationValue"]) if survival.get("liquidationValue") else None,
            "adjustedUplift": survival.get("uplift"),
        }


def _dfvApplyTwoStage(out: dict, twoStageDetail: dict | None) -> None:
    """Two-Stage DCF 상세를 out['twoStage'] 에 추가."""
    if not twoStageDetail:
        return
    out["twoStage"] = {
        "growthYears": twoStageDetail.get("growthYears"),
        "growthRates": twoStageDetail.get("growthRates"),
        "terminalGrowthRate": twoStageDetail.get("terminalGrowthRate"),
        "pvExplicit": twoStageDetail.get("pvExplicit"),
        "pvTerminal": twoStageDetail.get("pvTerminal"),
        "tvShare": twoStageDetail.get("tvShare"),
        "phases": twoStageDetail.get("phases") or [],
        "marginPath": twoStageDetail.get("marginPath"),
        "reinvestmentPath": twoStageDetail.get("reinvestmentPath"),
        "warnings": twoStageDetail.get("warnings") or [],
    }


def _dfvApplyRealOptions(out: dict, company: Any, basePeriod: str | None, ov: dict) -> None:
    """Real Options 값 — appliedAs 에 따라 uplift(bull) or floor 로 반영."""
    try:
        from dartlab.analysis.valuation.realOptions import calcRealOptionsValue

        ro = calcRealOptionsValue(company, basePeriod=basePeriod, overrides=ov)
        if ro and ro.get("optionValue") is not None:
            out["realOptions"] = ro
            if ro.get("appliedAs") == "uplift":
                out["scenarios"]["bull"] = round(out["scenarios"]["bull"] + ro["optionValue"])
            elif ro.get("appliedAs") == "floor":
                out["realOptionsFloor"] = ro.get("K")
    except (ImportError, AttributeError, ValueError, TypeError):
        pass


def _dfvApplyLiquidation(out: dict, liquidationDetail: dict | None) -> None:
    """Liquidation 상세를 out['liquidation'] 에 추가."""
    if not liquidationDetail:
        return
    out["liquidation"] = {
        "recoveries": liquidationDetail.get("recoveries"),
        "grossRecovery": liquidationDetail.get("grossRecovery"),
        "netToEquity": liquidationDetail.get("netToEquity"),
        "perShare": liquidationDetail.get("perShare"),
        "weightedRecoveryRate": liquidationDetail.get("weightedRecoveryRate"),
    }


def _dfvApplyConsistency(out: dict, consistency: dict | None) -> None:
    """Cash flow consistency 플래그를 out 에 평탄화 추가."""
    if not consistency:
        return
    out["consistencyFlags"] = consistency.get("flags", [])
    out["consistencyScore"] = consistency.get("score")
    out["consistencySeverity"] = consistency.get("severity")


_DFV_OVERRIDE_ALLOWED_KEYS = (
    "wacc",
    "terminalGrowth",
    "primaryModel",
    "lifeCyclePhase",
    "pSurvival",
    "liquidationValue",
    "liquidationDiscount",
    "countryCode",
    "countryRiskPremium",
)


def _dfvApplyOverrideMeta(out: dict, ov: dict, primarySwitchReason: str | None) -> None:
    """적용된 override + 자동 전환 메타데이터 기록."""
    if ov:
        out["overrideApplied"] = {k: v for k, v in ov.items() if k in _DFV_OVERRIDE_ALLOWED_KEYS}
    if primarySwitchReason:
        out.setdefault("overrideApplied", {})["primaryAutoSwitch"] = primarySwitchReason


def calcDFV(
    company: Any,
    *,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict | None:
    """dartlab Fair Value v2.

    Parameters
    ----------
    overrides : dict | None
        AI/사용자 가정 override. wacc, terminalGrowth, primaryModel 키 지원.

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
        overrideApplied : dict | None — 적용된 override (있으면)
    """
    from dartlab.synth.overrides import applyOverride

    ov = overrides or {}

    special = _dfvEarlyDispatch(company, basePeriod, ov)
    if special is not None:
        return special

    # 1. 기업유형 × 생애주기 → primary/secondary 선택
    from dartlab.analysis.valuation.fitness import selectModels

    forced_phase = applyOverride(None, "lifeCyclePhase", ov)
    models = selectModels(company, lifeCyclePhase=forced_phase)
    primaryKey = applyOverride(models["primary"], "primaryModel", ov)
    secondaryKeys = models["secondary"]
    survival_adj = bool(models.get("survivalAdj", False))
    lifePhase = models.get("lifeCyclePhase")

    # 2. 모든 방법론 적정가 수집 (+ liquidation 자산별 + dcf2stage 실로직)
    allMethods = _collectAllValues(company, basePeriod)

    # 2a. Liquidation — 자산별 회수율 (Damodaran Dark Side Ch.9)
    liquidationDetail = _calcLiquidationDetail(company, ov)
    if liquidationDetail and liquidationDetail.get("perShare"):
        allMethods["liquidation"] = liquidationDetail["perShare"]

    # 2b. Two-Stage DCF — 고성장 n년 명시적 + terminal 수렴 (Damodaran Ch.12)
    twoStageDetail = _calcTwoStageDcf(company, lifePhase, ov)
    if twoStageDetail and twoStageDetail.get("perShare"):
        allMethods["dcf2stage"] = twoStageDetail["perShare"]

    # 2c. relativeSurvival — relative 값 재사용 (survival 가중은 하단)
    if "relative" in allMethods and "relativeSurvival" not in allMethods:
        allMethods["relativeSurvival"] = allMethods["relative"]
    if not allMethods:
        return None

    # Phase 12 A1: Smart Primary Selector — override 가 있고 현재 primary 가 무감각이면 자동 전환
    primaryKey, _primary_switch_reason = _selectPrimaryWithOverrides(primaryKey, allMethods, ov)

    # 3. Quality-Adjusted WACC
    baseWacc = _getBaseWACC(company)
    baseWacc = applyOverride(baseWacc, "wacc", ov)
    from dartlab.analysis.valuation.qualityWACC import calcQualityWACC

    qw = calcQualityWACC(company, baseWacc, basePeriod=basePeriod)
    adjusted_wacc = qw["adjustedWACC"]

    # 4. Primary 모델 값 = dFV (Base)
    primaryValue = allMethods.get(primaryKey)

    # primary가 없으면 fallback: 가장 적합도 높은 방법론 사용
    if primaryValue is None:
        from dartlab.analysis.valuation.fitness import calcMethodFitness

        fit = calcMethodFitness(company, basePeriod=basePeriod)
        candidates = {k: v for k, v in allMethods.items() if v and v > 0}
        best_key = max(candidates.keys(), key=lambda k: fit.get(k, {}).get("fitness", 0), default=None)
        if best_key:
            primaryKey = best_key
            primaryValue = allMethods[best_key]
        else:
            return None

    if primaryValue is None or primaryValue <= 0:
        return None

    primaryKey, primaryValue = _dfvCheckRelativeExtreme(company, primaryKey, primaryValue, secondaryKeys, allMethods)

    # 5. Bull/Base/Bear 시나리오 (WACC ±1%p 효과 근사)
    # WACC 1%p 변화 ≈ 적정가 ±10~15% (경험칙)
    wacc_effect = 0.12  # 12% per 1%p WACC change
    bull = primaryValue * (1 + wacc_effect)
    bear = primaryValue * (1 - wacc_effect)

    # 6. 삼각검증
    triangulation = _triangulate(primaryKey, primaryValue, secondaryKeys, allMethods)

    # 7. DDM floor
    ddm_floor = None
    ddm_value = allMethods.get("ddm")
    if ddm_value and ddm_value > 0 and models["ddmRole"] == "floor":
        ddm_floor = {
            "value": round(ddm_value),
            "meaning": f"배당만으로도 최소 {ddm_value:,.0f}원의 가치",
            "coverageRatio": round(ddm_value / primaryValue, 2) if primaryValue > 0 else 0,
        }

    # 8. Survival 가중 (Dark Side of Valuation)
    survival = None
    adjusted_primary = primaryValue
    goingConcern = None
    if survival_adj:
        survival = _applySurvivalAdjustment(company, primaryValue, ov)
        if survival and survival.get("adjustedValue") is not None:
            goingConcern = primaryValue
            adjusted_primary = survival["adjustedValue"]

    # 9. 현재가 + upside (survival 반영한 adjusted_primary 기준)
    currentPrice = _getCurrentPrice(company)
    upside = (adjusted_primary - currentPrice) / currentPrice * 100 if currentPrice and currentPrice > 0 else None

    # 10. 신뢰도 + 의견
    confidence = triangulation.get("confidence", "low")
    opinion = _calcOpinion(upside)

    # 11. Cash Flow Consistency 검증
    consistency = _buildConsistency(company, primaryKey, primaryValue, triangulation, adjusted_wacc, ov)

    out = {
        "dFV": round(adjusted_primary),
        "scenarios": {"bull": round(bull), "base": round(adjusted_primary), "bear": round(bear)},
        "currentPrice": round(currentPrice) if currentPrice else None,
        "upside": round(upside, 1) if upside is not None else None,
        "opinion": opinion,
        "confidence": confidence,
        "primaryModel": primaryKey,
        "companyType": models.get("companyType"),
        "lifeCyclePhase": lifePhase,
        "triangulation": triangulation,
        "dividendFloor": ddm_floor,
        "qualityWACC": qw,
        "allMethods": {k: round(v) for k, v in allMethods.items()},
    }
    _dfvApplyGoingConcern(out, goingConcern, survival)
    _dfvApplyTwoStage(out, twoStageDetail)
    _dfvApplyRealOptions(out, company, basePeriod, ov)
    _dfvApplyLiquidation(out, liquidationDetail)
    _dfvApplyConsistency(out, consistency)
    _dfvApplyOverrideMeta(out, ov, _primary_switch_reason)
    return out


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
    """기본 WACC 추출 — Phase 4 G12: CAPM 기반 우선, 섹터 fallback.

    기존은 sectorParams.discountRate (대기업 10% 고정) 만 사용 → 삼성 AA급에 과도.
    Phase 4: `_estimateWacc` (CAPM + 시총 감쇠 + country) 우선 → 하한 4% 경계 반영.
    """
    # 1순위: CAPM 기반 (compute_company_wacc 경유)
    try:
        from dartlab.analysis.financial.investmentAnalysis import _estimateWacc

        w = _estimateWacc(company)
        if w is not None and 3.0 <= w <= 25.0:
            return float(w)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    # 2순위: sectorParams (기존 fallback)
    try:
        from dartlab.analysis.valuation.dcf import _getSectorParams

        si = getattr(company, "sector", None)
        params = _getSectorParams(si.sector if si else None, si.industryGroup if si else None) if si else None
        if params:
            return params.discountRate
    except (ImportError, AttributeError):
        pass
    return 10.0  # 최종 fallback


def _triangulate(primaryKey: str, primaryValue: float, secondaryKeys: list[str], allMethods: dict) -> dict:
    """삼각검증 — primary와 secondary 괴리 체크."""
    checks = []
    for key in secondaryKeys:
        sec_value = allMethods.get(key)
        if sec_value is None or sec_value <= 0:
            continue
        divergence = abs(primaryValue - sec_value) / primaryValue
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
    """현재 주가 추출 — currentPrice 속성 우선, 없으면 gather 경유.

    Returns
    -------
    float | None
        현재 주가 (원). 조회 실패 시 None.
    """
    try:
        price = getattr(company, "currentPrice", None)
        if price:
            return float(price)
        from dartlab.core.di import getMacroProvider

        g = getMacroProvider().getDefaultGather()
        p = g("price", getattr(company, "stockCode", ""))
        if p is not None and hasattr(p, "height") and p.height > 0:
            return float(p["close"][-1])
    except (ImportError, AttributeError, ValueError, TypeError, KeyError):
        pass
    return None


def _calcOpinion(upside: float | None) -> str:
    """upside 기반 투자 의견 산출.

    Returns
    -------
    str
        "강력매수" | "매수" | "보유" | "매도" | "강력매도" | "판단 불가".
    """
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


def _calcLiquidationValue(company: Any, overrides: dict) -> float | None:
    """Simple 청산가치 — survival weighting 용 (book × (1-discount))."""
    from dartlab.synth.overrides import applyOverride

    explicit = applyOverride(None, "liquidationValue", overrides)
    if explicit is not None:
        return float(explicit)

    try:
        bs = company.select("BS", ["자본총계", "총발행주식수"])
        from dartlab.core.utils.helpers import toDictBySnakeId

        parsed = toDictBySnakeId(bs)
        if not parsed:
            return None
        data, periods = parsed
        if not periods:
            return None
        latest = periods[0]
        equity = (data.get("total_stockholders_equity") or {}).get(latest)
        shares = (data.get("outstanding_shares") or {}).get(latest)
        if not equity or not shares or shares <= 0:
            return None
        discount = applyOverride(0.25, "liquidationDiscount", overrides)
        discount = max(0.0, min(0.7, float(discount)))
        return (equity * (1 - discount)) / shares
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        return None


def _inferShares(company: Any) -> int | None:
    """기존 calcDcf 결과의 equityValue / perShareValue 로 주식수 역산.

    BS 에 outstanding_shares 가 없는 경우 대응 (KRX 메타 의존 회피).
    """
    try:
        from dartlab.analysis.financial.valuation import calcDcf

        r = calcDcf(company)
        if isinstance(r, dict):
            eq = r.get("equityValue")
            ps = r.get("perShareValue")
            if eq and ps and ps > 0:
                return int(eq / ps)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return None


def _calcLiquidationDetail(company: Any, overrides: dict) -> dict | None:
    """Damodaran 자산별 회수율 청산가치 (Dark Side Ch.9)."""
    try:
        from dartlab.analysis.valuation.dcf import liquidationValuation
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return None

    try:
        bs = company.select(
            "BS",
            [
                "현금및현금성자산",
                "매출채권",
                "재고자산",
                "유형자산",
                "무형자산",
                "자산총계",
                "부채총계",
            ],
        )
        parsed = toDictBySnakeId(bs)
        if not parsed:
            return None
        data, periods = parsed
        if not periods:
            return None
        latest = periods[0]

        def _get(*keys: str) -> float:
            """BS 다중 키에서 첫 번째 유효 값 추출 (None → 0)."""
            for k in keys:
                v = (data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return 0.0

        cash = _get("cash_and_cash_equivalents", "cash_and_equivalents")
        receivables = _get("trade_receivables", "trade_and_other_receivables", "매출채권")
        inventory = _get("inventories", "재고자산")
        tangible = _get("tangible_assets", "유형자산")
        intangible = _get("intangible_assets", "무형자산")
        total_assets = _get("total_assets", "자산총계")
        total_liab = _get("total_liabilities", "부채총계")
        shares = _inferShares(company)

        other = max(0.0, total_assets - cash - receivables - inventory - tangible - intangible)

        return liquidationValuation(
            cash=cash,
            receivables=receivables,
            inventory=inventory,
            tangibleAssets=tangible,
            intangibleAssets=intangible,
            otherAssets=other,
            totalLiabilities=total_liab,
            shares=shares,
        )
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        return None


def _tsdResolveWacc(company: Any, overrides: dict) -> float:
    """WACC 해결 — override chain (forced/implied/bottomUp/country) → roic fallback → 9.0.

    Returns
    -------
    float
        Phase 4 G13 우선순위: forced wacc → Damodaran override path (compute_company_wacc)
        → calcRoicTimeline waccEstimate → 9.0 (최종 폴백).
    """
    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return 9.0

    forced_wacc = applyOverride(None, "wacc", overrides)
    implied_flag = applyOverride(False, "impliedERP", overrides)
    bottom_up_flag = applyOverride(False, "bottomUpBeta", overrides)
    country_code = applyOverride(None, "countryCode", overrides)

    if forced_wacc is not None:
        return float(forced_wacc)

    if implied_flag or bottom_up_flag or country_code:
        try:
            from dartlab.analysis.financial.proforma import computeCompanyWacc

            series = None
            try:
                series = getattr(company, "_series", None)
                if series is None and hasattr(company, "_finance"):
                    series = getattr(company._finance, "series", None)
            except (AttributeError, ValueError):
                series = None

            if series:
                wacc_val, _details = computeCompanyWacc(
                    series,
                    currency=getattr(company, "currency", "KRW"),
                    country=country_code,
                    impliedErp=bool(implied_flag),
                    bottomUpBeta=bool(bottom_up_flag),
                )
                return float(wacc_val)
        except (ImportError, AttributeError, ValueError, TypeError):
            pass

    try:
        roic = calcRoicTimeline(company)
        if roic and roic.get("history"):
            v = roic["history"][0].get("waccEstimate")
            if v is not None:
                return float(v)
    except (AttributeError, ValueError, TypeError):
        pass

    return 9.0


def _tsdResolveHighGrowth(company: Any) -> float:
    """매출 CAGR 기반 고성장률 — 기본 8.0%, clamp [-5%, 25%].

    Returns
    -------
    float
        calcGrowthTrend cagr.revenue → 폴백 8.0 → 상·하한 clamp.
    """
    try:
        from dartlab.analysis.financial.growthAnalysis import calcGrowthTrend
    except ImportError:
        return 8.0
    highG: float | None = None
    try:
        g = calcGrowthTrend(company)
        if g:
            highG = (g.get("cagr") or {}).get("revenue")
    except (AttributeError, ValueError, TypeError):
        pass
    if highG is None:
        highG = 8.0
    return max(-5.0, min(highG, 25.0))


def _tsdBuildPhases(lifePhase: str | None, highG: float, overrides: dict) -> tuple[list[int], list[float]]:
    """lifeCycle 별 phase 구성 (Damodaran Ch.12) + growthRates override.

    Returns
    -------
    (years_vec, rates_vec)
        phase 별 연수 리스트 와 성장률 리스트. growthRates override 있으면 교체
        (연수 는 10년 을 len 으로 균등 분할).
    """
    try:
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return [5], [highG]

    phase_config: dict[str, tuple[list[int], list[float]]] = {
        "earlyGrowth": ([5, 3, 2], [highG, highG * 0.5, highG * 0.2]),
        "highGrowth": ([5, 3, 2], [highG, highG * 0.7, highG * 0.4]),
        "matureGrowth": ([4], [min(highG, 8.0)]),
        "matureStable": ([3], [min(highG, 3.0)]),
        "decline": ([2], [min(highG, -2.0) if highG < 0 else min(highG, 0.0)]),
        "turnaround": ([5], [highG]),
    }
    years_vec, rates_vec = phase_config.get(lifePhase or "", ([5], [highG]))

    rates_override = applyOverride(None, "growthRates", overrides)
    if isinstance(rates_override, list) and rates_override:
        rates_vec = rates_override
        if len(years_vec) != len(rates_vec):
            years_vec = [max(1, 10 // len(rates_vec))] * len(rates_vec)

    return years_vec, rates_vec


def _tsdResolveTerminalGrowth(lifePhase: str | None, company: Any, overrides: dict) -> float:
    """영구성장률 — Phase 4 G12.3 phase 별 Rf 감쇠 매핑 + terminalGrowth override.

    Returns
    -------
    float
        Damodaran ERP riskFreeRate 기준 phase 별 감쇠값. override 있으면 우선.
    """
    try:
        from dartlab.synth.overrides import applyOverride
        from dartlab.synth.riskPremiums import loadDamodaranERP
    except ImportError:
        return 2.5

    currency = getattr(company, "currency", None)
    country = applyOverride(None, "countryCode", overrides)
    erp = loadDamodaranERP(countryCode=country, currency=currency)
    rf = erp["riskFreeRate"]
    tg_by_phase = {
        "earlyGrowth": max(2.0, rf - 0.5),
        "highGrowth": max(2.0, rf - 1.0),
        "matureGrowth": max(2.0, rf - 1.5),
        "matureStable": max(1.5, rf - 2.0),
        "decline": 0.5,
        "turnaround": max(2.0, rf - 1.0),
    }
    tg_default = tg_by_phase.get(lifePhase or "", max(1.0, rf - 1.0))
    return float(applyOverride(tg_default, "terminalGrowth", overrides))


def _tsdExtractBaseFcf(company: Any) -> float | None:
    """최근 5개년 양수 FCF (ocf - |capex|) 중앙값 (mid-cycle) 추출.

    Returns
    -------
    float | None
        positives 리스트 의 median. 양수 FCF 하나도 없으면 None.
    """
    try:
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return None
    try:
        cf = company.select("CF", ["영업활동현금흐름", "유형자산의취득"])
        parsed = toDictBySnakeId(cf)
        if not parsed:
            return None
        data, periods = parsed
        ocf_row = data.get("operating_cashflow") or {}
        capex_row = data.get("purchase_of_property_plant_and_equipment") or {}
        annual_years = [p for p in periods if p.isdigit() and len(p) == 4][:5]
        fcf_history: list[float] = []
        for y in annual_years:
            o = ocf_row.get(y)
            cx = capex_row.get(y)
            if o:
                fcf_history.append(float(o) - abs(float(cx or 0)))
        positives = sorted([f for f in fcf_history if f > 0])
        if positives:
            return positives[len(positives) // 2]
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    return None


def _tsdMaybeNormalizeFcf(baseFcf: float, lifePhase: str | None, company: Any) -> float:
    """Phase 5 G16 — 사이클/회복/적자 이력 기업은 Normalized FCF 로 교체 (Damodaran Ch.22).

    Returns
    -------
    float
        needsNormalized False 이면 base_fcf 그대로, True 면 calcNormalizedFcf 결과.
    """
    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
        from dartlab.analysis.financial.normalized import calcNormalizedFcf, needsNormalized
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return baseFcf

    roic_history_data: list[dict] = []
    try:
        roic = calcRoicTimeline(company)
        if roic and roic.get("history"):
            roic_history_data = roic["history"]
    except (AttributeError, ValueError, TypeError):
        pass

    if not needsNormalized(lifePhase, roic_history_data):
        return baseFcf

    rev_history: list[float] = []
    margin_history: list[float] = []
    try:
        is_rev = company.select("IS", ["매출액", "영업이익"])
        is_parsed = toDictBySnakeId(is_rev)
        if is_parsed:
            is_data, is_periods = is_parsed
            rev_row = is_data.get("sales") or {}
            op_row = is_data.get("operating_profit") or {}
            annual_ys = [p for p in is_periods if p.isdigit() and len(p) == 4][:5]
            for y in annual_ys:
                rv = rev_row.get(y)
                op = op_row.get(y)
                if rv and isinstance(rv, (int, float)) and rv > 0:
                    rev_history.append(float(rv))
                    margin_history.append(float(op) / float(rv) if op else 0.0)
    except (AttributeError, KeyError, TypeError, ValueError):
        return baseFcf

    try:
        norm = calcNormalizedFcf(rev_history, margin_history)
        if norm["method"] != "skip" and norm["normalizedFcf"]:
            return float(norm["normalizedFcf"])
    except (AttributeError, ValueError, TypeError):
        pass
    return baseFcf


def _tsdExtractNetDebtShares(company: Any) -> tuple[float, float] | None:
    """순차입금 (단기+장기+사채 - 현금) + 발행주식수 추출.

    Returns
    -------
    (net_debt, shares) | None
        BS periods 없거나 예외 시 None.
    """
    try:
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return None
    try:
        bs = company.select("BS", ["단기차입금", "장기차입금", "사채", "현금및현금성자산"])
        parsed = toDictBySnakeId(bs)
        if not parsed:
            return None
        data, periods = parsed
        if not periods:
            return None
        latest = periods[0]

        def _g(*keys: str) -> float:
            """BS 다중 키에서 차입금 값 추출 (None → 0)."""
            for k in keys:
                v = (data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return 0.0

        net_debt = (
            _g("shortterm_borrowings", "short_term_borrowings", "short_term_debt")
            + _g("longterm_borrowings", "long_term_borrowings", "long_term_debt")
            + _g("debentures", "corporate_bonds", "사채")
            - _g("cash_and_cash_equivalents", "cash_and_equivalents")
        )
        shares = _inferShares(company)
        return net_debt, shares
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _calcTwoStageDcf(company: Any, lifePhase: str | None, overrides: dict) -> dict | None:
    """Damodaran Multi-stage DCF (Ch.12) — lifeCycle 별 phase 자동 구성.

    - earlyGrowth → 3-phase: [5, 3, 2]년 × [g_high, g_high×0.5, g_high×0.2]
    - highGrowth → 3-phase: [5, 3, 2]년 × [g_high, g_high×0.7, g_high×0.4]
    - matureGrowth / matureStable / decline → 단일 phase

    Returns
    -------
    dict | None
        multiStageDcf(...) 결과. 필수 데이터 (positive FCF / BS periods) 없으면 None.
    """
    try:
        from dartlab.analysis.valuation.dcf import multiStageDcf
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return None

    wacc = _tsdResolveWacc(company, overrides)
    highG = _tsdResolveHighGrowth(company)
    years_vec, rates_vec = _tsdBuildPhases(lifePhase, highG, overrides)
    terminal_g = _tsdResolveTerminalGrowth(lifePhase, company, overrides)

    margin_path = applyOverride(None, "marginPath", overrides)
    reinvestment_path = applyOverride(None, "reinvestmentPath", overrides)

    baseFcf = _tsdExtractBaseFcf(company)
    if not baseFcf or baseFcf <= 0:
        return None
    baseFcf = _tsdMaybeNormalizeFcf(baseFcf, lifePhase, company)

    nd_shares = _tsdExtractNetDebtShares(company)
    if nd_shares is None:
        return None
    net_debt, shares = nd_shares

    return multiStageDcf(
        baseFcf=baseFcf,
        growthYears=years_vec,
        growthRates=rates_vec,
        terminalGrowthRate=terminal_g,
        wacc=wacc,
        marginPath=margin_path,
        reinvestmentPath=reinvestment_path,
        netDebt=net_debt,
        shares=shares,
    )


def _applySurvivalAdjustment(company: Any, primaryValue: float, overrides: dict) -> dict | None:
    """Dark Side of Valuation — Going-Concern × pSurvival 가중.

    CHS 부도확률 (12M PD) 을 chsFeatures 경로로 실제 추출. 실패 시 safe_default 폴백.
    """
    try:
        from dartlab.synth.distress import applySurvivalWeight, calcSurvivalWeight, computeChsProbability
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return None

    forced_p = applyOverride(None, "pSurvival", overrides)
    discount_override = applyOverride(None, "liquidationDiscount", overrides)

    if forced_p is not None:
        survival_dict = calcSurvivalWeight(
            probability=max(0.0, min(1.0, float(forced_p))),
            liquidationDiscount=discount_override,
        )
    else:
        # CHS 실추출 — chsFeatures SSOT 경유
        chs_result = computeChsProbability(company)
        if chs_result:
            survival_dict = calcSurvivalWeight(
                probability=chs_result["probability"],
                zone=chs_result["zone"],
                liquidationDiscount=discount_override,
            )
        else:
            # safe_default 폴백
            survival_dict = calcSurvivalWeight(
                probability=None,
                zone=None,
                liquidationDiscount=discount_override,
            )

    # liquidation 값 — Damodaran 자산별 회수 detail 의 perShare 우선, 없으면 book × (1-discount)
    liq_detail = _calcLiquidationDetail(company, overrides)
    liq_per_share = None
    if liq_detail and liq_detail.get("perShare"):
        liq_per_share = liq_detail["perShare"]
    else:
        liq_per_share = _calcLiquidationValue(company, overrides)

    weighted = applySurvivalWeight(primaryValue, liq_per_share, survival_dict)
    if liq_per_share is not None:
        weighted["liquidationValue"] = liq_per_share
    weighted["pSurvival"] = survival_dict.get("pSurvival")
    weighted["source"] = survival_dict.get("source")
    weighted["annualHazard"] = survival_dict.get("annualHazard")
    return weighted


def _buildConsistency(
    company: Any,
    primaryKey: str,
    primaryValue: float,
    triangulation: dict,
    wacc: float | None,
    overrides: dict,
) -> dict | None:
    """Cash Flow Consistency 검증 — dFV 결과에 consistencyFlags 주입용."""
    try:
        from dartlab.analysis.valuation.consistency import calcCashFlowConsistency
        from dartlab.synth.overrides import applyOverride
    except ImportError:
        return None

    # ROIC 추출
    roic_pct: float | None = None
    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline

        roic_data = calcRoicTimeline(company)
        if roic_data and roic_data.get("history"):
            roic_pct = roic_data["history"][0].get("roic")
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    tg = applyOverride(None, "terminalGrowth", overrides)
    country = applyOverride(None, "countryCode", overrides)
    currency = getattr(company, "currency", None)

    models_used = 1 + len(triangulation.get("checks") or [])

    return calcCashFlowConsistency(
        roicPct=roic_pct,
        waccPct=wacc,
        terminalGrowthPct=tg,
        primaryModel=primaryKey,
        modelsUsed=models_used,
        country=country,
        currency=currency,
    )
