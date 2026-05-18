"""forecast 의 dataclass — ForecastResult/ScenarioResult/SensitivityResult."""

from __future__ import annotations

from dataclasses import dataclass, field

from dartlab.core.utils.fmt import fmtBig, fmtPrice


@dataclass
class ForecastResult:
    """시계열 예측 결과."""

    metric: str
    metricLabel: str
    historical: list[float | None]
    projected: list[float]
    horizon: int
    method: str
    confidence: str
    rSquared: float
    growthRate: float
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    currency: str = "KRW"

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        c = self.currency
        lines = [
            f"[{self.metricLabel} 예측 — {self.method}]",
            f"  신뢰도: {self.confidence}  (R²={self.rSquared:.2f})",
            f"  성장률: {self.growthRate:.1f}%",
        ]
        validHist = [v for v in self.historical if v is not None]
        if validHist:
            lines.append(f"  최근 실적: {fmtBig(validHist[-1], c)}")
        if self.projected:
            for i, p in enumerate(self.projected, 1):
                lines.append(f"  +{i}년 예측: {fmtBig(p, c)}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


@dataclass
class ScenarioResult:
    """시나리오 분석 결과."""

    base: dict[str, float]
    bull: dict[str, float]
    bear: dict[str, float]
    probability: dict[str, float]
    weightedValue: float | None
    currentPrice: float | None
    warnings: list[str] = field(default_factory=list)
    currency: str = "KRW"

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        c = self.currency
        lines = ["[시나리오 분석]"]
        for label, scenario, prob in [
            ("Bull", self.bull, self.probability.get("bull", 25)),
            ("Base", self.base, self.probability.get("base", 50)),
            ("Bear", self.bear, self.probability.get("bear", 25)),
        ]:
            growth = scenario.get("growth", 0)
            value = scenario.get("perShareValue", 0)
            lines.append(f"  {label} ({prob:.0f}%): 성장 {growth:+.1f}%, 적정가 {fmtPrice(value, c)}")
        if self.weightedValue is not None:
            lines.append(f"  확률가중 적정가: {fmtPrice(self.weightedValue, c)}")
        if self.currentPrice:
            lines.append(f"  현재가: {fmtPrice(self.currentPrice, c)}")
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


@dataclass
class SensitivityResult:
    """민감도 분석 결과."""

    waccValues: list[float]
    growthValues: list[float]
    matrix: list[list[float]]
    baseWacc: float
    baseGrowth: float
    baseValue: float

    DISCLAIMER: str = "본 분석은 투자 참고용이며 투자 권유가 아닙니다."

    def __repr__(self) -> str:
        lines = ["[민감도 분석 — WACC × 영구성장률]"]
        header = "WACC \\ g  " + "  ".join(f"{g:.1f}%" for g in self.growthValues)
        lines.append(f"  {header}")
        for i, wacc in enumerate(self.waccValues):
            row = f"  {wacc:.1f}%    " + "  ".join(
                f"{self.matrix[i][j] / 1e4:,.0f}만" if self.matrix[i][j] > 0 else "  N/A"
                for j in range(len(self.growthValues))
            )
            lines.append(row)
        lines.append(f"  ※ {self.DISCLAIMER}")
        return "\n".join(lines)


# ── 예측 메트릭 정의 ──────────────────────────────────────────

FORECAST_TARGETS: dict[str, tuple[str, str, str]] = {
    "revenue": ("IS", "sales", "매출"),
    "operating_income": ("IS", "operating_profit", "영업이익"),
    "net_income": ("IS", "net_profit", "순이익"),
    "operating_cashflow": ("CF", "operating_cashflow", "영업CF"),
}

_FALLBACKS: dict[str, list[str]] = {
    "sales": ["revenue"],
    "operating_profit": ["operating_income"],
    "net_profit": ["net_income"],
}


# ── 예측 엔진 ──────────────────────────────────────────────
