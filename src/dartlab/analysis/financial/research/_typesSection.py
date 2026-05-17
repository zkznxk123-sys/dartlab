"""Research 섹션 dataclasses — types.py 에서 분리.

ResearchMeta + Executive/Thesis/Overview/SectorKpi(s) + Beneish + FinancialAnalysis +
EarningsQuality + MarketData + ForecastData + Insight/Distress/Anomaly/Risk/Valuation/Peer 섹션.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dartlab.analysis.financial.research._typesScoring import DuPontResult, QuantScores

# 리포트 섹션
# ══════════════════════════════════════


@dataclass
class ResearchMeta:
    """리포트 메타데이터."""

    stockCode: str = ""
    corpName: str = ""
    generatedAt: str = ""
    dataAsOf: str = ""
    coverageScore: float = 0.0  # 0~1
    market: str = "KR"
    currency: str = "KRW"
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExecutiveSummary:
    """핵심 요약."""

    opinion: str = ""  # "강력매수" ~ "강력매도"
    profile: str = ""  # "premium" | "growth" | "stable" | "caution" | "distress"
    targetPrice: float | None = None
    currentPrice: float | None = None
    upside: float | None = None
    thesis: str = ""
    grades: dict[str, str] = field(default_factory=dict)
    keyMetrics: list[dict[str, object]] = field(default_factory=list)


@dataclass
class InvestmentThesis:
    """투자논거."""

    bullCase: list[str] = field(default_factory=list)
    bearCase: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    monitoringPoints: list[str] = field(default_factory=list)
    confidence: float = 0.0
    summaryNarrative: str = ""


@dataclass
class CompanyOverview:
    """기업 개요."""

    description: str | None = None
    sectorName: str | None = None
    industryName: str | None = None
    newsHeadlines: list[str] = field(default_factory=list)


@dataclass
class SectorKpi:
    """단일 섹터 KPI."""

    name: str = ""
    label: str = ""
    value: float | None = None
    benchmark: float | None = None
    unit: str = ""
    assessment: str = ""  # "good" | "neutral" | "bad"


@dataclass
class SectorKpis:
    """섹터별 특화 KPI."""

    sectorName: str = ""
    kpis: list[SectorKpi] = field(default_factory=list)


@dataclass
class BeneishDetail:
    """Beneish M-Score 8변수 개별."""

    dsri: float | None = None  # 매출채권지수
    gmi: float | None = None  # 매출총이익지수
    aqi: float | None = None  # 자산품질지수
    sgi: float | None = None  # 매출성장지수
    depi: float | None = None  # 감가상각지수
    sgai: float | None = None  # 판관비지수
    lvgi: float | None = None  # 레버리지지수
    tata: float | None = None  # 발생주의비율
    mScore: float | None = None  # 종합 M-Score
    flagged: list[str] = field(default_factory=list)  # 경고 변수명 리스트


@dataclass
class FinancialAnalysis:
    """재무 분석."""

    dupont: DuPontResult | None = None
    marginTrends: dict[str, list[float | None]] = field(default_factory=dict)
    periods: list[str] = field(default_factory=list)
    # BS 요약 시계열
    bsSummary: dict[str, list[float | None]] = field(default_factory=dict)
    # CF 요약 시계열
    cfSummary: dict[str, list[float | None]] = field(default_factory=dict)
    # 3표 연결 지표 시계열
    crossStatementMetrics: dict[str, list[float | None]] = field(default_factory=dict)
    # Common-Size 분석 (Lens 2)
    isCommonSize: dict[str, list[float | None]] = field(default_factory=dict)  # IS항목/매출 %
    bsCommonSize: dict[str, list[float | None]] = field(default_factory=dict)  # BS항목/자산 %


@dataclass
class EarningsQuality:
    """이익의 질."""

    cfToNi: float | None = None
    accrualRatio: float | None = None
    ccc: float | None = None  # Cash Conversion Cycle (days)
    beneishMScore: float | None = None
    assessment: str = ""  # "high" | "moderate" | "low" | "questionable"


@dataclass
class MarketData:
    """시장 데이터 요약."""

    currentPrice: float | None = None
    marketCap: float | None = None
    per: float | None = None
    pbr: float | None = None
    dividendYield: float | None = None
    high52w: float | None = None
    low52w: float | None = None
    targetPrice: float | None = None
    analystCount: int | None = None
    buyRatio: float | None = None
    foreignHoldingRatio: float | None = None
    baseRate: float | None = None
    usdKrw: float | None = None


@dataclass
class ForecastData:
    """전망 데이터."""

    revenueConsensus: list[dict[str, object]] = field(default_factory=list)
    selfForecast: dict[str, object] | None = None
    scenarioSummary: dict[str, object] | None = None


# ══════════════════════════════════════
# 새 섹션 타입 — v2
# ══════════════════════════════════════


@dataclass
class InsightDetail:
    """insight 영역 상세 — 등급 + 근거 수치."""

    area: str = ""
    grade: str = ""
    summary: str = ""
    details: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)


@dataclass
class DistressSection:
    """부실 리스크 스코어카드."""

    level: str = ""  # safe/watch/warning/danger/critical
    overall: float = 0.0  # 0~100
    creditGrade: str = ""  # AAA~D
    creditDescription: str = ""
    riskFactors: list[str] = field(default_factory=list)
    cashRunwayMonths: float | None = None
    axesSummary: list[dict[str, object]] = field(default_factory=list)


@dataclass
class AnomalySection:
    """이상치 탐지 결과."""

    items: list[dict[str, object]] = field(default_factory=list)
    criticalCount: int = 0
    warningCount: int = 0


@dataclass
class RiskSection:
    """종합 리스크 — distress + anomalies + insight.risk 통합."""

    distress: DistressSection | None = None
    anomalies: AnomalySection | None = None
    insightRisk: InsightDetail | None = None
    riskNarrative: str = ""


@dataclass
class ValuationSection:
    """밸류에이션 — DCF/DDM/상대가치 종합."""

    dcfPerShare: float | None = None
    dcfMos: float | None = None  # 안전마진 (%)
    ddmPerShare: float | None = None
    relativePerShare: float | None = None
    fairValueRange: tuple[float, float] | None = None
    verdict: str = ""  # "저평가" | "적정" | "고평가"
    methodology: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PeerSection:
    """동종업 비교 — 섹터 배수 기반 (OOM 안전)."""

    sectorName: str = ""
    sectorMultiples: dict[str, float] = field(default_factory=dict)
    companyMultiples: dict[str, float | None] = field(default_factory=dict)
    premiumDiscount: dict[str, float | None] = field(default_factory=dict)
    peerNarrative: str = ""
