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
    from dartlab.core.overrides import applyOverride

    ov = overrides or {}

    # G21 (Phase 6): 금융업 자동 분기 — Bank Excess Return 우선 (Damodaran Ch.21)
    try:
        from dartlab.analysis.valuation.bankDFV import calcBankDFV, isFinancialCompany

        if isFinancialCompany(company):
            bank_result = calcBankDFV(company, basePeriod=basePeriod, overrides=ov)
            if bank_result and bank_result.get("dFV"):
                return bank_result
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # G22 (Phase 6): 지주사 자동 분기 — SOTP NAV 우선 (Damodaran Ch.16)
    # SOTP upside 절대값 100% 초과 시 데이터 신뢰도 낮음 → 일반 dispatch 로 fallback
    try:
        from dartlab.analysis.valuation.sotp import calcHoldingDFV
        from dartlab.review.templates import _checkHolding

        if _checkHolding(company):
            sotp_result = calcHoldingDFV(company, basePeriod=basePeriod, overrides=ov)
            if sotp_result and sotp_result.get("dFV"):
                up = sotp_result.get("upside")
                if up is None or abs(up) <= 100:
                    return sotp_result
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # 1. 기업유형 × 생애주기 → primary/secondary 선택
    from dartlab.analysis.valuation.fitness import selectModels

    forced_phase = applyOverride(None, "lifeCyclePhase", ov)
    models = selectModels(company, lifeCyclePhase=forced_phase)
    primary_key = applyOverride(models["primary"], "primaryModel", ov)
    secondary_keys = models["secondary"]
    survival_adj = bool(models.get("survivalAdj", False))
    life_phase = models.get("lifeCyclePhase")

    # 2. 모든 방법론 적정가 수집 (+ liquidation 자산별 + dcf2stage 실로직)
    all_methods = _collectAllValues(company, basePeriod)

    # 2a. Liquidation — 자산별 회수율 (Damodaran Dark Side Ch.9)
    liquidation_detail = _calcLiquidationDetail(company, ov)
    if liquidation_detail and liquidation_detail.get("perShare"):
        all_methods["liquidation"] = liquidation_detail["perShare"]

    # 2b. Two-Stage DCF — 고성장 n년 명시적 + terminal 수렴 (Damodaran Ch.12)
    two_stage_detail = _calcTwoStageDcf(company, life_phase, ov)
    if two_stage_detail and two_stage_detail.get("perShare"):
        all_methods["dcf2stage"] = two_stage_detail["perShare"]

    # 2c. relativeSurvival — relative 값 재사용 (survival 가중은 하단)
    if "relative" in all_methods and "relativeSurvival" not in all_methods:
        all_methods["relativeSurvival"] = all_methods["relative"]
    if not all_methods:
        return None

    # 3. Quality-Adjusted WACC
    base_wacc = _getBaseWACC(company)
    base_wacc = applyOverride(base_wacc, "wacc", ov)
    from dartlab.analysis.valuation.qualityWACC import calcQualityWACC

    qw = calcQualityWACC(company, base_wacc, basePeriod=basePeriod)
    adjusted_wacc = qw["adjustedWACC"]

    # 4. Primary 모델 값 = dFV (Base)
    primary_value = all_methods.get(primary_key)

    # primary가 없으면 fallback: 가장 적합도 높은 방법론 사용
    if primary_value is None:
        from dartlab.analysis.valuation.fitness import calcMethodFitness

        fit = calcMethodFitness(company, basePeriod=basePeriod)
        candidates = {k: v for k, v in all_methods.items() if v and v > 0}
        best_key = max(candidates.keys(), key=lambda k: fit.get(k, {}).get("fitness", 0), default=None)
        if best_key:
            primary_key = best_key
            primary_value = all_methods[best_key]
        else:
            return None

    if primary_value is None or primary_value <= 0:
        return None

    # G23 (Phase 6): primary=relative 가 현재가 ±150% 이탈 시 secondary fallback
    # Damodaran Ch.10: 산업 multiple 일시 과열/저평가 → 단일 모델 의존 위험 회피
    if primary_key in ("relative", "relativeSurvival"):
        try:
            _cp_check = _getCurrentPrice(company)
            if _cp_check and _cp_check > 0:
                ratio = primary_value / _cp_check
                if ratio > 2.5 or ratio < 0.4:
                    # 과대/과소 의심 → secondary 후보 중 현재가 근접한 모델로 교체
                    sec_candidates: list[tuple[str, float, float]] = []
                    for sk in secondary_keys:
                        sv = all_methods.get(sk)
                        if sv and sv > 0:
                            sr = sv / _cp_check
                            sec_candidates.append((sk, sv, abs(sr - 1.0)))
                    if sec_candidates:
                        sec_candidates.sort(key=lambda x: x[2])
                        primary_key, primary_value, _ = sec_candidates[0]
        except (AttributeError, ValueError, TypeError, ZeroDivisionError):
            pass

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

    # 8. Survival 가중 (Dark Side of Valuation)
    survival = None
    adjusted_primary = primary_value
    going_concern = None
    if survival_adj:
        survival = _applySurvivalAdjustment(company, primary_value, ov)
        if survival and survival.get("adjustedValue") is not None:
            going_concern = primary_value
            adjusted_primary = survival["adjustedValue"]

    # 9. 현재가 + upside (survival 반영한 adjusted_primary 기준)
    current_price = _getCurrentPrice(company)
    upside = (adjusted_primary - current_price) / current_price * 100 if current_price and current_price > 0 else None

    # 10. 신뢰도 + 의견
    confidence = triangulation.get("confidence", "low")
    opinion = _calcOpinion(upside)

    # 11. Cash Flow Consistency 검증
    consistency = _buildConsistency(company, primary_key, primary_value, triangulation, adjusted_wacc, ov)

    out = {
        "dFV": round(adjusted_primary),
        "scenarios": {"bull": round(bull), "base": round(adjusted_primary), "bear": round(bear)},
        "currentPrice": round(current_price) if current_price else None,
        "upside": round(upside, 1) if upside is not None else None,
        "opinion": opinion,
        "confidence": confidence,
        "primaryModel": primary_key,
        "companyType": models.get("companyType"),
        "lifeCyclePhase": life_phase,
        "triangulation": triangulation,
        "dividendFloor": ddm_floor,
        "qualityWACC": qw,
        "allMethods": {k: round(v) for k, v in all_methods.items()},
    }
    if going_concern is not None:
        out["goingConcernValue"] = round(going_concern)
    if survival is not None:
        out["survival"] = {
            "pSurvival": survival.get("pSurvival"),
            "liquidationValue": round(survival["liquidationValue"]) if survival.get("liquidationValue") else None,
            "adjustedUplift": survival.get("uplift"),
        }
    if two_stage_detail:
        out["twoStage"] = {
            "growthYears": two_stage_detail.get("growthYears"),
            "growthRates": two_stage_detail.get("growthRates"),
            "terminalGrowthRate": two_stage_detail.get("terminalGrowthRate"),
            "pvExplicit": two_stage_detail.get("pvExplicit"),
            "pvTerminal": two_stage_detail.get("pvTerminal"),
            "tvShare": two_stage_detail.get("tvShare"),
            "phases": two_stage_detail.get("phases") or [],
            "marginPath": two_stage_detail.get("marginPath"),
            "reinvestmentPath": two_stage_detail.get("reinvestmentPath"),
            "warnings": two_stage_detail.get("warnings") or [],
        }

    # Real Options — 이중계산 방지 서브 dict (primary 에 합산 금지)
    try:
        from dartlab.analysis.valuation.realOptions import calcRealOptionsValue

        ro = calcRealOptionsValue(company, basePeriod=basePeriod, overrides=ov)
        if ro and ro.get("optionValue") is not None:
            out["realOptions"] = ro
            if ro.get("appliedAs") == "uplift":
                # bull 시나리오에만 uplift 반영 (primary 는 불변)
                uplift = ro["optionValue"]
                out["scenarios"]["bull"] = round(out["scenarios"]["bull"] + uplift)
            elif ro.get("appliedAs") == "floor":
                out["realOptionsFloor"] = ro.get("K")
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    if liquidation_detail:
        out["liquidation"] = {
            "recoveries": liquidation_detail.get("recoveries"),
            "grossRecovery": liquidation_detail.get("grossRecovery"),
            "netToEquity": liquidation_detail.get("netToEquity"),
            "perShare": liquidation_detail.get("perShare"),
            "weightedRecoveryRate": liquidation_detail.get("weightedRecoveryRate"),
        }
    if consistency:
        out["consistencyFlags"] = consistency.get("flags", [])
        out["consistencyScore"] = consistency.get("score")
        out["consistencySeverity"] = consistency.get("severity")
    if ov:
        out["overrideApplied"] = {k: v for k, v in ov.items() if k in (
            "wacc", "terminalGrowth", "primaryModel", "lifeCyclePhase",
            "pSurvival", "liquidationValue", "liquidationDiscount",
            "countryCode", "countryRiskPremium",
        )}
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
        from dartlab.core.finance.dcf import _getSectorParams

        si = getattr(company, "sector", None)
        params = _getSectorParams(si.sector if si else None, si.industryGroup if si else None) if si else None
        if params:
            return params.discountRate
    except (ImportError, AttributeError):
        pass
    return 10.0  # 최종 fallback


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


