"""하방 시나리오 자동 민감도 — OPM/매출/금리 shock 시 핵심 지표 변화.

"만약 OPM이 5%p 떨어지면?" "매출이 15% 줄면?" "금리가 2%p 오르면?"
각 shock별로 ROE, FCF 커버리지, 이자보상배율 등 핵심 output을 재계산하여
보고서에 리스크/안전마진을 명시한다.

Returns
-------
dict
    baseCase : dict — 현재 핵심 지표
    shocks : dict — 시나리오별 영향
    criticalAssumptions : list[str] — 핵심 가정 목록
    breakdownPoint : dict | None — 손익분기 한계점
"""

from __future__ import annotations

from dartlab.analysis.financial._memoize import memoized_calc


@memoized_calc
def calcScenarioSensitivity(company, *, basePeriod: str | None = None) -> dict | None:
    """핵심 지표 3-shock 민감도 분석.

    Returns
    -------
    dict | None
        baseCase : dict
            opm : float — 영업이익률 (%)
            roe : float — ROE (%)
            interestCoverage : float — 이자보상배율
            debtRatio : float — 부채비율 (%)
            fcf : float — FCF (원)
        shocks : dict
            opm_minus_5pp : dict — OPM -5%p 시
            revenue_minus_15pct : dict — 매출 -15% 시
            interest_plus_2pp : dict — 금리 +2%p 시
        criticalAssumptions : list[str]
        breakdownPoint : dict | None
    """
    from dartlab.analysis.financial._helpers import toDictBySnakeId
    from dartlab.core.finance.helpers import annualColsFromPeriods

    parsed = toDictBySnakeId(
        company.select(
            "IS",
            [
                "sales",
                "operating_income",
                "net_profit",
                "interest_expense",
                "finance_cost",
            ],
        )
    )
    if parsed is None:
        return None
    isData, periods = parsed
    yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=1)
    if not yCols:
        return None

    col = yCols[0]

    def _get(row_key: str) -> float | None:
        """IS 데이터에서 최신 기간 값 추출."""
        v = isData.get(row_key, {}).get(col)
        return float(v) if v is not None else None

    revenue = _get("sales")
    op_income = _get("operating_income")
    ni = _get("net_profit")
    # 이자비용 다중 키 fallback
    interest = _get("interest_expense") or _get("finance_cost")
    if interest is None and op_income is not None and ni is not None:
        interest = op_income - ni  # 조세+이자 합산 근사

    if revenue is None or op_income is None:
        return None

    opm = op_income / revenue * 100 if revenue else None

    bs_parsed = toDictBySnakeId(company.select("BS", ["total_equity", "total_liabilities"]))
    equity = None
    debt_total = None
    if bs_parsed:
        bsData, bsPeriods = bs_parsed
        bsCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=1)
        if bsCols:
            bc = bsCols[0]
            equity = bsData.get("total_equity", {}).get(bc)
            debt_total = bsData.get("total_liabilities", {}).get(bc)
            if equity is not None:
                equity = float(equity)
            if debt_total is not None:
                debt_total = float(debt_total)

    roe = ni / equity * 100 if ni and equity and equity > 0 else None
    debt_ratio = debt_total / equity * 100 if debt_total and equity and equity > 0 else None
    interest_abs = abs(float(interest)) if interest else 0
    ic = op_income / interest_abs if interest_abs > 0 else None

    cf_parsed = toDictBySnakeId(
        company.select("CF", ["operating_cashflow", "purchase_of_property_plant_and_equipment"])
    )
    fcf = None
    if cf_parsed:
        cfData, cfPeriods = cf_parsed
        cfCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=1)
        if cfCols:
            cc = cfCols[0]
            ocf = cfData.get("operating_cashflow", {}).get(cc)
            capex = cfData.get("purchase_of_property_plant_and_equipment", {}).get(cc)
            if ocf is not None:
                fcf = float(ocf) - abs(float(capex or 0))

    baseCase = {
        "opm": round(opm, 1) if opm else None,
        "roe": round(roe, 1) if roe else None,
        "interestCoverage": round(ic, 1) if ic else None,
        "debtRatio": round(debt_ratio, 1) if debt_ratio else None,
        "fcf": fcf,
        # 내부 값 (calcImprovementLevers에서 재사용)
        "_revenue": revenue,
        "_op_income": op_income,
        "_equity": equity,
        "_interest_abs": interest_abs,
        "_cash": None,  # 추후 BS에서 채움
    }

    shocks = {}

    # Shock 1: OPM -5%p
    if opm is not None and revenue:
        shocked_opm = opm - 5
        shocked_op = revenue * shocked_opm / 100
        shocked_ni_est = shocked_op - interest_abs if interest_abs else shocked_op * 0.75
        shocked_roe = shocked_ni_est / equity * 100 if equity and equity > 0 else None
        shocked_ic = shocked_op / interest_abs if interest_abs > 0 else None
        shocks["opm_minus_5pp"] = {
            "opm": round(shocked_opm, 1),
            "roe": round(shocked_roe, 1) if shocked_roe else None,
            "interestCoverage": round(shocked_ic, 1) if shocked_ic else None,
            "verdict": _verdict_opm(shocked_opm, shocked_ic),
        }

    # Shock 2: Revenue -15%
    if revenue and opm is not None:
        shocked_rev = revenue * 0.85
        shocked_op2 = shocked_rev * opm / 100
        shocked_ni2 = shocked_op2 - interest_abs if interest_abs else shocked_op2 * 0.75
        shocked_roe2 = shocked_ni2 / equity * 100 if equity and equity > 0 else None
        shocked_ic2 = shocked_op2 / interest_abs if interest_abs > 0 else None
        shocks["revenue_minus_15pct"] = {
            "revenue_change": "-15%",
            "opm": round(opm, 1),
            "roe": round(shocked_roe2, 1) if shocked_roe2 else None,
            "interestCoverage": round(shocked_ic2, 1) if shocked_ic2 else None,
            "verdict": _verdict_rev(shocked_ic2),
        }

    # Shock 3: Interest +2%p (금리 인상 → 이자비용 증가)
    if interest_abs > 0 and debt_total and debt_total > 0:
        additional_interest = debt_total * 0.02
        shocked_interest = interest_abs + additional_interest
        shocked_ic3 = op_income / shocked_interest if shocked_interest > 0 else None
        shocked_ni3 = op_income - shocked_interest
        shocked_roe3 = shocked_ni3 / equity * 100 if equity and equity > 0 else None
        shocks["interest_plus_2pp"] = {
            "additionalInterest": round(additional_interest),
            "interestCoverage": round(shocked_ic3, 1) if shocked_ic3 else None,
            "roe": round(shocked_roe3, 1) if shocked_roe3 else None,
            "verdict": _verdict_rate(shocked_ic3),
        }

    # 핵심 가정
    assumptions = []
    if opm and opm > 10:
        assumptions.append(f"OPM {opm:.0f}%+ 유지")
    if revenue:
        assumptions.append("매출 성장 > 0")
    if ic and ic > 3:
        assumptions.append("금리 상승 제한적")

    # Breakdown point (OPM)
    breakdown = None
    if revenue and interest_abs > 0:
        bp_opm = interest_abs / revenue * 100
        safety = opm - bp_opm if opm else None
        breakdown = {
            "metric": "opm",
            "value": round(bp_opm, 1),
            "meaning": "이자 비용 감당 한계점",
            "safetyMargin": round(safety, 1) if safety else None,
        }

    return {
        "baseCase": baseCase,
        "shocks": shocks,
        "criticalAssumptions": assumptions,
        "breakdownPoint": breakdown,
    }


