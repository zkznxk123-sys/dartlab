"""동종비교 탭 — scatter 4사분면 + comparisonTable + trend 2.

bento packing: scatter (2×3) + comparisonTable (2×3) + trend (2×2) + trend (2×2).
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry

PEER_CARDS: dict[str, CatalogEntry] = {
    "peerScatter": {
        "kind": "scatter",
        "title": "위험-수익 사분면",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "value",
        "seriesPlan": [],
        "dataSpec": {"adapter": "peerScatter"},
        "options": {},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "ROE × 부채비율 산점도. 회사 본인 별표, 동종 평균 참조선.",
    },
    "peerComparisonTable": {
        "kind": "comparisonTable",
        "title": "동종 백분위 비교",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {"adapter": "peerComparison"},
        "options": {},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "주요 지표 동종 분위 (회사 vs 중앙값 + p25/p75 + 백분위).",
    },
    "peerProfitability": {
        "kind": "trend",
        "title": "수익성 추이",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "opm",
                "label": "영업이익률",
                "color": COLORS[4],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"operatingIncome": 1}, "den": {"revenue": 1}, "scale": 100},
            },
            {
                "key": "npm",
                "label": "순이익률",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"revenue": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "회사의 수익성 추세 — 동종 분포 비교 보조.",
    },
    "peerGrowth": {
        "kind": "trend",
        "title": "성장",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [
            {
                "key": "revYoy",
                "label": "매출 증가율",
                "color": COLORS[0],
                "intent": "primary",
                "unit": "%",
                "type": "bar",
                "yoy": "revenue",
            },
            {
                "key": "niYoy",
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
        "help": "매출·순이익 YoY — 동종 분포 보조 비교 자료.",
    },
}


PEER_KEYS: list[str] = ["peerScatter", "peerComparisonTable", "peerProfitability", "peerGrowth"]


__all__ = ["PEER_CARDS", "PEER_KEYS"]