def _calcLiquidationValue(company: Any, overrides: dict) -> float | None:
    """Simple 청산가치 — survival weighting 용 (book × (1-discount))."""
    from dartlab.core.overrides import applyOverride

    explicit = applyOverride(None, "liquidationValue", overrides)
    if explicit is not None:
        return float(explicit)

    try:
        bs = company.select("BS", ["자본총계", "총발행주식수"])
        from dartlab.analysis.financial._helpers import toDictBySnakeId

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
        from dartlab.analysis.financial._helpers import toDictBySnakeId
        from dartlab.core.finance.dcf import liquidationValuation
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


def _calcTwoStageDcf(company: Any, life_phase: str | None, overrides: dict) -> dict | None:
    """Damodaran Multi-stage DCF (Ch.12) — lifeCycle 별 phase 자동 구성.

    - earlyGrowth → 3-phase: [5, 3, 2]년 × [g_high, g_high×0.6, g_high×0.3]
    - highGrowth → 2-phase: [5, 2]년 × [g_high, g_high×0.5]
    - matureGrowth / matureStable / decline → 단일 phase
    """
    try:
        from dartlab.analysis.financial._helpers import toDictBySnakeId
        from dartlab.analysis.financial.growthAnalysis import calcGrowthTrend
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
        from dartlab.core.finance.dcf import multiStageDcf
        from dartlab.core.finance.riskPremiums import loadDamodaranERP
        from dartlab.core.overrides import applyOverride
    except ImportError:
        return None

    # WACC — Phase 4 G13: override chain 전파 (impliedERP / bottomUpBeta / countryCode)
    wacc: float | None = None
    forced_wacc = applyOverride(None, "wacc", overrides)
    implied_flag = applyOverride(False, "impliedERP", overrides)
    bottom_up_flag = applyOverride(False, "bottomUpBeta", overrides)
    country_code = applyOverride(None, "countryCode", overrides)

    if forced_wacc is not None:
        # 사용자/AI 가 WACC 직접 지정 — 최우선
        wacc = float(forced_wacc)
    elif implied_flag or bottom_up_flag or country_code:
        # Phase 3 Damodaran override 경로 — compute_company_wacc 직접 호출로 override 반영
        try:
            from dartlab.core.finance.proforma import compute_company_wacc

            # series 추출 — Company finance 접근 (AttributeError fallback)
            series = None
            try:
                series = getattr(company, "_series", None)
                if series is None and hasattr(company, "_finance"):
                    series = getattr(company._finance, "series", None)
            except (AttributeError, ValueError):
                series = None

            if series:
                wacc_val, _details = compute_company_wacc(
                    series,
                    currency=getattr(company, "currency", "KRW"),
                    country=country_code,
                    implied_erp=bool(implied_flag),
                    bottom_up_beta=bool(bottom_up_flag),
                )
                wacc = float(wacc_val)
        except (ImportError, AttributeError, ValueError, TypeError):
            wacc = None

    if wacc is None:
        # 기본 경로 — 기존 _estimateWacc
        try:
            roic = calcRoicTimeline(company)
            if roic and roic.get("history"):
                wacc = roic["history"][0].get("waccEstimate")
        except (AttributeError, ValueError, TypeError):
            pass
    if wacc is None:
        wacc = 9.0

    # 고성장률: calcGrowthTrend CAGR
    high_g: float | None = None
    try:
        g = calcGrowthTrend(company)
        if g:
            high_g = (g.get("cagr") or {}).get("revenue")
    except (AttributeError, ValueError, TypeError):
        pass
    if high_g is None:
        high_g = 8.0
    # 고성장률 상한 25% (과도 방지)
    high_g = max(-5.0, min(high_g, 25.0))

    # lifeCycle 별 phase 구성 (Damodaran 권고) — Phase 5 G17: highGrowth 10년 확장 (Ch.12)
    phase_config: dict[str, tuple[list[int], list[float]]] = {
        "earlyGrowth": ([5, 3, 2], [high_g, high_g * 0.5, high_g * 0.2]),
        "highGrowth":  ([5, 3, 2], [high_g, high_g * 0.7, high_g * 0.4]),  # 7→10년
        "matureGrowth":([4],       [min(high_g, 8.0)]),   # cap 8%
        "matureStable":([3],       [min(high_g, 3.0)]),   # cap 3% (GDP 근접)
        "decline":     ([2],       [min(high_g, -2.0) if high_g < 0 else min(high_g, 0.0)]),
        "turnaround":  ([5],       [high_g]),
    }
    years_vec, rates_vec = phase_config.get(life_phase or "", ([5], [high_g]))

    # override: growthRates 명시되면 우선
    rates_override = applyOverride(None, "growthRates", overrides)
    if isinstance(rates_override, list) and rates_override:
        rates_vec = rates_override
        if len(years_vec) != len(rates_vec):
            # 수동 phase 조정 — years 는 균등 분할
            years_vec = [max(1, 10 // len(rates_vec))] * len(rates_vec)

    margin_path = applyOverride(None, "marginPath", overrides)
    reinvestment_path = applyOverride(None, "reinvestmentPath", overrides)

    # 영구성장률 — Phase 4 G12.3: phase 별 Rf 감쇠 매핑
    currency = getattr(company, "currency", None)
    country = applyOverride(None, "countryCode", overrides)
    erp = loadDamodaranERP(countryCode=country, currency=currency)
    rf = erp["riskFreeRate"]
    tg_by_phase = {
        "earlyGrowth":  max(2.0, rf - 0.5),
        "highGrowth":   max(2.0, rf - 1.0),
        "matureGrowth": max(2.0, rf - 1.5),
        "matureStable": max(1.5, rf - 2.0),  # GDP 추종 (Damodaran 권고)
        "decline":      0.5,
        "turnaround":   max(2.0, rf - 1.0),
    }
    tg_default = tg_by_phase.get(life_phase or "", max(1.0, rf - 1.0))
    terminal_g = applyOverride(tg_default, "terminalGrowth", overrides)

    # baseFcf: 최근 5개년 중 양수 FCF 의 중앙값 (mid-cycle) — 최근 YTD 편향 회피
    base_fcf: float | None = None
    try:
        cf = company.select("CF", ["영업활동현금흐름", "유형자산의취득"])
        parsed = toDictBySnakeId(cf)
        if parsed:
            data, periods = parsed
            ocf_row = data.get("operating_cashflow") or {}
            capex_row = data.get("purchase_of_property_plant_and_equipment") or {}
            annual_years = [p for p in periods if p.isdigit() and len(p) == 4][:5]
            fcf_history: list[float] = []
            for y in annual_years:
                o = ocf_row.get(y)
                cx = capex_row.get(y)
                if o:
                    fcf_val = float(o) - abs(float(cx or 0))
                    fcf_history.append(fcf_val)
            positives = sorted([f for f in fcf_history if f > 0])
            if positives:
                base_fcf = positives[len(positives) // 2]  # 중앙값
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    if not base_fcf or base_fcf <= 0:
        return None

    # Phase 5 G16: Normalized Earnings (Damodaran Ch.22)
    # 사이클/회복/적자 이력 기업은 mid-cycle FCF 중앙값 대신 Normalized FCF 사용
    try:
        from dartlab.core.finance.normalized import calcNormalizedFcf, needsNormalized

        # ROIC history 추출 (적자 이력 판별용)
        roic_history_data: list[dict] = []
        try:
            _roic_for_norm = calcRoicTimeline(company)
            if _roic_for_norm and _roic_for_norm.get("history"):
                roic_history_data = _roic_for_norm["history"]
        except (AttributeError, ValueError, TypeError):
            pass

        if needsNormalized(life_phase, roic_history_data):
            # 매출/마진 시계열 추출 (최신 먼저)
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
                pass

            norm = calcNormalizedFcf(rev_history, margin_history)
            if norm["method"] != "skip" and norm["normalizedFcf"]:
                base_fcf = norm["normalizedFcf"]  # 사이클 중립 FCF 로 교체
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # 순차입금 + 발행주식수 (shares 는 calcDcf 결과 역산)
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
    except (AttributeError, KeyError, TypeError, ValueError):
        return None

    return multiStageDcf(
        baseFcf=base_fcf,
        growthYears=years_vec,
        growthRates=rates_vec,
        terminalGrowthRate=terminal_g,
        wacc=wacc,
        marginPath=margin_path,
        reinvestmentPath=reinvestment_path,
        netDebt=net_debt,
        shares=shares,
    )


def _applySurvivalAdjustment(company: Any, primary_value: float, overrides: dict) -> dict | None:
    """Dark Side of Valuation — Going-Concern × pSurvival 가중.

    CHS 부도확률 (12M PD) 을 chsFeatures 경로로 실제 추출. 실패 시 safe_default 폴백.
    """
    try:
        from dartlab.core.finance.chsFeatures import computeChsProbability
        from dartlab.core.finance.survival import applySurvivalWeight, calcSurvivalWeight
        from dartlab.core.overrides import applyOverride
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

    weighted = applySurvivalWeight(primary_value, liq_per_share, survival_dict)
    if liq_per_share is not None:
        weighted["liquidationValue"] = liq_per_share
    weighted["pSurvival"] = survival_dict.get("pSurvival")
    weighted["source"] = survival_dict.get("source")
    weighted["annualHazard"] = survival_dict.get("annualHazard")
    return weighted


def _buildConsistency(
    company: Any,
    primary_key: str,
    primary_value: float,
    triangulation: dict,
    wacc: float | None,
    overrides: dict,
) -> dict | None:
    """Cash Flow Consistency 검증 — dFV 결과에 consistencyFlags 주입용."""
    try:
        from dartlab.analysis.valuation.consistency import calcCashFlowConsistency
        from dartlab.core.overrides import applyOverride
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
        primaryModel=primary_key,
        modelsUsed=models_used,
        country=country,
        currency=currency,
    )
