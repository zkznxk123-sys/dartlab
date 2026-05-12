"""기업집계 매크로 지표 — scan finance.parquet 기반 bottom-up 집계.

순수 집계 함수. Polars DataFrame 입력 → 매크로 지표 출력.
core/ 계층 소속 — macro/corporate에서 소비.

Bloomberg/FactSet에서나 가능한 전종목 재무제표 → 매크로 지표 집계를
dartlab scan 데이터로 무료 제공.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

# ══════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════


@dataclass(frozen=True)
class EarningsCycleResult:
    """전종목 이익 사이클."""

    periods: list[str]
    totalOperatingIncome: list[float]  # 기간별 영업이익 합계
    yoyChanges: list[float | None]  # YoY 변화율 (%)
    currentDirection: str  # "expanding" | "stable" | "contracting"
    currentLabel: str
    companyCount: int
    description: str


@dataclass(frozen=True)
class PonziRatioResult:
    """Minsky Ponzi 비율 (ICR<1 기업 비중)."""

    periods: list[str]
    ratios: list[float]  # 기간별 ICR<1 비중 (0-1)
    currentRatio: float
    trend: str  # "rising" | "stable" | "falling"
    trendLabel: str  # "상승" | "안정" | "하락"
    description: str


@dataclass(frozen=True)
class LeverageCycleResult:
    """전종목 레버리지 사이클."""

    periods: list[str]
    medianDebtRatio: list[float]  # 기간별 부채비율 중간값 (%)
    currentLevel: float
    trend: str  # "rising" | "stable" | "falling"
    trendLabel: str
    description: str


# ══════════════════════════════════════
# 내부 헬퍼
# ══════════════════════════════════════

# ── scanBridge 경유 — DART/EDGAR 통일 ──

from dartlab.synth.scanBridge import (
    extractAnnualConsolidated as _extract_annual_consolidated,
)
from dartlab.synth.scanBridge import (
    medianRatioByYear as _median_ratio_bridge,
)
from dartlab.synth.scanBridge import (
    sumAccountByYear as _sum_account_bridge,
)

# ══════════════════════════════════════
# 공개 함수
# ══════════════════════════════════════


def aggregateEarningsCycle(financeDf: pl.DataFrame) -> EarningsCycleResult:
    """전종목 영업이익 합계 YoY → 이익 사이클.

    Args:
        financeDf: scan/finance.parquet 전체 DataFrame
    """
    annual = _extract_annual_consolidated(financeDf)
    result = _sum_account_bridge(annual, "영업이익")

    if len(result) < 2:
        return EarningsCycleResult([], [], [], "stable", "데이터부족", 0, "연간 영업이익 데이터 부족")

    periods = result.get_column("year").to_list()
    totals = result.get_column("total").to_list()
    counts = result.get_column("count").to_list()

    # YoY
    yoys: list[float | None] = [None]
    for i in range(1, len(totals)):
        if totals[i - 1] and abs(totals[i - 1]) > 0:
            yoys.append(round(((totals[i] - totals[i - 1]) / abs(totals[i - 1])) * 100, 1))
        else:
            yoys.append(None)

    # 방향
    last_yoy = yoys[-1]
    if last_yoy is not None and last_yoy > 5:
        direction, label = "expanding", "이익확장"
    elif last_yoy is not None and last_yoy < -5:
        direction, label = "contracting", "이익수축"
    else:
        direction, label = "stable", "안정"

    return EarningsCycleResult(
        periods=periods,
        totalOperatingIncome=[round(t / 1e8, 0) if t else 0 for t in totals],  # 억원 단위
        yoyChanges=yoys,
        currentDirection=direction,
        currentLabel=label,
        companyCount=counts[-1] if counts else 0,
        description=f"전종목 영업이익 {label} (YoY {last_yoy:+.1f}%, {counts[-1] if counts else 0}개사)"
        if last_yoy
        else "데이터 부족",
    )


def ponziRatio(financeDf: pl.DataFrame) -> PonziRatioResult:
    """ICR<1 기업 비중 추이 → Minsky Ponzi 비율.

    ICR(이자보상배율) = 영업이익 / 이자비용.
    ICR < 1 = 영업이익으로 이자도 못 갚는 기업.
    """
    from dartlab.synth.scanBridge import getAccountValue, isEdgarSchema

    annual = _extract_annual_consolidated(financeDf)

    # 연도 목록
    yearCol = "fy" if isEdgarSchema(annual) else "bsns_year"
    if yearCol not in annual.columns:
        return PonziRatioResult([], [], 0, "stable", "데이터부족", "이자비용 데이터 부족")

    years = sorted(annual[yearCol].unique().to_list())

    # 기간별 ICR<1 비중
    period_data: list[tuple[str, int, int]] = []
    for yr in years:
        op_map = getAccountValue(annual, "영업이익", year=yr)
        int_map = getAccountValue(annual, "이자비용", year=yr)
        common = set(op_map) & set(int_map)
        if not common:
            continue
        ponzi = sum(1 for c in common if int_map[c] != 0 and op_map[c] / abs(int_map[c]) < 1)
        period_data.append((yr, ponzi, len(common)))

    if not period_data:
        return PonziRatioResult([], [], 0, "stable", "데이터부족", "이자비용 데이터 부족")

    periods = [d[0] for d in period_data]
    ponzi_counts = [d[1] for d in period_data]
    totals = [d[2] for d in period_data]
    ratios = [round(p / t, 3) if t > 0 else 0 for p, t in zip(ponzi_counts, totals)]

    current = ratios[-1]
    if len(ratios) >= 2:
        if ratios[-1] > ratios[-2] + 0.02:
            trend, trendLabel = "rising", "상승"
        elif ratios[-1] < ratios[-2] - 0.02:
            trend, trendLabel = "falling", "하락"
        else:
            trend, trendLabel = "stable", "안정"
    else:
        trend, trendLabel = "stable", "안정"

    return PonziRatioResult(
        periods=periods,
        ratios=ratios,
        currentRatio=current,
        trend=trend,
        trendLabel=trendLabel,
        description=f"ICR<1 비중 {current:.1%} ({trendLabel}) — {ponzi_counts[-1]}/{totals[-1]}개사",
    )


def leverageCycle(financeDf: pl.DataFrame) -> LeverageCycleResult:
    """전종목 부채비율 중간값 추이."""
    annual = _extract_annual_consolidated(financeDf)
    result = _median_ratio_bridge(annual, "부채총계", "자본총계")

    if len(result) < 2:
        return LeverageCycleResult([], [], 0, "stable", "데이터부족", "부채비율 데이터 부족")

    periods = result.get_column("year").to_list()
    medians = [round(v, 1) if v is not None else 0 for v in result.get_column("median_ratio").to_list()]

    current = medians[-1]
    if len(medians) >= 2:
        if medians[-1] > medians[-2] + 2:
            trend, label = "rising", "상승"
        elif medians[-1] < medians[-2] - 2:
            trend, label = "falling", "하락"
        else:
            trend, label = "stable", "안정"
    else:
        trend, label = "stable", "안정"

    return LeverageCycleResult(
        periods=periods,
        medianDebtRatio=medians,
        currentLevel=current,
        trend=trend,
        trendLabel=label,
        description=f"전종목 부채비율 중간값 {current:.1f}% ({label})",
    )
