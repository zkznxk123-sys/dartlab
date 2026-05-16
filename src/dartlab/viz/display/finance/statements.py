"""IS / BS / CF 가공.

각 함수는 norm + nPeriods + periodKind 받아 dict 반환 — *raw 가공 결과*.
views.py 가 이걸 받아 표준 View JSON 으로 포장.
"""

from __future__ import annotations

import polars as pl

from dartlab.viz.display.finance.accounts import extractSeries
from dartlab.viz.display.finance.periods import lastNPeriods
from dartlab.viz.display.finance.schema import PeriodKind


def _safeDiv(a: float | None, b: float | None) -> float | None:
    """a / b 안전. b 가 0/None 이면 None."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _gp(rev: float | None, cos: float | None, gp: float | None) -> float | None:
    """매출총이익 — 직접 없으면 (매출 - 매출원가)."""
    if gp is not None:
        return gp
    if rev is not None and cos is not None:
        return rev - cos
    return None


# ═══════════════════════════════════════════════════════════
# IS 4
# ═══════════════════════════════════════════════════════════


def isOverview(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """매출/매출총이익/영업이익/순이익 + 마진 3종 (GPM/OPM/NPM).

    Returns:
        {periods, rows: [{key, label, values, unit}]}
    """
    periods = lastNPeriods(norm, nPeriods, periodKind)
    rev = extractSeries(norm, "revenue", periods)
    cos = extractSeries(norm, "costOfSales", periods)
    gp = extractSeries(norm, "grossProfit", periods)
    op = extractSeries(norm, "operatingIncome", periods)
    ni = extractSeries(norm, "netIncome", periods)

    gpVals = [_gp(rev[i], cos[i], gp[i]) for i in range(len(periods))]
    gpm = [(_safeDiv(gpVals[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]
    opm = [(_safeDiv(op[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]
    npm = [(_safeDiv(ni[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]

    return {
        "periods": periods,
        "rows": [
            {"key": "revenue", "label": "매출액", "values": rev, "unit": "원"},
            {"key": "costOfSales", "label": "매출원가", "values": cos, "unit": "원"},
            {"key": "grossProfit", "label": "매출총이익", "values": gpVals, "unit": "원"},
            {"key": "operatingIncome", "label": "영업이익", "values": op, "unit": "원"},
            {"key": "netIncome", "label": "당기순이익", "values": ni, "unit": "원"},
            {"key": "grossMargin", "label": "매출총이익률", "values": gpm, "unit": "%"},
            {"key": "operatingMargin", "label": "영업이익률", "values": opm, "unit": "%"},
            {"key": "netMargin", "label": "순이익률", "values": npm, "unit": "%"},
        ],
    }


def isRevenueTrend(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """매출 추세 + YoY 성장률."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    rev = extractSeries(norm, "revenue", periods)
    yoy: list[float | None] = [None]
    for i in range(1, len(rev)):
        prev, curr = rev[i - 1], rev[i]
        if prev is None or curr is None or prev <= 0:
            yoy.append(None)
        else:
            yoy.append((curr - prev) / prev * 100)
    return {"periods": periods, "revenue": rev, "yoy": yoy}


def isMarginTrend(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """이익률 추세 — GPM/OPM/NPM."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    rev = extractSeries(norm, "revenue", periods)
    gp = extractSeries(norm, "grossProfit", periods)
    cos = extractSeries(norm, "costOfSales", periods)
    op = extractSeries(norm, "operatingIncome", periods)
    ni = extractSeries(norm, "netIncome", periods)
    gpVals = [_gp(rev[i], cos[i], gp[i]) for i in range(len(periods))]
    gpm = [(_safeDiv(gpVals[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]
    opm = [(_safeDiv(op[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]
    npm = [(_safeDiv(ni[i], rev[i]) or 0) * 100 if rev[i] else None for i in range(len(periods))]
    return {"periods": periods, "gpm": gpm, "opm": opm, "npm": npm}


def isCostStructure(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """비용 구조 — 매출원가/판관비/연구개발/금융비용."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    return {
        "periods": periods,
        "costOfSales": extractSeries(norm, "costOfSales", periods),
        "sga": extractSeries(norm, "sga", periods),
        "rnd": extractSeries(norm, "rnd", periods),
        "financeCosts": extractSeries(norm, "financeCosts", periods),
    }


