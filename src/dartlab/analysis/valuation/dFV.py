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

# ── 헬퍼 (분리: _dFVHelpers.py SSOT, re-export 으로 BC 보존) ──
from dartlab.analysis.valuation._dFVHelpers import (
    _DFV_OVERRIDE_ALLOWED_KEYS,
    _MODEL_SENSITIVITY,
    _SELECTOR_IGNORE,
    _dfvApplyConsistency,
    _dfvApplyGoingConcern,
    _dfvApplyLiquidation,
    _dfvApplyOverrideMeta,
    _dfvApplyRealOptions,
    _dfvApplyTwoStage,
    _dfvCheckRelativeExtreme,
    _dfvEarlyDispatch,
    _selectPrimaryWithOverrides,
)
from dartlab.analysis.valuation._dFVTsd import (
    _tsdBuildPhases,
    _tsdExtractBaseFcf,
    _tsdExtractNetDebtShares,
    _tsdMaybeNormalizeFcf,
    _tsdResolveHighGrowth,
    _tsdResolveTerminalGrowth,
    _tsdResolveWacc,
)


def calcDFV(
    company: Any,
    *,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict | None:
    """dartlab Fair Value v2 — 기업유형 × 생애주기 × 다중 모델 삼각검증.

    Capabilities:
        Company 의 기업유형 (early/growth/mature/decline) × 생애주기 단계로
        primary 모델 (DCF/DDM/RIM/EV-EBITDA/PSR 등) 자동 선택, secondary 2 개
        cross-check + Damodaran qualityWACC 조정 + DDM dividend floor + 청산
        가치 안전망까지 결합한 단일 적정주가 산출.

    Args:
        company: Company 객체. ``finance``, ``stockCode``, ``currency``,
            ``benchmark`` (선택) 속성 필요.
        basePeriod: 기준 기간 (예 ``"2024Q4"``). ``None`` 이면 최신.
        overrides: AI/사용자 가정 override dict. 지원 키:
            - ``wacc`` (float): 강제 WACC
            - ``terminalGrowth`` (float): 영구성장률 강제
            - ``primaryModel`` (str): primary 모델 강제
            - ``lifeCyclePhase`` (str): 생애주기 강제
            - ``impliedERP``/``bottomUpBeta``/``countryCode``: WACC 산출 chain

    Returns:
        dict | None:
            - ``dFV`` (float): 적정주가 base (원)
            - ``scenarios`` (dict): ``{bull, base, bear}`` 시나리오 적정가
            - ``currentPrice`` (float|None)
            - ``upside`` (float): 적정 대비 (%)
            - ``opinion`` (str): 의견 ("강력매수"/"매수"/"중립"/"매도"/"강력매도")
            - ``confidence`` (str): 신뢰도 ("high"/"medium"/"low")
            - ``primaryModel`` (str): 사용된 primary 모델명
            - ``companyType`` (str|None)
            - ``triangulation`` (dict): 삼각검증 결과 (3 방법론 일치도)
            - ``dividendFloor`` (dict|None): DDM 하한
            - ``qualityWACC`` (dict): WACC 조정 상세
            - ``allMethods`` (dict): 모든 방법론 적정가 (참고용)
            - ``overrideApplied`` (dict|None): 적용된 override
            - ``survival`` (dict|None): 부도확률 기반 going-concern 가중
        데이터 부족 (BS/IS/CF 누락) 시 ``None``.

    Raises:
        없음 — 내부 catch.

    Example:
        >>> from dartlab import Company
        >>> r = calcDFV(Company("005930"), overrides={"wacc": 8.5})
        >>> r["dFV"], r["opinion"]
        (75000.0, '매수')

    Guide:
        primary 모델 선택 표 (fitness.selectModels): earlyGrowth/highGrowth →
        DCF (FCF 기반), mature → EV-EBITDA + DDM, decline → 청산가치 + DDM.
        secondary 2 개 cross-check 후 triangulation 일치도 ±25% 내면
        confidence=high.

    SeeAlso:
        - ``dartlab.analysis.valuation.dcf.dcfValuation``: DCF 단독
        - ``dartlab.analysis.valuation.dcf.ddmValuation``: DDM 단독
        - ``dartlab.synth.distress.survival.applySurvivalWeight``: distress 가중
        - ``dartlab.synth.riskPremiums.loadDamodaranERP``: ERP 룩업

    Requires:
        Company.finance (BS/IS/CF 시계열) + 종가 + analysis.financial 의 다수
        헬퍼 (ratios, valuation, growth, investment, proforma).

    AIContext:
        ``upside`` 만 단독 인용 금지 — primaryModel + triangulation 일치도 +
        confidence 셋 함께 노출. ``opinion`` 라벨은 사용자 향 표시이지 시장
        actionable signal 이 아님 (전문가 검토 필수).

    LLM Specifications:
        AntiPatterns:
            - upside 30%+ 인데 confidence="low" 결과를 그대로 인용 — 단일
              모델 의존 신호. triangulation 일치도 확인 필수.
            - overrides 키 추측 — 위 5 키만 적용됨, 나머지는 무시.
            - companyType "financial" 인데 DCF 강제 (overrides=primaryModel)
              금지 — 금융업은 RIM/DDM 만 의미.
        OutputSchema:
            상기 13 키 dict 또는 None. scenarios dict 는 bull/base/bear 3 키.
        Prerequisites:
            Company.finance + 종가 (gather("price")) + analysis 헬퍼 모듈.
        Freshness:
            finance = 최신 분기 (마감 후 30~45 일). 종가 = T+1.
        Dataflow:
            company → fitness.selectModels → primary/secondary 호출 →
            qualityWACC 조정 → applySurvivalWeight → triangulate → opinion.
        TargetMarkets: KR (DART), US (EDGAR).
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
