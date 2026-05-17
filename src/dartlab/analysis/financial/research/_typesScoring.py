"""Research 정량 스코어링 dataclasses — types.py 에서 분리.

Piotroski/MagicFormula/QMJ/Lynch/DuPont 스코어 + QuantScores 집계.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 정량 스코어링
# ══════════════════════════════════════


@dataclass
class PiotroskiScore:
    """Piotroski F-Score (0-9)."""

    total: int = 0
    components: dict[str, bool] = field(default_factory=dict)
    interpretation: str = ""  # "strong" | "moderate" | "weak"


@dataclass
class MagicFormulaScore:
    """Greenblatt Magic Formula."""

    roic: float | None = None
    earningsYield: float | None = None


@dataclass
class QmjScore:
    """AQR Quality Minus Junk (4-pillar)."""

    profitability: float | None = None
    growth: float | None = None
    safety: float | None = None
    payout: float | None = None
    composite: float | None = None


@dataclass
class LynchFairValue:
    """Peter Lynch Fair Value."""

    earningsGrowthRate: float | None = None  # 5Y EPS CAGR (%)
    fairValue: float | None = None  # growthRate * EPS
    currentPrice: float | None = None
    pegRatio: float | None = None
    signal: str | None = None  # "undervalued" | "fair" | "overvalued"


@dataclass
class DuPontResult:
    """DuPont 5-factor 분해."""

    netMargin: list[float | None] = field(default_factory=list)
    assetTurnover: list[float | None] = field(default_factory=list)
    equityMultiplier: list[float | None] = field(default_factory=list)
    roe: list[float | None] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)
    driver: str = ""  # "margin" | "turnover" | "leverage" | "balanced"
    # 5-factor 확장
    taxBurden: list[float | None] = field(default_factory=list)  # NI/EBT
    interestBurden: list[float | None] = field(default_factory=list)  # EBT/EBIT
    operatingMargin: list[float | None] = field(default_factory=list)  # EBIT/Sales
    roic: list[float | None] = field(default_factory=list)  # NOPAT/IC


@dataclass
class QuantScores:
    """정량 스코어링 프레임워크 종합."""

    piotroski: PiotroskiScore | None = None
    magicFormula: MagicFormulaScore | None = None
    qmj: QmjScore | None = None
    lynchFairValue: LynchFairValue | None = None
    buffettOwnerEarnings: float | None = None
    dupont: DuPontResult | None = None