def calcImprovementLevers(company, *, basePeriod: str | None = None) -> dict | None:
    """개선 레버 시뮬레이션 — 각 레버별 영향도 계산 + 우선순위.

    "진단"이 아니라 "처방" — 이 회사가 어떻게 하면 좋아지는가.
    scenarioSensitivity의 baseCase 재사용 + 상방 시나리오 5종 계산.

    Returns
    -------
    dict | None
        baseCase : dict — 현재 핵심 지표
        levers : list[dict] — 개선 레버 (영향도 순 정렬)
            name : str — 레버 이름
            driver : str — 레버 키
            impact : dict — 개선 후 지표
            difficulty : str — easy/medium/hard
            timeframe : str
        topLever : str — 가장 효과 큰 레버 driver
    """
    ss = calcScenarioSensitivity(company, basePeriod=basePeriod)
    if not ss:
        return None

    base = ss.get("baseCase", {})
    if not base:
        return None

    revenue = base.get("_revenue")
    op_income = base.get("_op_income")
    equity = base.get("_equity")
    interest_abs = base.get("_interest_abs", 0)
    fcf = base.get("fcf")
    opm = base.get("opm")
    roe = base.get("roe")

    # baseCase에 내부 값이 없으면 포기 (company.select 추가 호출 금지 — 메모리 압박 방어)
    if revenue is None:
        return None

    if not revenue or revenue <= 0:
        return None

    levers = []

    # 레버 1: 매출원가 3%p 절감
    if opm is not None:
        improved_opm = opm + 3
        improved_op = revenue * improved_opm / 100
        improved_ni = improved_op - interest_abs if interest_abs else improved_op * 0.75
        improved_roe = improved_ni / equity * 100 if equity and equity > 0 else None
        fcf_change = ((improved_op - op_income) / abs(fcf) * 100) if fcf and fcf != 0 else None
        levers.append(
            {
                "name": "매출원가 3%p 절감",
                "driver": "cogs_reduction_3pp",
                "impact": {
                    "opm": round(improved_opm, 1),
                    "roe": round(improved_roe, 1) if improved_roe else None,
                    "fcf_change_pct": round(fcf_change, 0) if fcf_change else None,
                },
                "difficulty": "medium",
                "timeframe": "1-2년",
                "effect_score": abs(fcf_change) if fcf_change else 0,
            }
        )

    # 레버 2: 판관비 2%p 절감
    if opm is not None:
        improved_opm2 = opm + 2
        improved_op2 = revenue * improved_opm2 / 100
        improved_ni2 = improved_op2 - interest_abs if interest_abs else improved_op2 * 0.75
        improved_roe2 = improved_ni2 / equity * 100 if equity and equity > 0 else None
        fcf_change2 = ((improved_op2 - op_income) / abs(fcf) * 100) if fcf and fcf != 0 else None
        levers.append(
            {
                "name": "판관비 2%p 절감",
                "driver": "sga_reduction_2pp",
                "impact": {
                    "opm": round(improved_opm2, 1),
                    "roe": round(improved_roe2, 1) if improved_roe2 else None,
                    "fcf_change_pct": round(fcf_change2, 0) if fcf_change2 else None,
                },
                "difficulty": "easy",
                "timeframe": "6개월-1년",
                "effect_score": abs(fcf_change2) if fcf_change2 else 0,
            }
        )

    # 레버 3: 매출 10% 성장 (고정비 레버리지)
    if opm is not None and revenue:
        grown_rev = revenue * 1.10
        # 고정비 부분은 불변 → 변동비만 증가
        variable_cost = revenue * (1 - opm / 100)
        grown_op = grown_rev - variable_cost * 1.10  # 변동비 비례 증가
        grown_opm = grown_op / grown_rev * 100
        grown_ni = grown_op - interest_abs if interest_abs else grown_op * 0.75
        grown_roe = grown_ni / equity * 100 if equity and equity > 0 else None
        levers.append(
            {
                "name": "매출 10% 성장",
                "driver": "revenue_growth_10pct",
                "impact": {
                    "opm": round(grown_opm, 1),
                    "roe": round(grown_roe, 1) if grown_roe else None,
                },
                "difficulty": "hard",
                "timeframe": "2-3년",
                "effect_score": abs(grown_opm - opm) if opm else 0,
            }
        )

    # 레버 4: 부채 30% 감축
    if interest_abs > 0 and op_income:
        reduced_interest = interest_abs * 0.70
        improved_ic = op_income / reduced_interest if reduced_interest > 0 else None
        saved = interest_abs - reduced_interest
        levers.append(
            {
                "name": "부채 30% 감축",
                "driver": "debt_reduction_30pct",
                "impact": {
                    "interestCoverage": round(improved_ic, 1) if improved_ic else None,
                    "interestSaved": round(saved),
                },
                "difficulty": "medium",
                "timeframe": "2-3년",
                "effect_score": saved / revenue * 100 if revenue else 0,
            }
        )

    # ── 기업유형별 특수 레버 (storyTemplate 연동) ──
    situational = _situationalLevers(company, base, revenue, op_income, opm, fcf, equity, interest_abs)
    levers.extend(situational)

    # 영향도 순 정렬
    levers.sort(key=lambda x: x.get("effect_score", 0), reverse=True)
    for lv in levers:
        lv.pop("effect_score", None)

    # 기업유형 라벨
    template_name = None
    try:
        from dartlab.core.finance.companyType import detectTemplate

        template_name = detectTemplate(company)
    except (ImportError, AttributeError):
        pass

    return {
        "baseCase": base,
        "levers": levers,
        "topLever": levers[0]["driver"] if levers else None,
        "companyType": template_name,
    }


