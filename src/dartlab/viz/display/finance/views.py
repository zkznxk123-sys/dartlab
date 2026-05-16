"""14 view 함수 — stockCode → 표준 View JSON.

frontend 가 dlCall("viz.finance.views.X") 로 호출하는 진입점.
모든 view 가 schema.View 동일 모양 반환:
  {kind, title, categories, series, evidenceBinding, meta, options?}

view 함수가 직접 결정하는 것:
- kind (trend/snapshot/breakdown/table/waterfall)
- title (한국어)
- categories 배치
- series 키·라벨·단위·intent (의미 슬롯)

frontend 가 결정하는 것:
- 실제 hex 컬러 (intent → 회사 디자인 토큰 매핑)
- 차트 타입 세부 옵션 (legend 위치, 폰트 등)
- 인터랙션
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import polars as pl

from dartlab.viz.display.finance import ratios, statements
from dartlab.viz.display.finance._cache import getCompany
from dartlab.viz.display.finance.normalize import normalize
from dartlab.viz.display.finance.schema import (
    EvidenceBinding,
    Meta,
    PeriodKind,
    Series,
    View,
    makeBinding,
    makeMeta,
)


def _ctx(stockCode: str) -> tuple[pl.DataFrame, str | None]:
    """Company 로드 + normalize. (norm, corpName) 반환."""
    company = getCompany(stockCode)
    norm = normalize(company.rawFinance)
    return norm, getattr(company, "corpName", None)


def _baseMeta(stockCode: str, corpName: str | None, periodKind: PeriodKind, periods: list[str]) -> Meta:
    """공통 meta 생성."""
    return makeMeta(
        stockCode,
        corpName=corpName,
        periodKind=periodKind,
        periods=periods,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )


def _trend(
    *,
    title: str,
    categories: list[str],
    series: list[Series],
    binding: EvidenceBinding,
    meta: Meta,
    options: dict | None = None,
) -> View:
    """trend View 생성."""
    out: View = {
        "kind": "trend",
        "title": title,
        "categories": categories,
        "series": series,
        "evidenceBinding": binding,
        "meta": meta,
    }
    if options:
        out["options"] = options
    return out


def _table(
    *,
    title: str,
    categories: list[str],
    series: list[Series],
    binding: EvidenceBinding,
    meta: Meta,
) -> View:
    """table View 생성."""
    return {
        "kind": "table",
        "title": title,
        "categories": categories,
        "series": series,
        "evidenceBinding": binding,
        "meta": meta,
    }


# ═══════════════════════════════════════════════════════════
# IS 4
# ═══════════════════════════════════════════════════════════


def isOverview(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 5) -> View:
    """손익계산서 총괄 (table)."""
    norm, corpName = _ctx(stockCode)
    o = statements.isOverview(norm, nPeriods, periodKind)
    periods = o["periods"]
    series: list[Series] = [
        {"key": r["key"], "label": r["label"], "data": r["values"], "unit": r["unit"]} for r in o["rows"]
    ]
    return _table(
        title="손익계산서 총괄",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "IS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def isRevenueTrend(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """매출 추세 + YoY (trend, dual axis)."""
    norm, corpName = _ctx(stockCode)
    r = statements.isRevenueTrend(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {"key": "revenue", "label": "매출액", "data": r["revenue"], "unit": "원", "intent": "primary", "type": "bar"},
        {
            "key": "yoy",
            "label": "YoY",
            "data": r["yoy"],
            "unit": "%",
            "intent": "accent",
            "type": "line",
            "axis": "right",
        },
    ]
    return _trend(
        title="매출액 추세",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "IS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def isMarginTrend(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """이익률 추세 — GPM/OPM/NPM (trend)."""
    norm, corpName = _ctx(stockCode)
    r = statements.isMarginTrend(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {"key": "gpm", "label": "매출총이익률", "data": r["gpm"], "unit": "%", "intent": "primary"},
        {"key": "opm", "label": "영업이익률", "data": r["opm"], "unit": "%", "intent": "accent"},
        {"key": "npm", "label": "순이익률", "data": r["npm"], "unit": "%", "intent": "neutral"},
    ]
    return _trend(
        title="이익률 추세 (GPM/OPM/NPM)",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "IS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def isCostStructure(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 5) -> View:
    """비용 구조 — stacked bar (trend, stacked)."""
    norm, corpName = _ctx(stockCode)
    c = statements.isCostStructure(norm, nPeriods, periodKind)
    periods = c["periods"]
    series: list[Series] = [
        {
            "key": "costOfSales",
            "label": "매출원가",
            "data": c["costOfSales"],
            "unit": "원",
            "intent": "primary",
            "type": "bar",
        },
        {"key": "sga", "label": "판매관리비", "data": c["sga"], "unit": "원", "intent": "accent", "type": "bar"},
        {"key": "rnd", "label": "연구개발", "data": c["rnd"], "unit": "원", "intent": "neutral", "type": "bar"},
        {
            "key": "financeCosts",
            "label": "금융비용",
            "data": c["financeCosts"],
            "unit": "원",
            "intent": "negative",
            "type": "bar",
        },
    ]
    return _trend(
        title="비용 구조",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "IS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
        options={"stacked": True},
    )


# ═══════════════════════════════════════════════════════════
# BS 3
# ═══════════════════════════════════════════════════════════


def bsOverview(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 5) -> View:
    """재무상태표 총괄 (table)."""
    norm, corpName = _ctx(stockCode)
    o = statements.bsOverview(norm, nPeriods, periodKind)
    periods = o["periods"]
    series: list[Series] = [
        {"key": r["key"], "label": r["label"], "data": r["values"], "unit": r["unit"]} for r in o["rows"]
    ]
    return _table(
        title="재무상태표 총괄",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "BS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def bsComposition(stockCode: str, *, periodKind: PeriodKind = "annual", period: str | None = None) -> View:
    """자산 / 부채+자본 구성 — breakdown 2 시리즈.

    series 2개 (assets / liabilitiesEquity) 각각 data + 항목 label 은 categories 가 아닌
    series 안 label 로 — 그래서 categories 는 두 시리즈 max length 의 인덱스로 둠.
    frontend 는 series 마다 자기 항목 라벨로 pie 그림.
    """
    norm, corpName = _ctx(stockCode)
    c = statements.bsComposition(norm, period, periodKind)
    p = c["period"]
    periods = [p] if p else []

    assetsItems: list[dict] = c["assets"]
    liabEqItems: list[dict] = c["liabilitiesEquity"]

    series: list[Series] = [
        {
            "key": "assets",
            "label": "자산 구성",
            "data": [it["value"] for it in assetsItems],
        },
        {
            "key": "liabilitiesEquity",
            "label": "부채+자본 구성",
            "data": [it["value"] for it in liabEqItems],
        },
    ]
    # categories 는 series 내부 항목 키 (assets 기준). frontend 가 series 별 labels 필요시
    # options.itemLabels 에서 가져감.
    out: View = {
        "kind": "breakdown",
        "title": f"재무 구성 ({p})" if p else "재무 구성",
        "categories": [it["key"] for it in assetsItems],
        "series": series,
        "evidenceBinding": makeBinding(stockCode, "BS", periodKind, periods),
        "meta": _baseMeta(stockCode, corpName, periodKind, periods),
        "options": {
            "dual": True,
            "itemLabels": {
                "assets": {it["key"]: it["label"] for it in assetsItems},
                "liabilitiesEquity": {it["key"]: it["label"] for it in liabEqItems},
            },
            "itemKeys": {
                "assets": [it["key"] for it in assetsItems],
                "liabilitiesEquity": [it["key"] for it in liabEqItems],
            },
        },
    }
    return out


def bsLeverage(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """레버리지 추세 (trend)."""
    norm, corpName = _ctx(stockCode)
    lv = statements.bsLeverage(norm, nPeriods, periodKind)
    periods = lv["periods"]
    series: list[Series] = [
        {"key": "debtToEquity", "label": "부채/자본", "data": lv["debtToEquity"], "unit": "%", "intent": "primary"},
        {"key": "debtToAssets", "label": "부채/자산", "data": lv["debtToAssets"], "unit": "%", "intent": "accent"},
        {"key": "currentRatio", "label": "유동비율", "data": lv["currentRatio"], "unit": "%", "intent": "neutral"},
    ]
    return _trend(
        title="레버리지 추세",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "BS", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


# ═══════════════════════════════════════════════════════════
# CF 3
# ═══════════════════════════════════════════════════════════


def cfOverview(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 5) -> View:
    """현금흐름표 총괄 (table)."""
    norm, corpName = _ctx(stockCode)
    o = statements.cfOverview(norm, nPeriods, periodKind)
    periods = o["periods"]
    series: list[Series] = [
        {"key": r["key"], "label": r["label"], "data": r["values"], "unit": r["unit"]} for r in o["rows"]
    ]
    return _table(
        title="현금흐름표 총괄",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "CF", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def cfWaterfall(stockCode: str, *, periodKind: PeriodKind = "annual", period: str | None = None) -> View:
    """현금흐름 waterfall (waterfall)."""
    norm, corpName = _ctx(stockCode)
    w = statements.cfWaterfall(norm, period, periodKind)
    p = w["period"]
    periods = [p] if p else []
    steps = w["steps"]

    # waterfall 은 series 1개, 각 step 이 자기 value+measure.
    # points 필드 사용 (data 대신).
    series: list[Series] = [
        {
            "key": "cashFlow",
            "label": "현금흐름",
            "points": [{"value": s["value"], "measure": s["measure"]} for s in steps],
            "unit": "원",
        }
    ]
    categories = [s["label"] for s in steps]
    out: View = {
        "kind": "waterfall",
        "title": f"현금흐름 ({p})" if p else "현금흐름",
        "categories": categories,
        "series": series,
        "evidenceBinding": makeBinding(stockCode, "CF", periodKind, periods),
        "meta": _baseMeta(stockCode, corpName, periodKind, periods),
        "options": {"stepKeys": [s["key"] for s in steps]},
    }
    return out


def cfFreeCashFlow(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """잉여현금흐름 (trend, combo bar+line)."""
    norm, corpName = _ctx(stockCode)
    f = statements.cfFreeCashFlow(norm, nPeriods, periodKind)
    periods = f["periods"]
    series: list[Series] = [
        {
            "key": "operating",
            "label": "영업CF",
            "data": f["operating"],
            "unit": "원",
            "intent": "primary",
            "type": "bar",
        },
        {"key": "capex", "label": "CapEx", "data": f["capex"], "unit": "원", "intent": "negative", "type": "bar"},
        {"key": "fcf", "label": "FCF", "data": f["fcf"], "unit": "원", "intent": "positive", "type": "bar"},
        {
            "key": "cfToRevenue",
            "label": "영업CF/매출",
            "data": f["cfToRevenue"],
            "unit": "%",
            "intent": "accent",
            "type": "line",
            "axis": "right",
        },
    ]
    return _trend(
        title="잉여현금흐름 (FCF)",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "CF", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


# ═══════════════════════════════════════════════════════════
# Ratios 4
# ═══════════════════════════════════════════════════════════


def ratiosProfitability(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """수익성 — ROE/ROA/GPM/OPM/NPM (trend)."""
    norm, corpName = _ctx(stockCode)
    r = ratios.profitability(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {"key": "roe", "label": "ROE", "data": r["roe"], "unit": "%", "intent": "primary"},
        {"key": "roa", "label": "ROA", "data": r["roa"], "unit": "%", "intent": "accent"},
        {"key": "gpm", "label": "GPM", "data": r["gpm"], "unit": "%", "intent": "neutral"},
        {"key": "opm", "label": "OPM", "data": r["opm"], "unit": "%", "intent": "positive"},
        {"key": "npm", "label": "NPM", "data": r["npm"], "unit": "%", "intent": "negative"},
    ]
    return _trend(
        title="수익성 비율",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "ratios", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def ratiosStability(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """안정성 — 유동/당좌/부채/자기자본 (trend)."""
    norm, corpName = _ctx(stockCode)
    r = ratios.stability(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {"key": "currentRatio", "label": "유동비율", "data": r["currentRatio"], "unit": "%", "intent": "primary"},
        {"key": "quickRatio", "label": "당좌비율", "data": r["quickRatio"], "unit": "%", "intent": "accent"},
        {"key": "debtRatio", "label": "부채비율", "data": r["debtRatio"], "unit": "%", "intent": "negative"},
        {"key": "equityRatio", "label": "자기자본비율", "data": r["equityRatio"], "unit": "%", "intent": "positive"},
    ]
    return _trend(
        title="안정성 비율",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "ratios", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def ratiosEfficiency(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """효율성 — 회전율 + DSO/DIO (trend, dual axis)."""
    norm, corpName = _ctx(stockCode)
    r = ratios.efficiency(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {"key": "assetTurnover", "label": "자산회전", "data": r["assetTurnover"], "unit": "회", "intent": "primary"},
        {
            "key": "inventoryTurnover",
            "label": "재고회전",
            "data": r["inventoryTurnover"],
            "unit": "회",
            "intent": "accent",
        },
        {
            "key": "receivableTurnover",
            "label": "매출채권회전",
            "data": r["receivableTurnover"],
            "unit": "회",
            "intent": "neutral",
        },
        {"key": "dso", "label": "DSO", "data": r["dso"], "unit": "일", "intent": "negative", "axis": "right"},
        {"key": "dio", "label": "DIO", "data": r["dio"], "unit": "일", "intent": "negative", "axis": "right"},
    ]
    return _trend(
        title="효율성 비율",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "ratios", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
    )


def ratiosGrowth(stockCode: str, *, periodKind: PeriodKind = "annual", nPeriods: int = 8) -> View:
    """성장성 — YoY 3종 + CAGR3y (trend, options 에 cagr3y)."""
    norm, corpName = _ctx(stockCode)
    r = ratios.growth(norm, nPeriods, periodKind)
    periods = r["periods"]
    series: list[Series] = [
        {
            "key": "revenueYoy",
            "label": "매출 YoY",
            "data": r["revenueYoy"],
            "unit": "%",
            "intent": "primary",
            "type": "bar",
        },
        {
            "key": "operatingYoy",
            "label": "영업이익 YoY",
            "data": r["operatingYoy"],
            "unit": "%",
            "intent": "accent",
            "type": "bar",
        },
        {
            "key": "netIncomeYoy",
            "label": "순이익 YoY",
            "data": r["netIncomeYoy"],
            "unit": "%",
            "intent": "neutral",
            "type": "bar",
        },
    ]
    return _trend(
        title="성장성 비율",
        categories=periods,
        series=series,
        binding=makeBinding(stockCode, "ratios", periodKind, periods),
        meta=_baseMeta(stockCode, corpName, periodKind, periods),
        options={"cagr3y": r["cagr3y"]},
    )


VIEWS: dict[str, Any] = {
    "isOverview": isOverview,
    "isRevenueTrend": isRevenueTrend,
    "isMarginTrend": isMarginTrend,
    "isCostStructure": isCostStructure,
    "bsOverview": bsOverview,
    "bsComposition": bsComposition,
    "bsLeverage": bsLeverage,
    "cfOverview": cfOverview,
    "cfWaterfall": cfWaterfall,
    "cfFreeCashFlow": cfFreeCashFlow,
    "ratiosProfitability": ratiosProfitability,
    "ratiosStability": ratiosStability,
    "ratiosEfficiency": ratiosEfficiency,
    "ratiosGrowth": ratiosGrowth,
}
