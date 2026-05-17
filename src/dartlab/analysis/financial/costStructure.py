"""비용 구조 분석 — 원가/판관비 비중, 영업레버리지, 손익분기점 시계열.

비용이 어떻게 움직이는지, 매출 변동에 이익이 얼마나 민감한지를 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from typing import Any

from dartlab.analysis.financial.accountSums import sumCostOfSales, sumSGA
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_YEARS = 8


# ── 유틸 ──


from dartlab.core.utils.calc import safePct as _pct  # noqa: E402

# ── 비용 비중 분해 ──


@memoizedCalc
def calcCostBreakdown(company, *, basePeriod: str | None = None) -> dict | None:
    """비용 구조 시계열 — 매출원가율 + 판관비율 + 영업비용률.

    Capabilities:
        IS 비용 3 종 (매출원가, 판관비, 영업비용 합계) 의 매출 대비 비중
        시계열 + 비용의 성격별 분류 (notesDetail) 자동 결합. 분리 키
        (sumCostOfSales/sumSGA) 폴백으로 회사별 계정 변형 흡수.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 7 키 (period + revenue +
              costOfSales + sga + 3 비율).
            - ``notesDetail`` (dict | None): 비용의 성격별 분류 주석.

    Raises:
        없음.

    Example:
        >>> r = calcCostBreakdown(Company("005930"))
        >>> r["history"][0]["costOfSalesRatio"]
        65.0  # 매출원가율 65%

    Guide:
        매출원가율 3 기 연속 상승 = 원가 부담 (calcCostStructureFlags 자동
        탐지). 판관비율 동시 상승 = 운영 효율 저하. 단년도 절대값보다 추세
        변화에 주목.

    When:
        비용 구조 변화·원가 부담 추세 진단, 마진 분석의 1 차 입력.

    How:
        IS rawNormalized → 매출 + sumCostOfSales (폴백) + sumSGA (폴백) →
        3 비율 → notesDetail (costByNature) 결합.

    SeeAlso:
        - ``calcOperatingLeverage``: DOL (영업레버리지)
        - ``calcBreakevenEstimate``: BEP + 안전마진
        - ``calcCostByNatureAnalysis``: 비용 성격별 (원재료/인건비/감가)
        - ``calcMarginTrend``: 마진 시계열 (대척 지표)

    Requires:
        IS (매출액, 매출원가, 판매비와관리비). 매출 None/0 인 period 는
        skip (가짜 0 출력 회피).

    AIContext:
        3 비율 절대값 + 추세 함께 인용. 매출원가율 추세 상승 + 판관비율
        하락 = 외부 원가 (원재료/인건비) 충격 — calcCostByNatureAnalysis
        의 카테고리별 분해로 원인 추적.

    LLM Specifications:
        AntiPatterns:
            - 단년도 비율 인용 — 동종 업종 평균 + 추세 함께 (calcMarginTrend).
            - 매출 0 period 출력 — 본 함수가 None/0 자동 skip.
        OutputSchema:
            ``{history: list[dict 7키], notesDetail?: dict}``.
        Prerequisites:
            IS 시계열 + 매출원가/판관비 표준 또는 분리 계정.
        Freshness:
            분기 + 시계열.
        Dataflow:
            IS → 매출 + sumCostOfSales (폴백) + sumSGA (폴백) → 3 비율 →
            notesDetail (costByNature) 결합.
        TargetMarkets: KR (DART), US (EDGAR — COGS/SG&A 표준).
    """
    # snakeId 단일 + sumCostOfSales / sumSGA 분리 키 fallback
    accounts = ["매출액", "매출원가", "판매비와관리비"]
    isResult = company.select("IS", accounts)
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None

    isData, isPeriods = isParsed
    revRow = isData.get("sales", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        # 매출 미수집 (None) 인 period 는 분석 skip — 매출 0 회사 사실상 없음 (None = 미수집).
        # 가짜 0 출력 회피 (신뢰성 원칙).
        rev = revRow.get(col)
        if rev is None or rev <= 0:
            continue
        cogs = sumCostOfSales(isData, col)  # 분리/통합 키 fallback
        sga = sumSGA(isData, col)  # 판매비/관리비 분리 키 fallback

        history.append(
            {
                "period": col,
                "revenue": rev,
                "costOfSales": cogs,
                "sga": sga,
                "costOfSalesRatio": _pct(cogs, rev),
                "sgaRatio": _pct(sga, rev),
                "operatingCostRatio": _pct(cogs + sga, rev),
            }
        )

    if not history:
        return None

    # notes enrichment — 비용의 성격별 분류 (있으면)
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    result: dict[str, Any] = {"history": history}
    notesDetail = fetchNotesDetail(company, ["costByNature"])
    if notesDetail:
        result["notesDetail"] = notesDetail

    return result


# ── 영업레버리지 ──


@memoizedCalc
def calcOperatingLeverage(company, *, basePeriod: str | None = None) -> dict | None:
    """영업레버리지 (DOL) 시계열 — 매출 변동 대비 영업이익 민감도.

    Capabilities:
        DOL = 영업이익 변화율 / 매출 변화율 (전년 대비). 양쪽 모두 양수일
        때만 의미 — 부호 전환 시 None. DOL 절대값 cap ±20 (극단 레버리지
        해석 무의미). contributionProxy = 매출총이익/영업이익 (고정비 구조
        프록시).

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 6 키 (period + revenue +
              operatingIncome + grossProfit + dol + contributionProxy).

    Raises:
        없음.

    Example:
        >>> r = calcOperatingLeverage(Company("005930"))
        >>> r["history"][0]["dol"]
        2.5  # 매출 10% 변동 시 영업이익 25% 변동

    Guide:
        DOL > 3 = 고정비 부담 큼 (반도체/철강/화학 제조업 전형). DOL < 1.5
        = 변동비 비중 큼 (소매/서비스). 경기 하강기에 DOL 높은 회사는
        영업이익 급락 위험. contributionProxy 와 함께 인용.

    When:
        고정비 구조 평가·경기 하강기 영업이익 민감도 진단 시.

    How:
        IS 매출/영업이익/매출총이익 매핑 → 전년 대비 변화율 비율로 DOL +
        contributionProxy 계산. 부호 전환 period 는 None.

    SeeAlso:
        - ``calcCostBreakdown``: 비용 구조 (DOL 의 근거)
        - ``calcBreakevenEstimate``: BEP + 안전마진
        - ``calcMarginTrend``: 영업이익률 추세

    Requires:
        IS (매출액, 영업이익, 매출총이익) ≥ 2 년.

    AIContext:
        DOL 단년도 절대값 + 추세 + 업종 평균 함께. 매출/영업이익 부호
        전환 (적자→흑자) 직후는 DOL 무의미 (None). 본 함수가 자동 None.

    LLM Specifications:
        AntiPatterns:
            - DOL 단독 인용 — 부호 전환 직후 None 무시.
            - 서비스업에 DOL 3 단정 — 제조업 기준 적용 부적합.
        OutputSchema:
            ``{history: list[dict 6키]}``.
        Prerequisites:
            IS 시계열 + 영업이익/매출총이익 표준 계정.
        Freshness:
            분기 + 시계열 ≥ 2 년.
        Dataflow:
            IS → 매출/영업이익 (전년 대비) → 변화율 → DOL (양수일 때만)
            → cap ±20 → contributionProxy = 매출총이익/영업이익.
        TargetMarkets: KR (DART), US (EDGAR — Operating Income 표준).
    """
    accounts = ["매출액", "영업이익", "매출총이익"]
    isResult = company.select("IS", accounts)
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None

    isData, isPeriods = isParsed
    revRow = isData.get("매출액", {})
    opRow = isData.get("영업이익", {})
    gpRow = isData.get("매출총이익", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    history = []
    for i, col in enumerate(yCols):
        rev = _getF2(revRow, col)
        opIncome = _getF2(opRow, col)
        gp = _getF2(gpRow, col)

        # DOL = 영업이익 변화율 / 매출 변화율 (전년 대비)
        # 양쪽 다 양수일 때만 의미 있음 (부호 전환 시 DOL 해석 불가)
        dol = None
        if i + 1 < len(yCols):
            prevCol = yCols[i + 1]
            prevRev = _getF2(revRow, prevCol)
            prevOp = _getF2(opRow, prevCol)
            if prevRev > 0 and prevOp > 0 and opIncome > 0:
                revChange = (rev - prevRev) / prevRev
                opChange = (opIncome - prevOp) / prevOp
                if abs(revChange) > 0.001:
                    rawDol = opChange / revChange
                    # DOL > 20이면 해석 무의미 (극단적 레버리지), cap 처리
                    dol = max(-20, min(20, rawDol))

        # contribution proxy = 매출총이익 / 영업이익 (고정비 구조 프록시)
        contributionProxy = None
        if opIncome > 0 and gp > 0:
            contributionProxy = gp / opIncome

        history.append(
            {
                "period": col,
                "revenue": rev,
                "operatingIncome": opIncome,
                "grossProfit": gp,
                "dol": dol,
                "contributionProxy": contributionProxy,
            }
        )

    return {"history": history} if history else None


# ── 손익분기점 추정 ──


@memoizedCalc
def calcBreakevenEstimate(company, *, basePeriod: str | None = None) -> dict | None:
    """손익분기점 (BEP) 추정 + 안전마진 시계열.

    Capabilities:
        BEP = 고정비 / (1 - 변동비율). 단순화 가정: 변동비 = 매출원가,
        고정비 = 판매비와관리비. 변동비율 95% 이상이면 한계이익률 무의미
        → BEP None. 안전마진 = (매출 - BEP) / 매출 × 100.

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 연도별 6 키 (period + revenue +
              fixedCostEstimate + variableCostRatio + bepRevenue +
              marginOfSafety).

    Raises:
        없음.

    Example:
        >>> r = calcBreakevenEstimate(Company("005930"))
        >>> r["history"][0]["marginOfSafety"]
        45.0  # 안전마진 45% — BEP 매출 대비 45% 여유

    Guide:
        안전마진 < 10% = 손익분기 근접 (경고). 30~50% = 양호. > 50% =
        매우 안정. 단순화 가정 (매출원가 = 변동비) 은 제조업에 적합,
        서비스업/소프트웨어는 인건비 분류 차이로 왜곡 가능.

    When:
        손익분기점 분석·안전마진 정성 평가 시.

    How:
        IS 매출/매출원가/판관비 매핑 → 변동비율 = 매출원가/매출 → BEP =
        판관비/(1-변동비율) → 안전마진 = (매출-BEP)/매출.

    SeeAlso:
        - ``calcOperatingLeverage``: DOL (BEP 와 paired)
        - ``calcCostBreakdown``: 비용 구조 (BEP 의 입력)
        - ``calcCostByNatureAnalysis``: 정확한 변동비/고정비 분해

    Requires:
        IS (매출액, 매출원가, 판매비와관리비).

    AIContext:
        안전마진 + BEP 매출 함께. 단순화 가정 한계 명시 — 정확한 변동비/
        고정비는 비용의 성격별 분류 (notes) 필요. calcCostByNatureAnalysis
        결과 함께 인용 권장.

    LLM Specifications:
        AntiPatterns:
            - 서비스/SW 회사에 매출원가 = 변동비 가정 — 인건비 (고정/준고정)
              왜곡.
            - 안전마진 50% → "안정" 단정 — 매출 변동성 (calcGrowthTrend) 함께.
        OutputSchema:
            ``{history: list[dict 6키]}``.
        Prerequisites:
            IS 시계열 + 매출원가 + 판관비 표준 계정.
        Freshness:
            분기 + 시계열.
        Dataflow:
            IS → 매출/매출원가/판관비 → 변동비율 = 매출원가/매출 → BEP =
            판관비/(1-변동비율) → 안전마진 = (매출-BEP)/매출.
        TargetMarkets: KR (DART), US (EDGAR — 제조업 최적).
    """
    accounts = ["매출액", "매출원가", "판매비와관리비"]
    isResult = company.select("IS", accounts)
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None

    isData, isPeriods = isParsed
    revRow = isData.get("매출액", {})
    cogsRow = isData.get("매출원가", {})
    sgaRow = isData.get("판매비와관리비", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod, _MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        rev = _getF3(revRow, col)
        cogs = _getF3(cogsRow, col)
        sga = _getF3(sgaRow, col)

        # 단순화: 변동비 = 매출원가, 고정비 = 판관비
        variableCostRatio = cogs / rev if rev > 0 else None
        fixedCost = sga
        bepRevenue = None
        marginOfSafety = None

        # 변동비율 95% 이상이면 한계이익률이 너무 작아 BEP 무의미
        if variableCostRatio is not None and 0 < variableCostRatio < 0.95:
            bepRevenue = fixedCost / (1 - variableCostRatio)
            if rev > 0:
                marginOfSafety = (rev - bepRevenue) / rev * 100

        history.append(
            {
                "period": col,
                "revenue": rev,
                "fixedCostEstimate": fixedCost,
                "variableCostRatio": variableCostRatio,
                "bepRevenue": bepRevenue,
                "marginOfSafety": marginOfSafety,
            }
        )

    return {"history": history} if history else None


# ── calcCostByNatureAnalysis + calcRawMaterialBreakdown → _costStructureDeep.py 분리 ──

from dartlab.analysis.financial._costStructureDeep import (  # noqa: E402, F401
    calcCostByNatureAnalysis,
    calcRawMaterialBreakdown,
)


@memoizedCalc
def calcCostStructureFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """비용 구조 경고 신호.

    Capabilities:
        - 매출원가율/판관비율 3 기 연속 상승, 고DOL, 안전마진 부족 시 한국어
          flags 산출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간.

    Returns:
        list[str]: 한국어 경고 메시지. 임계 미달 시 빈 리스트.

    Guide:
        flag 신호 — cogsRatio/sgaRatio 3 년 단조 상승, DOL > 3, 안전마진 < 10%.

    When:
        보고서·UI 위험 배너에 비용 구조 경고 한 줄 표시.

    How:
        ``calcCostBreakdown`` + ``calcOperatingLeverage`` + ``calcBreakevenEstimate``
        결과를 임계와 비교 후 한국어 포맷팅.

    Requires:
        하위 3 calc 가용성.

    Raises:
        없음.

    Example:
        >>> calcCostStructureFlags(Company("005930"))
        ["매출원가율 3년 연속 상승 ..."]

    SeeAlso:
        - ``calcCostBreakdown``: 본 함수 입력

    AIContext:
        AI 답변에서 비용 구조 위험 인용 시.
    """
    flags = []

    breakdown = calcCostBreakdown(company, basePeriod=basePeriod)
    if breakdown and len(breakdown["history"]) >= 3:
        hist = breakdown["history"]
        # 매출원가율 3년 연속 상승
        cogsRatios = [h.get("costOfSalesRatio") for h in hist[:3]]
        if all(r is not None for r in cogsRatios):
            if cogsRatios[0] > cogsRatios[1] > cogsRatios[2]:
                flags.append(f"매출원가율 3년 연속 상승 ({cogsRatios[2]:.1f}% -> {cogsRatios[0]:.1f}%)")

        # 판관비율 3년 연속 상승
        sgaRatios = [h.get("sgaRatio") for h in hist[:3]]
        if all(r is not None for r in sgaRatios):
            if sgaRatios[0] > sgaRatios[1] > sgaRatios[2]:
                flags.append(f"판관비율 3년 연속 상승 ({sgaRatios[2]:.1f}% -> {sgaRatios[0]:.1f}%)")

    leverage = calcOperatingLeverage(company, basePeriod=basePeriod)
    if leverage and leverage["history"]:
        h0 = leverage["history"][0]
        dol = h0.get("dol")
        if dol is not None and dol > 3:
            flags.append(f"영업레버리지(DOL) {dol:.1f} — 매출 변동에 이익 민감")

    bep = calcBreakevenEstimate(company, basePeriod=basePeriod)
    if bep and bep["history"]:
        h0 = bep["history"][0]
        mos = h0.get("marginOfSafety")
        if mos is not None and mos < 10:
            flags.append(f"안전마진 {mos:.1f}% — 손익분기점 근접")

    return flags
