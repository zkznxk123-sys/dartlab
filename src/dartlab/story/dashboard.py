"""Dashboard question catalog for story-driven company dashboards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardQuestion:
    """Question-level dashboard pack exported to the landing manifest."""

    id: str
    question: str
    tocLabel: str
    sectionKeys: tuple[str, ...]
    blockKeys: tuple[str, ...]
    statementKeys: tuple[str, ...] = ()
    evidenceTopics: tuple[str, ...] = ()
    vizKeys: tuple[str, ...] = ()

    def toDict(self) -> dict:
        """Return JSON-ready dashboard question metadata."""
        return {
            "id": self.id,
            "question": self.question,
            "tocLabel": self.tocLabel,
            "sectionKeys": list(self.sectionKeys),
            "blockKeys": list(self.blockKeys),
            "statementKeys": list(self.statementKeys),
            "evidenceTopics": list(self.evidenceTopics),
            "vizKeys": list(self.vizKeys),
        }


DASHBOARD_QUESTIONS: tuple[DashboardQuestion, ...] = (
    DashboardQuestion(
        id="overview",
        question="한눈에 결론은 무엇인가?",
        tocLabel="결론",
        sectionKeys=("종합평가",),
        blockKeys=("scorecard", "summaryFlags", "creditScore", "peerPosition"),
        statementKeys=("IS", "BS", "CF"),
        evidenceTopics=("finance", "report", "docs", "map", "price", "peer"),
        vizKeys=("kpi_sparklines", "peer_position_radar"),
    ),
    DashboardQuestion(
        id="business",
        question="이 회사는 무엇으로 돈을 버나?",
        tocLabel="수익원",
        sectionKeys=("수익구조",),
        blockKeys=("profile", "segmentComposition", "growth", "concentration", "revenueQuality"),
        statementKeys=("IS",),
        evidenceTopics=("finance", "docs", "map"),
        vizKeys=("is_revenue_profit", "report_evidence_matrix"),
    ),
    DashboardQuestion(
        id="profit",
        question="번 돈은 얼마나 남나?",
        tocLabel="수익성",
        sectionKeys=("수익성", "비용구조"),
        blockKeys=("marginTrend", "returnTrend", "costBreakdown", "profitabilityFlags"),
        statementKeys=("IS",),
        evidenceTopics=("finance", "docs"),
        vizKeys=("is_margin_trend", "is_revenue_profit"),
    ),
    DashboardQuestion(
        id="cash",
        question="이익은 현금으로 바뀌나?",
        tocLabel="현금",
        sectionKeys=("현금흐름", "이익품질"),
        blockKeys=("cashFlowOverview", "cashQuality", "ocfDecomposition", "accrualAnalysis"),
        statementKeys=("IS", "CF"),
        evidenceTopics=("finance", "report", "docs"),
        vizKeys=("cf_signed_flow", "cf_waterfall"),
    ),
    DashboardQuestion(
        id="stability",
        question="자산과 부채 구조는 안전한가?",
        tocLabel="안정성",
        sectionKeys=("안정성", "자금조달"),
        blockKeys=("leverageTrend", "coverageTrend", "distressScore", "fundingSources"),
        statementKeys=("BS", "CF"),
        evidenceTopics=("finance", "report", "docs"),
        vizKeys=("bs_capital_structure", "bs_debt_ratio_trend"),
    ),
    DashboardQuestion(
        id="allocation",
        question="번 돈은 어디에 묶이고 어디에 재투자되나?",
        tocLabel="자산배치",
        sectionKeys=("자본배분", "자산구조"),
        blockKeys=("assetStructure", "workingCapital", "capexPattern", "fcfUsage", "reinvestment", "dividendPolicy"),
        statementKeys=("BS", "CF"),
        evidenceTopics=("finance", "report", "docs"),
        vizKeys=("bs_asset_composition", "capital_allocation_flow"),
    ),
    DashboardQuestion(
        id="valuation",
        question="현재 가격은 무엇을 반영하나?",
        tocLabel="가격",
        sectionKeys=("가치평가", "비교분석", "시장분석"),
        blockKeys=("valuationSynthesis", "relativeValuation", "priceTarget", "peerPosition"),
        statementKeys=("IS", "BS", "CF"),
        evidenceTopics=("finance", "price", "peer", "macro"),
        vizKeys=("valuation_multiples", "peer_position_radar"),
    ),
    DashboardQuestion(
        id="evidence",
        question="보고서와 원문은 숫자를 뒷받침하나?",
        tocLabel="근거",
        sectionKeys=("storyValidation", "공시변화", "지배구조"),
        blockKeys=("storyPrecedents", "plausibilityBand", "valuationSins", "disclosureChangeSummary"),
        statementKeys=("IS", "BS", "CF"),
        evidenceTopics=("finance", "report", "docs"),
        vizKeys=("report_evidence_matrix",),
    ),
)


def listDashboardQuestions() -> list[dict]:
    """Return dashboard question packs for static manifest generation."""
    return [question.toDict() for question in DASHBOARD_QUESTIONS]