# ═══════════════════════════════════════════════════════════
# BS 3
# ═══════════════════════════════════════════════════════════


def bsOverview(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """자산/부채/자본 총계 + 유동/비유동 + 현금."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    from dartlab.viz.display.finance.accounts import standard

    keys = (
        "assets",
        "currentAssets",
        "nonCurrentAssets",
        "liabilities",
        "currentLiabilities",
        "nonCurrentLiabilities",
        "equity",
        "cash",
    )
    rows = []
    for k in keys:
        rows.append(
            {
                "key": k,
                "label": standard(k).label,
                "values": extractSeries(norm, k, periods),
                "unit": "원",
            }
        )
    return {"periods": periods, "rows": rows}


def bsComposition(norm: pl.DataFrame, period: str | None, periodKind: PeriodKind) -> dict:
    """자산 / (부채+자본) 구성 — 단일 기간.

    Returns:
        {period, assets: [{key, label, value}], liabilitiesEquity: [{key, label, value}]}
    """
    if period is None:
        ps = lastNPeriods(norm, 1, periodKind)
        period = ps[-1] if ps else None
    if period is None:
        return {"period": None, "assets": [], "liabilitiesEquity": []}

    def _val(key: str) -> float | None:
        return extractSeries(norm, key, [period])[0]

    cur, nonCur = _val("currentAssets"), _val("nonCurrentAssets")
    cash, inv, rec = _val("cash"), _val("inventories"), _val("receivables")
    curLiab, nonCurLiab = _val("currentLiabilities"), _val("nonCurrentLiabilities")
    equity, shortD, longD = _val("equity"), _val("shortDebt"), _val("longDebt")
    retained = _val("retainedEarnings")

    assets: list[dict] = []
    if cash is not None:
        assets.append({"key": "cash", "label": "현금성자산", "value": cash})
    if rec is not None:
        assets.append({"key": "receivables", "label": "매출채권", "value": rec})
    if inv is not None:
        assets.append({"key": "inventories", "label": "재고자산", "value": inv})
    otherCur = (cur or 0) - sum(v for v in (cash, rec, inv) if v is not None)
    if cur is not None and otherCur > 0:
        assets.append({"key": "otherCurrentAssets", "label": "기타유동자산", "value": otherCur})
    if nonCur is not None:
        assets.append({"key": "nonCurrentAssets", "label": "비유동자산", "value": nonCur})

    liabEq: list[dict] = []
    if shortD is not None:
        liabEq.append({"key": "shortDebt", "label": "단기차입금", "value": shortD})
    otherCurL = (curLiab or 0) - (shortD or 0)
    if curLiab is not None and otherCurL > 0:
        liabEq.append({"key": "otherCurrentLiabilities", "label": "기타유동부채", "value": otherCurL})
    if longD is not None:
        liabEq.append({"key": "longDebt", "label": "장기차입금", "value": longD})
    otherNonCurL = (nonCurLiab or 0) - (longD or 0)
    if nonCurLiab is not None and otherNonCurL > 0:
        liabEq.append({"key": "otherNonCurrentLiabilities", "label": "기타비유동부채", "value": otherNonCurL})
    if retained is not None:
        liabEq.append({"key": "retainedEarnings", "label": "이익잉여금", "value": retained})
    otherEq = (equity or 0) - (retained or 0)
    if equity is not None and otherEq > 0:
        liabEq.append({"key": "otherEquity", "label": "기타자본", "value": otherEq})

    return {"period": period, "assets": assets, "liabilitiesEquity": liabEq}


def bsLeverage(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """레버리지 — D/E · D/A · 유동비."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    assets = extractSeries(norm, "assets", periods)
    liab = extractSeries(norm, "liabilities", periods)
    eq = extractSeries(norm, "equity", periods)
    curA = extractSeries(norm, "currentAssets", periods)
    curL = extractSeries(norm, "currentLiabilities", periods)
    debtToEquity = [(_safeDiv(liab[i], eq[i]) or 0) * 100 if liab[i] and eq[i] else None for i in range(len(periods))]
    debtToAssets = [
        (_safeDiv(liab[i], assets[i]) or 0) * 100 if liab[i] and assets[i] else None for i in range(len(periods))
    ]
    currentRatio = [
        (_safeDiv(curA[i], curL[i]) or 0) * 100 if curA[i] and curL[i] else None for i in range(len(periods))
    ]
    return {
        "periods": periods,
        "debtToEquity": debtToEquity,
        "debtToAssets": debtToAssets,
        "currentRatio": currentRatio,
    }


# ═══════════════════════════════════════════════════════════
# CF 3
# ═══════════════════════════════════════════════════════════


def cfOverview(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """영업/투자/재무 + 순현금변동 + FCF."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    op = extractSeries(norm, "cfOperating", periods)
    inv = extractSeries(norm, "cfInvesting", periods)
    fin = extractSeries(norm, "cfFinancing", periods)
    capex = extractSeries(norm, "capex", periods)
    netChange = [
        (op[i] or 0) + (inv[i] or 0) + (fin[i] or 0) if any(v is not None for v in (op[i], inv[i], fin[i])) else None
        for i in range(len(periods))
    ]
    fcf = [(op[i] or 0) - abs(capex[i] or 0) if op[i] is not None else None for i in range(len(periods))]
    return {
        "periods": periods,
        "rows": [
            {"key": "cfOperating", "label": "영업활동", "values": op, "unit": "원"},
            {"key": "cfInvesting", "label": "투자활동", "values": inv, "unit": "원"},
            {"key": "cfFinancing", "label": "재무활동", "values": fin, "unit": "원"},
            {"key": "netChange", "label": "순현금증감", "values": netChange, "unit": "원"},
            {"key": "fcf", "label": "잉여현금흐름", "values": fcf, "unit": "원"},
        ],
    }


def cfWaterfall(norm: pl.DataFrame, period: str | None, periodKind: PeriodKind) -> dict:
    """현금 waterfall — 기초/영업/투자/재무/기말.

    Returns:
        {period, steps: [{key, label, value, measure}]}
        measure: absolute | relative | total
    """
    if period is None:
        ps = lastNPeriods(norm, 1, periodKind)
        period = ps[-1] if ps else None
    if period is None:
        return {"period": None, "steps": []}

    op = extractSeries(norm, "cfOperating", [period])[0]
    inv = extractSeries(norm, "cfInvesting", [period])[0]
    fin = extractSeries(norm, "cfFinancing", [period])[0]
    cash = extractSeries(norm, "cash", [period])[0]

    startCash = (cash or 0) - ((op or 0) + (inv or 0) + (fin or 0))
    return {
        "period": period,
        "steps": [
            {"key": "startCash", "label": "기초현금", "value": startCash, "measure": "absolute"},
            {"key": "cfOperating", "label": "영업활동", "value": op, "measure": "relative"},
            {"key": "cfInvesting", "label": "투자활동", "value": inv, "measure": "relative"},
            {"key": "cfFinancing", "label": "재무활동", "value": fin, "measure": "relative"},
            {"key": "endCash", "label": "기말현금", "value": cash, "measure": "total"},
        ],
    }


def cfFreeCashFlow(norm: pl.DataFrame, nPeriods: int, periodKind: PeriodKind) -> dict:
    """FCF = 영업CF - CapEx + 영업CF/매출."""
    periods = lastNPeriods(norm, nPeriods, periodKind)
    op = extractSeries(norm, "cfOperating", periods)
    capex = extractSeries(norm, "capex", periods)
    rev = extractSeries(norm, "revenue", periods)
    fcf = [(op[i] or 0) - abs(capex[i] or 0) if op[i] is not None else None for i in range(len(periods))]
    cfToRev = [
        (op[i] / rev[i] * 100) if op[i] is not None and rev[i] not in (None, 0) else None for i in range(len(periods))
    ]
    return {
        "periods": periods,
        "operating": op,
        "capex": [abs(v) if v is not None else None for v in capex],
        "fcf": fcf,
        "cfToRevenue": cfToRev,
    }
