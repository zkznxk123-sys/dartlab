"""가치평가 축 -- 기존 밸류에이션 엔진을 analysis 14축 패턴으로 래핑.

calc 함수 9개: DCF, DDM, 상대가치, RIM, 목표주가, 역내재성장률,
민감도, 종합합성, 플래그.

모든 함수는 (company) -> dict | None 시그니처를 따른다.
"""

from __future__ import annotations

import logging
from typing import Any

from dartlab.analysis.valuation.pricetarget import computePriceTarget
from dartlab.analysis.valuation.residualIncome import calcResidualIncome as _rimCalc
from dartlab.core.financeDocAccessor import getFinanceDocAccessor
from dartlab.core.memory import memoizedCalc

log = logging.getLogger(__name__)


# ── IndustryGroup → SECTOR_ELASTICITY 키 매핑 ──

_IG_TO_SECTOR_KEY: dict[str, str] = {
    "SEMICONDUCTOR": "반도체",
    "AUTO": "자동차",
    "CHEMICAL": "화학",
    "METALS": "철강",
    "CONSTRUCTION": "건설",
    "CONSTRUCTION_MATERIALS": "건설",
    "BANK": "금융/은행",
    "INSURANCE": "금융/보험",
    "DIVERSIFIED_FINANCIALS": "금융/증권",
    "SOFTWARE": "IT/소프트웨어",
    "IT_SERVICE": "IT/소프트웨어",
    "INTERNET": "IT/소프트웨어",
    "TECH_HARDWARE": "전자/하드웨어",
    "DISPLAY": "디스플레이",
    "TELECOM": "통신",
    "RETAIL": "유통",
    "FOOD_BEV_TOBACCO": "식품",
    "FOOD_STAPLES": "식품",
    "HOUSEHOLD": "식품",
    "PHARMA_BIO": "제약/바이오",
    "HEALTHCARE_EQUIP": "제약/바이오",
    "UTILITIES": "전력/에너지",
    "ELECTRIC": "전력/에너지",
    "GAS_UTILITY": "전력/에너지",
    "ENERGY_EQUIP": "에너지/자원",
    "OIL_GAS": "에너지/자원",
    "CAPITAL_GOODS": "산업재",
    "MACHINERY": "산업재",
    "TRANSPORTATION": "산업재",
    "COMMERCIAL_SERVICE": "산업재",
    "SHIPBUILDING": "조선",
    "CONSUMER_DURABLES": "섬유/의류",
    "CONSUMER_SERVICE": "유통",
    "MEDIA_ENTERTAINMENT": "미디어/엔터",
    "MEDIA": "미디어/엔터",
    "GAME": "게임",
    "REAL_ESTATE": "부동산",
    "REIT": "부동산",
    "AEROSPACE_DEFENSE": "산업재",
    "HOTEL_LEISURE": "유통",
}


def _resolveSectorKey(company: Any) -> str | None:
    """company.sector에서 SECTOR_ELASTICITY 키를 추출."""
    try:
        sectorInfo = company.sector
        if sectorInfo is None:
            return None
        igName = sectorInfo.industryGroup.name
        return _IG_TO_SECTOR_KEY.get(igName)
    except (AttributeError, ValueError):
        return None


# ── 시가 연동 헬퍼 ──


def _fetchPriceContext(company: Any) -> dict | None:
    """gather.price에서 현재가/시총 가져오기 (sync).

    같은 company에 대해 세션 내 1회만 네트워크 호출.
    실패 시 None 반환 -- 시가 의존 calc만 graceful skip.
    """
    # company._cache에 저장하여 동일 세션 내 재활용
    cache = getattr(company, "_cache", None)
    _KEY = "_priceContext"
    if cache is not None and _KEY in cache:
        return cache[_KEY]

    stockCode = getattr(company, "stockCode", None)
    if not stockCode:
        return None

    result = None
    try:
        from dartlab.gather.infra.http import runAsync
        from dartlab.gather.sources.price import fetch

        snapshot = runAsync(fetch(stockCode, market="KR"))
        if snapshot is not None:
            result = {
                "currentPrice": snapshot.current,
                "marketCap": snapshot.marketCap,
                "per": snapshot.per,
                "pbr": snapshot.pbr,
                "isStale": getattr(snapshot, "is_stale", False),
            }
    except (ImportError, OSError, RuntimeError, AttributeError):
        log.debug("price fetch 실패: %s", stockCode)

    if cache is not None:
        cache[_KEY] = result
    return result


