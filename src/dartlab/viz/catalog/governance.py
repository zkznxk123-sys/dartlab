"""거버넌스·리스크 탭 — KPI 4 + distress gauge + 이상신호 + 이익품질 + 자본거버넌스.

bento packing: KPI 4 (1×1) + gauge (1×2) + topList (1×3) + trend (2×2) + trend (2×2).
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry


def _kpi(title: str, label: str, *, ratio=None, account=None, unit: str, intent: str, helpText: str) -> CatalogEntry:
    tile: dict = {"label": label, "unit": unit, "intent": intent}
    if account:
        tile["account"] = account
    if ratio:
        tile["ratio"] = ratio
    return {
        "kind": "kpiTile",
        "title": title,
        "topic": "ratios" if ratio else "IS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [],
        "dataSpec": {"adapter": "kpiFromNorm", "tilePlans": [tile]},
        "options": {},
        "layout": {"colSpan": 4, "rowSpan": 2},
        "help": helpText,
    }


GOVERNANCE_CARDS: dict[str, CatalogEntry] = {
    "governanceKpiCfNi": {
        **_kpi(
            "영업CF/순이익",
            "CF/NI",
            ratio={"num": {"cfOperating": 1}, "den": {"netIncome": 1}, "scale": 100},
            unit="%",
            intent="primary",
            helpText="100%↑ 정상. 70% 미만 지속은 분식 의심.",
        ),
        "subCategory": "quality",
    },
    "governanceKpiEquityRatio": _kpi(
        "자기자본비율",
        "자기자본/자산",
        ratio={"num": {"equity": 1}, "den": {"assets": 1}, "scale": 100},
        unit="%",
        intent="positive",
        helpText="50%+ 보수적. 30% 이하는 부채 의존.",
    ),
    "governanceKpiReRatio": _kpi(
        "이익잉여금/자본",
        "내부유보율",
        ratio={"num": {"retainedEarnings": 1}, "den": {"equity": 1}, "scale": 100},
        unit="%",
        intent="accent",
        helpText="누적 이익잉여금 비중. 높을수록 보수적 거버넌스.",
    ),
    # governanceKpiDebtRatio 폐기 — finance.kpiDebtRatio 와 ratio 완전 중복 (v3-r5 §6).
    # distressGauge 폐기 — finance.py riskDistress 와 중복 gauge (Altman Z')
    # anomalySignals 폐기 — finance.py riskAnomaly 와 중복 topList (이상신호)
    "earningsQualityTrend": {
        "kind": "trend",
        "title": "이익 품질",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [
            {
                "key": "cfNi",
                "label": "영업CF/순이익",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"cfOperating": 1}, "den": {"netIncome": 1}, "scale": 100},
            },
            {
                "key": "cfRev",
                "label": "영업CF/매출",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"cfOperating": 1}, "den": {"revenue": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "layout": {"colSpan": 6, "rowSpan": 6},
        "help": "영업CF/순이익 100%↑ = 회계이익이 진짜 현금. 70% 미만 지속은 분식 의심.",
    },
    "capitalGovernance": {
        "kind": "trend",
        "title": "자본 거버넌스",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "equityRatio",
                "label": "자기자본비율",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"equity": 1}, "den": {"assets": 1}, "scale": 100},
            },
            {
                "key": "reRatio",
                "label": "이익잉여금/자본",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"retainedEarnings": 1}, "den": {"equity": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "layout": {"colSpan": 6, "rowSpan": 6},
        "help": "자기자본비율 + 이익잉여금/자본. 내부유보 누적 = 보수적 거버넌스.",
    },
}


GOVERNANCE_KEYS: list[str] = [
    "governanceKpiCfNi",
    "governanceKpiEquityRatio",
    "governanceKpiReRatio",
    "earningsQualityTrend",
    "capitalGovernance",
]


__all__ = ["GOVERNANCE_CARDS", "GOVERNANCE_KEYS"]
