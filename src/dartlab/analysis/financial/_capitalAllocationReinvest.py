"""capitalAllocation 의 재투자/FCF 사용처/플래그 cluster — Reinvestment/FcfUsage/Flags."""

from __future__ import annotations

from dartlab.analysis.financial._capitalAllocationPayout import (
    calcDividendPolicy,
    calcShareholderReturn,
)
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.calc import safePct as _pct
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get
_MAX_YEARS = 8


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
