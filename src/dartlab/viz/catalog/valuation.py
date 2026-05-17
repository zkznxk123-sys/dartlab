"""가치평가 탭 — KPI 4 개 분리 + diffView + 상대가치 시계열 + 시나리오.

bento 밀도 packing: 4 KPI 한 row + diffView (2×3) + relativeValueTrend (2×2) +
scenarioGrowth (2×2).
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
        "tab": "valuation",
        "seriesPlan": [],
        "dataSpec": {"adapter": "kpiFromNorm", "tilePlans": [tile]},
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": helpText,
    }


VALUATION_CARDS: dict[str, CatalogEntry] = {
    "valuationKpiOp": _kpi(
        "영업이익",
        "영업이익",
        account="operatingIncome",
        unit="원",
        intent="positive",
        helpText="현금흐름 추정 베이스.",
    ),
    "valuationKpiNi": _kpi(
        "당기순이익",
        "순이익",
        account="netIncome",
        unit="원",
        intent="primary",
        helpText="EPS·PER 계산 기반.",
    ),
    "valuationKpiFcf": _kpi(
        "잉여현금흐름",
        "FCF",
        compose={"cfOperating": 1, "capex": -1},
        unit="원",
        intent="positive",
        helpText="DCF 모델의 입력. 영업CF − CapEx.",
    ),
    "valuationKpiRoe": _kpi(
        "ROE",
        "ROE",
        ratio={"num": {"netIncome": 1}, "den": {"equity": 1}, "scale": 100},
        unit="%",
        intent="primary",
        helpText="자본 효율. 정당화 PBR 의 입력.",
    ),
    "valuationDiff": {
        "kind": "diffView",
        "title": "전기 대비 변화",
        "topic": "IS",
        "tab": "valuation",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "diffFromNorm",
            "periodLabel": "YoY",
            "tilePlans": [
                {"label": "매출", "account": "revenue", "unit": "원"},
                {"label": "영업이익", "account": "operatingIncome", "unit": "원"},
                {"label": "순이익", "account": "netIncome", "unit": "원"},
                {"label": "FCF", "compose": {"cfOperating": 1, "capex": -1}, "unit": "원"},
                {"label": "자기자본", "account": "equity", "unit": "원"},
                {"label": "이익잉여금", "account": "retainedEarnings", "unit": "원"},
            ],
        },
        "options": {},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "직전 기간 대비 변화율 — 가치 펀더멘탈 모멘텀 확인.",
    },
    "relativeValueTrend": {
        "kind": "trend",
        "title": "자본 기반 가치 추이",
        "topic": "BS",
        "tab": "valuation",
        "seriesPlan": [
            {
                "key": "equity",
                "label": "자기자본",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "원",
                "type": "line",
                "account": "equity",
            },
            {
                "key": "retainedEarnings",
                "label": "이익잉여금",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "원",
                "type": "line",
                "account": "retainedEarnings",
            },
        ],
        "options": {"unit": "원"},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "장부가 추이 — 자기자본·이익잉여금. 시장 멀티플 정상화 근거.",
    },
    "scenarioGrowth": {
        "kind": "trend",
        "title": "성장 시나리오 (과거 분포)",
        "topic": "IS",
        "tab": "valuation",
        "seriesPlan": [
            {
                "key": "revenueYoy",
                "label": "매출 증가율",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "bar",
                "yoy": "revenue",
            },
            {
                "key": "netIncomeYoy",
                "label": "순이익 증가율",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "bar",
                "yoy": "netIncome",
            },
        ],
        "options": {"unit": "%"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "Bull/Base/Bear 시나리오를 위한 과거 성장 분포. 평균 + 표준편차로 g 추정.",
    },
}


VALUATION_KEYS: list[str] = [
    "valuationKpiOp",
    "valuationKpiNi",
    "valuationKpiFcf",
    "valuationKpiRoe",
    "valuationDiff",
    "relativeValueTrend",
    "scenarioGrowth",
]


__all__ = ["VALUATION_CARDS", "VALUATION_KEYS"]
