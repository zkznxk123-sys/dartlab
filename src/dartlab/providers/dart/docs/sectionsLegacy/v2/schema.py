"""sections artifact 공통 schema — DART/EDGAR provider 무관 분석 SSOT.

plan snazzy-wibbling-origami v4 PR-E10 — provider 분기 path 의 시작점.

분석 코드 (quant/industry/frame/scan) 는 본 13 컬럼만 사용해 DART/EDGAR 어느
쪽이든 동일 코드로 동작.

dtype 동결: polars 0.20+ Utf8 / Int32 / Int8. 변경 시 architecture 가드 실패
(test_sections_schema_parity.py).
"""

from __future__ import annotations

import polars as pl

# DART 와 EDGAR 가 동시 보존해야 하는 공통 본체 컬럼 (13 개).
PROVIDER_AGNOSTIC_COLS: tuple[tuple[str, pl.DataType], ...] = (
    ("topic", pl.Utf8),  # KR.businessOverview / US.item1Business namespace
    ("blockType", pl.Utf8),  # heading | text | table
    ("blockOrder", pl.Int32),  # DOM/XML 순서
    ("textLevel", pl.Int8),  # heading depth (1~7)
    ("textPath", pl.Utf8),  # "Item 8 > Note 1. Summary" (heading stack join)
    ("textSemanticPathKey", pl.Utf8),  # canonical cross-period 매칭 key (raw normalized)
    ("textComparablePathKey", pl.Utf8),  # (topic, leaf) — 약한 수평화 (legacy 호환)
    ("rowIdentityKey", pl.Utf8),  # 초강화 SSOT — (topic, parentNorm, leafNorm, anchorHash)
    ("anchorHash", pl.Int64),  # content anchor 단어 sorted xxhash64 (0 = anchor 없음)
    ("segmentKey", pl.Utf8),  # path-anchored cross-period invariant
    ("content_raw", pl.Utf8),  # raw XML/HTML 단편 (viewer SSOT, 모든 태그 보존)
    ("period", pl.Utf8),  # YYYYQn (annual=Q4 alias)
    ("rcept_no", pl.Utf8),  # filing identifier (DART rcept_no / EDGAR accession_no)
)

PROVIDER_AGNOSTIC_COL_NAMES: frozenset[str] = frozenset(name for name, _ in PROVIDER_AGNOSTIC_COLS)


def validateProviderAgnosticSchema(df: pl.DataFrame) -> list[str]:
    """sections DataFrame 의 schema 가 PROVIDER_AGNOSTIC_COLS 와 일치하는지 검증.

    Args:
        df: DART 또는 EDGAR sections artifact 의 단일 period DataFrame.

    Returns:
        violation 메시지 list. 빈 list = parity ✓.
    """
    actualCols = set(df.columns)
    violations: list[str] = []
    for name, dtype in PROVIDER_AGNOSTIC_COLS:
        if name not in actualCols:
            violations.append(f"missing column: {name} ({dtype})")
            continue
        actualDtype = df.schema[name]
        if actualDtype != dtype:
            violations.append(f"dtype mismatch: {name} expected {dtype} got {actualDtype}")
    return violations


__all__ = [
    "PROVIDER_AGNOSTIC_COLS",
    "PROVIDER_AGNOSTIC_COL_NAMES",
    "validateProviderAgnosticSchema",
]
