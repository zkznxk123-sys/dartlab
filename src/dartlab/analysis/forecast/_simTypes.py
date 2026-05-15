"""시뮬레이션 결과 타입 — 4 dataclass + DISCLAIMER.

analysis/forecast/simulation.py 가 1106 줄 god module 이라 types 분리.
identity 보존을 위해 simulation.py 가 본 모듈에서 re-export 한다.

타입:
- SimulationResult — 단일 시나리오 (base/bull/bear) 시뮬레이션 결과
- MonteCarloResult — Monte Carlo 다중 iteration 결과
- StressTestResult — 스트레스 테스트 결과
- BacktestResult — 시뮬레이션 백테스트 결과
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dartlab.core.utils.fmt import fmtBig, fmtPrice
from dartlab.synth.scenario import SectorElasticity


@dataclass
class SimulationResult:
    """단일 시나리오 시뮬레이션 결과."""

    scenarioName: str
    scenarioLabel: str
    years: int
    revenuePath: list[float]
    operatingIncomePath: list[float]
    marginPath: list[float]
    fcfPath: list[float]
    dcfValue: float
    perShareValue: float | None
    revenueChangePct: float
    marginChangeBps: float
    elasticityUsed: SectorElasticity
    assumptions: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    currency: str = "KRW"

    DISCLAIMER: str = "본 시뮬레이션은 참고용이며 실제 경제 상황과 다를 수 있습니다."

    def __repr__(self) -> str:
        c = self.currency
        lines = [f"[{self.scenarioLabel} 시뮬레이션]"]
        lines.append(f"  경기감응도: {self.elasticityUsed}")
        for i, (rev, oi, mg) in enumerate(
            zip(
                self.revenuePath,
                self.operatingIncomePath,
                self.marginPath,
            )
        ):
            lines.append(f"  +{i + 1}년: 매출 {fmtBig(rev, c)}, 영업이익 {fmtBig(oi, c)}, 마진 {mg:.1f}%")
        lines.append(f"  매출 변화: {self.revenueChangePct:+.1f}%")
        lines.append(f"  마진 변화: {self.marginChangeBps:+.0f}bps")
        if self.perShareValue is not None:
            lines.append(f"  주당 가치: {fmtPrice(self.perShareValue, c)}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


@dataclass
class MonteCarloResult:
    """Monte Carlo 시뮬레이션 결과."""

    iterations: int
    scenarioName: str
    percentiles: dict[str, dict[str, float]]
    expectedValue: float
    stdDev: float
    var95: float
    upsideProbability: float
    warnings: list[str] = field(default_factory=list)
    currency: str = "KRW"

    DISCLAIMER: str = "본 시뮬레이션은 참고용이며 실제 경제 상황과 다를 수 있습니다."

    def __repr__(self) -> str:
        c = self.currency
        lines = [f"[Monte Carlo — {self.scenarioName} ({self.iterations:,}회)]"]
        for metric, pcts in self.percentiles.items():
            p5 = pcts.get("p5", 0)
            p50 = pcts.get("p50", 0)
            p95 = pcts.get("p95", 0)
            lines.append(f"  {metric}: P5={fmtBig(p5, c)}  P50={fmtBig(p50, c)}  P95={fmtBig(p95, c)}")
        lines.append(f"  기대값: {fmtBig(self.expectedValue, c)}")
        lines.append(f"  VaR(95%): {fmtBig(self.var95, c)}")
        lines.append(f"  상승 확률: {self.upsideProbability:.0f}%")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


@dataclass
class StressTestResult:
    """스트레스 테스트 결과."""

    scenarioName: str
    scenarioLabel: str
    year3RevenueChange: float
    year3MarginChange: float
    year3DebtRatio: float | None
    year3CurrentRatio: float | None
    year3InterestCoverage: float | None
    survivalRisk: str
    dividendSustainable: bool
    recoveryTimeline: str
    warnings: list[str] = field(default_factory=list)

    DISCLAIMER: str = "본 시뮬레이션은 참고용이며 실제 경제 상황과 다를 수 있습니다."

    def __repr__(self) -> str:
        lines = [f"[스트레스 테스트 — {self.scenarioLabel}]"]
        lines.append(f"  3년 후 매출 변화: {self.year3RevenueChange:+.1f}%")
        lines.append(f"  3년 후 마진 변화: {self.year3MarginChange:+.0f}bps")
        if self.year3DebtRatio is not None:
            lines.append(f"  3년 후 부채비율: {self.year3DebtRatio:.0f}%")
        if self.year3CurrentRatio is not None:
            lines.append(f"  3년 후 유동비율: {self.year3CurrentRatio:.0f}%")
        if self.year3InterestCoverage is not None:
            lines.append(f"  3년 후 이자보상배율: {self.year3InterestCoverage:.1f}x")
        lines.append(f"  생존 위험도: {self.survivalRisk}")
        lines.append(f"  배당 지속: {'가능' if self.dividendSustainable else '불가능'}")
        lines.append(f"  회복 전망: {self.recoveryTimeline}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


@dataclass
class BacktestResult:
    """시뮬레이션 백테스트 결과."""

    scenariosTested: int
    directionAccuracy: float
    avgError: float
    scenarioHitRate: float
    details: list[dict]
    warnings: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        lines = [f"[시뮬레이션 백테스트 ({self.scenariosTested}개 시나리오)]"]
        lines.append(f"  방향 정확도: {self.directionAccuracy:.0f}%")
        lines.append(f"  평균 오차: {self.avgError:.1f}%")
        lines.append(f"  시나리오 적중률: {self.scenarioHitRate:.0f}%")
        return "\n".join(lines)


__all__ = [
    "BacktestResult",
    "MonteCarloResult",
    "SimulationResult",
    "StressTestResult",
]
