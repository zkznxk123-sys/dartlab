"""CF (현금흐름표) 가공 — overview / waterfall / freeCashFlow."""

from __future__ import annotations

import polars as pl

from dartlab.viz.financial.accounts import extractSeries
from dartlab.viz.financial.periods import lastNPeriods


def overview(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """영업/투자/재무 + 순현금변동 + FCF."""
    periods = lastNPeriods(norm, nPeriods, mode)
    op = extractSeries(norm, "cfOperating", periods)
    inv = extractSeries(norm, "cfInvesting", periods)
    fin = extractSeries(norm, "cfFinancing", periods)
    capex = extractSeries(norm, "capex", periods)
    rows = [
        {"key": "cfOperating", "label": "영업활동", "values": [op[p] for p in periods], "unit": "원"},
        {"key": "cfInvesting", "label": "투자활동", "values": [inv[p] for p in periods], "unit": "원"},
        {"key": "cfFinancing", "label": "재무활동", "values": [fin[p] for p in periods], "unit": "원"},
        {
            "key": "netChange",
            "label": "순현금증감",
            "values": [
                (op[p] or 0) + (inv[p] or 0) + (fin[p] or 0)
                if any(v is not None for v in (op[p], inv[p], fin[p]))
                else None
                for p in periods
            ],
            "unit": "원",
        },
        {
            "key": "fcf",
            "label": "잉여현금흐름",
            "values": [(op[p] or 0) - abs(capex[p] or 0) if op[p] is not None else None for p in periods],
            "unit": "원",
        },
    ]
    return {"periods": periods, "rows": rows}


def waterfall(norm: pl.DataFrame, period: str | None = None, mode: str = "annual") -> dict:
    """현금 흐름 waterfall — 시작 현금 + 영업/투자/재무 + 종료 현금.

    Returns:
        {period, steps: [{label, value, measure}]}
        measure: relative | total
    """
    if period is None:
        ps = lastNPeriods(norm, 2, mode)
        period = ps[-1] if ps else None
    if period is None:
        return {"period": None, "steps": []}

    ps = [period]
    op = extractSeries(norm, "cfOperating", ps)[period]
    inv = extractSeries(norm, "cfInvesting", ps)[period]
    fin = extractSeries(norm, "cfFinancing", ps)[period]
    cash = extractSeries(norm, "cash", ps)[period]

    startCash = (cash or 0) - ((op or 0) + (inv or 0) + (fin or 0))
    steps = [
        {"label": "기초현금", "value": startCash, "measure": "absolute"},
        {"label": "영업활동", "value": op, "measure": "relative"},
        {"label": "투자활동", "value": inv, "measure": "relative"},
        {"label": "재무활동", "value": fin, "measure": "relative"},
        {"label": "기말현금", "value": cash, "measure": "total"},
    ]
    return {"period": period, "steps": steps}


def freeCashFlow(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """잉여현금흐름 = 영업CF - CapEx + 영업CF/매출 비율."""
    periods = lastNPeriods(norm, nPeriods, mode)
    op = extractSeries(norm, "cfOperating", periods)
    capex = extractSeries(norm, "capex", periods)
    rev = extractSeries(norm, "revenue", periods)
    fcf = [(op[p] or 0) - abs(capex[p] or 0) if op[p] is not None else None for p in periods]
    cfToRev = [(op[p] / rev[p] * 100) if op[p] is not None and rev[p] not in (None, 0) else None for p in periods]
    return {
        "periods": periods,
        "operating": [op[p] for p in periods],
        "capex": [abs(capex[p]) if capex[p] is not None else None for p in periods],
        "fcf": fcf,
        "cfToRevenue": cfToRev,
        "unit": "원",
    }
