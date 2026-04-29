"""Viz intent catalog for story-driven dashboards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VizIntent:
    """Dashboard visual intent exported to the landing manifest."""

    key: str
    chartType: str
    title: str
    purpose: str
    statement: str
    component: str
    periodMode: str
    compareMode: str
    requiredMetricIds: tuple[str, ...]
    evidenceTopics: tuple[str, ...]
    blockKeys: tuple[str, ...] = ()

    def toDict(self) -> dict:
        """Return JSON-ready visual intent metadata."""
        return {
            "key": self.key,
            "chartType": self.chartType,
            "title": self.title,
            "purpose": self.purpose,
            "statement": self.statement,
            "component": self.component,
            "periodMode": self.periodMode,
            "compareMode": self.compareMode,
            "requiredMetricIds": list(self.requiredMetricIds),
            "evidenceTopics": list(self.evidenceTopics),
            "blockKeys": list(self.blockKeys),
        }


VIZ_INTENTS: tuple[VizIntent, ...] = (
    VizIntent(
        key="kpi_sparklines",
        chartType="sparkline",
        title="핵심 지표 5년 흐름",
        purpose="trend",
        statement="IS",
        component="kpi_ribbon",
        periodMode="Q",
        compareMode="yoy",
        requiredMetricIds=("revenue", "op", "net", "opMargin", "roe", "debtRatio", "ocf", "fcf", "per", "pbr"),
        evidenceTopics=("finance",),
        blockKeys=("scorecard",),
    ),
    VizIntent(
        key="is_revenue_profit",
        chartType="combo",
        title="매출과 이익 흐름",
        purpose="trend",
        statement="IS",
        component="small_multiples",
        periodMode="Q",
        compareMode="yoy",
        requiredMetricIds=("revenue", "op", "net", "opMargin", "netMargin"),
        evidenceTopics=("finance",),
        blockKeys=("growth", "segmentComposition"),
    ),
    VizIntent(
        key="is_margin_trend",
        chartType="line",
        title="영업이익률과 순이익률",
        purpose="trend",
        statement="IS",
        component="margin_lines",
        periodMode="Q",
        compareMode="yoy",
        requiredMetricIds=("opMargin", "netMargin"),
        evidenceTopics=("finance",),
        blockKeys=("marginTrend",),
    ),
    VizIntent(
        key="bs_capital_structure",
        chartType="bar",
        title="자산 = 부채 + 자본",
        purpose="composition",
        statement="BS",
        component="stacked_composition",
        periodMode="Q",
        compareMode="latest",
        requiredMetricIds=("assets", "liabilities", "equity"),
        evidenceTopics=("finance",),
        blockKeys=("leverageTrend", "fundingSources"),
    ),
    VizIntent(
        key="bs_asset_composition",
        chartType="bar",
        title="자산 구성과 묶인 돈",
        purpose="composition",
        statement="BS",
        component="asset_mix",
        periodMode="Q",
        compareMode="latest",
        requiredMetricIds=("cash", "receivables", "inventory", "tangible", "intangible", "assets"),
        evidenceTopics=("finance",),
        blockKeys=("assetStructure", "workingCapital"),
    ),
    VizIntent(
        key="bs_debt_ratio_trend",
        chartType="line",
        title="부채비율 추이",
        purpose="risk",
        statement="BS",
        component="ratio_lines",
        periodMode="Q",
        compareMode="yoy",
        requiredMetricIds=("debtRatio",),
        evidenceTopics=("finance",),
        blockKeys=("leverageTrend", "distressScore"),
    ),
    VizIntent(
        key="cf_signed_flow",
        chartType="bar",
        title="영업/투자/재무/FCF 흐름",
        purpose="bridge",
        statement="CF",
        component="signed_bars",
        periodMode="Q",
        compareMode="yoy",
        requiredMetricIds=("ocf", "icf", "financingCf", "fcf"),
        evidenceTopics=("finance",),
        blockKeys=("cashFlowOverview", "fcfUsage"),
    ),
    VizIntent(
        key="cf_waterfall",
        chartType="waterfall",
        title="최신 현금흐름 브릿지",
        purpose="bridge",
        statement="CF",
        component="waterfall",
        periodMode="Q",
        compareMode="latest",
        requiredMetricIds=("ocf", "icf", "financingCf", "closingCash"),
        evidenceTopics=("finance",),
        blockKeys=("cashFlowOverview",),
    ),
    VizIntent(
        key="capital_allocation_flow",
        chartType="bar",
        title="FCF 이후 자본배분",
        purpose="bridge",
        statement="CF",
        component="signed_bars",
        periodMode="Q",
        compareMode="latest",
        requiredMetricIds=("fcf", "capex", "dividendPaid", "financingCf"),
        evidenceTopics=("finance", "report", "docs"),
        blockKeys=("fcfUsage", "reinvestment", "dividendPolicy", "shareholderReturn"),
    ),
    VizIntent(
        key="valuation_multiples",
        chartType="bar",
        title="시장 가격 배수",
        purpose="valuation",
        statement="PRICE",
        component="valuation_bars",
        periodMode="Q",
        compareMode="latest",
        requiredMetricIds=("per", "pbr", "dividendYield"),
        evidenceTopics=("price", "finance"),
        blockKeys=("relativeValuation", "valuationSynthesis"),
    ),
    VizIntent(
        key="peer_position_radar",
        chartType="radar",
        title="업종 내 위치",
        purpose="comparison",
        statement="PEER",
        component="peer_score",
        periodMode="Q",
        compareMode="peer",
        requiredMetricIds=("profitabilityGrade", "growthGrade", "debtGrade", "qualityGrade", "governanceGrade"),
        evidenceTopics=("peer", "map"),
        blockKeys=("peerPosition",),
    ),
    VizIntent(
        key="report_evidence_matrix",
        chartType="heatmap",
        title="보고서/원문 근거 연결",
        purpose="evidence",
        statement="REPORT",
        component="evidence_matrix",
        periodMode="Q",
        compareMode="topic",
        requiredMetricIds=("reportFacts", "docs", "changes"),
        evidenceTopics=("report", "docs"),
        blockKeys=("storyPrecedents", "disclosureChangeSummary"),
    ),
)


def listVizIntents() -> list[dict]:
    """Return dashboard visual intents for static manifest generation."""
    return [intent.toDict() for intent in VIZ_INTENTS]
