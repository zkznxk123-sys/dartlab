"""상대가치 + 청산가치 + 민감도 분석 — dcf.py 에서 분리."""

from __future__ import annotations

from typing import Optional

from dartlab.analysis.valuation._dcfHelpers import (
    _epsGrowth3Y,
    _estimateSectorPsr,
    _getNetDebt,
    _normalizedEarnings,
)
from dartlab.analysis.valuation._dcfTypes import RelativeValuationResult, SensitivityResult
from dartlab.core.utils.extract import getLatest, getTTM
from dartlab.frame.sector import SectorParams

_LIQUIDATION_RECOVERY = {
    "cash": 1.00,
    "receivables": 0.70,
    "inventory": 0.50,
    "tangible": 0.60,
    "intangible": 0.10,
    "other": 0.40,
}


def liquidationValuation(
    *,
    cash: float = 0.0,
    receivables: float = 0.0,
    inventory: float = 0.0,
    tangibleAssets: float = 0.0,
    intangibleAssets: float = 0.0,
    otherAssets: float = 0.0,
    totalLiabilities: float = 0.0,
    shares: int | None = None,
    recoveryOverrides: dict | None = None,
) -> dict:
    """Damodaran 청산가치 — 자산별 회수율 차등.

    Returns
    -------
    dict
        recoveries : dict — 자산별 회수 금액
        grossRecovery : float — 총 자산 회수 합
        netToEquity : float — 부채 상환 후 잔여
        perShare : float | None
        weightedRecoveryRate : float — 가중 평균 회수율 (0.0~1.0)
    """
    recovery = dict(_LIQUIDATION_RECOVERY)
    if recoveryOverrides:
        recovery.update(recoveryOverrides)

    components = {
        "cash": cash * recovery["cash"],
        "receivables": receivables * recovery["receivables"],
        "inventory": inventory * recovery["inventory"],
        "tangible": tangibleAssets * recovery["tangible"],
        "intangible": intangibleAssets * recovery["intangible"],
        "other": otherAssets * recovery["other"],
    }
    gross = sum(components.values())
    net_to_equity = gross - totalLiabilities
    per_share = (net_to_equity / shares) if (shares and shares > 0 and net_to_equity > 0) else None

    gross_raw = cash + receivables + inventory + tangibleAssets + intangibleAssets + otherAssets
    weighted_rate = gross / gross_raw if gross_raw > 0 else 0.0

    return {
        "recoveries": components,
        "grossRecovery": gross,
        "netToEquity": net_to_equity,
        "perShare": per_share,
        "weightedRecoveryRate": weighted_rate,
        "recoveryRates": recovery,
    }


