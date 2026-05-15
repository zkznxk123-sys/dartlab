"""DART reprt_code 매핑 + 기간 선택 helper.

11013 = Q1 (1Q)        — quarterly
11012 = HY (반기)      — quarterly (반기 = 누적 H1)
11014 = Q3 (3Q 누적)   — quarterly
11011 = FY (사업보고서) — annual
"""

from __future__ import annotations

from typing import Literal

import polars as pl

REPRT_CODE_MAP: dict[str, tuple[str, str]] = {
    "11013": ("Q1", "quarterly"),
    "11012": ("HY", "halfYear"),
    "11014": ("Q3", "quarterly"),
    "11011": ("FY", "annual"),
}


def resolvePeriods(df: pl.DataFrame, mode: Literal["annual", "quarterly"]) -> list[str]:
    """가용 기간 정렬 (오래된 → 최신).

    Args:
        df: rawNormalize.normalize 출력.
        mode: annual → periodKind=='Y' (FY), quarterly → 모든 분기 (Q1/HY/Q3/FY).
    """
    if df is None or df.height == 0:
        return []
    if mode == "annual":
        sub = df.filter(pl.col("periodKind") == "Y")
    else:
        sub = df
    return sorted(sub["period"].unique().to_list(), key=_periodSortKey)


def lastNPeriods(df: pl.DataFrame, n: int, mode: Literal["annual", "quarterly"]) -> list[str]:
    """최근 N 기간."""
    periods = resolvePeriods(df, mode)
    return periods[-n:] if n > 0 else periods


def _periodSortKey(p: str) -> tuple[int, int]:
    """2024-Q3 → (2024, 3), 2024-FY → (2024, 4)."""
    year, tag = p.split("-", 1)
    order = {"Q1": 1, "HY": 2, "Q3": 3, "FY": 4}.get(tag, 0)
    return (int(year), order)
