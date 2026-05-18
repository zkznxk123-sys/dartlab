"""revenueForecast 의 5 dataclass — CompanyDataBundle/SegmentForecast/BacklogSignal/RevenueForecastAIOverlay/RevenueForecastResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from dartlab.core.utils.fmt import fmtBig

# L1 → L0 데이터 브릿지


@dataclass
class CompanyDataBundle:
    """L1(Company) → L0(forecast) 데이터 브릿지."""

    segmentRevenue: pl.DataFrame | None = None  # c.segments.revenue
    salesDf: pl.DataFrame | None = None  # c.salesOrder.salesDf
    orderDf: pl.DataFrame | None = None  # c.salesOrder.orderDf
    structuralBreak: dict | None = None  # calcStructuralBreak() 결과


@dataclass
class SegmentForecast:
    """개별 세그먼트 예측 결과."""

    name: str
    historical: list[float | None]
    projected: list[float]
    growthRates: list[float]
    method: str
    shareOfRevenue: float  # 최근 매출 비중 (%, 0~100)
    lifecycle: str


@dataclass
class BacklogSignal:
    """수주잔고 기반 선행 시그널."""

    backlogRevenueRatio: float  # 현재 B/R ratio
    brRatioTrend: str  # "increasing" | "stable" | "declining"
    impliedRevenueGrowth: float  # 수주잔고 기반 내재 매출 성장률 (%)
    conversionRate: float  # 과거 평균 수주→매출 전환율
    sectorsApplicable: bool  # 건설/조선/방산만 강신호


@dataclass
class RevenueForecastAIOverlay:
    """AI 보정 결과 — 구조화된 스키마."""

    growthAdjustment: list[float]  # 연도별 %p 보정
    direction: str  # "up" | "down" | "neutral"
    magnitude: str  # "minor" (<2%p) | "moderate" (2-5%p) | "major" (>5%p)
    scenarioShift: dict[str, float] | None = None  # 시나리오 확률 이동
    reasoning: list[str] = field(default_factory=list)  # 보정 근거
    applied: bool = False


# ══════════════════════════════════════
# 결과 타입
# ══════════════════════════════════════


@dataclass
class RevenueForecastResult:
    """매출 예측 결과 — 소스별 기여도 투명 공개."""

    historical: list[float | None]
    projected: list[float]
    horizon: int
    method: str  # "ensemble" | "timeseries_only" | "consensus_only" | "N/A"
    confidence: str  # "high" | "medium" | "low"
    growthRates: list[float]  # 연도별 YoY 성장률 (%)
    sources: list[str]  # ["timeseries", "consensus", "macro", "roic"]
    sourceWeights: dict[str, float]  # {"timeseries": 0.4, "consensus": 0.45, ...}
    consensusRevenue: list[float] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    aiContext: dict = field(default_factory=dict)

    # v3 확장 필드 (전부 default — 하위호환)
    scenarios: dict[str, list[float]] = field(default_factory=dict)  # base/bull/bear
    scenarioGrowthRates: dict[str, list[float]] = field(default_factory=dict)
    scenarioProbabilities: dict[str, float] = field(default_factory=dict)
    segmentForecasts: list[SegmentForecast] = field(default_factory=list)
    backlogSignal: BacklogSignal | None = None
    aiOverlay: RevenueForecastAIOverlay | None = None
    forwardTestKey: str | None = None
    currency: str = "KRW"

    # v4: 예측 불가능성 명시 (네이트 실버 — 예측할 수 없는 것을 예측하지 마라)
    forecastable: bool = True
    unforecastableReason: str = ""

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        cur = self.currency
        lines = [f"[매출 예측 — {self.method}]"]
        lines.append(f"  신뢰도: {self.confidence}")
        lc = self.aiContext.get("lifecycle", "")
        if lc:
            lines.append(f"  라이프사이클: {lc}")
        lines.append(f"  소스: {', '.join(f'{k}({v:.0%})' for k, v in self.sourceWeights.items())}")

        validHist = [v for v in self.historical if v is not None]
        if self.projected and validHist:
            base = (
                self.projected[0] / (1 + self.growthRates[0] / 100)
                if self.growthRates and self.growthRates[0] != -100
                else validHist[-1]
            )
            lines.append(f"  기준 매출: {fmtBig(base, cur)}")
        elif validHist:
            lines.append(f"  최근 실적: {fmtBig(validHist[-1], cur)}")

        for i, (proj, gr) in enumerate(zip(self.projected, self.growthRates), 1):
            lines.append(f"  +{i}년: {fmtBig(proj, cur)} ({gr:+.1f}%)")

        # v3: 시나리오
        if self.scenarios:
            probs = self.scenarioProbabilities
            for label in ("bull", "bear"):
                sc = self.scenarios.get(label, [])
                sg = self.scenarioGrowthRates.get(label, [])
                prob = probs.get(label, 0)
                if sc:
                    lines.append(
                        f"  {label.title()}({prob:.0f}%): {fmtBig(sc[0], cur)} ({sg[0]:+.1f}%)"
                        if sg
                        else f"  {label.title()}: {fmtBig(sc[0], cur)}"
                    )

        # v3: 세그먼트
        if self.segmentForecasts:
            lines.append(f"  세그먼트: {len(self.segmentForecasts)}개 부문")
            for sf in self.segmentForecasts[:3]:  # 상위 3개만 표시
                if sf.projected:
                    lines.append(
                        f"    {sf.name}({sf.shareOfRevenue:.0f}%): {fmtBig(sf.projected[0], cur)} ({sf.growthRates[0]:+.1f}%)"
                        if sf.growthRates
                        else f"    {sf.name}: {fmtBig(sf.projected[0], cur)}"
                    )

        # v3: 수주잔고
        if self.backlogSignal:
            bs = self.backlogSignal
            lines.append(
                f"  수주잔고: B/R={bs.backlogRevenueRatio:.1f}x ({bs.brRatioTrend}), 내재 성장 {bs.impliedRevenueGrowth:+.1f}%"
            )

        if self.assumptions:
            for a in self.assumptions:
                lines.append(f"  · {a}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)
