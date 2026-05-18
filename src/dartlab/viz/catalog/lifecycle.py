"""생애주기·시나리오 탭 — phaseIndicator + 단계 KPI 4 + 현금흐름 패턴 + 자본 배치.

bento packing: phaseIndicator (4×1) + KPI×4 (1×1) + cashflowPattern (2×2) + capitalDeployment (2×2).
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry


def _kpi(
    title: str, label: str, *, ratio=None, account=None, compose=None, yoy=None, unit: str, intent: str, helpText: str
) -> CatalogEntry:
    tile: dict = {"label": label, "unit": unit, "intent": intent}
    if account:
        tile["account"] = account
    if ratio:
        tile["ratio"] = ratio
    if compose:
        tile["compose"] = compose
    if yoy:
        tile["yoy"] = yoy
    return {
        "kind": "kpiTile",
        "title": title,
        "topic": "ratios" if ratio else "IS",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [],
        "dataSpec": {"adapter": "kpiFromNorm", "tilePlans": [tile]},
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": helpText,
    }


LIFECYCLE_CARDS: dict[str, CatalogEntry] = {
    "lifeCyclePhase": {
        "kind": "phaseIndicator",
        "title": "생애주기 단계",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [],
        "dataSpec": {"adapter": "lifeCyclePhase"},
        "options": {},
        "layout": {"colSpan": 4, "rowSpan": 1},
        "help": "Damodaran 6 단계 (도입·성장·성숙Ⅰ·성숙Ⅱ·쇠퇴·회복) + 신뢰도.",
    },
    "lifecycleKpiRevenue": _kpi(
        "매출 YoY",
        "매출 YoY",
        yoy="revenue",
        unit="%",
        intent="primary",
        helpText="매출 YoY % — 도입/성장 단계 핵심 신호.",
    ),
    "lifecycleKpiOpMargin": _kpi(
        "영업이익률",
        "영업이익률",
        ratio={"num": {"operatingIncome": 1}, "den": {"revenue": 1}, "scale": 100},
        unit="%",
        intent="positive",
        helpText="성숙기 진입 신호 — 마진 안정화.",
    ),
    "lifecycleKpiRoe": _kpi(
        "ROE",
        "ROE",
        ratio={"num": {"netIncome": 1}, "den": {"equity": 1}, "scale": 100},
        unit="%",
        intent="primary",
        helpText="자본 효율. 단계별 정상 범위 다름.",
    ),
    "lifecycleKpiFcfMargin": _kpi(
        "FCF/매출",
        "FCF Margin",
        ratio={"num": {"cfOperating": 1, "capex": -1}, "den": {"revenue": 1}, "scale": 100},
        unit="%",
        intent="positive",
        helpText="잉여현금흐름 비율. 성숙기 후 강하게 양수.",
    ),
    "cashflowPattern": {
        "kind": "trend",
        "title": "현금흐름 3축",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [
            {
                "key": "cfo",
                "label": "영업CF",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "원",
                "type": "line",
                "account": "cfOperating",
            },
            {
                "key": "cfi",
                "label": "투자CF",
                "color": COLORS[2],
                "intent": "negative",
                "unit": "원",
                "type": "line",
                "account": "cfInvesting",
            },
            {
                "key": "cff",
                "label": "재무CF",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "line",
                "account": "cfFinancing",
            },
        ],
        "options": {"unit": "원"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "영업+/투자-/재무- = 성숙기, 모두+ = 도입기, 영업- = 위기.",
    },
    "capitalDeployment": {
        "kind": "trend",
        "title": "자본 배치 추이",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [
            {
                "key": "capex",
                "label": "CapEx",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "account": "capex",
            },
            {
                "key": "rnd",
                "label": "R&D",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "원",
                "type": "bar",
                "account": "rnd",
            },
        ],
        "options": {"unit": "원"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "CapEx + R&D 절대값. 비중 변화로 도입기→성숙기 전이 식별.",
    },
}


LIFECYCLE_KEYS: list[str] = [
    "lifeCyclePhase",
    "lifecycleKpiRevenue",
    "lifecycleKpiOpMargin",
    "lifecycleKpiRoe",
    "lifecycleKpiFcfMargin",
    "cashflowPattern",
    "capitalDeployment",
]


__all__ = ["LIFECYCLE_CARDS", "LIFECYCLE_KEYS"]
