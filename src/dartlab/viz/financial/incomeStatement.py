"""IS (손익계산서) 가공 — overview / revenueTrend / marginTrend / costStructure."""

from __future__ import annotations

import polars as pl

from dartlab.viz.financial.accounts import extractSeries
from dartlab.viz.financial.periods import lastNPeriods


def _safe(a: float | None, b: float | None) -> float | None:
    """a / b 안전 나눗셈. b == 0 또는 None 이면 None."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _yoy(curr: float | None, prev: float | None) -> float | None:
    """전기 대비 성장률 % — prev == 0 또는 음수면 None."""
    if curr is None or prev is None or prev <= 0:
        return None
    return (curr - prev) / prev * 100.0


def overview(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """IS 총괄 — 매출/매출총이익/영업이익/순이익 + 비율 + YoY.

    Returns:
        {periods, rows: [{key, label, values, unit}], series}
    """
    periods = lastNPeriods(norm, nPeriods, mode)
    keys = ("revenue", "costOfSales", "grossProfit", "operatingIncome", "netIncome")
    seriesByKey = {k: extractSeries(norm, k, periods) for k in keys}

    rows = []
    for k in keys:
        from dartlab.viz.financial.accounts import standard

        sa = standard(k)
        rows.append(
            {
                "key": k,
                "label": sa.label,
                "values": [seriesByKey[k][p] for p in periods],
                "unit": "원",
            }
        )

    def _gm(p: str) -> float | None:
        """매출총이익률 — gp 또는 (rev - cos) / rev. 둘 다 없으면 None."""
        gp = seriesByKey["grossProfit"][p]
        rev = seriesByKey["revenue"][p]
        cos = seriesByKey["costOfSales"][p]
        if rev is None or rev == 0:
            return None
        if gp is not None:
            return gp / rev
        if cos is not None:
            return (rev - cos) / rev
        return None

    rows.append(
        {
            "key": "grossMargin",
            "label": "매출총이익률(%)",
            "values": [(_gm(p) * 100) if _gm(p) is not None else None for p in periods],
            "unit": "%",
        }
    )
    rows.append(
        {
            "key": "operatingMargin",
            "label": "영업이익률(%)",
            "values": [
                (_safe(seriesByKey["operatingIncome"][p], seriesByKey["revenue"][p]) or 0) * 100
                if seriesByKey["revenue"][p] is not None
                else None
                for p in periods
            ],
            "unit": "%",
        }
    )
    rows.append(
        {
            "key": "netMargin",
            "label": "순이익률(%)",
            "values": [
                (_safe(seriesByKey["netIncome"][p], seriesByKey["revenue"][p]) or 0) * 100
                if seriesByKey["revenue"][p] is not None
                else None
                for p in periods
            ],
            "unit": "%",
        }
    )
    return {"periods": periods, "rows": rows}


def revenueTrend(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """매출액 추세 + YoY 성장률 overlay."""
    periods = lastNPeriods(norm, nPeriods, mode)
    rev = extractSeries(norm, "revenue", periods)
    values = [rev[p] for p in periods]
    yoy = [None] + [_yoy(values[i], values[i - 1]) for i in range(1, len(values))]
    return {
        "periods": periods,
        "revenue": values,
        "yoy": yoy,
        "unit": "원",
    }


def marginTrend(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """이익률 추세 — GPM/OPM/NPM 3 시리즈."""
    periods = lastNPeriods(norm, nPeriods, mode)
    rev = extractSeries(norm, "revenue", periods)
    gp = extractSeries(norm, "grossProfit", periods)
    cos = extractSeries(norm, "costOfSales", periods)
    op = extractSeries(norm, "operatingIncome", periods)
    ni = extractSeries(norm, "netIncome", periods)

    def gpVal(p: str) -> float | None:
        """매출총이익 — 직접 항목이 없으면 매출 - 매출원가."""
        if gp[p] is not None:
            return gp[p]
        if rev[p] is not None and cos[p] is not None:
            return rev[p] - cos[p]
        return None

    gpm = [(_safe(gpVal(p), rev[p]) or 0) * 100 if rev[p] else None for p in periods]
    opm = [(_safe(op[p], rev[p]) or 0) * 100 if rev[p] else None for p in periods]
    npm = [(_safe(ni[p], rev[p]) or 0) * 100 if rev[p] else None for p in periods]
    return {"periods": periods, "gpm": gpm, "opm": opm, "npm": npm, "unit": "%"}


def costStructure(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """비용 구조 — 매출원가 + SGA + R&D + 금융비용 stacked."""
    periods = lastNPeriods(norm, nPeriods, mode)
    cos = extractSeries(norm, "costOfSales", periods)
    sga = extractSeries(norm, "sga", periods)
    rnd = extractSeries(norm, "rnd", periods)
    fin = extractSeries(norm, "financeCosts", periods)
    return {
        "periods": periods,
        "costOfSales": [cos[p] for p in periods],
        "sga": [sga[p] for p in periods],
        "rnd": [rnd[p] for p in periods],
        "financeCosts": [fin[p] for p in periods],
        "unit": "원",
    }
