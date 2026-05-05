"""DataEntry — raw 카테고리 진입점 (Cut 8 분할).

단일 진실의 원천은 list 자체. 로직은 ``core/registry.py``.
"""

from __future__ import annotations

from dartlab.core.registry import ColumnMeta, DataEntry  # noqa: F401

_RAW_ENTRIES: list[DataEntry] = [
    # raw — 원본 parquet
    # ═══════════════════════════════════════════════════════
    DataEntry(
        name="rawDocs",
        label="공시 원본",
        category="raw",
        dataType="dataframe",
        description="공시 문서 원본 parquet. 가공 전 전체 테이블과 텍스트.",
        requires="docs",
    ),
    DataEntry(
        name="rawFinance",
        label="XBRL 원본",
        category="raw",
        dataType="dataframe",
        description="XBRL 재무제표 원본 parquet. 매핑/정규화 전 원본 데이터.",
        requires="finance",
    ),
    DataEntry(
        name="rawReport",
        label="보고서 원본",
        category="raw",
        dataType="dataframe",
        description="정기보고서 API 원본 parquet. 파싱 전 원본 데이터.",
        requires="report",
    ),
    # ═══════════════════════════════════════════════════════
]
