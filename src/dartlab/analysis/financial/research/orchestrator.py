"""Research 오케스트레이터 — Company → ResearchResult."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from dartlab.analysis.financial.research.quality import calcCoverageScore
from dartlab.analysis.financial.research.scoring import calcAllScores
from dartlab.analysis.financial.research.thesis import classifyProfile, synthesizeThesis
from dartlab.analysis.financial.research.types import (
    AnomalySection,
    CompanyOverview,
    DistressSection,
    EarningsQuality,
    ExecutiveSummary,
    FinancialAnalysis,
    ForecastData,
    InsightDetail,
    MarketData,
    PeerSection,
    ResearchMeta,
    ResearchResult,
    RiskSection,
    ValuationSection,
)
from dartlab.analysis.forecast.forecast import forecastMetric

_log = logging.getLogger(__name__)


def generateResearch(
    company: object,
    *,
    sections: list[str] | None = None,
    includeMarket: bool = True,
) -> ResearchResult:
    """종합 기업분석 리포트 생성.

    Parameters
    ----------
    company : object
        Company 객체.
    sections : list[str], optional
        포함할 섹션 목록. None이면 전체.
    includeMarket : bool
        시장 데이터 포함 여부.

    Returns
    -------
    ResearchResult
        종합 리포트 (executive/thesis/risk/valuation/forecast/narrative 등).
    """
    result = ResearchResult()
    wantAll = sections is None
    want = set(sections) if sections else set()

    stockCode = getattr(company, "stockCode", "")
    corpName = getattr(company, "corpName", "")

    # ── Phase 0: Meta ──
    result.meta = ResearchMeta(
        stockCode=stockCode,
        corpName=corpName,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )

    # ── Phase 1: Finance ──
    aSeries, aYears = _getAnnualData(company)
    ratios = _safeAttr(company, "finance", "ratios")

    # ── Phase 2: Insight (확장 — details/distress/anomalies 전부 수집) ──
    insights = None
    insightDetails: list[InsightDetail] = []
    if wantAll or want & {"executive", "thesis", "risk", "insightDetails"}:
        insights = _safeGet(company, "insights")

    grades: dict[str, str] = {}
    if insights is not None:
        try:
            grades = insights.grades()
        except (AttributeError, TypeError):
            pass
        insightDetails = _extractInsightDetails(insights)
        result.insightDetails = insightDetails

    # ── Phase 2: ESG ──
    esgResult = None
    if wantAll or "esgGovernance" in want:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            esgResult = _safeGet(company, "esg")

    # ── Phase 2: QuantScores ──
    quantScores = None
    currentPrice = None
    sharesOutstanding = None

    if aSeries and (wantAll or want & {"quantScores", "executive", "thesis"}):
        if includeMarket:
            currentPrice, sharesOutstanding = _getMarketInfo(company)
        quantScores = calcAllScores(
            aSeries,
            aYears,
            currentPrice=currentPrice,
            sharesOutstanding=sharesOutstanding,
        )
        result.quantScores = quantScores

    # ── Phase 2: Earnings Quality ──
    if aSeries and (wantAll or "earningsQuality" in want):
        result.earningsQuality = _buildEarningsQuality(aSeries, ratios)

    # ── Phase 2: Financial ──
    if aSeries and (wantAll or "financial" in want):
        result.financial = _buildFinancial(aSeries, aYears, quantScores)

    # ── Phase 2: Sector KPIs ──
    if aSeries and (wantAll or "sectorKpis" in want):
        result.sectorKpis = _buildSectorKpis(company, aSeries, ratios)

    # ── Phase 2: Overview ──
    if wantAll or "overview" in want:
        result.overview = _buildOverview(company)

    # ── Phase 3: Market Data ──
    marketData = None
    if includeMarket and (wantAll or want & {"marketData", "executive", "valuation"}):
        marketData = _buildMarketData(company)
        result.marketData = marketData
        if currentPrice is None and marketData:
            currentPrice = marketData.currentPrice

    # ── Phase 3: Valuation (NEW — analyst 엔진 활용) ──
    if aSeries and includeMarket and (wantAll or "valuation" in want):
        result.valuationAnalysis = _buildValuation(company, currentPrice, sharesOutstanding)

    # ── Phase 3: Forecast (확장 — 자체예측 + 시나리오) ──
    if includeMarket and (wantAll or "forecast" in want):
        result.forecast = _buildForecast(company, aSeries)

    # ── Phase 3: Peer (NEW — OOM 안전, 섹터 배수 기반) ──
    if aSeries and (wantAll or "peer" in want):
        result.peerAnalysis = _buildPeerAnalysis(company, ratios, marketData)

    # ── Phase 3: Risk (NEW — distress + anomalies + insight.risk) ──
    if wantAll or "risk" in want:
        result.riskAnalysis = _buildRiskAnalysis(insights, insightDetails)

    # ── Phase 4: Executive ──
    upside = None
    opinion = ""
    if marketData and marketData.targetPrice and marketData.currentPrice:
        upside = (marketData.targetPrice - marketData.currentPrice) / marketData.currentPrice
        opinion = _classifyOpinion(upside)

    # valuation verdict도 반영
    if not opinion and result.valuationAnalysis and result.valuationAnalysis.verdict:
        va = result.valuationAnalysis
        if va.verdict == "저평가":
            opinion = "매수"
        elif va.verdict == "고평가":
            opinion = "매도"
        else:
            opinion = "중립"

    keyMetrics = _buildKeyMetrics(ratios, quantScores, marketData)

    result.executive = ExecutiveSummary(
        opinion=opinion,
        profile=classifyProfile(grades, upside),
        targetPrice=marketData.targetPrice if marketData else None,
        currentPrice=currentPrice,
        upside=upside,
        grades=grades,
        keyMetrics=keyMetrics,
    )

    # ── Phase 4: Narrative (v3 — 교차분석 서술) ──
    if aSeries and (wantAll or want & {"narrative", "thesis"}):
        try:
            from dartlab.analysis.financial.insight.benchmark import getBenchmark
            from dartlab.analysis.financial.research.narrative import buildNarrative
            from dartlab.industry import getParams

            sectorInfo = _safeGet(company, "sector")
            sectorEnum = getattr(sectorInfo, "sector", sectorInfo)
            sectorBench = getBenchmark(sectorEnum) if sectorEnum else None
            sectorPar = getParams(sectorInfo) if sectorInfo and hasattr(sectorInfo, "sector") else None

            result.narrativeAnalysis = buildNarrative(
                aSeries,
                aYears,
                result.financial.dupont if result.financial else None,
                result.earningsQuality,
                result.marketData,
                company,
                sectorBenchmark=sectorBench,
                sectorParams=sectorPar,
                ratios=ratios,
            )
        except (ImportError, OSError, ValueError, AttributeError, TypeError) as exc:
            _log.debug("narrative 실패: %s", exc)

    # ── Phase 4: Thesis (전면 재작성 — insightDetails/valuation/risk/narrative 전달) ──
    if wantAll or "thesis" in want:
        result.thesis = synthesizeThesis(
            result.executive,
            insightDetails=insightDetails,
            valuationAnalysis=result.valuationAnalysis,
            riskAnalysis=result.riskAnalysis,
            quantScores=quantScores,
            earningsQuality=result.earningsQuality,
            forecastData=result.forecast,
            narrativeAnalysis=result.narrativeAnalysis,
        )

    # ── Meta: coverage ──
    result.meta.coverageScore = calcCoverageScore(
        hasFinance=aSeries is not None,
        hasDocs=getattr(company, "_hasDocs", False),
        hasInsight=insights is not None,
        hasMarket=marketData is not None,
        hasValuation=result.valuationAnalysis is not None,
        hasForecast=result.forecast is not None,
        hasEsg=esgResult is not None,
        hasSectorKpis=result.sectorKpis is not None,
        hasRisk=result.riskAnalysis is not None,
        hasPeer=result.peerAnalysis is not None,
        hasNarrative=result.narrativeAnalysis is not None,
    )

    metaWarnings: list[str] = []
    if aSeries is None:
        metaWarnings.append("재무 데이터 없음")
    if not includeMarket:
        metaWarnings.append("시장 데이터 미포함")
    result.meta.warnings = metaWarnings

    return result


# ══════════════════════════════════════
# 내부 헬퍼 — 기존
# ══════════════════════════════════════


def _getAnnualData(company: object) -> tuple[dict | None, list[str]]:
    """Company에서 연간 시계열 추출."""
    try:
        finance = getattr(company, "finance", None)
        if finance is None:
            return None, []
        annual = getattr(finance, "annual", None)
        if annual is None:
            return None, []
        return annual
    except (RuntimeError, FileNotFoundError, OSError) as exc:
        _log.debug("연간 데이터 로드 실패: %s", exc)
        return None, []


def _safeGet(company: object, attr: str) -> object:
    """Company property 안전 접근."""
    try:
        return getattr(company, attr, None)
    except (RuntimeError, FileNotFoundError, OSError, ValueError) as exc:
        _log.debug("%s 로드 실패: %s", attr, exc)
        return None


def _safeAttr(company: object, namespace: str, attr: str) -> object:
    """Company.namespace.attr 안전 접근."""
    try:
        ns = getattr(company, namespace, None)
        if ns is None:
            return None
        return getattr(ns, attr, None)
    except (RuntimeError, FileNotFoundError, OSError, ValueError) as exc:
        _log.debug("%s.%s 로드 실패: %s", namespace, attr, exc)
        return None


def _getMarketInfo(company: object) -> tuple[float | None, float | None]:
    """현재가 + 발행주식수."""
    try:
        from dartlab.gather import getDefaultGather

        g = getDefaultGather()
        stockCode = getattr(company, "stockCode", "")
        snap = g.price(stockCode)
        if snap is None:
            return None, None

        price = getattr(snap, "current", None)
        marketCap = getattr(snap, "market_cap", None)
        shares = None
        if price and marketCap and price > 0:
            shares = marketCap / price
        return price, shares
    except (ImportError, OSError, ValueError) as exc:
        _log.debug("market info 실패: %s", exc)
        return None, None


def _buildEarningsQuality(aSeries: dict, ratios: object) -> EarningsQuality:
    """이익의 질 조립."""
    from dartlab.core.finance.extract import getLatest, getTTM

    ni = getTTM(aSeries, "IS", "net_profit", strict=False)
    ocf = getTTM(aSeries, "CF", "operating_cashflow", strict=False)

    cfToNi = None
    if ni and ocf and ni != 0:
        cfToNi = round(ocf / ni, 2)

    beneish = getattr(ratios, "beneish_m_score", None) if ratios else None
    ccc = getattr(ratios, "cash_conversion_cycle", None) if ratios else None

    ta = getLatest(aSeries, "BS", "total_assets")
    accrual = None
    if ni is not None and ocf is not None and ta and ta > 0:
        accrual = round((ni - ocf) / ta, 4)

    assessment = "moderate"
    if cfToNi is not None:
        if cfToNi > 1.0 and (accrual is None or accrual < 0.05):
            assessment = "high"
        elif cfToNi < 0.5 or (accrual is not None and accrual > 0.15):
            assessment = "questionable"
        elif cfToNi < 0.8:
            assessment = "low"

    return EarningsQuality(
        cfToNi=cfToNi,
        accrualRatio=accrual,
        ccc=ccc,
        beneishMScore=beneish,
        assessment=assessment,
    )


def _at(lst: list, i: int):
    """i 번째 안전 조회."""
    return lst[i] if i < len(lst) else None


def _pickSeries(data: dict, candidates: list[str]) -> list:
    """후보 키 리스트 중 값이 있는 첫 시계열 반환."""
    for c in candidates:
        raw = data.get(c, [])
        if raw and any(v is not None for v in raw):
            return raw
    return data.get(candidates[0], []) if candidates else []


def _buildIsTrends(
    aSeries: dict, aYears: list[str], start: int, n: int
) -> tuple[dict[str, list[float | None]], list[str], list[float | None]]:
    """IS 기반 시계열 — 수익성/원가/효율성/성장/규모. 반환: (trends, periods, niAbs)."""
    salesList = aSeries.get("IS", {}).get("sales", [])
    cogsList = aSeries.get("IS", {}).get("cost_of_sales", [])
    opList = aSeries.get("IS", {}).get("operating_profit", [])
    niList = aSeries.get("IS", {}).get("net_profit", [])
    bsData = aSeries.get("BS", {})
    recvList = _pickSeries(bsData, ["trade_receivable", "trade_and_other_receivables"])
    invList = bsData.get("inventories", [])
    payList = _pickSeries(bsData, ["trade_payable", "trade_and_other_payables"])

    periods: list[str] = []
    opMargins: list[float | None] = []
    netMargins: list[float | None] = []
    grossMargins: list[float | None] = []
    cogsRatios: list[float | None] = []
    sgaRatios: list[float | None] = []
    dsoList: list[float | None] = []
    dioList: list[float | None] = []
    dpoList: list[float | None] = []
    cccList: list[float | None] = []
    salesGr: list[float | None] = []
    opGr: list[float | None] = []
    salesAbs: list[float | None] = []
    opAbs: list[float | None] = []
    niAbs: list[float | None] = []

    for i in range(start, n):
        s = _at(salesList, i)
        cogs = _at(cogsList, i)
        op = _at(opList, i)
        ni = _at(niList, i)
        recv = _at(recvList, i)
        inv = _at(invList, i)
        pay = _at(payList, i)
        periods.append(aYears[i])

        salesAbs.append(s)
        opAbs.append(op)
        niAbs.append(ni)

        _appendMarginRow(s, cogs, op, ni, opMargins, netMargins, grossMargins, cogsRatios, sgaRatios)
        _appendCccRow(s, cogs, recv, inv, pay, dsoList, dioList, dpoList, cccList)
        _appendGrowthRow(i, s, op, salesList, opList, salesGr, opGr)

    trends = {
        "operatingMargin": opMargins,
        "netMargin": netMargins,
        "grossMargin": grossMargins,
        "costOfSalesRatio": cogsRatios,
        "sgaRatio": sgaRatios,
        "dso": dsoList,
        "dio": dioList,
        "dpo": dpoList,
        "ccc": cccList,
        "salesGrowth": salesGr,
        "opGrowth": opGr,
        "sales": salesAbs,
        "operatingProfit": opAbs,
        "netProfit": niAbs,
    }
    return trends, periods, niAbs


def _appendMarginRow(s, cogs, op, ni, opMargins, netMargins, grossMargins, cogsRatios, sgaRatios) -> None:
    """한 기간의 수익성 지표 5개 append (opM, netM, grossM, cogsR, sgaR)."""
    if not (s and s > 0):
        opMargins.append(None)
        netMargins.append(None)
        grossMargins.append(None)
        cogsRatios.append(None)
        sgaRatios.append(None)
        return
    opMargins.append(round(op / s * 100, 2) if op is not None else None)
    netMargins.append(round(ni / s * 100, 2) if ni is not None else None)
    if cogs is None:
        grossMargins.append(None)
        cogsRatios.append(None)
        sgaRatios.append(None)
        return
    grossMargins.append(round((s - cogs) / s * 100, 2))
    cogsRatios.append(round(cogs / s * 100, 2))
    if op is not None:
        sgaRatios.append(round((s - cogs - op) / s * 100, 2))
    else:
        sgaRatios.append(None)


def _appendCccRow(s, cogs, recv, inv, pay, dsoList, dioList, dpoList, cccList) -> None:
    """한 기간의 DSO/DIO/DPO/CCC append."""
    dso = recv / (s / 365) if recv is not None and s and s > 0 else None
    dio = inv / (cogs / 365) if inv is not None and cogs and cogs > 0 else None
    dpo = pay / (cogs / 365) if pay is not None and cogs and cogs > 0 else None
    dsoList.append(round(dso, 1) if dso is not None else None)
    dioList.append(round(dio, 1) if dio is not None else None)
    dpoList.append(round(dpo, 1) if dpo is not None else None)
    if dso is not None and dio is not None and dpo is not None:
        cccList.append(round(dso + dio - dpo, 1))
    else:
        cccList.append(None)


def _appendGrowthRow(i, s, op, salesList, opList, salesGr, opGr) -> None:
    """한 기간의 매출/영업이익 YoY append."""
    prevIdx = i - 1
    if prevIdx < 0 or prevIdx >= len(salesList):
        salesGr.append(None)
        opGr.append(None)
        return
    ps = salesList[prevIdx]
    if ps and ps != 0 and s is not None:
        salesGr.append(round((s - ps) / abs(ps) * 100, 1))
    else:
        salesGr.append(None)
    po = _at(opList, prevIdx)
    if po and po != 0 and op is not None:
        opGr.append(round((op - po) / abs(po) * 100, 1))
    else:
        opGr.append(None)


_BS_SUMMARY_KEYS: dict[str, list[str]] = {
    "totalAssets": ["total_assets"],
    "currentAssets": ["current_assets"],
    "nonCurrentAssets": ["noncurrent_assets", "non_current_assets"],
    "totalLiabilities": ["total_liabilities"],
    "totalEquity": ["total_stockholders_equity", "total_equity", "owners_of_parent_equity"],
    "cashAndEquivalents": ["cash_and_cash_equivalents"],
    "shortTermBorrowings": ["shortterm_borrowings", "short_term_borrowings"],
    "longTermBorrowings": ["longterm_borrowings", "long_term_borrowings"],
    "retainedEarnings": ["retained_earnings"],
    "inventories": ["inventories"],
    "tradeReceivable": ["trade_and_other_receivables", "trade_receivable"],
}


def _buildBsSummary(aSeries: dict, start: int, n: int) -> dict[str, list[float | None]]:
    """BS 요약 시계열 + 부채비율/유동비율 파생."""
    bsData = aSeries.get("BS", {})
    bsSummary: dict[str, list[float | None]] = {}
    for outKey, srcCandidates in _BS_SUMMARY_KEYS.items():
        raw = _pickSeries(bsData, srcCandidates)
        bsSummary[outKey] = [_at(raw, i) for i in range(start, n)]

    debtRatios: list[float | None] = []
    currentRatios: list[float | None] = []
    clList = bsData.get("current_liabilities", [])
    for i in range(start, n):
        idx = i - start
        tl = _at(bsSummary["totalLiabilities"], idx)
        te = _at(bsSummary["totalEquity"], idx)
        ca = _at(bsSummary["currentAssets"], idx)
        cl = _at(clList, i)
        debtRatios.append(round(tl / te * 100, 1) if tl and te and te != 0 else None)
        currentRatios.append(round(ca / cl * 100, 1) if ca and cl and cl != 0 else None)
    bsSummary["debtRatio"] = debtRatios
    bsSummary["currentRatio"] = currentRatios
    return bsSummary


def _buildCfSummary(aSeries: dict, start: int, n: int) -> dict[str, list[float | None]]:
    """CF 요약 시계열 + FCF 파생."""
    cfData = aSeries.get("CF", {})
    cfKeys = {
        "operatingCf": ["operating_cashflow", "operating_cf", "cash_flows_from_business"],
        "investingCf": ["investing_cashflow", "investing_cf"],
        "financingCf": ["financing_cashflow", "financing_cf", "cash_flows_from_financing_activities"],
    }
    cfSummary: dict[str, list[float | None]] = {}
    for outKey, srcCandidates in cfKeys.items():
        raw = _pickSeries(cfData, srcCandidates)
        cfSummary[outKey] = [_at(raw, i) for i in range(start, n)]

    capexRaw = _pickSeries(cfData, ["purchase_of_property_plant_and_equipment", "capital_expenditures", "capex"])
    fcfList: list[float | None] = []
    capexList: list[float | None] = []
    for i in range(start, n):
        ocf = _at(cfSummary["operatingCf"], i - start)
        cx = _at(capexRaw, i)
        capexList.append(cx)
        if ocf is not None and cx is not None:
            fcfList.append(round(ocf - abs(cx), 1))
        elif ocf is not None:
            fcfList.append(ocf)
        else:
            fcfList.append(None)
    cfSummary["capex"] = capexList
    cfSummary["fcf"] = fcfList
    return cfSummary


def _buildCrossMetrics(
    aSeries: dict,
    cfSummary: dict[str, list[float | None]],
    niAbs: list[float | None],
    periods: list[str],
    start: int,
    n: int,
) -> dict[str, list[float | None]]:
    """3표 교차 지표 — OCF/NI, capex/감가상각, 이익잉여금 증가율."""
    cfData = aSeries.get("CF", {})
    bsData = aSeries.get("BS", {})
    ocfToNi: list[float | None] = []
    for idx in range(len(periods)):
        ocf = _at(cfSummary["operatingCf"], idx)
        ni = _at(niAbs, idx)
        if ocf is not None and ni is not None and ni != 0:
            ocfToNi.append(round(ocf / ni, 2))
        else:
            ocfToNi.append(None)

    deprRaw = _pickSeries(cfData, ["depreciation_amortization", "depreciation", "depreciation_and_amortization"])
    capexRaw = _pickSeries(cfData, ["purchase_of_property_plant_and_equipment", "capital_expenditures", "capex"])
    capexToDepr: list[float | None] = []
    for i in range(start, n):
        cx = _at(capexRaw, i)
        dp = _at(deprRaw, i)
        if cx is not None and dp is not None and dp != 0:
            capexToDepr.append(round(abs(cx) / abs(dp), 2))
        else:
            capexToDepr.append(None)

    reRaw = bsData.get("retained_earnings", [])
    reGrowth: list[float | None] = []
    for i in range(start, n):
        cur = _at(reRaw, i)
        prev = _at(reRaw, i - 1) if i - 1 >= 0 else None
        if cur is not None and prev is not None and prev != 0:
            reGrowth.append(round((cur - prev) / abs(prev) * 100, 1))
        else:
            reGrowth.append(None)

    return {
        "ocfToNetIncome": ocfToNi,
        "capexToDepreciation": capexToDepr,
        "retainedEarningsGrowth": reGrowth,
    }


def _buildIsCommonSize(aSeries: dict, start: int, n: int) -> dict[str, list[float | None]]:
    """Common-Size IS — 매출=100% 기준."""
    isKeys = {
        "costOfSales": "cost_of_sales",
        "grossProfit": "gross_profit",
        "operatingProfit": "operating_profit",
        "netProfit": "net_profit",
        "incomeTaxExpense": "income_tax_expense",
    }
    isData = aSeries.get("IS", {})
    salesList = isData.get("sales", [])
    result: dict[str, list[float | None]] = {}
    for outKey, srcKey in isKeys.items():
        raw = isData.get(srcKey, [])
        vals: list[float | None] = []
        for i in range(start, n):
            s = _at(salesList, i)
            v = _at(raw, i)
            vals.append(round(v / s * 100, 2) if s and s > 0 and v is not None else None)
        result[outKey] = vals
    return result


_BS_CS_KEYS: dict[str, list[str]] = {
    "currentAssets": ["current_assets", "total_current_assets"],
    "nonCurrentAssets": ["noncurrent_assets", "non_current_assets", "total_non_current_assets"],
    "totalLiabilities": ["total_liabilities"],
    "totalEquity": ["total_stockholders_equity", "total_equity", "owners_of_parent_equity"],
    "inventories": ["inventories"],
    "tradeReceivable": ["trade_and_other_receivables", "trade_receivable"],
    "ppe": ["property_plant_and_equipment"],
    "intangibleAssets": ["intangible_assets"],
}


def _buildBsCommonSize(aSeries: dict, start: int, n: int) -> dict[str, list[float | None]]:
    """Common-Size BS — 자산=100% 기준."""
    bsData = aSeries.get("BS", {})
    taRaw = bsData.get("total_assets", [])
    result: dict[str, list[float | None]] = {}
    for outKey, srcCandidates in _BS_CS_KEYS.items():
        raw = _pickSeries(bsData, srcCandidates)
        vals: list[float | None] = []
        for i in range(start, n):
            ta = _at(taRaw, i)
            v = _at(raw, i)
            vals.append(round(v / ta * 100, 2) if ta and ta > 0 and v is not None else None)
        result[outKey] = vals
    return result


def _buildFinancial(aSeries: dict, aYears: list[str], quantScores: object) -> FinancialAnalysis:
    """재무 분석 조립 orchestrator — 6 sub (Q3.1d split).

    수익성/원가구조/효율성/성장/규모 + BS·CF 요약 + 3표 교차 + Common-Size.
    """
    dupont = getattr(quantScores, "dupont", None) if quantScores else None
    salesList = aSeries.get("IS", {}).get("sales", [])
    n = min(len(salesList), len(aYears))
    start = max(0, n - 5)

    trends, periods, niAbs = _buildIsTrends(aSeries, aYears, start, n)
    bsSummary = _buildBsSummary(aSeries, start, n)
    cfSummary = _buildCfSummary(aSeries, start, n)
    crossMetrics = _buildCrossMetrics(aSeries, cfSummary, niAbs, periods, start, n)
    isCommonSize = _buildIsCommonSize(aSeries, start, n)
    bsCommonSize = _buildBsCommonSize(aSeries, start, n)

    return FinancialAnalysis(
        dupont=dupont,
        marginTrends=trends,
        periods=periods,
        bsSummary=bsSummary,
        cfSummary=cfSummary,
        crossStatementMetrics=crossMetrics,
        isCommonSize=isCommonSize,
        bsCommonSize=bsCommonSize,
    )


def _buildSectorKpis(company: object, aSeries: dict, ratios: object) -> object:
    """섹터 KPI 조립."""
    try:
        from dartlab.analysis.financial.research.sectorKpi import calcSectorKpis

        sectorInfo = _safeGet(company, "sector")
        sector = getattr(sectorInfo, "sector", sectorInfo)
        return calcSectorKpis(sector, aSeries, ratios)
    except (ImportError, ValueError, AttributeError) as exc:
        _log.debug("sectorKpi 실패: %s", exc)
        return None


def _buildOverview(company: object) -> CompanyOverview:
    """기업 개요."""
    desc = None
    try:
        overview = company.show("businessOverview")  # type: ignore[union-attr]
        if overview is not None and hasattr(overview, "height") and overview.height > 0:
            cols = [c for c in overview.columns if c[0].isdigit()]
            if cols:
                latestCol = cols[0]
                vals = overview[latestCol].to_list()
                texts = [v for v in vals if isinstance(v, str) and v.strip()]
                if texts:
                    desc = texts[0][:500]
    except (RuntimeError, AttributeError, OSError):
        pass

    sectorInfo = _safeGet(company, "sector")
    sectorEnum = getattr(sectorInfo, "sector", sectorInfo)
    sectorName = sectorEnum.value if sectorEnum and hasattr(sectorEnum, "value") else None

    return CompanyOverview(description=desc, sectorName=sectorName)


def _buildMarketData(company: object) -> MarketData | None:
    """시장 데이터 수집."""
    try:
        from dartlab.gather import getDefaultGather

        g = getDefaultGather()
        stockCode = getattr(company, "stockCode", "")

        snap = g.price(stockCode)
        cons = g.consensus(stockCode)
        flow = g.flow(stockCode)
        macro = g.macro()

        md = MarketData()
        if snap is not None and hasattr(snap, "current"):
            md.currentPrice = getattr(snap, "current", None)
            md.marketCap = getattr(snap, "market_cap", None)
            md.per = getattr(snap, "per", None)
            md.pbr = getattr(snap, "pbr", None)
            md.dividendYield = getattr(snap, "dividend_yield", None)
            md.high52w = getattr(snap, "high_52w", None)
            md.low52w = getattr(snap, "low_52w", None)
        if cons is not None and hasattr(cons, "target_price"):
            md.targetPrice = getattr(cons, "target_price", None)
            md.analystCount = getattr(cons, "analyst_count", None)
            md.buyRatio = getattr(cons, "buy_ratio", None)
        if flow is not None and hasattr(flow, "foreign_holding_ratio"):
            md.foreignHoldingRatio = getattr(flow, "foreign_holding_ratio", None)
        if macro is not None and isinstance(macro, dict):
            md.baseRate = macro.get("baseRate")
            md.usdKrw = macro.get("usdKrw")

        return md
    except (ImportError, OSError, ValueError) as exc:
        _log.debug("market data 실패: %s", exc)
        return None


def _buildKeyMetrics(ratios: object, quantScores: object, marketData: object) -> list[dict[str, object]]:
    """핵심 지표 4-6개."""
    metrics: list[dict[str, object]] = []

    if marketData:
        per = getattr(marketData, "per", None)
        if per is not None:
            metrics.append({"label": "PER", "value": per, "unit": "배"})
        pbr = getattr(marketData, "pbr", None)
        if pbr is not None:
            metrics.append({"label": "PBR", "value": pbr, "unit": "배"})

    if ratios:
        roe = getattr(ratios, "roe", None)
        if roe is not None:
            metrics.append({"label": "ROE", "value": round(roe, 1), "unit": "%"})
        debtRatio = getattr(ratios, "debt_ratio", None)
        if debtRatio is not None:
            metrics.append({"label": "부채비율", "value": round(debtRatio, 1), "unit": "%"})

    if quantScores:
        p = getattr(quantScores, "piotroski", None)
        if p:
            metrics.append({"label": "Piotroski F", "value": p.total, "unit": "/9"})

    return metrics[:6]


def _classifyOpinion(upside: float) -> str:
    """업사이드 → 투자의견."""
    if upside > 0.30:
        return "강력매수"
    if upside > 0.10:
        return "매수"
    if upside > -0.10:
        return "중립"
    if upside > -0.30:
        return "매도"
    return "강력매도"


# ══════════════════════════════════════
# 내부 헬퍼 — v2 신규
# ══════════════════════════════════════


def _extractInsightDetails(insights: object) -> list[InsightDetail]:
    """AnalysisResult에서 10영역 상세 추출."""
    areas = [
        "performance",
        "profitability",
        "health",
        "cashflow",
        "governance",
        "risk",
        "opportunity",
        "predictability",
        "uncertainty",
        "coreEarnings",
    ]
    result: list[InsightDetail] = []
    for area in areas:
        ir = getattr(insights, area, None)
        if ir is None:
            continue
        grade = getattr(ir, "grade", "")
        summary = getattr(ir, "summary", "")
        details = getattr(ir, "details", [])
        risks = [getattr(f, "text", str(f)) for f in getattr(ir, "risks", [])]
        opportunities = [getattr(f, "text", str(f)) for f in getattr(ir, "opportunities", [])]
        result.append(
            InsightDetail(
                area=area,
                grade=grade,
                summary=summary,
                details=details if isinstance(details, list) else [],
                risks=risks,
                opportunities=opportunities,
            )
        )
    return result


def _buildValuation(
    company: object,
    currentPrice: float | None,
    shares: float | None,
) -> ValuationSection | None:
    """analyst 밸류에이션 호출 → ValuationSection."""
    try:
        valSummary = company.valuation(shares=int(shares) if shares else None)  # type: ignore[union-attr]
        if valSummary is None:
            return None

        dcfPs = None
        dcfMos = None
        ddmPs = None
        relPs = None
        methodology: list[str] = []
        warnings: list[str] = []

        dcf = getattr(valSummary, "dcf", None)
        if dcf:
            dcfPs = getattr(dcf, "perShareValue", None)
            dcfMos = getattr(dcf, "marginOfSafety", None)
            if dcfPs:
                methodology.append(f"DCF (WACC {getattr(dcf, 'discountRate', '?')}%)")
            for w in getattr(dcf, "warnings", []):
                warnings.append(w)

        ddm = getattr(valSummary, "ddm", None)
        if ddm:
            ddmPs = getattr(ddm, "intrinsicValue", None)
            model = getattr(ddm, "modelUsed", "")
            if ddmPs and model != "N/A":
                methodology.append(f"DDM ({model})")

        rel = getattr(valSummary, "relative", None)
        if rel:
            relPs = getattr(rel, "consensusValue", None)
            if relPs:
                methodology.append("상대가치 (PER/PBR/EV-EBITDA)")

        fvr = getattr(valSummary, "fairValueRange", None)
        verdict = getattr(valSummary, "verdict", "") or ""

        return ValuationSection(
            dcfPerShare=dcfPs,
            dcfMos=dcfMos,
            ddmPerShare=ddmPs,
            relativePerShare=relPs,
            fairValueRange=fvr,
            verdict=verdict,
            methodology=methodology,
            warnings=warnings,
        )
    except (ImportError, OSError, ValueError, AttributeError, TypeError, RuntimeError) as exc:
        _log.debug("valuation 실패: %s", exc)
        return None


def _buildForecast(company: object, aSeries: dict | None) -> ForecastData | None:
    """전망 데이터 — 컨센서스 + 자체예측."""
    fd = ForecastData()

    # 1) 컨센서스 (gather)
    try:
        from dartlab.gather import getDefaultGather

        g = getDefaultGather()
        stockCode = getattr(company, "stockCode", "")
        revCons = g.revenue_consensus(stockCode)
        if revCons:
            fd.revenueConsensus = [
                {
                    "fiscalYear": getattr(rc, "fiscal_year", None),
                    "revenueEst": getattr(rc, "revenue_est", None),
                    "operatingProfitEst": getattr(rc, "operating_profit_est", None),
                    "epsEst": getattr(rc, "eps_est", None),
                }
                for rc in revCons
            ]
    except (ImportError, OSError, ValueError) as exc:
        _log.debug("consensus forecast 실패: %s", exc)

    # 2) 자체 매출 예측 (analyst.forecast)
    if aSeries:
        try:
            ts = getattr(getattr(company, "finance", None), "timeseries", None)
            series = ts[0] if isinstance(ts, tuple) else ts
            if series:
                fcResult = forecastMetric(series, metric="revenue", horizon=3)
                if fcResult and getattr(fcResult, "projected", None):
                    gr = getattr(fcResult, "growthRate", None)
                    fd.selfForecast = {
                        "method": "OLS/CAGR",
                        "growthRate": round(gr, 1) if gr is not None else None,
                        "confidence": "high" if getattr(fcResult, "rSquared", 0) > 0.7 else "moderate",
                        "projected": getattr(fcResult, "projected", []),
                    }
        except (ImportError, OSError, ValueError, AttributeError, TypeError) as exc:
            _log.debug("self forecast 실패: %s", exc)

    hasData = fd.revenueConsensus or fd.selfForecast is not None
    return fd if hasData else None


def _buildPeerAnalysis(
    company: object,
    ratios: object,
    marketData: MarketData | None,
) -> PeerSection | None:
    """동종업 비교 — 섹터 배수 기반 (OOM 안전, peer.discover 호출 안 함)."""
    try:
        sectorInfo = _safeGet(company, "sector")
        sectorEnum = getattr(sectorInfo, "sector", sectorInfo)
        if sectorEnum is None:
            return None

        sectorName = sectorEnum.value if hasattr(sectorEnum, "value") else str(sectorEnum)

        # 섹터 파라미터에서 배수 가져오기
        sectorMultiples: dict[str, float] = {}
        try:
            from dartlab.industry import SECTOR_PARAMS

            sp = SECTOR_PARAMS.get(sectorEnum)
            if sp:
                sectorMultiples = {
                    "PER": sp.perMultiple,
                    "PBR": sp.pbrMultiple,
                    "EV/EBITDA": sp.evEbitdaMultiple,
                }
        except (ImportError, AttributeError):
            pass

        # 기업 현재 배수
        companyMultiples: dict[str, float | None] = {}
        if marketData:
            companyMultiples["PER"] = marketData.per
            companyMultiples["PBR"] = marketData.pbr
        if ratios:
            evEbitda = getattr(ratios, "ev_ebitda", None)
            if evEbitda is not None:
                companyMultiples["EV/EBITDA"] = evEbitda

        # 할인/할증 계산
        premiumDiscount: dict[str, float | None] = {}
        for key in ["PER", "PBR", "EV/EBITDA"]:
            cv = companyMultiples.get(key)
            sv = sectorMultiples.get(key)
            if cv is not None and sv and sv > 0:
                premiumDiscount[key] = round((cv - sv) / sv * 100, 1)
            else:
                premiumDiscount[key] = None

        # 서술
        narrative = _buildPeerNarrative(sectorName, companyMultiples, sectorMultiples, premiumDiscount)

        return PeerSection(
            sectorName=sectorName,
            sectorMultiples=sectorMultiples,
            companyMultiples=companyMultiples,
            premiumDiscount=premiumDiscount,
            peerNarrative=narrative,
        )
    except (ImportError, OSError, ValueError, AttributeError) as exc:
        _log.debug("peer 실패: %s", exc)
        return None


def _buildPeerNarrative(
    sectorName: str,
    companyMultiples: dict[str, float | None],
    sectorMultiples: dict[str, float],
    premiumDiscount: dict[str, float | None],
) -> str:
    """peer 비교 서술 생성."""
    parts = []
    for key in ["PER", "PBR"]:
        pd = premiumDiscount.get(key)
        if pd is not None:
            if pd < -15:
                parts.append(f"{key} 기준 섹터 대비 {abs(pd):.0f}% 할인")
            elif pd > 15:
                parts.append(f"{key} 기준 섹터 대비 {pd:.0f}% 할증")
    return " | ".join(parts) if parts else f"{sectorName} 섹터 평균 배수 대비 비교"


def _buildRiskAnalysis(
    insights: object,
    insightDetails: list[InsightDetail],
) -> RiskSection | None:
    """distress + anomalies + insight.risk → RiskSection."""
    if insights is None:
        return None

    distressSection = None
    anomalySection = None
    insightRisk = None

    # distress
    distress = getattr(insights, "distress", None)
    if distress is not None:
        axes = []
        for ax in getattr(distress, "axes", []):
            axes.append(
                {
                    "name": getattr(ax, "name", ""),
                    "score": getattr(ax, "score", 0),
                    "weight": getattr(ax, "weight", 0),
                }
            )
        distressSection = DistressSection(
            level=getattr(distress, "level", ""),
            overall=getattr(distress, "overall", 0),
            creditGrade=getattr(distress, "creditGrade", ""),
            creditDescription=getattr(distress, "creditDescription", ""),
            riskFactors=getattr(distress, "riskFactors", []),
            cashRunwayMonths=getattr(distress, "cashRunwayMonths", None),
            axesSummary=axes,
        )

    # anomalies
    anomalies = getattr(insights, "anomalies", None)
    if anomalies:
        items = []
        critCount = 0
        warnCount = 0
        for a in anomalies:
            sev = getattr(a, "severity", "")
            items.append(
                {
                    "severity": sev,
                    "category": getattr(a, "category", ""),
                    "text": getattr(a, "text", ""),
                    "value": getattr(a, "value", None),
                }
            )
            if sev in ("critical", "danger"):
                critCount += 1
            elif sev == "warning":
                warnCount += 1
        anomalySection = AnomalySection(items=items, criticalCount=critCount, warningCount=warnCount)

    # insight.risk
    for d in insightDetails:
        if d.area == "risk":
            insightRisk = d
            break

    # narrative
    narrative = _buildRiskNarrative(distressSection, anomalySection)

    hasData = distressSection is not None or anomalySection is not None
    if not hasData:
        return None

    return RiskSection(
        distress=distressSection,
        anomalies=anomalySection,
        insightRisk=insightRisk,
        riskNarrative=narrative,
    )


def _buildRiskNarrative(
    distress: DistressSection | None,
    anomalies: AnomalySection | None,
) -> str:
    """종합 리스크 서술."""
    parts = []
    if distress:
        if distress.level in ("safe", "watch"):
            parts.append(f"부실 위험 낮음 (신용 {distress.creditGrade})")
        elif distress.level == "warning":
            parts.append(f"부실 주의 필요 (신용 {distress.creditGrade})")
        else:
            parts.append(f"부실 위험 높음 (신용 {distress.creditGrade}, 종합 {distress.overall:.0f}/100)")

    if anomalies:
        total = anomalies.criticalCount + anomalies.warningCount
        if anomalies.criticalCount > 0:
            parts.append(f"심각 이상치 {anomalies.criticalCount}건 감지")
        elif total > 0:
            parts.append(f"이상치 {total}건 감지 (경고 수준)")
        else:
            parts.append("이상치 미감지")

    return " | ".join(parts)
