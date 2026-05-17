"""자본배분 분석 — 배당, 주주환원, 재투자, FCF 사용처 시계열.

벌어들인 돈을 어디에 쓰는지를 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import (
    annualColsFromPeriods,
    toDictBySnakeId,
)

_MAX_YEARS = 8


# ── 유틸 ──


from dartlab.core.utils.calc import safePct as _pct  # noqa: E402

# ── 배당 정책 ──


@memoizedCalc
def calcDividendPolicy(company, *, basePeriod: str | None = None) -> dict | None:
    """배당 정책 시계열 — 배당성향 + 배당 성장률 + 연속 배당 연수 + 정책 분류.

    Capabilities:
        CF 의 dividends_paid + IS 의 net_profit 시계열에서 배당성향 (payout)
        + 배당 성장률 (CAGR) + 연속 배당 연수 산출. capitalAllocation 의
        핵심 함수 — Damodaran 의 dividend policy 4 사분면 (high/low growth ×
        high/low payout) 분류 가능.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 dict (period, dividendsPaid,
              netIncome, payoutRatio, dividendGrowth)
            - ``consecutiveYears`` (int): 연속 배당 연수 (배당 단절 시 reset)

    Raises:
        없음.

    Example:
        >>> r = calcDividendPolicy(Company("005930"))
        >>> r["history"][0]["payoutRatio"], r["consecutiveYears"]
        (25, 30)  # 25% 배당성향, 30 년 연속 배당

    Guide:
        payoutRatio 임계: < 20% = 성장 우선, 20~50% = 균형, > 50% = 배당
        우선. 연속 배당 5+ 년 = dividend aristocrats 후보. KR 기준 평균 ~ 20%,
        US 기준 ~ 30% (S&P 500 평균). 배당 성장률 5%+ 가 5 년 연속 = 우수.

    When:
        Capital allocation 분석 + AI 배당 정책 답변.

    How:
        CF dividends_paid + IS net_profit → payoutRatio + CAGR + 연속 카운트.

    SeeAlso:
        - ``ddmValuation``: 배당 기반 가치 평가 (본 함수 입력)
        - ``calcShareholderReturn``: 자사주매입 + 배당 합산
        - ``narrateRepayment``: 배당 → 차입금 상환 여력 분석

    Requires:
        CF (dividends_paid) + IS (net_profit) 시계열 ≥ 2 년.

    AIContext:
        consecutiveYears + payoutRatio 함께 인용. KR 대기업 (삼성/현대) 은
        20~30 년 연속 배당 사례 많음. 무배당 회사는 history 빈 list,
        consecutiveYears=0.

    LLM Specifications:
        AntiPatterns:
            - payoutRatio > 100% 결과를 "비정상" 단정 — 일시적 (turnaround)
              가능. 3 년 평균 확인.
            - 분기 dividends_paid 4 회 합산이 안 되면 TTM fallback —
              ``_annualDividends`` 자동 처리.
        OutputSchema:
            ``{history: list[dict 5키], consecutiveYears: int}``.
        Prerequisites:
            CF/dividends_paid + IS/net_profit ≥ 2 년.
        Freshness:
            최신 분기 + 5~10 년 시계열.
        Dataflow:
            CF/dividends_paid → 연간 합산 → /net_profit → payoutRatio
            + CAGR + 연속 배당 카운트.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    cfResult = company.select("CF", ["dividends_paid"])
    isResult = company.select("IS", ["당기순이익"])

    cfParsed = toDictBySnakeId(cfResult)
    isParsed = toDictBySnakeId(isResult)
    if cfParsed is None or isParsed is None:
        return None

    cfData, cfPeriods = cfParsed
    isData, _ = isParsed

    divRow = cfData.get("dividends_paid", {})
    niRow = isData.get("net_profit", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    consecutiveYears = 0
    countingConsecutive = True

    for i, col in enumerate(yCols):
        divPaid = abs(_getF(divRow, col))  # CF에서 음수로 나옴
        ni = _getF(niRow, col)

        payoutRatio = _pct(divPaid, ni) if ni > 0 else None

        # 배당 성장률 — base effect cap ±999%
        # prev=0 (신규배당) 또는 cur=0 (중단) 은 None.
        # 신규배당 base effect (예: SK +8600%, HMM +2913%) 는 사용자 혼란 → cap.
        dividendGrowth = None
        if i + 1 < len(yCols):
            prevCol = yCols[i + 1]
            prevDiv = abs(_getF(divRow, prevCol))
            if prevDiv > 0 and divPaid > 0:
                rawGrowth = (divPaid - prevDiv) / prevDiv * 100
                dividendGrowth = round(max(min(rawGrowth, 999.0), -999.0), 2)

        history.append(
            {
                "period": col,
                "dividendsPaid": divPaid,
                "netIncome": ni,
                "payoutRatio": payoutRatio,
                "dividendGrowth": dividendGrowth,
            }
        )

        # 연속 배당 연수
        if countingConsecutive:
            if divPaid > 0:
                consecutiveYears += 1
            else:
                countingConsecutive = False

    return {"history": history, "consecutiveYears": consecutiveYears} if history else None


# ── 주주환원 ──


@memoizedCalc
def calcShareholderReturn(company, *, basePeriod: str | None = None) -> dict | None:
    """주주환원 시계열 — 배당 + 자사주 매입 vs FCF.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        history : list[dict]
            period : str — 기간
            dividendsPaid : float — 배당금 (원)
            treasuryStockPurchase : float — 자사주 매입액 (원)
            totalReturn : float — 총주주환원 (원)
            fcf : float — 잉여현금흐름 (원)
            returnToFcf : float | None — 주주환원/FCF 비율 (%)

    Capabilities:
        - 배당 + 자사주 매입 합산 → 총주주환원 vs FCF 비교 시계열
        - returnToFcf ≥ 50% = 강한 주주환원

    Guide:
        FCF 의 50%+ 환원이 5 년 지속 = shareholder-friendly 회사. Buffett 선호 지표.

    When:
        Capital allocation + AI 주주환원 답변.

    How:
        CF dividends_paid + treasury 합산 → /FCF 시계열.

    Requires:
        CF 시계열 + FCF 계산 가능.

    Raises:
        없음.

    Example:
        >>> calcShareholderReturn(company)["history"][0]["returnToFcf"]
        65

    See Also:
        - calcDividendPolicy : 배당 단일
        - calcFcfUsage : FCF 사용 분해

    AIContext:
        "주주환원 비율" 답변 시 returnToFcf 인용.
    """
    cfResult = company.select(
        "CF",
        [
            "operating_cashflow",
            "purchase_of_property_plant_and_equipment",
            "purchase_of_intangible_assets",
            "dividends_paid",
            "purchase_of_treasury_stock",
        ],
    )

    cfParsed = toDictBySnakeId(cfResult)
    if cfParsed is None:
        return None

    cfData, cfPeriods = cfParsed

    ocfRow = cfData.get("operating_cashflow", {})
    capexRow = cfData.get("purchase_of_property_plant_and_equipment", {})
    intCapexRow = cfData.get("purchase_of_intangible_assets", {})
    divRow = cfData.get("dividends_paid", {})
    tsRow = cfData.get("purchase_of_treasury_stock", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        divPaid = abs(_getF2(divRow, col))
        ocf = _getF2(ocfRow, col)
        capex = abs(_getF2(capexRow, col)) + abs(_getF2(intCapexRow, col))
        fcf = ocf - capex

        tsPurchase = abs(_getF2(tsRow, col))

        totalReturn = divPaid + tsPurchase
        returnToFcf = _pct(totalReturn, fcf) if fcf > 0 else None

        history.append(
            {
                "period": col,
                "dividendsPaid": divPaid,
                "treasuryStockPurchase": tsPurchase,
                "totalReturn": totalReturn,
                "fcf": fcf,
                "returnToFcf": returnToFcf,
            }
        )

    return {"history": history} if history else None


# ── 재투자 ──


@memoizedCalc
def calcReinvestment(company, *, basePeriod: str | None = None) -> dict | None:
    """재투자 시계열 — 재투자율, CAPEX/매출.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        history : list[dict]
            period : str — 기간
            capex : float — 자본적지출 (원)
            operatingIncome : float — 영업이익 (원)
            revenue : float — 매출 (원)
            capexToRevenue : float | None — CAPEX/매출 비율 (%)
            retentionRate : float | None — 유보율 (%)

    Capabilities:
        - CAPEX (유무형 합산) + 영업이익 + 유보율 시계열
        - 재투자 강도 측정

    Guide:
        capexToRevenue ≥ 10% = 재투자 중심 (성장형). retentionRate ≥ 80% = 성장 우선.

    When:
        재투자 분석 + AI capex 답변.

    How:
        CF capex + IS revenue/net 시계열 → ratio 계산.

    Requires:
        CF/IS 시계열.

    Raises:
        없음.

    Example:
        >>> calcReinvestment(company)["history"][0]["capexToRevenue"]
        8.5

    See Also:
        - calcFcfUsage : FCF 사용
        - investmentAnalysis.* : 정밀 capex

    AIContext:
        "재투자 강도" 답변 시 capexToRevenue + retentionRate 인용.
    """
    cfResult = company.select(
        "CF",
        ["purchase_of_property_plant_and_equipment", "purchase_of_intangible_assets", "dividends_paid"],
    )
    isResult = company.select("IS", ["영업이익", "매출액", "당기순이익"])

    cfParsed = toDictBySnakeId(cfResult)
    isParsed = toDictBySnakeId(isResult)
    if cfParsed is None or isParsed is None:
        return None

    cfData, cfPeriods = cfParsed
    isData, _ = isParsed

    capexRow = cfData.get("purchase_of_property_plant_and_equipment", {})
    intCapexRow = cfData.get("purchase_of_intangible_assets", {})
    divRow = cfData.get("dividends_paid", {})
    opRow = isData.get("operating_profit", {})
    revRow = isData.get("sales", {})
    niRow = isData.get("net_profit", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        capex = abs(_getF3(capexRow, col)) + abs(_getF3(intCapexRow, col))
        opIncome = _getF3(opRow, col)
        rev = _getF3(revRow, col)
        ni = _getF3(niRow, col)
        divPaid = abs(_getF3(divRow, col))

        # 유보율 = 1 - 배당성향
        retentionRate = None
        if ni > 0:
            payoutRatio = divPaid / ni
            retentionRate = (1 - payoutRatio) * 100

        history.append(
            {
                "period": col,
                "capex": capex,
                "operatingIncome": opIncome,
                "revenue": rev,
                "capexToRevenue": _pct(capex, rev),
                "retentionRate": retentionRate,
            }
        )

    return {"history": history} if history else None


# ── FCF 사용처 분해 ──


@memoizedCalc
def calcFcfUsage(company, *, basePeriod: str | None = None) -> dict | None:
    """FCF 사용처 분해 시계열 — 배당/부채상환/잔여.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        history : list[dict]
            period : str — 기간
            fcf : float — 잉여현금흐름 (원)
            dividendsPaid : float — 배당금 지급 (원)
            debtRepaid : float — 부채 상환 (원)
            residual : float — 잔여 현금 (원)

    Capabilities:
        - FCF → 배당/부채상환/잔여 3 분해 시계열
        - 잔여 = M&A 또는 현금 누적

    Guide:
        residual / FCF ≥ 30% 가 5 년 지속 = 자본 적재 (war chest).

    When:
        FCF 사용처 분석 + AI 자본 배분 답변.

    How:
        CF dividends + debt repayments + FCF 계산.

    Requires:
        CF 시계열.

    Raises:
        없음.

    Example:
        >>> calcFcfUsage(company)["history"][0]["residual"]
        2000000000

    See Also:
        - calcShareholderReturn : 주주환원
        - calcReinvestment : 재투자

    AIContext:
        "FCF 어디 쓰는가" 답변 시 dividend/debt/residual 비중 인용.
    """
    cfResult = company.select(
        "CF",
        [
            "operating_cashflow",
            "purchase_of_property_plant_and_equipment",
            "purchase_of_intangible_assets",
            "dividends_paid",
            "repayment_of_longterm_borrowings",
            "redemption_of_current_portion_of_longterm_borrowings",
            "repayment_of_bonds_and_longterm_borrowings",
            "repayment_of_borrowings",  # Fallback: 단/장기 분리 안 된 통합 차입금 상환 (audit 04 #B 같은 패턴)
        ],
    )
    cfParsed = toDictBySnakeId(cfResult)
    if cfParsed is None:
        return None

    cfData, cfPeriods = cfParsed
    ocfRow = cfData.get("operating_cashflow", {})
    capexRow = cfData.get("purchase_of_property_plant_and_equipment", {})
    intCapexRow = cfData.get("purchase_of_intangible_assets", {})
    divRow = cfData.get("dividends_paid", {})
    repayRow1 = cfData.get("repayment_of_longterm_borrowings", {})
    repayRow2 = cfData.get("redemption_of_current_portion_of_longterm_borrowings", {})
    repayRow3 = cfData.get("repayment_of_bonds_and_longterm_borrowings", {})
    repayRow4 = cfData.get("repayment_of_borrowings", {})  # 통합 차입금 상환

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        ocf = _getF4(ocfRow, col)
        capex = abs(_getF4(capexRow, col)) + abs(_getF4(intCapexRow, col))
        fcf = ocf - capex
        divPaid = abs(_getF4(divRow, col))
        # 분리 키 + 통합 키 fallback. 어느 한쪽이 모두 0이면 다른 쪽이 활성됨
        debtRepaidSplit = abs(_getF4(repayRow1, col)) + abs(_getF4(repayRow2, col)) + abs(_getF4(repayRow3, col))
        debtRepaidUnified = abs(_getF4(repayRow4, col))
        debtRepaid = debtRepaidSplit if debtRepaidSplit > 0 else debtRepaidUnified
        residual = fcf - divPaid - debtRepaid

        history.append(
            {
                "period": col,
                "fcf": fcf,
                "dividendsPaid": divPaid,
                "debtRepaid": debtRepaid,
                "residual": residual,
            }
        )

    return {"history": history} if history else None


# ── 배당 서술 보강 (docs) ──


@memoizedCalc
def calcDividendDocs(company, *, basePeriod: str | None = None) -> dict | None:
    """docs dividend 토픽에서 배당성향, 배당수익률, 주당배당금 추출.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        dps : float | None — 주당배당금 (원)
        payoutRatio : float | None — 배당성향 (%)
        dividendYield : float | None — 배당수익률 (%)
        period : str — 기준 기간

    Capabilities:
        - DART dividend 토픽에서 주당배당금/배당성향/배당수익률 직접 추출
        - 보통주 기준 최신 기간

    Guide:
        DART 정식 dividend 토픽 사용 (calcDividendPolicy CF 합산 보완). dps 누락 시 None.

    When:
        AI 배당 답변 직접 수치 + 배당 관련 표시.

    How:
        ``company.select("dividend", ...)`` → 항목 매칭 → 보통주 dps/yield 추출.

    Requires:
        DART dividend 토픽.

    Raises:
        없음.

    Example:
        >>> calcDividendDocs(company)["dps"]
        1500

    See Also:
        - calcDividendPolicy : CF 합산 버전
        - calcShareholderReturn : 합산

    AIContext:
        "주당 배당금" 답변 시 dps + payoutRatio 인용.
    """
    from dartlab.core.utils.helpers import parseNumStr

    result = company.select("dividend", ["주당현금배당금", "현금배당성향", "현금배당수익률"])
    if result is None:
        return None

    import polars as pl

    df = result if isinstance(result, pl.DataFrame) else getattr(result, "df", None)
    if df is None or "항목" not in df.columns:
        return None

    from dartlab.core.utils.helpers import periodCols

    pCols = periodCols(df)
    if not pCols:
        return None

    latestCol = pCols[0]
    labelCol = "항목"
    items = df[labelCol].to_list()
    vals = df[latestCol].to_list()

    dps = None
    payoutRatio = None
    dividendYield = None

    for it, v in zip(items, vals):
        it = str(it)
        parsed = parseNumStr(str(v))
        if parsed is None:
            continue
        if "주당현금배당금" in it and "보통주" in it and dps is None:
            dps = parsed
        elif "현금배당성향" in it and "당기" in it and payoutRatio is None:
            payoutRatio = parsed
        elif "현금배당수익률" in it and "보통주" in it and dividendYield is None:
            dividendYield = parsed

    if dps is None and payoutRatio is None and dividendYield is None:
        return None

    return {
        "dps": dps,
        "payoutRatio": payoutRatio,
        "dividendYield": dividendYield,
        "period": latestCol,
    }


# ── 자사주 현황 (docs/report) ──


@memoizedCalc
def calcTreasuryStockStatus(company, *, basePeriod: str | None = None) -> dict | None:
    """treasuryStock 토픽에서 자사주 취득/처분/소각 현황 추출.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        rows : list[dict]
            method : str — 취득방법
            beginShares : float — 기초수량 (주)
            acquired : float — 취득수량 (주)
            disposed : float — 처분수량 (주)
            retired : float — 소각수량 (주)
            endShares : float — 기말수량 (주)

    Capabilities:
        - DART treasuryStock 토픽 + EDGAR XBRL fallback 으로 자사주 시계열
        - 취득/처분/소각 분해

    Guide:
        retired (소각) 가 acquired (취득) 보다 크면 자사주 누적 ↓ (주주환원 강).

    When:
        자사주 분석 + AI buyback 답변.

    How:
        company.show("treasuryStock") → DataFrame 총계 행 추출.

    Requires:
        DART treasuryStock 토픽 또는 EDGAR XBRL.

    Raises:
        없음.

    Example:
        >>> calcTreasuryStockStatus(company)["rows"][0]["acquired"]
        100000

    See Also:
        - calcShareholderReturn : 주주환원
        - _edgarTreasuryStockFallback

    AIContext:
        "자사주 매입 현황" 답변 시 acquired + retired 인용.
    """
    result = company.show("treasuryStock")

    # EDGAR fallback: XBRL companyfacts에서 자사주 데이터 추출
    market = getattr(company, "market", "KR")
    if result is None and market == "US":
        return _edgarTreasuryStockFallback(company)

    if result is None:
        return None

    import polars as pl

    if not isinstance(result, pl.DataFrame):
        return None

    # report 토픽 — 이미 수치 DataFrame
    if "기말수량" not in result.columns and "기말잔량" not in result.columns:
        return None

    endCol = "기말수량" if "기말수량" in result.columns else "기말잔량"
    beginCol = "기초수량" if "기초수량" in result.columns else None
    acqCol = "변동수량(취득)" if "변동수량(취득)" in result.columns else None
    dispCol = "변동수량(처분)" if "변동수량(처분)" in result.columns else None
    retCol = "변동수량(소각)" if "변동수량(소각)" in result.columns else None

    # 총계 행만 추출
    rows = []
    for row in result.iter_rows(named=True):
        method = str(row.get("취득방법(대)", row.get("취득방법(중)", "")))
        if "총계" not in method:
            continue
        entry = {"method": method}
        if beginCol:
            entry["beginShares"] = row.get(beginCol)
        if acqCol:
            entry["acquired"] = row.get(acqCol)
        if dispCol:
            entry["disposed"] = row.get(dispCol)
        if retCol:
            entry["retired"] = row.get(retCol)
        entry["endShares"] = row.get(endCol)
        rows.append(entry)

    return {"rows": rows} if rows else None


def _edgarTreasuryStockFallback(company) -> dict | None:
    """EDGAR: companyfacts XBRL에서 자사주 관련 태그 추출.

    Returns
    -------
    dict | None
        ``{"rows": [{"method": str, "acquired": float(달러), "endShares": None}, ...], "source": "XBRL"}``.
        데이터 없으면 None.
    """
    try:
        from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

        # CF에서 자사주 매입 금액 추출
        parsed = toDictBySnakeId(company.select("CF", ["purchase_of_treasury_stock", "share_repurchase"]))
        if parsed is None:
            return None
        cfData, cfPeriods = parsed
        yCols = annualColsFromPeriods(cfPeriods, maxYears=5)
        if not yCols:
            return None

        tsRow = cfData.get("purchase_of_treasury_stock", cfData.get("share_repurchase", {}))
        rows = []
        for col in yCols:
            v = tsRow.get(col)
            if v is not None:
                rows.append(
                    {
                        "method": f"Share Repurchase ({col})",
                        "acquired": abs(float(v)),
                        "endShares": None,
                    }
                )

        return {"rows": rows, "source": "XBRL"} if rows else None
    except (AttributeError, ValueError, TypeError, KeyError):
        return None


# ── 플래그 ──


@memoizedCalc
def calcCapitalAllocationFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """자본배분 경고 신호.

    Returns
    -------
    list[str]
        경고 메시지 문자열 리스트 (배당 초과, FCF 초과 환원, 극소 투자 등).

    Capabilities:
        - 배당 초과/FCF 초과 환원/극소 투자 등 자본배분 경고 누적
        - story flag 박스 입력

    Guide:
        flag ≥ 2 = 자본배분 다중 경고. 배당 초과 + FCF 초과 환원 = 부채 의존.

    When:
        Capital allocation 경고 + AI 위험 답변.

    How:
        sub-calc 결과 임계 비교 → 메시지 누적.

    Requires:
        sub-calc 가용.

    Raises:
        없음.

    Example:
        >>> calcCapitalAllocationFlags(company)
        ['배당성향 110% — 이익 초과 배당']

    See Also:
        - calcDividendPolicy : payout
        - calcShareholderReturn : 환원/FCF

    AIContext:
        "자본배분 경고" 답변 시 flag list 인용.
    """
    flags = []

    dividend = calcDividendPolicy(company, basePeriod=basePeriod)
    if dividend and dividend["history"]:
        h0 = dividend["history"][0]
        pr = h0.get("payoutRatio")
        if pr is not None and pr > 100:
            flags.append(f"배당성향 {pr:.0f}% — 이익 초과 배당")

        # 배당 3년 연속 감소
        hist = dividend["history"]
        if len(hist) >= 3:
            divs = [h["dividendsPaid"] for h in hist[:3]]
            if divs[0] < divs[1] < divs[2] and divs[2] > 0:
                flags.append("배당금 3년 연속 감소")

    shareholder = calcShareholderReturn(company, basePeriod=basePeriod)
    if shareholder and shareholder["history"]:
        h0 = shareholder["history"][0]
        rtf = h0.get("returnToFcf")
        if rtf is not None and rtf > 100:
            flags.append(f"주주환원/FCF {rtf:.0f}% — FCF 초과 환원")

    reinvest = calcReinvestment(company, basePeriod=basePeriod)
    if reinvest and reinvest["history"]:
        h0 = reinvest["history"][0]
        cr = h0.get("capexToRevenue")
        if cr is not None and cr < 1:
            flags.append(f"CAPEX/매출 {cr:.1f}% — 극소 투자")

    return flags
