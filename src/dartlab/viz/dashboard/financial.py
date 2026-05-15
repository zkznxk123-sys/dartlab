"""Dashboard 14 컴포넌트 — IS 4 + BS 3 + CF 3 + Ratios 4.

각 함수는 stockCode 받아 `{data, chartSpec, meta}` 3-키 dict 반환.
- data: 가공 결과 (rows/series/categories)
- chartSpec: frontend 차트 렌더 합의 (kind/series.colorSlot/options)
- meta: stockCode/corpName/periodKind/periods/generatedAt
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import polars as pl

from dartlab.viz.dashboard.companyCache import getCompany
from dartlab.viz.financial import balanceSheet, cashFlow, incomeStatement, ratios
from dartlab.viz.financial.rawNormalize import normalize


def _ctx(stockCode: str) -> tuple[pl.DataFrame, dict]:
    """Company 로드 → normalize + 메타 base."""
    company = getCompany(stockCode)
    norm = normalize(company.rawFinance)
    return norm, {
        "stockCode": str(stockCode),
        "corpName": getattr(company, "corpName", None),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _binding(stockCode: str, topic: str, periodKind: str, periods: list[str]) -> dict:
    """evidenceBinding 표준 dict."""
    return {
        "tableRef": f"finance:{topic}:{periodKind}",
        "source": "finance",
        "stockCode": stockCode,
        "topic": topic,
        "periodKind": periodKind,
        "periods": periods,
    }


def _periodKind(mode: str) -> str:
    """annual → Y, quarterly → Q."""
    return "Y" if mode == "annual" else "Q"


# ═══════════════════════════════════════════════════════════
# IS 4 — 손익계산서
# ═══════════════════════════════════════════════════════════


def isOverview(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 5) -> dict:
    """IS 총괄 — 매출/매출원가/매출총이익/영업이익/순이익 + 비율."""
    norm, meta = _ctx(target)
    o = incomeStatement.overview(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": o["periods"], "source": "finance"})
    return {
        "data": {"rows": o["rows"], "periods": o["periods"], "unit": "원"},
        "chartSpec": {
            "kind": "table",
            "title": "손익계산서 총괄",
            "categories": o["periods"],
            "series": [
                {"key": r["key"], "label": r["label"], "colorSlot": "primary", "type": "table"} for r in o["rows"]
            ],
            "options": {"unit": "원"},
            "evidenceBinding": _binding(target, "IS", _periodKind(mode), o["periods"]),
        },
        "meta": meta,
    }


def isRevenueTrend(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """매출 추세 + YoY overlay."""
    norm, meta = _ctx(target)
    rt = incomeStatement.revenueTrend(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": rt["periods"], "source": "finance"})
    return {
        "data": {"categories": rt["periods"], "revenue": rt["revenue"], "yoy": rt["yoy"], "unit": "원"},
        "chartSpec": {
            "kind": "bar",
            "title": "매출액 추세",
            "categories": rt["periods"],
            "series": [
                {"key": "revenue", "label": "매출액", "colorSlot": "primary", "type": "bar", "data": rt["revenue"]},
                {
                    "key": "yoy",
                    "label": "YoY(%)",
                    "colorSlot": "tertiary",
                    "type": "line",
                    "data": rt["yoy"],
                    "yAxis": "right",
                },
            ],
            "options": {"unit": "원", "yoyOverlay": True},
            "evidenceBinding": _binding(target, "IS", _periodKind(mode), rt["periods"]),
        },
        "meta": meta,
    }


def isMarginTrend(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """이익률 추세 — GPM/OPM/NPM."""
    norm, meta = _ctx(target)
    mt = incomeStatement.marginTrend(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": mt["periods"], "source": "finance"})
    return {
        "data": {"categories": mt["periods"], "gpm": mt["gpm"], "opm": mt["opm"], "npm": mt["npm"], "unit": "%"},
        "chartSpec": {
            "kind": "line",
            "title": "이익률 추세 (GPM/OPM/NPM)",
            "categories": mt["periods"],
            "series": [
                {"key": "gpm", "label": "매출총이익률", "colorSlot": "primary", "type": "line", "data": mt["gpm"]},
                {"key": "opm", "label": "영업이익률", "colorSlot": "secondary", "type": "line", "data": mt["opm"]},
                {"key": "npm", "label": "순이익률", "colorSlot": "tertiary", "type": "line", "data": mt["npm"]},
            ],
            "options": {"unit": "%"},
            "evidenceBinding": _binding(target, "IS", _periodKind(mode), mt["periods"]),
        },
        "meta": meta,
    }


def isCostStructure(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 5) -> dict:
    """비용 구조 — 매출원가 + SGA + R&D + 금융비용 stacked."""
    norm, meta = _ctx(target)
    cs = incomeStatement.costStructure(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": cs["periods"], "source": "finance"})
    return {
        "data": cs,
        "chartSpec": {
            "kind": "bar",
            "title": "비용 구조",
            "categories": cs["periods"],
            "series": [
                {
                    "key": "costOfSales",
                    "label": "매출원가",
                    "colorSlot": "primary",
                    "type": "bar",
                    "data": cs["costOfSales"],
                },
                {"key": "sga", "label": "판관비", "colorSlot": "secondary", "type": "bar", "data": cs["sga"]},
                {"key": "rnd", "label": "연구개발", "colorSlot": "tertiary", "type": "bar", "data": cs["rnd"]},
                {
                    "key": "financeCosts",
                    "label": "금융비용",
                    "colorSlot": "warning",
                    "type": "bar",
                    "data": cs["financeCosts"],
                },
            ],
            "options": {"stacked": True, "unit": "원"},
            "evidenceBinding": _binding(target, "IS", _periodKind(mode), cs["periods"]),
        },
        "meta": meta,
    }


# ═══════════════════════════════════════════════════════════
# BS 3 — 재무상태표
# ═══════════════════════════════════════════════════════════


def bsOverview(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 5) -> dict:
    """BS 총괄 — 자산/부채/자본 + 유동/비유동 + 현금."""
    norm, meta = _ctx(target)
    o = balanceSheet.overview(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": o["periods"], "source": "finance"})
    return {
        "data": {"rows": o["rows"], "periods": o["periods"], "unit": "원"},
        "chartSpec": {
            "kind": "table",
            "title": "재무상태표 총괄",
            "categories": o["periods"],
            "series": [
                {"key": r["key"], "label": r["label"], "colorSlot": "primary", "type": "table"} for r in o["rows"]
            ],
            "options": {"unit": "원"},
            "evidenceBinding": _binding(target, "BS", _periodKind(mode), o["periods"]),
        },
        "meta": meta,
    }


def bsComposition(target: str, *, mode: Literal["annual", "quarterly"] = "annual", period: str | None = None) -> dict:
    """자산 / 부채+자본 구성 — pie × 2."""
    norm, meta = _ctx(target)
    co = balanceSheet.composition(norm, period, mode)
    p = co["period"]
    meta.update({"periodKind": _periodKind(mode), "periods": [p] if p else [], "source": "finance"})
    slots = ("primary", "secondary", "tertiary", "muted", "success", "warning", "destructive")
    return {
        "data": co,
        "chartSpec": {
            "kind": "pie",
            "title": f"재무 구성 ({p})",
            "categories": [b["label"] for b in co["assetsBreakdown"]],
            "series": [
                {
                    "key": "assets",
                    "label": "자산",
                    "data": [b["value"] for b in co["assetsBreakdown"]],
                    "labels": [b["label"] for b in co["assetsBreakdown"]],
                    "colorSlots": [slots[i % len(slots)] for i in range(len(co["assetsBreakdown"]))],
                },
                {
                    "key": "liabEq",
                    "label": "부채+자본",
                    "data": [b["value"] for b in co["liabEquityBreakdown"]],
                    "labels": [b["label"] for b in co["liabEquityBreakdown"]],
                    "colorSlots": [slots[i % len(slots)] for i in range(len(co["liabEquityBreakdown"]))],
                },
            ],
            "options": {"unit": "원", "dual": True},
            "evidenceBinding": _binding(target, "BS", _periodKind(mode), [p] if p else []),
        },
        "meta": meta,
    }


def bsLeverage(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """레버리지 — D/E / D/A / 유동비."""
    norm, meta = _ctx(target)
    lv = balanceSheet.leverage(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": lv["periods"], "source": "finance"})
    return {
        "data": lv,
        "chartSpec": {
            "kind": "line",
            "title": "레버리지 추세",
            "categories": lv["periods"],
            "series": [
                {
                    "key": "debtToEquity",
                    "label": "부채/자본(%)",
                    "colorSlot": "primary",
                    "type": "line",
                    "data": lv["debtToEquity"],
                },
                {
                    "key": "debtToAssets",
                    "label": "부채/자산(%)",
                    "colorSlot": "secondary",
                    "type": "line",
                    "data": lv["debtToAssets"],
                },
                {
                    "key": "currentRatio",
                    "label": "유동비(%)",
                    "colorSlot": "tertiary",
                    "type": "line",
                    "data": lv["currentRatio"],
                },
            ],
            "options": {"unit": "%"},
            "evidenceBinding": _binding(target, "BS", _periodKind(mode), lv["periods"]),
        },
        "meta": meta,
    }


# ═══════════════════════════════════════════════════════════
# CF 3 — 현금흐름표
# ═══════════════════════════════════════════════════════════


def cfOverview(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 5) -> dict:
    """CF 총괄 — 영업/투자/재무 + 순현금변동 + FCF."""
    norm, meta = _ctx(target)
    o = cashFlow.overview(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": o["periods"], "source": "finance"})
    return {
        "data": {"rows": o["rows"], "periods": o["periods"], "unit": "원"},
        "chartSpec": {
            "kind": "table",
            "title": "현금흐름표 총괄",
            "categories": o["periods"],
            "series": [
                {"key": r["key"], "label": r["label"], "colorSlot": "primary", "type": "table"} for r in o["rows"]
            ],
            "options": {"unit": "원"},
            "evidenceBinding": _binding(target, "CF", _periodKind(mode), o["periods"]),
        },
        "meta": meta,
    }


def cfWaterfall(target: str, *, mode: Literal["annual", "quarterly"] = "annual", period: str | None = None) -> dict:
    """현금흐름 waterfall — 기초+영업+투자+재무+기말."""
    norm, meta = _ctx(target)
    w = cashFlow.waterfall(norm, period, mode)
    p = w["period"]
    meta.update({"periodKind": _periodKind(mode), "periods": [p] if p else [], "source": "finance"})
    slotMap = {"absolute": "muted", "total": "muted"}
    series = []
    for s in w["steps"]:
        v = s["value"]
        if s["measure"] == "relative":
            slot = "success" if (v or 0) >= 0 else "destructive"
        else:
            slot = slotMap.get(s["measure"], "muted")
        series.append({"key": s["label"], "label": s["label"], "value": v, "measure": s["measure"], "colorSlot": slot})
    return {
        "data": w,
        "chartSpec": {
            "kind": "waterfall",
            "title": f"현금흐름 ({p})",
            "categories": [s["label"] for s in w["steps"]],
            "series": series,
            "options": {"unit": "원"},
            "evidenceBinding": _binding(target, "CF", _periodKind(mode), [p] if p else []),
        },
        "meta": meta,
    }


def cfFreeCashFlow(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """잉여현금흐름 = 영업CF - CapEx + 영업CF/매출 비율."""
    norm, meta = _ctx(target)
    f = cashFlow.freeCashFlow(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": f["periods"], "source": "finance"})
    return {
        "data": f,
        "chartSpec": {
            "kind": "bar",
            "title": "잉여현금흐름 (FCF)",
            "categories": f["periods"],
            "series": [
                {"key": "operating", "label": "영업CF", "colorSlot": "primary", "type": "bar", "data": f["operating"]},
                {"key": "capex", "label": "CapEx", "colorSlot": "destructive", "type": "bar", "data": f["capex"]},
                {"key": "fcf", "label": "FCF", "colorSlot": "success", "type": "bar", "data": f["fcf"]},
                {
                    "key": "cfToRevenue",
                    "label": "영업CF/매출(%)",
                    "colorSlot": "tertiary",
                    "type": "line",
                    "data": f["cfToRevenue"],
                    "yAxis": "right",
                },
            ],
            "options": {"unit": "원"},
            "evidenceBinding": _binding(target, "CF", _periodKind(mode), f["periods"]),
        },
        "meta": meta,
    }


# ═══════════════════════════════════════════════════════════
# Ratios 4 — 재무비율
# ═══════════════════════════════════════════════════════════


def ratiosProfitability(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """수익성 — ROE/ROA/GPM/OPM/NPM."""
    norm, meta = _ctx(target)
    r = ratios.profitability(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": r["periods"], "source": "finance"})
    return {
        "data": r,
        "chartSpec": {
            "kind": "line",
            "title": "수익성 비율",
            "categories": r["periods"],
            "series": [
                {"key": "roe", "label": "ROE", "colorSlot": "primary", "type": "line", "data": r["roe"]},
                {"key": "roa", "label": "ROA", "colorSlot": "secondary", "type": "line", "data": r["roa"]},
                {"key": "gpm", "label": "GPM", "colorSlot": "tertiary", "type": "line", "data": r["gpm"]},
                {"key": "opm", "label": "OPM", "colorSlot": "success", "type": "line", "data": r["opm"]},
                {"key": "npm", "label": "NPM", "colorSlot": "warning", "type": "line", "data": r["npm"]},
            ],
            "options": {"unit": "%"},
            "evidenceBinding": _binding(target, "ratios", _periodKind(mode), r["periods"]),
        },
        "meta": meta,
    }


def ratiosStability(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """안정성 — 유동비/당좌비/부채비/자기자본비."""
    norm, meta = _ctx(target)
    r = ratios.stability(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": r["periods"], "source": "finance"})
    return {
        "data": r,
        "chartSpec": {
            "kind": "line",
            "title": "안정성 비율",
            "categories": r["periods"],
            "series": [
                {
                    "key": "currentRatio",
                    "label": "유동비",
                    "colorSlot": "primary",
                    "type": "line",
                    "data": r["currentRatio"],
                },
                {
                    "key": "quickRatio",
                    "label": "당좌비",
                    "colorSlot": "secondary",
                    "type": "line",
                    "data": r["quickRatio"],
                },
                {
                    "key": "debtRatio",
                    "label": "부채비",
                    "colorSlot": "destructive",
                    "type": "line",
                    "data": r["debtRatio"],
                },
                {
                    "key": "equityRatio",
                    "label": "자기자본비",
                    "colorSlot": "success",
                    "type": "line",
                    "data": r["equityRatio"],
                },
            ],
            "options": {"unit": "%"},
            "evidenceBinding": _binding(target, "ratios", _periodKind(mode), r["periods"]),
        },
        "meta": meta,
    }


def ratiosEfficiency(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """효율성 — 자산회전/재고회전/매출채권회전 + DSO/DIO."""
    norm, meta = _ctx(target)
    r = ratios.efficiency(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": r["periods"], "source": "finance"})
    return {
        "data": r,
        "chartSpec": {
            "kind": "line",
            "title": "효율성 비율",
            "categories": r["periods"],
            "series": [
                {
                    "key": "assetTurnover",
                    "label": "자산회전(회)",
                    "colorSlot": "primary",
                    "type": "line",
                    "data": r["assetTurnover"],
                },
                {
                    "key": "inventoryTurnover",
                    "label": "재고회전(회)",
                    "colorSlot": "secondary",
                    "type": "line",
                    "data": r["inventoryTurnover"],
                },
                {
                    "key": "receivableTurnover",
                    "label": "매출채권회전(회)",
                    "colorSlot": "tertiary",
                    "type": "line",
                    "data": r["receivableTurnover"],
                },
                {
                    "key": "dso",
                    "label": "DSO(일)",
                    "colorSlot": "warning",
                    "type": "line",
                    "data": r["dso"],
                    "yAxis": "right",
                },
                {
                    "key": "dio",
                    "label": "DIO(일)",
                    "colorSlot": "destructive",
                    "type": "line",
                    "data": r["dio"],
                    "yAxis": "right",
                },
            ],
            "options": {"unit": "회"},
            "evidenceBinding": _binding(target, "ratios", _periodKind(mode), r["periods"]),
        },
        "meta": meta,
    }


def ratiosGrowth(target: str, *, mode: Literal["annual", "quarterly"] = "annual", nPeriods: int = 8) -> dict:
    """성장성 — 매출 YoY / 영업이익 YoY / 순이익 YoY + CAGR3y."""
    norm, meta = _ctx(target)
    r = ratios.growth(norm, nPeriods, mode)
    meta.update({"periodKind": _periodKind(mode), "periods": r["periods"], "source": "finance"})
    return {
        "data": r,
        "chartSpec": {
            "kind": "bar",
            "title": "성장성 비율",
            "categories": r["periods"],
            "series": [
                {
                    "key": "revenueYoy",
                    "label": "매출 YoY(%)",
                    "colorSlot": "primary",
                    "type": "bar",
                    "data": r["revenueYoy"],
                },
                {
                    "key": "operatingYoy",
                    "label": "영업이익 YoY(%)",
                    "colorSlot": "secondary",
                    "type": "bar",
                    "data": r["operatingYoy"],
                },
                {
                    "key": "netIncomeYoy",
                    "label": "순이익 YoY(%)",
                    "colorSlot": "tertiary",
                    "type": "bar",
                    "data": r["netIncomeYoy"],
                },
            ],
            "options": {"unit": "%", "cagr3y": r["cagr3y"]},
            "evidenceBinding": _binding(target, "ratios", _periodKind(mode), r["periods"]),
        },
        "meta": meta,
    }
