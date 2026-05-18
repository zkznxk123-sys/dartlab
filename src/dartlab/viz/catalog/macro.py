"""거시·섹터 탭 — 사이클 phaseIndicator + KPI 4 개 분리 + 매출/부채 사이클.

bento packing: cyclePhase (4×1) + KPI×4 (1×1) + revenueCycle (2×2) + debtCycle (2×2).
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry


def _kpi(
    title: str, label: str, *, ratio=None, account=None, yoy=None, unit: str, intent: str, helpText: str
) -> CatalogEntry:
    tile: dict = {"label": label, "unit": unit, "intent": intent}
    if account:
        tile["account"] = account
    if ratio:
        tile["ratio"] = ratio
    if yoy:
        tile["yoy"] = yoy
    return {
        "kind": "kpiTile",
        "title": title,
        "topic": "ratios" if ratio else "IS",
        "tab": "financial",
        "subCategory": "value",
        "seriesPlan": [],
        "dataSpec": {"adapter": "kpiFromNorm", "tilePlans": [tile]},
        "options": {},
        "layout": {"colSpan": 3, "rowSpan": 3},
        "help": helpText,
    }


MACRO_CARDS: dict[str, CatalogEntry] = {
    "cyclePhase": {
        "kind": "phaseIndicator",
        "title": "경기 사이클 단계 (회사 기준)",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "value",
        "seriesPlan": [],
        "dataSpec": {"adapter": "lifeCyclePhase"},
        "options": {},
        "layout": {"colSpan": 12, "rowSpan": 3},
        "help": "회사 매출·이익 사이클 단계 (Damodaran). 외부 macroExposure 결합은 후속.",
    },
    "macroKpiRevenue": _kpi(
        "매출 변동",
        "매출 YoY",
        yoy="revenue",
        unit="%",
        intent="primary",
        helpText="경기에 직접 노출 — 매출 YoY %.",
    ),
    "macroKpiOpMargin": _kpi(
        "영업이익률",
        "영업이익률",
        ratio={"num": {"operatingIncome": 1}, "den": {"revenue": 1}, "scale": 100},
        unit="%",
        intent="positive",
        helpText="고정비 레버리지 — 경기 둔화 시 빠르게 하락.",
    ),
    "macroKpiCogsRatio": _kpi(
        "매출원가율",
        "매출원가/매출",
        ratio={"num": {"costOfSales": 1}, "den": {"revenue": 1}, "scale": 100},
        unit="%",
        intent="negative",
        helpText="원자재·환율 영향이 직접 반영되는 지표.",
    ),
    "macroKpiDso": _kpi(
        "DSO (일)",
        "매출채권회수일",
        ratio={"num": {"receivables": 365}, "den": {"revenue": 1}, "scale": 1},
        unit="일",
        intent="accent",
        helpText="경기 둔화 시 회수 지연 — DSO 증가.",
    ),
    "revenueCycle": {
        "kind": "trend",
        "title": "매출 사이클",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "value",
        "seriesPlan": [
            {
                "key": "revenue",
                "label": "매출액",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "원",
                "type": "bar",
                "account": "revenue",
            },
            {
                "key": "revYoy",
                "label": "YoY",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "axis": "right",
                "yoy": "revenue",
            },
        ],
        "options": {"unit": "원"},
        "layout": {"colSpan": 4, "rowSpan": 4},
        "help": "매출 절대값 + YoY. 산업 경기 사이클과의 동조성 시각화.",
    },
    "debtCycle": {
        "kind": "trend",
        "title": "부채 사이클",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "value",
        "seriesPlan": [
            {
                "key": "shortDebt",
                "label": "단기차입금",
                "color": COLORS[2],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "debt",
                "account": "shortDebt",
            },
            {
                "key": "longDebt",
                "label": "장기차입금",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "debt",
                "account": "longDebt",
            },
        ],
        "options": {"unit": "원", "stacked": True},
        "layout": {"colSpan": 4, "rowSpan": 4},
        "help": "차입금 시계열 — 금리 사이클 노출. 단기 비중 ↑ = 금리 민감.",
    },
}


MACRO_KEYS: list[str] = [
    "cyclePhase",
    "macroKpiRevenue",
    "macroKpiOpMargin",
    "macroKpiCogsRatio",
    "macroKpiDso",
    "revenueCycle",
    "debtCycle",
]


__all__ = ["MACRO_CARDS", "MACRO_KEYS"]