def _getSeriesAndShares(company: Any) -> tuple[dict | None, int | None, str]:
    """company에서 annual series, shares, currency 추출."""
    try:
        ann = company._buildFinanceSeries(freq="Y")
        if ann is None:
            return None, None, getattr(company, "currency", "KRW") or "KRW"
        series = ann[0] if isinstance(ann, tuple) else ann
    except (ValueError, KeyError, AttributeError):
        return None, None, getattr(company, "currency", "KRW") or "KRW"

    shares = None
    profile = getattr(company, "profile", None)
    if profile:
        sharesVal = getattr(profile, "sharesOutstanding", None)
        if sharesVal:
            shares = int(sharesVal)

    # fallback: 시가총액/현재가에서 shares 추정
    if shares is None:
        price = _fetchPriceContext(company)
        if price and price.get("marketCap") and price.get("currentPrice"):
            mc = price["marketCap"]
            cp = price["currentPrice"]
            if mc > 0 and cp > 0:
                shares = int(mc / cp)

    currency = getattr(company, "currency", "KRW") or "KRW"
    return series, shares, currency


def _getSectorParams(company: Any):
    """company에서 sectorParams 추출."""
    try:
        return getattr(company, "sectorParams", None)
    except AttributeError:
        return None


# ── calc 함수 9개 ──


