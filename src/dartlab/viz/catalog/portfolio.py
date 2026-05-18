"""사업포트폴리오 탭 — KPI 4 개 분리 + 자본배분 sankey + 비용구조 + 자본효율.

bento 밀도 packing: 4 KPI 한 row + 자본배분 stacked/waterfall + costMix (2×3) + capitalReturns (2×3, 3 시리즈 auto).
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry


def _kpi(
    title: str, label: str, *, account=None, ratio=None, compose=None, unit: str, intent: str, helpText: str
) -> CatalogEntry:
    tile: dict = {"label": label, "unit": unit, "intent": intent}
    if account:
        tile["account"] = account
    if ratio:
        tile["ratio"] = ratio
    if compose:
        tile["compose"] = compose
    return {
        "kind": "kpiTile",
        "title": title,
        "topic": "ratios" if ratio else "IS",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [],
        "dataSpec": {"adapter": "kpiFromNorm", "tilePlans": [tile]},
        "options": {},
        "layout": {"colSpan": 4, "rowSpan": 2},
        "help": helpText,
    }


PORTFOLIO_CARDS: dict[str, CatalogEntry] = {
    "portfolioKpiRevenue": _kpi(
        "매출",
        "매출",
        account="revenue",
        unit="원",
        intent="primary",
        helpText="본업 규모. 사업 부문별 비중은 비용구조·자본배분 카드에서.",
    ),
    # portfolioKpiOp 폐기 — finance.py kpiOperatingIncome 와 중복
    # portfolioKpiOpMargin 폐기 — finance.py 와 별도 KPI 인데 lifecycleKpiOpMargin 과 중복
    "portfolioKpiRnd": _kpi(
        "R&D 비중",
        "R&D/매출",
        ratio={"num": {"rnd": 1}, "den": {"revenue": 1}, "scale": 100},
        unit="%",
        intent="accent",
        helpText="매출 대비 R&D. 5%+ 기술집약, 1% 미만 전통산업.",
    ),
    "portfolioCapitalAllocation": {
        "kind": "trend",
        "title": "자본배분 (시간축)",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {"adapter": "capitalAllocationBars"},
        "options": {"stacked": True, "unit": "원"},
        "layout": {"colSpan": 8, "rowSpan": 8},
        "help": "연도별 자본 사용처 — 설비투자 / 배당 / 부채상환 / 잉여. 사업 우선순위 추적.",
    },
    "costMix": {
        "kind": "trend",
        "title": "비용 구조",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "costOfSales",
                "label": "매출원가",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "costOfSales",
            },
            {
                "key": "sga",
                "label": "판관비",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "sga",
            },
            {
                "key": "rnd",
                "label": "R&D",
                "color": COLORS[4],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "rnd",
            },
        ],
        "options": {"stacked": True, "unit": "원"},
        "layout": {"colSpan": 8, "rowSpan": 8},
        "help": "원가·판관비·R&D 비중 추이. R&D 비중 ↑ 미래 투자 의지.",
    },
    "capitalReturns": {
        "kind": "trend",
        "title": "자본 효율 추이",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "roe",
                "label": "ROE",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"equity": 1}, "scale": 100},
            },
            {
                "key": "roa",
                "label": "ROA",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"assets": 1}, "scale": 100},
            },
            {
                "key": "assetTurn",
                "label": "자산회전율",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "회",
                "type": "line",
                "axis": "right",
                "ratio": {"num": {"revenue": 1}, "den": {"assets": 1}, "scale": 1},
            },
        ],
        "options": {"unit": "%"},
        "help": "ROE/ROA + 자산회전율. ROIC vs WACC 정밀 산출은 후속.",
    },
}


PORTFOLIO_KEYS: list[str] = [
    "portfolioKpiRevenue",
    "portfolioKpiRnd",
    "portfolioCapitalAllocation",
    "costMix",
    "capitalReturns",
]


__all__ = ["PORTFOLIO_CARDS", "PORTFOLIO_KEYS"]
