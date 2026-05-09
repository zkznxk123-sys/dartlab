"""Industry lifecycle clock — Vernon 3-phase + 쇠퇴 classification.

L2 분석엔진 시간축 (과거 phase 시계열 → 현재 phase → 미래 전이 신호).

학술 기반:
- Vernon (1966) "International investment and international trade in the product cycle":
  introduction → growth → maturity 3 phase.
- Gort & Klepper (1982) "Time paths in the diffusion of product innovations":
  5-phase 변형 (도입·성장·shakeout·성숙·쇠퇴) — dartlab 은 3+1 (쇠퇴) 형식 채택.

분류 룰 (산업 매출 YoY 기준):
- 도입 (introduction): yoy >= 30% — 강한 성장기 + 시장 형성
- 성장 (growth): 10% <= yoy < 30% — 안정 확장
- 성숙 (maturity): 0% <= yoy < 10% — 둔화 + 안정
- 쇠퇴 (decline): yoy < 0% — 매출 축소

Confidence 는 advisory — 단일 YoY 기반 분류는 점예측이 아니라 phase trend 신호.
backtest SSOT 는 quant.walkForward — lifecycle 은 phase 라벨링만 담당, 백테스트 X.
"""

from __future__ import annotations

import math

import polars as pl

# (introduction, growth, maturity) 임계 — 그 아래는 쇠퇴.
_PHASE_THRESHOLDS = {
    "introduction": 30.0,  # %
    "growth": 10.0,
    "maturity": 0.0,
}


def classifyPhase(yoyGrowthPct: float | None) -> str:
    """단일 YoY 성장률 → Vernon 3+쇠퇴 phase 라벨.

    None / NaN 입력 시 'unknown' (첫 해 — yoy 계산 불가).
    """
    if yoyGrowthPct is None:
        return "unknown"
    if isinstance(yoyGrowthPct, float) and math.isnan(yoyGrowthPct):
        return "unknown"
    if yoyGrowthPct >= _PHASE_THRESHOLDS["introduction"]:
        return "도입"
    if yoyGrowthPct >= _PHASE_THRESHOLDS["growth"]:
        return "성장"
    if yoyGrowthPct >= _PHASE_THRESHOLDS["maturity"]:
        return "성숙"
    return "쇠퇴"


def classifyLifecycle(
    industryId: str,
    *,
    years: list[str] | None = None,
) -> pl.DataFrame:
    """산업 라이프사이클 시계열 — 연도별 phase + YoY 성장 + 기업수.

    Parameters
    ----------
    industryId : str
        산업 ID (예: ``"semiconductor"``).
    years : list[str] | None
        분석 대상 연도 list. None 이면 buildTimelineSummary 기본 (최근 5 년).

    Returns
    -------
    pl.DataFrame
        columns:
            연도 : str — 회계연도 (YYYY)
            매출(조) : float — 산업 전체 매출 합계 (조원)
            기업수 : int — 해당 연도 매출 보고 기업 수
            yoy성장률 : float — 전년 대비 매출 성장률 (%, 첫 해 null)
            phase : str — 도입 / 성장 / 성숙 / 쇠퇴 / unknown
        industryId 미존재 또는 데이터 부족 시 빈 DataFrame.

    Notes
    -----
    backtest SSOT 는 ``dartlab.quant.walkForward`` — 본 함수는 phase 라벨링만 담당.
    forecast 신뢰도 = advisory (학술 모델 기반 회고 분류, 점예측 X).
    """
    from dartlab.industry.build.financials import buildTimelineSummary
    from dartlab.industry.build.pipeline import loadNodes

    nodes = loadNodes()
    timeline = buildTimelineSummary(nodes, industryId, years=years)
    if timeline.height == 0:
        return pl.DataFrame(
            schema={
                "연도": pl.Utf8,
                "매출(조)": pl.Float64,
                "기업수": pl.Int64,
                "yoy성장률": pl.Float64,
                "phase": pl.Utf8,
            }
        )

    annual = (
        timeline.group_by("연도")
        .agg(
            pl.col("매출(조)").sum().alias("매출(조)"),
            pl.col("기업수").sum().alias("기업수"),
        )
        .sort("연도")
        .with_columns(((pl.col("매출(조)") / pl.col("매출(조)").shift(1) - 1.0) * 100.0).alias("yoy성장률"))
    )

    return annual.with_columns(pl.col("yoy성장률").map_elements(classifyPhase, return_dtype=pl.Utf8).alias("phase"))
