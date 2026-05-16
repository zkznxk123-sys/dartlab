"""1-3 자산 구조 분석 — 계산만 담당.

BS를 영업/비영업으로 재분류하여 자산 운영 구조를 본다.
블록 조립은 story/builders.py가 한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from typing import Any

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_YEARS = 8
_MAX_QUARTERS = 5


from dartlab.core.utils.calc import safePct as _pct  # noqa: E402
from dartlab.core.utils.safe import getFirst as _getFirst  # noqa: E402

# ── 영업/비영업 분류 매핑 ──

# 영업자산 — 이중 카운팅 방지를 위해 fallback 쌍 분리
# "매출채권" / "매출채권및기타채권" → 하나만 사용 (_getFirst)
# "매입채무" / "매입채무및기타채무" → 하나만 사용 (_getFirst)
_OP_ASSET_SIMPLE = [
    "기타유동금융자산",
    "재고자산",
    "선급금",
    "기타유동자산",
    # 고정영업자산
    "유형자산",
    "사용권자산",
    "무형자산",
    "영업권",
    "건설중인자산",
    "투자부동산",
]
_OP_ASSET_FALLBACK = [["매출채권", "매출채권및기타채권"]]

_NON_OP_ASSET_ACCOUNTS = [
    "현금및현금성자산",
    "단기금융자산",
    "장기금융자산",
    "관계기업등지분관련투자자산",
    "기타비유동금융자산",
]

# 관계기업 투자: 기업마다 다른 항목 사용 → fallback 쌍
_ASSOCIATES_FALLBACK = ("관계기업등지분관련투자자산", "지분법적용투자지분")

_OP_LIAB_SIMPLE = [
    "선수금",
    "계약부채",
    "선수수익",
    "미지급비용",
    "미지급금",
    "충당부채",
    "기타유동부채",
]
_OP_LIAB_FALLBACK = [["매입채무", "매입채무및기타채무"]]

# 운전자본: fallback 체인 (매출채권 없으면 매출채권및기타채권 사용)
_WC_REC_KEYS = ["매출채권", "매출채권및기타채권"]
_WC_PAY_KEYS = ["매입채무", "매입채무및기타채무"]
_WC_ASSET_KEYS = ["재고자산", "선급금", "기타유동자산"]

_FIXED_OP_KEYS = ["유형자산", "사용권자산", "무형자산", "영업권", "건설중인자산"]


def _sumOp(data: dict, col: str, simpleKeys: list[str], fallbackPairs: list[list[str]]) -> float:
    """영업자산/부채 합산 (fallback 쌍은 하나만 선택).

    Parameters
    ----------
    data : dict
        ``{snakeId: {period: value}}`` 형태의 BS 데이터.
    col : str
        대상 기간 컬럼.
    simpleKeys : list[str]
        단순 합산 대상 계정 키 목록.
    fallbackPairs : list[list[str]]
        fallback 쌍 목록. 각 쌍에서 첫 번째 값이 있으면 사용, 없으면 두 번째.

    Returns
    -------
    float
        합산 금액 (원). 모두 없으면 0.
    """
    total = sum(_get(data.get(k, {}), col) for k in simpleKeys)
    for pair in fallbackPairs:
        total += _getFirst(data, pair, col)
    return total


# ── 메인: 자산 구조 ──


@memoizedCalc
def calcAssetStructure(company, *, basePeriod: str | None = None) -> dict | None:
    """자산을 영업/비영업으로 재분류 → 순영업자산 (NOA) + 자본배분 진단.

    Capabilities:
        BS 의 자산을 영업자산 (PP&E + 운전자본 + 영업관련 무형) vs 비영업자산
        (현금 + 투자유가증권 + 비영업 부동산) 으로 재분류. NOA (Net Operating
        Assets) = 영업자산 - 영업부채 산출. Penman/Healy (2018) 회계분석
        프레임의 핵심.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns
    -------
    dict | None
        latest : dict
            totalAssets : float — 총자산 (원)
            opAssets : float — 영업자산 (원)
            opAssetsPct : float — 영업자산 비중 (%)
            nonOpAssets : float — 비영업자산 (원)
            nonOpAssetsPct : float — 비영업자산 비중 (%)
            workingCapital : float — 순운전자본 (원)
            fixedOpAssets : float — 고정영업자산 (원)
            noa : float — 순영업자산 (원)
            netFinDebt : float — 순금융부채 (원)
        history : list[dict] — 연도별 자산 구조 시계열
        diagnosis : str — 자산 구조 진단
        notesDetail : dict | None — 주석 상세 데이터

    Raises:
        없음.

    Example:
        >>> r = calcAssetStructure(Company("005930"))
        >>> r["latest"]["opAssetsPct"], r["latest"]["nonOpAssetsPct"]
        (68, 32)  # 영업 68%, 비영업 (현금/투자) 32%

    Guide:
        영업자산 비중 > 70% = 영업 집중, 30~70% = 균형, < 30% = 비영업
        과다 (지주사 또는 자본배분 비효율 신호). NOA 증가 추세 = 자본 재투자
        (cumulative reinvestment). Penman ROE 분해: ROE = RNOA + FLEV × Spread.

    SeeAlso:
        - ``calcWorkingCapital``: 순운전자본 분해
        - ``calcCapexPattern``: 고정영업자산 변화
        - ``analyzeProfitability``: ROE/ROA 분석 (NOA 기반)

    Requires:
        Company.select(BS, [자산총계, 부채총계, 영업자산 + 영업부채 후보]).

    AIContext:
        비영업자산 비중 50%+ 회사 (예 캐시카우) 는 RNOA 가 ROE 보다 훨씬 높음
        — 영업 효율성 평가에 유용. opAssets/nonOpAssets 비중 시계열 추세
        함께 노출.

    LLM Specifications:
        AntiPatterns:
            - 단년도 NOA 만 보고 효율성 판단 — 3 년 추세 필요.
            - 캡티브 금융 회사 (현대차/기아) → 비영업 (금융자회사 자산) 큼.
              "비영업 과다" 단정 금지.
        OutputSchema:
            ``{latest: dict 9키, history: list[dict], diagnosis: str,
            notesDetail: dict | None}``.
        Prerequisites:
            BS 시계열 + 자산/부채 standardAccounts.
        Freshness:
            최신 분기 + 3~5 년 시계열.
        Dataflow:
            BS → 영업자산 (PPE + 무형 + 운전자본) + 비영업 (현금 + 투자) 분리
            → NOA 합성 → diagnosis.
        TargetMarkets: KR (DART), US (EDGAR). 표준 계정 매핑은 standardAccounts.
    """
    _allFallback = [k for pair in _OP_ASSET_FALLBACK + _OP_LIAB_FALLBACK for k in pair]
    allAccounts = (
        ["자산총계", "부채총계"]
        + _OP_ASSET_SIMPLE
        + _allFallback
        + _NON_OP_ASSET_ACCOUNTS
        + list(_ASSOCIATES_FALLBACK)
        + _OP_LIAB_SIMPLE
    )
    result = company.select("BS", allAccounts)
    parsed = toDictBySnakeId(result)
    if parsed is None:
        return None

    data, allPeriods = parsed
    taRow = data.get("자산총계")
    if taRow is None:
        return None

    yCols = annualColsFromPeriods(allPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    latest = None

    for col in yCols:
        ta = _get(taRow, col)
        if ta <= 0:
            continue

        # 영업자산 합산 (fallback 쌍은 하나만 선택)
        opAssets = _sumOp(data, col, _OP_ASSET_SIMPLE, _OP_ASSET_FALLBACK)
        # 비영업자산 합산 (관계기업 투자는 fallback 쌍)
        nonOpAssets = 0
        for k in _NON_OP_ASSET_ACCOUNTS:
            if k == _ASSOCIATES_FALLBACK[0]:
                v = _get(data.get(k, {}), col)
                if v == 0:
                    v = _get(data.get(_ASSOCIATES_FALLBACK[1], {}), col)
                nonOpAssets += v
            else:
                nonOpAssets += _get(data.get(k, {}), col)
        # 나머지 = 총자산 - 영업 - 비영업 (분류 안 된 것)
        otherAssets = ta - opAssets - nonOpAssets

        # 영업부채 (fallback 쌍은 하나만 선택)
        opLiab = _sumOp(data, col, _OP_LIAB_SIMPLE, _OP_LIAB_FALLBACK)

        # 순영업자산(NOA) = 영업자산 - 영업부채
        noa = opAssets - opLiab

        # 순운전자본 자산/부채 (fallback 체인)
        rec = _getFirst(data, _WC_REC_KEYS, col)
        wcAssets = rec + sum(_get(data.get(k, {}), col) for k in _WC_ASSET_KEYS)
        pay = _getFirst(data, _WC_PAY_KEYS, col)
        wcOtherLiab = sum(
            _get(data.get(k, {}), col) for k in ["선수금", "계약부채", "선수수익", "미지급비용", "미지급금"]
        )
        wcLiab = pay + wcOtherLiab
        wc = wcAssets - wcLiab

        # 고정영업자산
        fixedOp = sum(_get(data.get(k, {}), col) for k in _FIXED_OP_KEYS)

        # 순금융부채
        cash = _get(data.get("현금및현금성자산", {}), col)
        stFin = _get(data.get("단기금융자산", {}), col)
        finDebt = _get(data.get("부채총계", {}), col) - opLiab
        netFinDebt = max(0, finDebt - cash - stFin)

        # 세부 구성 (매 연도)
        recVal = _getFirst(data, _WC_REC_KEYS, col)
        invVal = _get(data.get("재고자산", {}), col)
        ppeVal = _get(data.get("유형자산", {}), col)
        intVal = _get(data.get("무형자산", {}), col)
        gwVal = _get(data.get("영업권", {}), col)
        rouVal = _get(data.get("사용권자산", {}), col)
        cipVal = _get(data.get("건설중인자산", {}), col)
        assocVal = _get(data.get(_ASSOCIATES_FALLBACK[0], {}), col)
        if assocVal == 0:
            assocVal = _get(data.get(_ASSOCIATES_FALLBACK[1], {}), col)
        invstVal = assocVal + _get(data.get("장기금융자산", {}), col)

        entry = {
            "period": col,
            "totalAssets": ta,
            "opAssets": opAssets,
            "opAssetsPct": _pct(opAssets, ta),
            "nonOpAssets": nonOpAssets,
            "nonOpAssetsPct": _pct(nonOpAssets, ta),
            "otherAssetsPct": _pct(otherAssets, ta),
            "noa": noa,
            "wc": wc,
            "fixedOp": fixedOp,
            # 세부 항목
            "receivables": recVal,
            "inventory": invVal,
            "ppe": ppeVal,
            "intangibles": intVal,
            "goodwill": gwVal,
            "rou": rouVal,
            "cip": cipVal,
            "cash": cash,
            "stFinancial": stFin,
            "investments": invstVal,
        }
        history.append(entry)

        if latest is None:
            latest = {
                "totalAssets": ta,
                "opAssets": opAssets,
                "opAssetsPct": _pct(opAssets, ta),
                "nonOpAssets": nonOpAssets,
                "nonOpAssetsPct": _pct(nonOpAssets, ta),
                "otherAssets": ta - opAssets - nonOpAssets,
                "otherAssetsPct": _pct(ta - opAssets - nonOpAssets, ta),
                "workingCapital": wc,
                "fixedOpAssets": fixedOp,
                "noa": noa,
                "netFinDebt": netFinDebt,
            }

    if latest is None:
        return None

    # 진단
    opPct = latest["opAssetsPct"]
    nonOpPct = latest["nonOpAssetsPct"]
    if opPct >= 70:
        diagnosis = "영업자산 중심 — 자산 대부분이 사업에 투입됨"
    elif nonOpPct >= 40:
        diagnosis = "비영업자산 과다 — 투자/금융자산 비중이 높음 (지주회사 성격)"
    elif opPct >= 50:
        diagnosis = "혼합 구조 — 영업자산과 비영업자산이 섞여 있음"
    else:
        diagnosis = "비영업 우위 — 영업 자산보다 비영업 자산이 많음"

    # notes enrichment — 주석에서 상세 분해 데이터 추가 (있으면)
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesDetail = fetchNotesDetail(company, ["inventory", "tangibleAsset", "intangibleAsset", "investmentProperty"])

    resultDict: dict[str, Any] = {
        "latest": latest,
        "history": history,
        "diagnosis": diagnosis,
    }
    if notesDetail:
        resultDict["notesDetail"] = notesDetail

    return resultDict


# ── 운전자본 ──


@memoizedCalc
def calcWorkingCapital(company, *, basePeriod: str | None = None) -> dict | None:
    """운전자본 상세 + CCC.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        latest : dict
            wc : float — 순운전자본 (원)
            receivables : float — 매출채권 (원)
            inventory : float — 재고자산 (원)
            payables : float — 매입채무 (원)
            receivableDays : float — 매출채권 회수일수 (일)
            inventoryDays : float — 재고자산 보유일수 (일)
            payableDays : float — 매입채무 지급일수 (일)
            ccc : float — 현금전환주기 (일)
        history : list[dict] — 연도별 운전자본 시계열
    """
    bsAccounts = ["매출채권", "매출채권및기타채권", "재고자산", "매입채무", "매입채무및기타채무"]
    isAccounts = ["매출액", "매출원가"]

    bsResult = company.select("BS", bsAccounts)
    isResult = company.select("IS", isAccounts)
    bsParsed = toDictBySnakeId(bsResult)
    isParsed = toDictBySnakeId(isResult)
    if bsParsed is None or isParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    isData, isPeriods = isParsed

    invRow = bsData.get("재고자산", {})
    revRow = isData.get("매출액", {})
    cogsRow = isData.get("매출원가", {})

    yCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    def _getFlow(row: dict, col: str) -> float:
        """flow 행에서 값 추출 (None → 0)."""
        v = row.get(col)
        return v if v is not None else 0

    history = []
    latest = None

    for col in yCols:
        rec = _getFirst(bsData, _WC_REC_KEYS, col)
        inv = _get(invRow, col)
        pay = _getFirst(bsData, _WC_PAY_KEYS, col)
        rev = _getFlow(revRow, col)
        cogs = _getFlow(cogsRow, col)
        wc = rec + inv - pay

        # 회전일수
        recDays = rec / rev * 365 if rev > 0 else None
        invDays = inv / cogs * 365 if cogs > 0 else None
        payDays = pay / cogs * 365 if cogs > 0 else None
        ccc = None
        if recDays is not None and invDays is not None and payDays is not None:
            ccc = recDays + invDays - payDays

        entry = {
            "period": col,
            "wc": wc,
            "receivableDays": recDays,
            "inventoryDays": invDays,
            "payableDays": payDays,
            "ccc": ccc,
        }
        history.append(entry)

        if latest is None:
            latest = {
                "wc": wc,
                "receivables": rec,
                "inventory": inv,
                "payables": pay,
                "receivableDays": recDays,
                "inventoryDays": invDays,
                "payableDays": payDays,
                "ccc": ccc,
            }

    if latest is None:
        return None
    return {"latest": latest, "history": history}


# ── calcCapexPattern + calcInvestmentPropertyTrend + calcIntangibleAssetDetail → _assetCapex.py 분리 ──

from dartlab.analysis.financial._assetCapex import (  # noqa: E402, F401
    calcCapexPattern,
    calcIntangibleAssetDetail,
    calcInvestmentPropertyTrend,
)

# ── 자산 플래그 ──


@memoizedCalc
def calcAssetFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """자산 구조 경고 신호.

    Returns
    -------
    list[str]
        경고 메시지 문자열 리스트 (비영업자산 과다, CCC 과다, CAPEX 부족/과잉, 자산효율 악화 등).
    """
    flags = []

    structure = calcAssetStructure(company, basePeriod=basePeriod)
    if structure:
        lat = structure["latest"]
        if lat["nonOpAssetsPct"] >= 40:
            flags.append(f"비영업자산 {lat['nonOpAssetsPct']:.0f}% — 지주/투자 성격")
        hist0 = structure["history"][0] if structure["history"] else {}
        if hist0:
            ta = lat["totalAssets"]
            cipPct = _pct(hist0.get("cip", 0), ta)
            if cipPct >= 10:
                flags.append(f"건설중인자산 {cipPct:.0f}% — 대규모 투자 진행 중")
            invPct = _pct(hist0.get("inventory", 0), ta)
            if invPct >= 20:
                flags.append(f"재고자산 {invPct:.0f}% — 재고 비대화 주의")

    wc = calcWorkingCapital(company, basePeriod=basePeriod)
    if wc and wc["latest"]["ccc"] is not None:
        ccc = wc["latest"]["ccc"]
        if ccc > 2000:
            pass  # CCC > 2000일은 데이터 왜곡 가능성 → 경고 제외
        elif ccc > 120:
            flags.append(f"CCC {ccc:.0f}일 — 현금 회수 매우 느림")
        # CCC < 0은 선수금/매입채무 우위로 운전자본 효율적 → 경고 아닌 정보
        # efficiency.py의 "운전자본 유리 구조"로 충분

    capex = calcCapexPattern(company, basePeriod=basePeriod)
    if capex and capex["latest"]["capexToDepRatio"] is not None:
        ratio = capex["latest"]["capexToDepRatio"]
        if ratio < 0.5 and ratio > 0:
            flags.append(f"CAPEX/감가상각 {ratio:.1f}배 — 투자 부족 (자산 노후화 위험)")
        elif ratio > 3.0:
            flags.append(f"CAPEX/감가상각 {ratio:.1f}배 — 공격적 투자")

    from dartlab.analysis.financial.efficiency import calcTurnoverTrend

    turnover = calcTurnoverTrend(company, basePeriod=basePeriod)
    if turnover and turnover.get("totalAssetTurnover"):
        tat = turnover["totalAssetTurnover"]
        if len(tat) >= 2:
            newest = tat[0].get("value")
            oldest = tat[-1].get("value")
            if newest is not None and oldest is not None and oldest > 0:
                change = (newest - oldest) / oldest * 100
                if change < -20:
                    flags.append(f"총자산회전율 {change:.0f}% 하락 — 자산 효율 악화")

    return flags
