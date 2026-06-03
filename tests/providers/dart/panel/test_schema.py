"""panel schema mirror — PANEL_SCHEMA 16-col 계약 + PIVOT_INDEX (데이터 0).

``providers/dart/panel/schema.py`` 의 16-col 동결 계약을 검증. 컬럼 수·핵심 컬럼·PIVOT_INDEX
멤버가 cross-market 계약대로인지 (build write·read pivot 양쪽이 본 schema 만 의존).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_panel_schema_16_col_contract() -> None:
    """PANEL_SCHEMA 는 16-col 동결 — 핵심 컬럼 존재 + 타입 (+sectionPath, +contentSig)."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA

    assert len(PANEL_SCHEMA) == 16, f"16-col 동결 위반: {len(PANEL_SCHEMA)}"
    for col in ("chapter", "sectionLeaf", "blockLeaf", "xbrlClass", "contentRaw", "period", "corp", "disclosureKey"):
        assert col in PANEL_SCHEMA, f"필수 컬럼 부재: {col}"
    # contentRaw = 단일 본문 컬럼 (content_plain/stripped 표시파생 금지 — R4).
    assert PANEL_SCHEMA["contentRaw"] == pl.Utf8
    assert "content_plain" not in PANEL_SCHEMA
    assert "scope" not in PANEL_SCHEMA  # scope 는 read 파생 (저장 안 함).
    assert "leafType" not in PANEL_SCHEMA  # leafType 도 read 파생 (contentRaw TABLE 마커).
    # 신규: sectionPath(lost-by-flatten 계층 truth, bake) + contentSig(내용 SimHash 정렬 앵커, bake).
    assert PANEL_SCHEMA["sectionPath"] == pl.Utf8
    assert PANEL_SCHEMA["contentSig"] == pl.UInt64


def test_pivot_index_members() -> None:
    """PIVOT_INDEX = 회사내 다기간 + 회사간 정렬 키 (scope 포함, xbrlClass 제외)."""
    from dartlab.providers.dart.panel.schema import PIVOT_INDEX

    assert "disclosureKey" in PIVOT_INDEX
    assert "scope" in PIVOT_INDEX  # read 파생 — era drift 흡수.
    assert "xbrlClass" not in PIVOT_INDEX  # era drift 로 행 쪼개짐 → 제외.
