"""2-1 수익성 분석 -- 이익의 흐름을 추적한다.

select()로 IS/BS 원본 계정을 가져와서
금액 + 비율 + YoY 변동을 시계열로 보여준다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from typing import Any

from dartlab.analysis.financial.accountSums import sumBorrowings
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import MAX_RATIO_YEARS, annualColsFromPeriods, toDictBySnakeId

_MAX_YEARS = MAX_RATIO_YEARS


def _yoy(cur, prev) -> float | None:
    """전기대비 증감률 계산.

    Returns
    -------
    float | None
        YoY 변화율 (%). 계산 불가 시 None.
    """
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 2)


from dartlab.core.utils.calc import safePct as _pctOf  # noqa: E402

# ── 이익 구조 시계열 ──


def _isFinancialSector(company) -> bool:
    """금융업(은행/보험/증권) 판별."""
    try:
        sector = getattr(company, "sector", None)
        if sector is not None:
            from dartlab.frame.sector import Sector

            if sector.sector == Sector.FINANCIALS:
                return True
    except (AttributeError, ImportError):
        pass
    return False


@memoizedCalc
def calcMarginTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """이익 구조 시계열 — 매출 → 매출원가 → 매출총이익 → 판관비 → 영업이익 → 순이익.

    Capabilities:
        IS 의 5 마진 단계 (매출 → COGS → GP → SG&A → OP → NI) 시계열을 산출.
        일반/금융업 분기 (금융업은 이자수익 + 금융이익). YoY 변화율 함께
        제공해 마진 압박/개선 추세 식별.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 13 키 dict (revenue, cogs,
              grossProfit/Margin, sga, operatingIncome/Margin, netIncome/Margin
              + 각 YoY)
            - ``displayHints`` (dict): UI 표시 메타 (core 컬럼 + 한국어 라벨)

    Raises:
        없음.

    Example:
        >>> r = calcMarginTrend(Company("005930"))
        >>> r["history"][0]["operatingMargin"], r["history"][0]["grossMargin"]
        (12.5, 35.0)

    Guide:
        마진 추세 (3 년) 가 progressive 개선/악화면 신호 강함. Operating
        margin 안정 (변동 ±2%p) + Net margin 변동 큼 = 영업외 손익 영향
        (한국 회사 흔함). 금융업은 NIM (Net Interest Margin) 별도 분석.

    SeeAlso:
        - ``analyzeProfitability``: 정성 분석 (본 함수 결과 사용)
        - ``calcReturnTrend``: ROE/ROA/ROIC 시계열
        - ``calcMarginWaterfall``: COGS/SG&A 비중 변화 분해

    Requires:
        IS 시계열 (매출/매출원가/판관비/영업이익/당기순이익) ≥ 2 년.

    AIContext:
        history list 의 첫 dict 가 최신 (latest), [1] = 전년. YoY 변화 분석시
        주의 — 일회성 영업외 (자산매각 등) 가 netMargin 만 영향. 마진 5
        단계 함께 보면 영업 구조 + 영업외 영향 분리 가능.

    LLM Specifications:
        AntiPatterns:
            - 매출액 (revenue) 만 보고 성장 단정 — 영업이익 동반 확인 필수.
            - 금융업 (은행/보험) 에 일반 마진 적용 — isFinancial 자동 분기
              되지만 결과 dict 의 cogs/sga 가 0 일 수 있음.
        OutputSchema:
            ``{history: list[dict], displayHints: dict}``.
        Prerequisites:
            IS 시계열 + 일반/금융업 분기 표준 계정.
        Freshness:
            최신 분기 + 5 년 시계열 (annualColsFromPeriods).
        Dataflow:
            IS → 5 마진 단계 추출 → YoY 계산 → displayHints 메타 합성.
        TargetMarkets: KR (DART 표준), US (EDGAR — 일부 표준 계정 매핑 필요).
    """
    isFinancial = _isFinancialSector(company)

    if isFinancial:
        isResult = company.select("IS", ["이자수익", "금융이익", "영업이익", "당기순이익"])
    else:
        isResult = company.select(
            "IS", ["매출액", "매출원가", "매출총이익", "판매비와관리비", "영업이익", "당기순이익"]
        )

    parsed = toDictBySnakeId(isResult)
    if parsed is None:
        return None

    data, periods = parsed

    if isFinancial:
        # 금융업: 금융이익을 revenue 대체 (이자수익은 일부일 뿐)
        rev = data.get("금융이익", {}) or data.get("이자수익", {})
        op = data.get("영업이익", {})
        ni = data.get("당기순이익", {})
        finIncome = data.get("이자수익", {})
    else:
        rev = data.get("매출액", {})
        op = data.get("영업이익", {})
        ni = data.get("당기순이익", {})

    cogs = data.get("매출원가", {}) if not isFinancial else {}
    gp = data.get("매출총이익", {}) if not isFinancial else {}
    sga = data.get("판매비와관리비", {}) if not isFinancial else {}

    yCols = annualColsFromPeriods(periods, basePeriod, _MAX_YEARS + 1)
    if len(yCols) < 2:
        return None
    history = []
    for i, col in enumerate(yCols):
        prevCol = yCols[i + 1] if i + 1 < len(yCols) else None
        r = rev.get(col)
        if r is None or r == 0:
            continue

        _op = op.get(col)
        _ni = ni.get(col)
        _opPrev = op.get(prevCol) if prevCol else None
        _niPrev = ni.get(prevCol) if prevCol else None
        _rPrev = rev.get(prevCol) if prevCol else None

        row: dict = {
            "period": col,
            "revenue": r,
            "revenueYoy": _yoy(r, _rPrev) if prevCol else None,
            "operatingIncome": _op,
            "operatingMargin": _pctOf(_op, r),
            "operatingIncomeYoy": _yoy(_op, _opPrev) if prevCol else None,
            "netIncome": _ni,
            "netMargin": _pctOf(_ni, r),
            "netIncomeYoy": _yoy(_ni, _niPrev) if prevCol else None,
        }

        if isFinancial:
            row["revenueLabel"] = "금융이익"
            row["financialIncome"] = finIncome.get(col)
        else:
            row["cogs"] = cogs.get(col)
            row["grossProfit"] = gp.get(col)
            row["grossMargin"] = _pctOf(gp.get(col), r)
            row["sga"] = sga.get(col)

        history.append(row)

    if not history:
        return None
    result: dict[str, Any] = {"history": history}
    if isFinancial:
        result["isFinancial"] = True

    # Phase 7 G24: 영업마진 변화 driver 분해 — 각 history entry 에 drivers 주입
    # 이전기 대비 원가율/판관비/환율 driver 자동 분해 (McKinsey + Damodaran Ch.11)
    if not isFinancial:
        try:
            from dartlab.analysis.financial.attribution import decomposeMarginChange

            for i in range(len(history) - 1):
                cur = history[i]
                prev = history[i + 1]
                revT = cur.get("revenue")
                rev_t1 = prev.get("revenue")
                cogsT = cur.get("cogs")
                cogs_t1 = prev.get("cogs")
                sgaT = cur.get("sga")
                sga_t1 = prev.get("sga")
                if all(isinstance(v, (int, float)) for v in (revT, rev_t1, cogsT, cogs_t1, sgaT, sga_t1)):
                    attribution = decomposeMarginChange(
                        revenueT=revT,
                        revenueT1=rev_t1,
                        cogsT=cogsT,
                        cogsT1=cogs_t1,
                        sgaT=sgaT,
                        sgaT1=sga_t1,
                    )
                    cur["drivers"] = attribution.get("drivers") or []
                    cur["driversExplained"] = attribution.get("explainedPct")
        except (ImportError, AttributeError, TypeError, ValueError):
            pass

    # Phase 8 A5: turningPoints 헬퍼 1줄
    from dartlab.synth.turningPoint import injectTurningPoints

    result["turningPoints"] = injectTurningPoints(history, seriesKey="operatingMargin", minDeltaPct=25.0)

    # R22-2: AI 가 표 만들 때 핵심 컬럼을 빠뜨리지 않도록 명시.
    result["displayHints"] = {
        "core": ["period", "revenue", "operatingMargin", "netMargin", "grossMargin"],
        "note": "수익성 응답 시 operatingMargin/netMargin/grossMargin 컬럼을 표에 반드시 포함",
    }
    # Phase 15 C1: _showKey 힌트 — AI 가 자율적으로 `show("IS")` 재검증 호출 가능
    result["_showKey"] = "IS"
    result["_showFields"] = ["매출액", "영업이익", "당기순이익"]
    return result


# ── ROE 분해 (듀퐁 5요소) ──


@memoizedCalc
def calcReturnTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """ROE 구조 분해 -- 수익을 어떻게 만드는가.

    IS + BS에서 원본 계정을 가져와서 듀퐁 5요소를 직접 계산.
    ROE = (NI/EBT) x (EBT/EBIT) x (EBIT/Rev) x (Rev/TA) x (TA/Equity)
        = 세금부담 x 이자부담 x 영업마진 x 자산회전 x 레버리지

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            netIncome : float — 당기순이익 (원)
            equity : float — 자기자본 (원)
            totalAssets : float — 총자산 (원)
            roe : float — 자기자본이익률 (%)
            roa : float — 총자산이익률 (%)
            taxBurden : float — 세금부담률 (배)
            interestBurden : float — 이자부담률 (배)
            operatingMargin : float — 영업이익률 (%)
            assetTurnover : float — 자산회전율 (배)
            leverage : float — 재무레버리지 (배)
    """
    isResult = company.select("IS", ["매출액", "영업이익", "법인세차감전순이익", "당기순이익"])
    bsResult = company.select("BS", ["자산총계", "자본총계"])

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    rev = isData.get("매출액", {})
    opIncome = isData.get("영업이익", {})
    pbt = isData.get("법인세차감전순이익", {})
    niRow = isData.get("당기순이익", {})
    ta = bsData.get("자산총계", {})
    eq = bsData.get("자본총계", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None
    history = []
    for col in yCols:
        r = rev.get(col)
        o = opIncome.get(col)
        p = pbt.get(col)
        n = niRow.get(col)
        a = ta.get(col)
        e = eq.get(col)

        roe = _pctOf(n, e)
        roa = _pctOf(n, a)

        # 듀퐁 5요소 (원본에서 직접)
        taxBurden = round(n / p, 4) if n is not None and p is not None and p != 0 else None
        interestBurden = round(p / o, 4) if p is not None and o is not None and o != 0 else None
        operatingMargin = _pctOf(o, r)
        assetTurnover = round(r / a, 4) if r is not None and a is not None and a != 0 else None
        leverage = round(a / e, 4) if a is not None and e is not None and e != 0 else None

        history.append(
            {
                "period": col,
                "netIncome": n,
                "equity": e,
                "totalAssets": a,
                "roe": roe,
                "roa": roa,
                "taxBurden": taxBurden,
                "interestBurden": interestBurden,
                "operatingMargin": operatingMargin,
                "assetTurnover": assetTurnover,
                "leverage": leverage,
            }
        )

    return {"history": history} if history else None


# ── 마진 워터폴 ──


@memoizedCalc
def calcMarginWaterfall(company, *, basePeriod: str | None = None) -> dict | None:
    """매출 -> 순이익 마진 워터폴 분해.

    각 단계에서 얼마나 줄어드는지를 금액 + 비율(%)로 보여준다.

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            steps : list[dict] — 워터폴 단계별 (label, value, pct)
    """
    isResult = company.select(
        "IS",
        [
            "매출액",
            "매출원가",
            "매출총이익",
            "판매비와관리비",
            "영업이익",
            "금융비용",
            "금융수익",
            "법인세차감전순이익",
            "법인세비용",
            "당기순이익",
        ],
    )
    parsed = toDictBySnakeId(isResult)
    if parsed is None:
        return None

    data, periods = parsed
    rev = data.get("매출액", {})
    cogs = data.get("매출원가", {})
    gp = data.get("매출총이익", {})
    sgaRow = data.get("판매비와관리비", {})
    opRow = data.get("영업이익", {})
    finCost = data.get("금융비용", {})
    finInc = data.get("금융수익", {})
    pbt = data.get("법인세차감전순이익", {})
    tax = data.get("법인세비용", {})
    ni = data.get("당기순이익", {})

    yCols = annualColsFromPeriods(periods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    def _pct(val, r):
        """매출 대비 비율 계산 (%)."""
        if val is None or r is None or r == 0:
            return None
        return round(val / r * 100, 2)

    history = []
    for col in yCols:
        r = rev.get(col)
        if r is None or r == 0:
            continue

        steps = [{"label": "매출", "amount": r, "pct": 100.0, "cumPct": 100.0}]

        cogsV = cogs.get(col)
        gpV = gp.get(col)
        if cogsV is not None:
            steps.append(
                {
                    "label": "매출원가",
                    "amount": cogsV,
                    "pct": -abs(_pct(cogsV, r) or 0),
                    "cumPct": _pct(gpV, r) or round(100 - abs(_pct(cogsV, r) or 0), 2),
                }
            )
        if gpV is not None:
            steps.append({"label": "매출총이익", "amount": gpV, "pct": _pct(gpV, r), "cumPct": _pct(gpV, r)})

        sgaV = sgaRow.get(col)
        opV = opRow.get(col)
        if sgaV is not None:
            steps.append(
                {
                    "label": "판관비",
                    "amount": sgaV,
                    "pct": -abs(_pct(sgaV, r) or 0),
                    "cumPct": _pct(opV, r) or round((_pct(gpV, r) or 0) - abs(_pct(sgaV, r) or 0), 2),
                }
            )
        if opV is not None:
            steps.append({"label": "영업이익", "amount": opV, "pct": _pct(opV, r), "cumPct": _pct(opV, r)})

        fcV = finCost.get(col)
        fiV = finInc.get(col)
        opPct = _pct(opV, r) or 0
        if fcV is not None:
            steps.append(
                {
                    "label": "금융비용",
                    "amount": fcV,
                    "pct": -abs(_pct(fcV, r) or 0),
                    "cumPct": round(opPct - abs(_pct(fcV, r) or 0), 2),
                }
            )
        if fiV is not None:
            steps.append(
                {
                    "label": "금융수익",
                    "amount": fiV,
                    "pct": abs(_pct(fiV, r) or 0),
                    "cumPct": round(opPct - abs(_pct(fcV, r) or 0) + abs(_pct(fiV, r) or 0), 2),
                }
            )

        pbtV = pbt.get(col)
        if pbtV is not None:
            steps.append({"label": "세전이익", "amount": pbtV, "pct": _pct(pbtV, r), "cumPct": _pct(pbtV, r)})

        taxV = tax.get(col)
        if taxV is not None:
            steps.append(
                {
                    "label": "법인세",
                    "amount": taxV,
                    "pct": -abs(_pct(taxV, r) or 0),
                    "cumPct": round((_pct(pbtV, r) or 0) - abs(_pct(taxV, r) or 0), 2),
                }
            )

        niV = ni.get(col)
        if niV is not None:
            steps.append({"label": "순이익", "amount": niV, "pct": _pct(niV, r), "cumPct": _pct(niV, r)})

        history.append({"period": col, "steps": steps})

    return {"history": history} if history else None


# ── 플래그 ──


@memoizedCalc
def calcProfitabilityFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """수익성 경고/기회 플래그.

    Returns
    -------
    list[str]
        경고/기회 메시지 리스트. 빈 리스트이면 이상 없음.
    """
    flags: list[str] = []
    isFinancial = _isFinancialSector(company)

    trend = calcMarginTrend(company, basePeriod=basePeriod)
    if trend and len(trend["history"]) >= 3:
        hist = trend["history"]
        # 영업이익률 3기 연속 하락
        oms = [h.get("operatingMargin") for h in hist[:3]]
        if all(v is not None for v in oms) and oms[0] < oms[1] < oms[2]:
            flags.append(f"영업이익률 3기 연속 하락 ({oms[0]:.1f}%)")
        if oms[0] is not None and oms[0] < 0:
            flags.append(f"영업적자 ({oms[0]:.1f}%)")

    # 마진 괴리 감지 — 순이익률 vs 영업이익률
    if trend and trend["history"]:
        latest = trend["history"][0]
        nm = latest.get("netMargin")
        om = latest.get("operatingMargin")
        if nm is not None and om is not None and om > 0:
            ratio = nm / om
            if isFinancial:
                # 금융업: 금융이익은 순이자+수수료(매출총이익 성격)이므로
                # 영업이익 > 금융이익은 구조적으로 정상.
                # 순이익률 << 영업이익률은 금융비용/충당금 때문.
                if ratio > 3.0:
                    flags.append(f"순이익률({nm:.1f}%)이 영업이익률({om:.1f}%)의 {ratio:.1f}배 — 비영업이익 확인 필요")
            else:
                if ratio > 2.0:
                    flags.append(
                        f"순이익률({nm:.1f}%)이 영업이익률({om:.1f}%)의 {ratio:.1f}배 — 대규모 비영업이익 존재"
                    )
                elif 0 < ratio < 0.3:
                    flags.append(f"순이익률이 영업이익률의 {ratio:.1f}배 — 대규모 비영업손실")
        if om is not None and abs(om) > 100:
            if isFinancial:
                flags.append(
                    f"금융업 IS 구조: 금융이익 대비 영업이익률 {om:.1f}%"
                    " (금융이익=순금융수익, 수수료·보험 등 별도 합산)"
                )
            else:
                # 지주사(로열티/지분법 수입 위주)는 영업이익률 100%+ 정상.
                # "데이터 이상"이라고 하면 사용자에게 불필요한 공포 유발.
                flags.append(
                    f"영업이익률 {om:.1f}% — 매출 대비 영업이익이 크다 (지주사·로열티·지분법이익 구조일 수 있음)"
                )

    if isFinancial:
        flags.append("금융업: ROE·ROA가 핵심 수익성 지표 (마진 분석은 참고용)")

    ret = calcReturnTrend(company, basePeriod=basePeriod)
    if ret and ret["history"]:
        h = ret["history"][0]
        roe = h.get("roe")
        roa = h.get("roa")
        lev = h.get("leverage")
        if roe is not None and roa is not None and lev is not None:
            if isFinancial:
                # 금융업은 레버리지 10x+ 가 정상 (은행 자기자본비율 ~8%)
                if roe > 8:
                    flags.append(f"양호한 ROE ({roe:.1f}%, 금융업 기준)")
            else:
                if lev > 3:
                    flags.append(f"ROE의 레버리지 의존도 높음 (자산/자본 = {lev:.1f}배)")
                if roe > 15 and roa > 5 and lev < 2:
                    flags.append(f"진성 고수익 (ROE {roe:.1f}%, 낮은 레버리지)")

    return flags


# ── Penman RNOA + FLEV/SPREAD 분해 ──


@memoizedCalc
def calcPenmanDecomposition(company, *, basePeriod: str | None = None) -> dict | None:
    """Penman 분해 -- ROE가 영업력인지 레버리지인지 분리.

    ROCE = RNOA + FLEV × SPREAD
    RNOA = NOPAT / NOA  (순영업자산수익률)
    FLEV = NFO / Equity  (금융레버리지)
    NBC  = 순금융비용 / NFO  (순차입비용률)
    SPREAD = RNOA - NBC  (초과수익률)
    leverageEffect = FLEV × SPREAD  (레버리지 효과)

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            rnoa : float — 순영업자산수익률 (%)
            flev : float — 금융레버리지 (배)
            nbc : float — 순차입비용률 (%)
            spread : float — 초과수익률 RNOA-NBC (%)
            leverageEffect : float — 레버리지 효과 FLEV×SPREAD (%)
            roce : float — 자기자본수익률 RNOA+leverageEffect (%)

    학술근거: Nissim & Penman (2001), Penman FSA&SV 5e.
    """
    isResult = company.select("IS", ["영업이익", "법인세비용", "법인세차감전순이익", "금융이익", "금융비용"])
    bsResult = company.select(
        "BS",
        [
            "자산총계",
            "자본총계",
            "매출채권및기타채권",
            "재고자산",
            "유형자산",
            "무형자산",
            "매입채무",
            "선수금",
            "계약부채",
            "단기차입금",
            "장기차입금",
            "차입금단기",
            "long_term_borrowings",
            "short_term_borrowings",
            "차입부채",
            "장기차입부채",
            "유동성장기차입금",
            "사채",
            "현금및현금성자산",
        ],
    )

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    opRow = isData.get("operating_profit", {})
    taxRow = isData.get("income_tax_expense") or isData.get("income_taxes", {})
    ptRow = isData.get("profit_before_tax", {})
    finIncRow = isData.get("finance_income", {})
    finCostRow = isData.get("finance_costs", {})

    eqRow = bsData.get("total_stockholders_equity", {})
    recRow = bsData.get("trade_and_other_receivables", {})
    invRow = bsData.get("inventories", {})
    ppeRow = bsData.get("tangible_assets", {})
    intRow = bsData.get("intangible_assets", {})
    apRow = bsData.get("trade_and_other_payables", {})
    advRow = bsData.get("advance_from_customers", {})
    contRow = bsData.get("contract_liabilities", {})
    bsData.get("shortterm_borrowings", {})
    bsData.get("longterm_borrowings", {})
    bsData.get("borrowings", {})  # 통합 차입금 fallback
    bsData.get("debentures", {})
    cashRow = bsData.get("cash_and_cash_equivalents", {})

    yCols = annualColsFromPeriods(isPeriods, maxYears=_MAX_YEARS, basePeriod=basePeriod)
    if len(yCols) < 2:
        return None

    history = []
    for col in yCols:
        # NOPAT = 영업이익 × (1 - 유효세율)
        opIncome = _getF(opRow, col)
        taxExpense = abs(_getF(taxRow, col))
        ptIncome = abs(_getF(ptRow, col))
        effectiveTaxRate = taxExpense / ptIncome if ptIncome > 0 else 0.25
        effectiveTaxRate = min(effectiveTaxRate, 0.5)
        nopat = opIncome * (1 - effectiveTaxRate) if opIncome != 0 else None

        # NOA = 영업자산 - 영업부채
        opAssets = _get(recRow, col) + _get(invRow, col) + _get(ppeRow, col) + _get(intRow, col)
        opLiab = _get(apRow, col) + _get(advRow, col) + _get(contRow, col)
        noa = opAssets - opLiab if opAssets > 0 else None

        # NFO = 금융부채 - 금융자산(현금)
        # 차입금: 회사 키 패턴 무관 헬퍼
        finDebt = sumBorrowings(bsData, col)
        cash = _get(cashRow, col)
        nfo = finDebt - cash

        # 순금융비용
        finInc = _getF(finIncRow, col)
        finCost = _getF(finCostRow, col)
        netFinCost = finCost - finInc  # 양수 = 순비용

        equity = _get(eqRow, col)

        # RNOA
        rnoa = round(nopat / noa * 100, 2) if nopat is not None and noa and noa > 0 else None
        # FLEV
        flev = round(nfo / equity, 2) if equity > 0 else None
        # NBC
        nbc = round(netFinCost * (1 - effectiveTaxRate) / abs(nfo) * 100, 2) if nfo != 0 else None
        # SPREAD
        spread = round(rnoa - nbc, 2) if rnoa is not None and nbc is not None else None
        # Leverage Effect
        levEffect = round(flev * spread, 2) if flev is not None and spread is not None else None
        # ROCE (검증: ≈ RNOA + leverageEffect)
        roce = round(rnoa + levEffect, 2) if rnoa is not None and levEffect is not None else None

        history.append(
            {
                "period": col,
                "rnoa": rnoa,
                "flev": flev,
                "nbc": nbc,
                "spread": spread,
                "leverageEffect": levEffect,
                "roce": roce,
            }
        )

    if not history:
        return None

    return {"history": history}


# ── McKinsey ROIC Tree ──


@memoizedCalc
def calcRoicTree(company, *, basePeriod: str | None = None) -> dict | None:
    """McKinsey ROIC Tree → ROIC 분해 (마진 × 회전율 → COGS/SG&A/Tax + WC/Fixed).

    Capabilities:
        McKinsey "Valuation" (Koller 2020) 의 ROIC 분해 — ROIC = Margin × Turnover.
        Margin 은 (COGS/Rev + SG&A/Rev + TaxRate) 로 분해, Turnover 는 WC vs
        Fixed Capital 로 분해. ROIC 변화의 원인 (마진 vs 회전율) 자동 식별.
        Penman/Damodaran 의 ROE 분해와 보완.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 ROIC tree (period, roic,
              operatingMargin, capitalTurnover, grossMargin, sgaRatio,
              effectiveTaxRate, wcTurnover, fixedTurnover, marginDriver,
              turnoverDriver)

    Raises:
        없음.

    Example:
        >>> r = calcRoicTree(Company("005930"))
        >>> r["history"][0]["roic"], r["history"][0]["marginDriver"]
        (15, 'cogs')  # ROIC 15%, 변화 주도 = COGS

    Guide:
        ROIC 임계: > 15% = excellent (cost of capital 10% 가정), 10~15% =
        good, < 10% = value destroyer. marginDriver 가 "cogs" 인데 매출 증가
        시기 = 규모 경제, "sga" 우세 = 영업 효율 개선 또는 악화.

    SeeAlso:
        - ``calcMarginTrend``: 마진 단순 시계열
        - ``calcReturnTrend``: ROE/ROA/ROIC 시계열
        - ``calcPenmanDecomposition``: ROE 분해 (RNOA + FLEV × Spread)
        - Koller, T. (2020) "Valuation: Measuring and Managing"

    Requires:
        IS 시계열 (매출/매출원가/판관비/세금) + BS (운전자본 + 고정자본) ≥ 2 년.

    AIContext:
        ROIC > WACC = value creator, < WACC = value destroyer. marginDriver +
        turnoverDriver 라벨을 사용자에게 노출 — "왜 ROIC 가 변했는지" 직접
        설명.

    LLM Specifications:
        AntiPatterns:
            - ROIC 절대값만 인용 — WACC 와 비교 필수 (calcDFV 의 qualityWACC
              사용 권장).
            - 단년도 분해 — 3 년 추세로 marginDriver 의 안정성 확인 필수.
        OutputSchema:
            ``{history: list[dict 11키]}``.
        Prerequisites:
            IS + BS 시계열 + standardAccounts (매출원가/판관비/세금).
        Freshness:
            최신 분기 + 시계열 (5 년 권장).
        Dataflow:
            IS → margin 분해 (COGS/SG&A/Tax) + BS → IC = WC + Fixed →
            Turnover → ROIC = margin × turnover → driver 식별.
        TargetMarkets: KR (DART), US (EDGAR). 표준 계정 매핑.
    """
    isResult = company.select(
        "IS", ["매출액", "매출원가", "판매비와관리비", "영업이익", "법인세비용", "법인세차감전순이익"]
    )
    bsResult = company.select(
        "BS",
        [
            "매출채권및기타채권",
            "재고자산",
            "매입채무",
            "유형자산",
            "무형자산",
            "자본총계",
            "단기차입금",
            "장기차입금",
            "차입금단기",
            "long_term_borrowings",
            "short_term_borrowings",
            "차입부채",
            "장기차입부채",
            "유동성장기차입금",
            "사채",
            "현금및현금성자산",
        ],
    )

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    revRow = isData.get("sales", {})
    cogsRow = isData.get("cost_of_sales", {})
    sgaRow = isData.get("selling_and_administrative_expenses", {})
    opRow = isData.get("operating_profit", {})
    taxRow = isData.get("income_tax_expense") or isData.get("income_taxes", {})
    ptRow = isData.get("profit_before_tax", {})

    arRow = bsData.get("trade_and_other_receivables", {})
    invRow = bsData.get("inventories", {})
    apRow = bsData.get("trade_and_other_payables", {})
    ppeRow = bsData.get("tangible_assets", {})
    intRow = bsData.get("intangible_assets", {})
    bsData.get("total_stockholders_equity", {})
    bsData.get("shortterm_borrowings", {})
    bsData.get("longterm_borrowings", {})
    bsData.get("borrowings", {})  # 통합 차입금 fallback
    bsData.get("debentures", {})
    bsData.get("cash_and_cash_equivalents", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        rev = _getF(revRow, col)
        if rev <= 0:
            continue
        cogs = _getF(cogsRow, col)
        sga = _getF(sgaRow, col)
        opIncome = _getF(opRow, col)
        taxExp = abs(_getF(taxRow, col))
        ptIncome = abs(_getF(ptRow, col))

        # Margin 분해
        grossMargin = round((rev - cogs) / rev * 100, 2) if cogs else None
        sgaRatio = round(sga / rev * 100, 2) if sga else None
        opMargin = round(opIncome / rev * 100, 2)
        effectiveTax = round(taxExp / ptIncome * 100, 2) if ptIncome > 0 else 25.0
        effectiveTax = min(effectiveTax, 50.0)

        # NOPAT
        nopat = opIncome * (1 - effectiveTax / 100)

        # Invested Capital
        wc = _get(arRow, col) + _get(invRow, col) - _get(apRow, col)
        fc = _get(ppeRow, col) + _get(intRow, col)
        ic = wc + fc if (wc + fc) > 0 else None

        # ROIC
        roic = round(nopat / ic * 100, 2) if ic and ic > 0 else None

        # Capital Turnover
        capTurnover = round(rev / ic, 2) if ic and ic > 0 else None

        # WC/Fixed Turnover
        wcTurnover = round(rev / wc, 2) if wc > 0 else None
        fixedTurnover = round(rev / fc, 2) if fc > 0 else None

        # 마진 드라이버 판단
        if grossMargin is not None and sgaRatio is not None:
            if grossMargin > 40:
                marginDriver = "높은 가격결정력 (매출총이익률 > 40%)"
            elif sgaRatio and sgaRatio < 15:
                marginDriver = "낮은 판관비 (SGA < 15%)"
            elif opMargin > 15:
                marginDriver = "고마진 사업모델"
            elif opMargin < 5:
                marginDriver = "박리다매 또는 원가 경쟁"
            else:
                marginDriver = "보통 수준"
        else:
            marginDriver = None

        # 자본회전 드라이버 판단
        if capTurnover is not None:
            if capTurnover > 2:
                turnoverDriver = "자산 경량 모델 (자본회전 > 2회)"
            elif capTurnover < 0.5:
                turnoverDriver = "자본 집약 (자본회전 < 0.5회)"
            else:
                turnoverDriver = "보통 수준"
        else:
            turnoverDriver = None

        history.append(
            {
                "period": col,
                "roic": roic,
                "operatingMargin": opMargin,
                "capitalTurnover": capTurnover,
                "grossMargin": grossMargin,
                "sgaRatio": sgaRatio,
                "effectiveTaxRate": round(effectiveTax, 1),
                "wcTurnover": wcTurnover,
                "fixedTurnover": fixedTurnover,
                "marginDriver": marginDriver,
                "turnoverDriver": turnoverDriver,
            }
        )

    if not history:
        return None
    return {"history": history}
