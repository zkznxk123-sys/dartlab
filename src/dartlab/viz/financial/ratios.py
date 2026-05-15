"""재무비율 — profitability / stability / efficiency / growth."""

from __future__ import annotations

import polars as pl

from dartlab.viz.financial.accounts import extractSeries
from dartlab.viz.financial.periods import lastNPeriods


def _safe(a: float | None, b: float | None) -> float | None:
    """안전 나눗셈."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct(x: float | None) -> float | None:
    """비율 × 100, None safe."""
    return x * 100 if x is not None else None


def profitability(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """ROE / ROA / GPM / OPM / NPM."""
    periods = lastNPeriods(norm, nPeriods, mode)
    rev = extractSeries(norm, "revenue", periods)
    gp = extractSeries(norm, "grossProfit", periods)
    cos = extractSeries(norm, "costOfSales", periods)
    op = extractSeries(norm, "operatingIncome", periods)
    ni = extractSeries(norm, "netIncome", periods)
    assets = extractSeries(norm, "assets", periods)
    eq = extractSeries(norm, "equity", periods)

    def _gp(p: str) -> float | None:
        """매출총이익 — 직접 없으면 (매출 - 매출원가)."""
        if gp[p] is not None:
            return gp[p]
        if rev[p] is not None and cos[p] is not None:
            return rev[p] - cos[p]
        return None

    roe = [_pct(_safe(ni[p], eq[p])) for p in periods]
    roa = [_pct(_safe(ni[p], assets[p])) for p in periods]
    gpm = [_pct(_safe(_gp(p), rev[p])) for p in periods]
    opm = [_pct(_safe(op[p], rev[p])) for p in periods]
    npm = [_pct(_safe(ni[p], rev[p])) for p in periods]
    return {
        "periods": periods,
        "roe": roe,
        "roa": roa,
        "gpm": gpm,
        "opm": opm,
        "npm": npm,
        "unit": "%",
    }


def stability(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """유동비율 / 부채비율 / 자기자본비율."""
    periods = lastNPeriods(norm, nPeriods, mode)
    curA = extractSeries(norm, "currentAssets", periods)
    curL = extractSeries(norm, "currentLiabilities", periods)
    liab = extractSeries(norm, "liabilities", periods)
    eq = extractSeries(norm, "equity", periods)
    assets = extractSeries(norm, "assets", periods)
    cash = extractSeries(norm, "cash", periods)
    rec = extractSeries(norm, "receivables", periods)

    currentRatio = [_pct(_safe(curA[p], curL[p])) for p in periods]
    debtRatio = [_pct(_safe(liab[p], eq[p])) for p in periods]
    equityRatio = [_pct(_safe(eq[p], assets[p])) for p in periods]
    quickRatio = [_pct(_safe((cash[p] or 0) + (rec[p] or 0) if curL[p] else None, curL[p])) for p in periods]
    return {
        "periods": periods,
        "currentRatio": currentRatio,
        "quickRatio": quickRatio,
        "debtRatio": debtRatio,
        "equityRatio": equityRatio,
        "unit": "%",
    }


def efficiency(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """자산회전 / 재고회전 / 매출채권회전."""
    periods = lastNPeriods(norm, nPeriods, mode)
    rev = extractSeries(norm, "revenue", periods)
    cos = extractSeries(norm, "costOfSales", periods)
    assets = extractSeries(norm, "assets", periods)
    inv = extractSeries(norm, "inventories", periods)
    rec = extractSeries(norm, "receivables", periods)

    assetTurn = [_safe(rev[p], assets[p]) for p in periods]
    invTurn = [_safe(cos[p], inv[p]) for p in periods]
    recTurn = [_safe(rev[p], rec[p]) for p in periods]
    dso = [_safe(365.0, v) for v in recTurn]
    dio = [_safe(365.0, v) for v in invTurn]
    return {
        "periods": periods,
        "assetTurnover": assetTurn,
        "inventoryTurnover": invTurn,
        "receivableTurnover": recTurn,
        "dso": dso,
        "dio": dio,
        "unit": "회",
    }


def growth(norm: pl.DataFrame, nPeriods: int, mode: str = "annual") -> dict:
    """매출 YoY / 영업이익 YoY / 순이익 YoY + CAGR3y."""
    periods = lastNPeriods(norm, nPeriods + 1, mode)
    rev = extractSeries(norm, "revenue", periods)
    op = extractSeries(norm, "operatingIncome", periods)
    ni = extractSeries(norm, "netIncome", periods)

    def _yoyList(series: dict) -> list[float | None]:
        """기간별 YoY % 리스트 (첫 기간 None)."""
        ps = list(series.keys())
        out: list[float | None] = [None]
        for i in range(1, len(ps)):
            prev, curr = series[ps[i - 1]], series[ps[i]]
            if prev is None or curr is None or prev <= 0:
                out.append(None)
            else:
                out.append((curr - prev) / prev * 100)
        return out

    revYoy = _yoyList(rev)
    opYoy = _yoyList(op)
    niYoy = _yoyList(ni)

    cagr3y = None
    if len(periods) >= 4:
        start = rev[periods[-4]]
        end = rev[periods[-1]]
        if start and start > 0 and end and end > 0:
            cagr3y = ((end / start) ** (1 / 3) - 1) * 100

    return {
        "periods": periods[1:],
        "revenueYoy": revYoy[1:],
        "operatingYoy": opYoy[1:],
        "netIncomeYoy": niYoy[1:],
        "cagr3y": cagr3y,
        "unit": "%",
    }
