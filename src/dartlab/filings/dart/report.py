"""RUNTIME report shaping — DART OpenAPI 정기보고서 parquet → apiType 별 표.

facade show 의 report 분기. report parquet (apiType keyed, 172 col 광역) 을
apiType 로 필터 + all-null 컬럼 제거 → 해당 항목의 유의 컬럼만 노출.

LLM Specifications:
    AntiPatterns:
        - 172 컬럼 통째 반환 금지 — apiType 무관 all-null 컬럼 제거.
        - 옛 providers report 파서 import 금지 — parquet 직접.
    OutputSchema:
        - ``reportTopic(code, apiType) -> pl.DataFrame | None``.
    Prerequisites:
        - data/dart/report/{code}.parquet.
    TargetMarkets:
        - KR (DART OpenAPI).
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.filings.dart import config

_log = logging.getLogger(__name__)

# apiType 무관 광역 컬럼 (provenance) — 유지.
_KEEP_META = ("apiType", "apiName", "year", "quarter", "rcept_no")


def reportTopic(code: str, apiType: str, *, period: str | None = None) -> pl.DataFrame | None:
    """report apiType 표 — 해당 apiType 행 + 유의(non-null) 컬럼만.

    Args:
        code: 종목코드.
        apiType: DART apiType (dividend/executive/employee/…).
        period: year 필터 (예: "2024"). None = 전체.

    Returns:
        DataFrame (해당 apiType 의 의미 컬럼만) 또는 None.
    """
    p = config.reportPath(code)
    if not p.exists():
        return None
    try:
        lf = pl.scan_parquet(str(p)).filter(pl.col("apiType") == apiType)
        if period:
            lf = lf.filter(pl.col("year") == period)
        df = lf.collect()
    except (pl.exceptions.PolarsError, OSError) as exc:
        _log.warning("report read 실패 %s %s: %s", code, apiType, exc)
        return None
    if df.is_empty():
        return None
    # all-null 컬럼 제거 (해당 apiType 가 안 쓰는 광역 컬럼 정리).
    keep = [c for c in df.columns if c in _KEEP_META or df[c].null_count() < df.height]
    return df.select(keep)