def relativeValuation(
    series: dict,
    sectorParams: Optional[SectorParams] = None,
    marketCap: Optional[float] = None,
    shares: Optional[int] = None,
    currentPrice: Optional[float] = None,
) -> RelativeValuationResult:
    """섹터 배수 기반 상대가치 추정 (Normalized Earnings 지원)."""
    warnings: list[str] = []
    sp = sectorParams or SectorParams(
        discountRate=10.0,
        growthRate=3.0,
        perMultiple=15,
        pbrMultiple=1.2,
        evEbitdaMultiple=8,
        label="기타",
    )

    sectorMults: dict[str, float] = {
        "PER": sp.perMultiple,
        "PBR": sp.pbrMultiple,
        "EV/EBITDA": sp.evEbitdaMultiple,
    }

    netIncome = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income")
    equity = getLatest(series, "BS", "total_stockholders_equity") or getLatest(series, "BS", "owners_of_parent_equity")
    revenue = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")

    normNi, normEps, useNormalized = _normalizedEarnings(series, shares)
    if useNormalized and normNi is not None:
        netIncome = normNi
        warnings.append("정규화 수익 적용 (과거 평균 ROE x 현재 BPS)")

    multKeys = ["PER", "PBR", "EV/EBITDA", "PSR", "PEG"]
    currentMults: dict[str, Optional[float]] = {k: None for k in multKeys}
    if marketCap and marketCap > 0:
        if netIncome and netIncome > 0:
            currentMults["PER"] = round(marketCap / netIncome, 1)
        if equity and equity > 0:
            currentMults["PBR"] = round(marketCap / equity, 1)
        if revenue and revenue > 0:
            currentMults["PSR"] = round(marketCap / revenue, 2)

    implied: dict[str, Optional[float]] = {k: None for k in multKeys}
    premiumDisc: dict[str, Optional[float]] = {k: None for k in multKeys}

    if shares and shares > 0:
        if netIncome is not None and netIncome > 0:
            eps = netIncome / shares
            implied["PER"] = round(eps * sp.perMultiple, 0)

        if equity is not None and equity > 0:
            bps = equity / shares
            implied["PBR"] = round(bps * sp.pbrMultiple, 0)

        oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
        dep = getTTM(series, "CF", "depreciation_and_amortization")
        if oi is not None and oi > 0:
            if dep is None:
                ta = getLatest(series, "BS", "tangible_assets") or 0
                ia = getLatest(series, "BS", "intangible_assets") or 0
                dep = ta * 0.05 + ia * 0.1
                warnings.append("감가상각 미확인 -> 추정치 적용")
            ebitda = oi + (dep or 0)
            if ebitda > 0:
                nd = _getNetDebt(series)
                impliedEv = ebitda * sp.evEbitdaMultiple
                impliedEq = impliedEv - nd
                if impliedEq > 0:
                    implied["EV/EBITDA"] = round(impliedEq / shares, 0)

        if revenue is not None and revenue > 0:
            sps = revenue / shares
            sectorPsr = _estimateSectorPsr(sp)
            sectorMults["PSR"] = sectorPsr
            implied["PSR"] = round(sps * sectorPsr, 0)

        epsGrowth = _epsGrowth3Y(series, shares)
        if epsGrowth is not None and epsGrowth > 0 and currentMults.get("PER"):
            peg = round(currentMults["PER"] / epsGrowth, 2)
            currentMults["PEG"] = peg
            eps = netIncome / shares if netIncome and netIncome > 0 else 0
            if eps > 0:
                implied["PEG"] = round(eps * epsGrowth, 0)
                sectorMults["PEG"] = 1.0

    if currentPrice and currentPrice > 0:
        for key in multKeys:
            iv = implied[key]
            if iv is not None and iv > 0:
                premiumDisc[key] = round((currentPrice - iv) / iv * 100, 1)

    multWeights = {"EV/EBITDA": 3.0, "PER": 2.5, "PBR": 1.5, "PSR": 1.0, "PEG": 1.0}
    _ivCap = currentPrice * 5 if currentPrice and currentPrice > 0 else float("inf")
    weightedSum = 0.0
    totalWeight = 0.0
    for key in multKeys:
        iv = implied[key]
        if iv is not None and 0 < iv < _ivCap:
            w = multWeights.get(key, 1.0)
            weightedSum += iv * w
            totalWeight += w
    consensus = round(weightedSum / totalWeight, 0) if totalWeight > 0 else None

    if totalWeight == 0:
        warnings.append("상대가치 추정 불가 (재무 데이터 부족)")

    return RelativeValuationResult(
        sectorMultiples=sectorMults,
        currentMultiples=currentMults,
        impliedValues=implied,
        premiumDiscount=premiumDisc,
        consensusValue=consensus,
        warnings=warnings,
    )


def sensitivityAnalysis(
    series: dict,
    shares: Optional[int] = None,
    sectorParams: Optional[SectorParams] = None,
    currentPrice: Optional[float] = None,
    currency: str = "KRW",
    waccRange: float = 2.0,
    growthRange: float = 2.0,
    steps: int = 5,
) -> SensitivityResult | None:
    """WACC x 영구성장률 민감도 그리드.

    DCF 결과를 WACC +-waccRange, 영구성장률 +-growthRange로 재계산.
    """
    from dartlab.analysis.valuation.dcf import dcfValuation

    baseDcf = dcfValuation(
        series,
        shares=shares,
        sectorParams=sectorParams,
        currentPrice=currentPrice,
        currency=currency,
    )
    baseWacc = baseDcf.discountRate
    baseTg = baseDcf.terminalGrowth

    grid: list[dict] = []
    waccStep = waccRange * 2 / (steps - 1) if steps > 1 else 0
    growthStep = growthRange * 2 / (steps - 1) if steps > 1 else 0

    for wi in range(steps):
        wacc = baseWacc - waccRange + wi * waccStep
        if wacc <= 0:
            continue
        for gi in range(steps):
            tg = baseTg - growthRange + gi * growthStep
            if tg >= wacc:
                continue
            result = dcfValuation(
                series,
                shares=shares,
                sectorParams=sectorParams,
                discountRate=wacc,
                terminalGrowth=tg,
                currentPrice=currentPrice,
                currency=currency,
            )
            grid.append(
                {
                    "wacc": round(wacc, 1),
                    "terminalGrowth": round(tg, 1),
                    "perShareValue": result.perShareValue,
                    "enterpriseValue": result.enterpriseValue,
                }
            )

    return SensitivityResult(
        grid=grid,
        baseWacc=baseWacc,
        baseTerminalGrowth=baseTg,
        baseValue=baseDcf.perShareValue,
    )