def _situationalLevers(company, base, revenue, op_income, opm, fcf, equity, interest_abs) -> list[dict]:
    """기업 상태에 따른 특수 레버 — 7종 유형별 분기."""
    levers: list[dict] = []

    # ── 적자 기업: 흑자 전환 breakeven ──
    if opm is not None and opm < 0 and revenue:
        breakeven_rev = interest_abs / 0.05 if interest_abs > 0 else abs(op_income) / 0.10  # OPM 5% 가정
        growth_needed = (breakeven_rev - revenue) / revenue * 100 if revenue > 0 else None
        levers.append(
            {
                "name": f"흑자 전환 — 매출 {growth_needed:+.0f}% 필요 (OPM 5% 가정)"
                if growth_needed
                else "흑자 전환 경로",
                "driver": "breakeven_revenue",
                "impact": {
                    "breakeven_revenue": round(breakeven_rev),
                    "required_growth": round(growth_needed, 1) if growth_needed else None,
                },
                "difficulty": "hard",
                "timeframe": "2-3년",
                "effect_score": 100,  # 적자 기업에게 최우선
            }
        )

    # ── 현금부자: 배당 확대 vs 재투자 ──
    debt_ratio = base.get("debtRatio")
    if debt_ratio is not None and debt_ratio < 50 and fcf and fcf > 0 and equity and equity > 0:
        # FLEV 마이너스 = 순현금
        # 배당성향 20%p 확대 시 ROE 변화 (Penman FLEV 효과)
        dividend_increase = fcf * 0.20
        # 자본 감소 → ROE 분모 감소 → ROE 증가
        reduced_equity = equity - dividend_increase
        ni = base.get("roe", 0) / 100 * equity if base.get("roe") else None
        new_roe = ni / reduced_equity * 100 if ni and reduced_equity > 0 else None
        if new_roe and base.get("roe"):
            levers.append(
                {
                    "name": f"배당 확대 (FCF의 20%) → ROE {base['roe']:.1f}% → {new_roe:.1f}%",
                    "driver": "dividend_expansion",
                    "impact": {"roe": round(new_roe, 1), "dividendIncrease": round(dividend_increase)},
                    "difficulty": "easy",
                    "timeframe": "즉시 가능",
                    "effect_score": abs(new_roe - base["roe"]),
                }
            )

    # ── 턴어라운드: 생존 가능 기간 ──
    if opm is not None and opm > 0 and opm < 5 and fcf is not None:
        cash = base.get("_cash")
        if cash is None:
            try:
                from dartlab.analysis.financial._helpers import toDictBySnakeId
                from dartlab.core.finance.helpers import annualColsFromPeriods

                bs_p = toDictBySnakeId(company.select("BS", ["cash_and_cash_equivalents"]))
                if bs_p:
                    bsD, bsP = bs_p
                    bsC = annualColsFromPeriods(bsP, maxYears=1)
                    if bsC:
                        cash = float(bsD.get("cash_and_cash_equivalents", {}).get(bsC[0]) or 0)
            except (AttributeError, ValueError, TypeError):
                pass

        if cash and cash > 0 and fcf < 0:
            months = round(cash / abs(fcf) * 12)
            levers.append(
                {
                    "name": f"현금 소진까지 약 {months}개월 — 구조조정 시급",
                    "driver": "cash_runway",
                    "impact": {"cashRunwayMonths": months, "currentCash": round(cash)},
                    "difficulty": "critical",
                    "timeframe": f"{months}개월",
                    "effect_score": 200,  # 생존 이슈는 최우선
                }
            )

    # ── 사이클 기업: 다운턴 방어 OPM ──
    if opm is not None and opm > 10 and interest_abs > 0 and revenue:
        min_opm = interest_abs / revenue * 100  # 이자비용 감당 최소 OPM
        buffer = opm - min_opm
        if buffer < 10:
            levers.append(
                {
                    "name": f"다운턴 방어선 OPM {min_opm:.1f}% (현재 대비 -{buffer:.1f}%p 여유)",
                    "driver": "cycle_defense_opm",
                    "impact": {"minOPM": round(min_opm, 1), "bufferPP": round(buffer, 1)},
                    "difficulty": "awareness",
                    "timeframe": "사이클 하강 시",
                    "effect_score": 50,
                }
            )

    # ── 고성장 기업: 재투자 ROI ─��
    if opm is not None and opm > 15 and revenue:
        try:
            from dartlab.analysis.financial._helpers import toDictBySnakeId
            from dartlab.core.finance.helpers import annualColsFromPeriods

            cf_p = toDictBySnakeId(company.select("CF", ["purchase_of_property_plant_and_equipment"]))
            if cf_p:
                cfD, cfP = cf_p
                cfC = annualColsFromPeriods(cfP, maxYears=1)
                if cfC:
                    capex = abs(float(cfD.get("purchase_of_property_plant_and_equipment", {}).get(cfC[0]) or 0))
                    if capex > 0:
                        capex_to_rev = capex / revenue * 100
                        roic = opm * (revenue / equity) if equity and equity > 0 else None
                        levers.append(
                            {
                                "name": f"CAPEX/매출 {capex_to_rev:.1f}% — ROIC 대비 재투자 효율",
                                "driver": "reinvestment_efficiency",
                                "impact": {
                                    "capexToRevenue": round(capex_to_rev, 1),
                                    "estimatedROIC": round(roic, 1) if roic else None,
                                },
                                "difficulty": "medium",
                                "timeframe": "지속",
                                "effect_score": 30,
                            }
                        )
        except (AttributeError, ValueError, TypeError):
            pass

    return levers


def _verdict_opm(opm: float, ic: float | None) -> str:
    """OPM shock 후 위험 판단문 반환.

    Returns
    -------
    str
        "영업적자 전환" | "이자 감당 위험" | "마진 압박 심각" | "감내 가능".
    """
    if opm < 0:
        return "영업적자 전환"
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    if opm < 5:
        return "마진 압박 심각"
    return "감내 가능"


def _verdict_rev(ic: float | None) -> str:
    """매출 shock 후 위험 판단문 반환.

    Returns
    -------
    str
        "이자 감당 위험" | "감내 가능".
    """
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    return "감내 가능"


def _verdict_rate(ic: float | None) -> str:
    """금리 shock 후 위험 판단문 반환.

    Returns
    -------
    str
        "이자 감당 위험" | "여유 축소" | "감내 가능".
    """
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    if ic is not None and ic < 3:
        return "여유 축소"
    return "감내 가능"
