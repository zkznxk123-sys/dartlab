"""기간 헬퍼. periodKind 인코딩 1종: annual | quarterly.

period 라벨 형식:
- annual: YYYY-FY
- quarterly: YYYY-Q1 / YYYY-HY / YYYY-Q3 / YYYY-FY
정렬 키: (year, tag_order) — Q1=1, HY=2, Q3=3, FY=4.
"""

from __future__ import annotations

import polars as pl

from dartlab.viz.display.finance.schema import PeriodKind

_TAG_ORDER = {"Q1": 1, "HY": 2, "Q3": 3, "FY": 4}


def _sortKey(period: str) -> tuple[int, int]:
    """2024-Q3 → (2024, 3), 2024-FY → (2024, 4)."""
    year, tag = period.split("-", 1)
    return (int(year), _TAG_ORDER.get(tag, 0))


def resolvePeriods(norm: pl.DataFrame, periodKind: PeriodKind) -> list[str]:
    """가용 기간 정렬 (오래된 → 최신)."""
    if norm is None or norm.height == 0:
        return []
    if periodKind == "annual":
        sub = norm.filter(pl.col("periodKind") == "annual")
    else:
        sub = norm
    return sorted(sub["period"].unique().to_list(), key=_sortKey)


def lastNPeriods(norm: pl.DataFrame, n: int, periodKind: PeriodKind) -> list[str]:
    """최근 N 기간."""
    periods = resolvePeriods(norm, periodKind)
    return periods[-n:] if n > 0 else periods
