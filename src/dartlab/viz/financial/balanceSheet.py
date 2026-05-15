"""BS (재무상태표) 가공 — overview / composition / leverage."""

from __future__ import annotations

import polars as pl

from dartlab.viz.financial.accounts import extractSeries
from dartlab.viz.financial.periods import lastNPeriods


def _safe(a: float | None, b: float | None) -> float | None:
    """안전 나눗셈."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def overview(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """자산/부채/자본 총계 + 유동/비유동 + 현금."""
    periods = lastNPeriods(norm, nPeriods, mode)
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
    out: dict = {"periods": periods, "rows": []}
    from dartlab.viz.financial.accounts import standard

    for k in keys:
        s = extractSeries(norm, k, periods)
        out["rows"].append({"key": k, "label": standard(k).label, "values": [s[p] for p in periods], "unit": "원"})
    return out


def composition(norm: pl.DataFrame, period: str | None = None, mode: str = "annual") -> dict:
    """자산 / (부채+자본) 구성 비율 — 최근 1 기.

    Returns:
        {period, assetsBreakdown: [{label, value}],
                 liabEquityBreakdown: [{label, value}]}
    """
    if period is None:
        ps = lastNPeriods(norm, 1, mode)
        period = ps[-1] if ps else None
    if period is None:
        return {"period": None, "assetsBreakdown": [], "liabEquityBreakdown": []}

    pp = [period]
    cur = extractSeries(norm, "currentAssets", pp)[period]
    nonCur = extractSeries(norm, "nonCurrentAssets", pp)[period]
    cash = extractSeries(norm, "cash", pp)[period]
    inv = extractSeries(norm, "inventories", pp)[period]
    rec = extractSeries(norm, "receivables", pp)[period]
    curLiab = extractSeries(norm, "currentLiabilities", pp)[period]
    nonCurLiab = extractSeries(norm, "nonCurrentLiabilities", pp)[period]
    equity = extractSeries(norm, "equity", pp)[period]
    shortD = extractSeries(norm, "shortDebt", pp)[period]
    longD = extractSeries(norm, "longDebt", pp)[period]
    retained = extractSeries(norm, "retainedEarnings", pp)[period]

    assetsBreakdown = []
    if cash is not None:
        assetsBreakdown.append({"label": "현금성자산", "value": cash})
    if rec is not None:
        assetsBreakdown.append({"label": "매출채권", "value": rec})
    if inv is not None:
        assetsBreakdown.append({"label": "재고자산", "value": inv})
    otherCur = (cur or 0) - sum(v for v in (cash, rec, inv) if v is not None)
    if cur is not None and otherCur > 0:
        assetsBreakdown.append({"label": "기타유동자산", "value": otherCur})
    if nonCur is not None:
        assetsBreakdown.append({"label": "비유동자산", "value": nonCur})

    liabEqBreakdown = []
    if shortD is not None:
        liabEqBreakdown.append({"label": "단기차입금", "value": shortD})
    otherCurLiab = (curLiab or 0) - (shortD or 0)
    if curLiab is not None and otherCurLiab > 0:
        liabEqBreakdown.append({"label": "기타유동부채", "value": otherCurLiab})
    if longD is not None:
        liabEqBreakdown.append({"label": "장기차입금", "value": longD})
    otherNonCurLiab = (nonCurLiab or 0) - (longD or 0)
    if nonCurLiab is not None and otherNonCurLiab > 0:
        liabEqBreakdown.append({"label": "기타비유동부채", "value": otherNonCurLiab})
    if retained is not None:
        liabEqBreakdown.append({"label": "이익잉여금", "value": retained})
    otherEq = (equity or 0) - (retained or 0)
    if equity is not None and otherEq > 0:
        liabEqBreakdown.append({"label": "기타자본", "value": otherEq})

    return {"period": period, "assetsBreakdown": assetsBreakdown, "liabEquityBreakdown": liabEqBreakdown}


def leverage(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """레버리지 비율 — D/E, D/A, 유동비, 부채비."""
    periods = lastNPeriods(norm, nPeriods, mode)
    assets = extractSeries(norm, "assets", periods)
    liab = extractSeries(norm, "liabilities", periods)
    eq = extractSeries(norm, "equity", periods)
    curA = extractSeries(norm, "currentAssets", periods)
    curL = extractSeries(norm, "currentLiabilities", periods)
    debtToEquity = [(_safe(liab[p], eq[p]) or 0) * 100 if liab[p] and eq[p] else None for p in periods]
    debtToAssets = [(_safe(liab[p], assets[p]) or 0) * 100 if liab[p] and assets[p] else None for p in periods]
    currentRatio = [(_safe(curA[p], curL[p]) or 0) * 100 if curA[p] and curL[p] else None for p in periods]
    debtRatio = [(_safe(liab[p], eq[p]) or 0) * 100 if liab[p] and eq[p] else None for p in periods]
    return {
        "periods": periods,
        "debtToEquity": debtToEquity,
        "debtToAssets": debtToAssets,
        "currentRatio": currentRatio,
        "debtRatio": debtRatio,
        "unit": "%",
    }