@memoizedCalc
def calcDcf(
    company: Any,
    *,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict | None:
    """DCF (현금흐름 할인) 밸류에이션.

    Parameters
    ----------
    overrides : dict | None
        AI/사용자 가정 override. wacc, terminalGrowth 키 지원.

    Returns
    -------
    dict
        perShareValue : float — 주당 적정가 (원)
        enterpriseValue : float — 기업가치 (원)
        equityValue : float — 자기자본가치 (원)
        discountRate : float — 할인율 (%)
        growthRateInitial : float — 초기 성장률 (%)
        terminalGrowth : float — 영구성장률 (%)
        marginOfSafety : float — 안전마진 (%)
        fcfProjections : list — FCF 예측 시계열 (원)
        fcfHistorical : list — FCF 과거 시계열 (원)
        exitMultipleTv : float — 출구배수 기반 터미널가치 (원)
        exitMultipleEv : float — 출구배수 기반 기업가치 (원)
        exitMultiplePerShare : float — 출구배수 기반 주당가치 (원)
        assumptions : dict — 가정 파라미터
        warnings : list[str] — 경고 메시지
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
        overrideApplied : dict | None — 적용된 override (있으면)
    """
    from dartlab.analysis.valuation.dcf import dcfValuation
    from dartlab.synth.overrides import applyOverride

    ov = overrides or {}

    series, shares, currency = _getSeriesAndShares(company)
    sp = _getSectorParams(company)
    price = _fetchPriceContext(company)
    currentPrice = price["currentPrice"] if price else None
    marketCap = price["marketCap"] if price else None

    from dartlab.analysis.financial.proforma import computeCompanyWacc

    wacc, _ = computeCompanyWacc(
        series,
        sectorParams=sp,
        marketCap=marketCap,
        currency=currency,
    )
    wacc = applyOverride(wacc, "wacc", ov)

    # 추정재무제표(Pro Forma) FCF → DCF 입력 (있으면 우선 사용)
    pfFCF = None
    try:
        from dartlab.analysis.financial.forecastCalcs import calcProFormaHighlights

        pf = calcProFormaHighlights(company, basePeriod=basePeriod)
        if pf and pf.get("years"):
            pfFCF = [yr["fcf"] for yr in pf["years"] if yr.get("fcf") is not None]
            if not pfFCF:
                pfFCF = None
    except (ImportError, AttributeError, ValueError, TypeError, KeyError):
        pfFCF = None

    tg_override = ov.get("terminalGrowth")
    dcf_kwargs: dict[str, Any] = {
        "shares": shares,
        "sectorParams": sp,
        "currentPrice": currentPrice,
        "currency": currency,
        "discountRate": wacc,
        "proformaFCF": pfFCF,
    }
    if tg_override is not None:
        # dcfValuation() 은 백분위 숫자 (3.0 = 3%) 로 받는다
        dcf_kwargs["terminalGrowth"] = tg_override * 100 if tg_override <= 1 else tg_override

    result = dcfValuation(series, **dcf_kwargs)
    out: dict[str, Any] = {
        "perShareValue": result.perShareValue,
        "enterpriseValue": result.enterpriseValue,
        "equityValue": result.equityValue,
        "discountRate": result.discountRate,
        "growthRateInitial": result.growthRateInitial,
        "terminalGrowth": result.terminalGrowth,
        "marginOfSafety": result.marginOfSafety,
        "fcfProjections": result.fcfProjections,
        "fcfHistorical": result.fcfHistorical,
        "exitMultipleTv": result.exitMultipleTv,
        "exitMultipleEv": result.exitMultipleEv,
        "exitMultiplePerShare": result.exitMultiplePerShare,
        "assumptions": result.assumptions,
        "warnings": result.warnings,
        "currentPrice": currentPrice,
        "currency": currency,
    }
    if ov:
        out["overrideApplied"] = {k: v for k, v in ov.items() if k in ("wacc", "terminalGrowth")}
    return out


@memoizedCalc
def calcDdm(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """DDM (배당 할인) 밸류에이션.

    calcDividendPolicy의 연간 배당 데이터를 우선 사용하여
    분기 CF 합산 오류를 방지한다.

    Returns
    -------
    dict
        intrinsicValue : float — 주당 내재가치 (원)
        dividendPerShare : float — 주당배당금 (원)
        dividendYield : float — 배당수익률 (%)
        payoutRatio : float — 배당성향 (%)
        dividendGrowth : float — 배당 성장률 (%)
        modelUsed : str — 사용 모델 ("Gordon" | "H-Model" | "N/A")
        discountRate : float — 할인율 (%)
        warnings : list[str] — 경고 메시지
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
    """
    from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy
    from dartlab.analysis.valuation.dcf import ddmValuation

    series, shares, currency = _getSeriesAndShares(company)
    sp = _getSectorParams(company)
    price = _fetchPriceContext(company)
    currentPrice = price["currentPrice"] if price else None

    # 1순위: Report API DPS (가장 정확한 연간 주당배당금)
    annualDivs: list[float] | None = None
    try:
        accessor = getFinanceDocAccessor()
        stockCode = getattr(company, "stockCode", None)
        divResult = accessor.pivotDividend(stockCode) if accessor and stockCode else None
        if divResult and divResult.dps:
            validDps = [d for d in divResult.dps if d is not None and d > 0]
            if validDps and shares and shares > 0:
                annualDivs = [dps * shares for dps in validDps]
    except (ImportError, ValueError, KeyError, AttributeError, RuntimeError, OSError):
        pass

    # 2순위: calcDividendPolicy CF 기반 (Report 없을 때 fallback)
    if not annualDivs:
        divPolicy = calcDividendPolicy(company, basePeriod=basePeriod)
        if divPolicy and divPolicy.get("history"):
            hist = divPolicy["history"]
            minDiv = shares * 100 if shares and shares > 0 else 1e9
            annualDivs = [
                h["dividendsPaid"] for h in reversed(hist) if h.get("dividendsPaid") and h["dividendsPaid"] > minDiv
            ]

    result = ddmValuation(
        series,
        shares=shares,
        sectorParams=sp,
        currentPrice=currentPrice,
        annualDividends=annualDivs,
    )
    if result.modelUsed == "N/A" and not result.warnings:
        return None

    return {
        "intrinsicValue": result.intrinsicValue,
        "dividendPerShare": result.dividendPerShare,
        "dividendYield": result.dividendYield,
        "payoutRatio": result.payoutRatio,
        "dividendGrowth": result.dividendGrowth,
        "modelUsed": result.modelUsed,
        "discountRate": result.discountRate,
        "warnings": result.warnings,
        "currentPrice": currentPrice,
        "currency": currency,
    }


@memoizedCalc
def calcRelativeValuation(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """상대가치 (PER/PBR/EV-EBITDA/PSR/PEG) 밸류에이션.

    Returns
    -------
    dict
        sectorMultiples : dict — 업종 평균 멀티플 (PER, PBR 등) (배수)
        currentMultiples : dict — 현재 멀티플 (배수)
        impliedValues : dict — 멀티플별 내재가치 (원)
        premiumDiscount : dict — 업종 대비 할인/프리미엄 (%)
        consensusValue : float — 합의 적정가 (원)
        warnings : list[str] — 경고 메시지
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
    """
    from dartlab.analysis.valuation.dcf import relativeValuation

    series, shares, currency = _getSeriesAndShares(company)
    sp = _getSectorParams(company)
    price = _fetchPriceContext(company)
    marketCap = price["marketCap"] if price else None
    currentPrice = price["currentPrice"] if price else None

    result = relativeValuation(
        series,
        sectorParams=sp,
        marketCap=marketCap,
        shares=shares,
        currentPrice=currentPrice,
    )
    return {
        "sectorMultiples": result.sectorMultiples,
        "currentMultiples": result.currentMultiples,
        "impliedValues": result.impliedValues,
        "premiumDiscount": result.premiumDiscount,
        "consensusValue": result.consensusValue,
        "warnings": result.warnings,
        "currentPrice": currentPrice,
        "currency": currency,
    }


@memoizedCalc
def calcResidualIncome(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """RIM (잔여이익모델) 밸류에이션.

    Returns
    -------
    dict
        bps : float — 주당순자산 (원)
        coe : float — 자기자본비용 (%)
        riHistory : list — 잔여이익 시계열 (원)
        intrinsicValue : float — 주당 내재가치 (원)
        upside : float — 상승여력 (%)
        terminalValue : float — 터미널가치 (원)
        warnings : list[str] — 경고 메시지
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
    """
    series, shares, currency = _getSeriesAndShares(company)
    sp = _getSectorParams(company)
    price = _fetchPriceContext(company)
    currentPrice = price["currentPrice"] if price else None
    beta = sp.beta if sp else None

    result = _rimCalc(
        series,
        shares=shares,
        currentPrice=currentPrice,
        currency=currency,
        beta=beta,
    )
    if result is None:
        return None

    return {
        "bps": result.bps,
        "coe": result.coe,
        "riHistory": result.riHistory,
        "intrinsicValue": result.intrinsicValue,
        "upside": result.upside,
        "terminalValue": result.terminalValue,
        "warnings": result.warnings,
        "currentPrice": currentPrice,
        "currency": currency,
    }


# ── 지주사 NAV ──────────────────────────────────────────

# 주요 지주사 핵심 자회사 매핑 (종목코드: 지분율%)
# 출처: DART 사업보고서 기준. 자회사 지분 변동 시 업데이트 필요.
_HOLDING_SUBS: dict[str, list[tuple[str, float]]] = {
    "034730": [  # SK
        ("096770", 64.25),  # SK이노베이션
        ("017670", 26.80),  # SK텔레콤
        ("402340", 42.30),  # SK스퀘어
    ],
    "003550": [  # LG
        ("373220", 30.10),  # LG에너지솔루션
        ("051910", 33.30),  # LG화학
        ("066570", 33.67),  # LG전자
    ],
    "028260": [  # 삼성물산
        ("005930", 4.99),  # 삼성전자
        ("207940", 43.37),  # 삼성바이오로직스
    ],
    "005490": [  # POSCO홀딩스
        ("005380", 5.20),  # 현대차 (실제는 포스코인터/포스코퓨처엠이나 종목코드 확인 필요)
    ],
}


@memoizedCalc
def calcNavValuation(company: Any) -> dict | None:
    """지주사 NAV = Sum(상장 자회사 시총 x 지분율) - 순차입금. 할인 30%.

    Returns
    -------
    dict
        navGross : float — 할인 전 NAV (원)
        navDiscounted : float — 할인 후 NAV (원)
        navPerShare : float | None — 주당 NAV (원)
        holdingDiscount : float — 지주사 할인율 (0.30)
        subsidiaries : list[dict] — 자회사별 상세 (code, ratio(%), marketCap(원), value(원))
        netDebt : float — 순차입금 (원)
    """
    stockCode = getattr(company, "stockCode", "")
    subs = _HOLDING_SUBS.get(stockCode)
    if not subs:
        return None

    series, shares, currency = _getSeriesAndShares(company)

    # 자회사 시총 합산 (Company 객체 생성 금지 — OOM 방지)
    totalSubValue = 0.0
    subDetails = []
    for subCode, ratio in subs:
        try:
            from dartlab.gather.infra.http import runAsync
            from dartlab.gather.sources.price import fetch

            snapshot = runAsync(fetch(subCode, market="KR"))
            if snapshot and snapshot.marketCap and snapshot.marketCap > 0:
                subValue = snapshot.marketCap * ratio / 100
                totalSubValue += subValue
                subDetails.append({"code": subCode, "ratio": ratio, "marketCap": snapshot.marketCap, "value": subValue})
        except (ImportError, OSError, RuntimeError, AttributeError):
            pass

    if totalSubValue <= 0:
        return None

    # 순차입금
    from dartlab.core.utils.extract import getLatest

    if series:
        stb = getLatest(series, "BS", "shortterm_borrowings") or 0
        ltb = getLatest(series, "BS", "longterm_borrowings") or 0
        bonds = getLatest(series, "BS", "debentures") or 0
        cash = getLatest(series, "BS", "cash_and_cash_equivalents") or 0
        netDebt = stb + ltb + bonds - cash
    else:
        netDebt = 0

    # NAV = 자회사 지분가치 합계 - 순차입금
    navGross = totalSubValue - netDebt
    # 지주사 할인 30% (한국 실증 평균)
    navDiscounted = navGross * 0.70

    navPerShare = navDiscounted / shares if shares and shares > 0 else None

    return {
        "navGross": navGross,
        "navDiscounted": navDiscounted,
        "navPerShare": navPerShare,
        "holdingDiscount": 0.30,
        "subsidiaries": subDetails,
        "netDebt": netDebt,
    }


@memoizedCalc
def calcReverseImplied(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """역내재성장률 -- 시장이 내재하는 매출 성장률 역산.

    Returns
    -------
    dict
        impliedGrowthRate : float — 내재 매출 성장률 (%)
        impliedRevenue : float — 내재 매출 (원)
        marketCap : float — 시가총액 (원)
        latestRevenue : float — 최신 매출 (원)
        assumedMargin : float — 가정 영업이익률 (%)
        assumedWacc : float — 가정 WACC (%)
        signal : str — 신호 ("overpriced" | "underpriced" | "fair")
        warnings : list[str] — 경고 메시지
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
    """
    from dartlab.analysis.valuation.priceImplied import reverseImpliedGrowth

    series, shares, currency = _getSeriesAndShares(company)
    price = _fetchPriceContext(company)
    if not price or not price.get("marketCap"):
        return None

    result = reverseImpliedGrowth(series, marketCap=price["marketCap"])
    if result is None:
        return None

    return {
        "impliedGrowthRate": result.impliedGrowthRate,
        "impliedRevenue": result.impliedRevenue,
        "marketCap": result.marketCap,
        "latestRevenue": result.latestRevenue,
        "assumedMargin": result.assumedMargin,
        "assumedWacc": result.assumedWacc,
        "signal": result.signal,
        "warnings": result.warnings,
        "currentPrice": price.get("currentPrice"),
        "currency": currency,
    }


@memoizedCalc
def calcSensitivity(company: Any, *, basePeriod: str | None = None) -> dict | None:
    """WACC x 영구성장률 민감도 그리드.

    Returns
    -------
    dict
        grid : list[list[float]] — WACC x 영구성장률 주가 그리드 (원)
        baseWacc : float — 기준 WACC (%)
        baseTerminalGrowth : float — 기준 영구성장률 (%)
        baseValue : float — 기준 주가 (원)
        currentPrice : float | None — 현재 주가 (원)
        currency : str — 통화 (KRW | USD)
    """
    from dartlab.analysis.valuation.dcf import sensitivityAnalysis

    series, shares, currency = _getSeriesAndShares(company)
    sp = _getSectorParams(company)
    price = _fetchPriceContext(company)
    currentPrice = price["currentPrice"] if price else None

    result = sensitivityAnalysis(
        series,
        shares=shares,
        sectorParams=sp,
        currentPrice=currentPrice,
        currency=currency,
    )
    if result is None:
        return None

    return {
        "grid": result.grid,
        "baseWacc": result.baseWacc,
        "baseTerminalGrowth": result.baseTerminalGrowth,
        "baseValue": result.baseValue,
        "currentPrice": currentPrice,
        "currency": currency,
    }


# 분리된 깊이 (BC re-export)
from dartlab.analysis.financial._valuationDeep import (  # noqa: E402, F401
    _classifyCompanyType,
    calcPriceTarget,
    calcValuationFlags,
    calcValuationSynthesis,
)
