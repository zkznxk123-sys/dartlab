"""EDGAR panel builder mirror — sectionsToPanel 16-col 계약 + remap 규칙 (데이터 0).

``providers/edgar/panel/build/builder.py`` 의 순수 remap 검증. in-memory 합성 sections long 으로
PANEL_SCHEMA 16-col 적합·content fallback·leafType 매핑·rowIdentity 안정·narrative(null key) 계약.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _syntheticSections() -> pl.DataFrame:
    """2 period(10-K 2개 기간) × 다 row 합성 sections long (gather 산출 형태)."""
    return pl.DataFrame(
        {
            "topic": [
                "10-K::item1Business",
                "10-K::item1ARiskFactors",
                "10-K::item8FinancialStatements",
                "10-K::item1Business",  # 다음 기간 동일 item (수평화 키 안정 검증)
            ],
            "blockType": ["text", "heading", "table", "text"],
            "blockOrder": [0, 1, 2, 0],
            "source_title": ["Item 1. Business", "Item 1A. Risk Factors", "Financial Statements", "Item 1. Business"],
            "content_raw": ["<p>biz</p>", "", "<table>x</table>", "<p>biz2</p>"],
            "content_plain": ["biz", "risk plain", "x", "biz2"],
            "period": ["2024Q4", "2024Q4", "2024Q4", "2023Q4"],
            "ticker": ["aapl", "aapl", "aapl", "aapl"],
            "accession_no": ["0000320193-24-1", "0000320193-24-1", "0000320193-24-1", "0000320193-23-9"],
            "form_type": ["10-K", "10-K", "10-K", "10-K"],
        }
    )


def test_sections_to_panel_16_col_contract() -> None:
    """출력 컬럼·dtype == PANEL_SCHEMA (cross-market 16-col 계약)."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    assert list(out.columns) == list(PANEL_SCHEMA.keys()), "16-col 키·순서 불일치"
    assert out.schema == PANEL_SCHEMA, f"dtype 불일치: {out.schema}"
    assert out.height == 4


def test_sections_to_panel_empty_input() -> None:
    """빈/None 입력 → 빈 16-col DataFrame (예외 없음)."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(pl.DataFrame())
    assert out.is_empty()
    assert list(out.columns) == list(PANEL_SCHEMA.keys())


def test_remap_columns() -> None:
    """chapter=form · sectionLeaf=itemId · sectionPath=topic · corp=ticker upper · rceptNo=accession."""
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    r0 = out.row(0, named=True)
    assert r0["chapter"] == "10-K"
    assert r0["sectionLeaf"] == "item1Business"
    assert r0["sectionPath"] == "10-K::item1Business"
    assert r0["blockLeaf"] == "Item 1. Business"
    assert r0["corp"] == "AAPL"  # ticker upper
    assert r0["rceptNo"] == "0000320193-24-1"
    assert r0["period"] == "2024Q4"


def test_leaf_type_mapping() -> None:
    """blockType heading→text, table→table, text→text (PANEL_SCHEMA 2값)."""
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    leaf = out["leafType"].to_list()
    assert leaf == ["text", "text", "table", "text"], leaf  # heading(idx1)→text
    assert set(out["leafType"].unique()) <= {"text", "table"}


def test_content_raw_fallback_to_plain() -> None:
    """content_raw 빈 셀(OOM 가드) → content_plain fallback (보드 본문 보유)."""
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    # idx1 의 content_raw="" → content_plain "risk plain" 으로 채워짐
    assert out["contentRaw"][1] == "risk plain"
    assert out["contentRaw"][0] == "<p>biz</p>"  # 정상 raw 보존


def test_narrative_null_keys() -> None:
    """section 블록은 narrative — disclosureKey/xbrlClass 전부 null, xbrlMatched False."""
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    assert out["disclosureKey"].null_count() == out.height
    assert out["xbrlClass"].null_count() == out.height
    assert out["xbrlMatched"].to_list() == [False] * out.height


def test_row_identity_stable_across_periods() -> None:
    """같은 (form, itemId) 는 기간 가로질러 같은 rowIdentity (수평화 키 안정)."""
    from dartlab.providers.dart.panel.mapper import rowIdentity
    from dartlab.providers.edgar.panel.build.builder import sectionsToPanel

    out = sectionsToPanel(_syntheticSections())
    # idx0(2024Q4)·idx3(2023Q4) 둘 다 item1Business → 같은 NARR rowIdentity
    id0 = rowIdentity(out["disclosureKey"][0], out["chapter"][0], out["sectionLeaf"][0])
    id3 = rowIdentity(out["disclosureKey"][3], out["chapter"][3], out["sectionLeaf"][3])
    assert id0 == id3, f"수평화 키 불안정: {id0} != {id3}"
    assert id0.startswith("NARR::")  # narrative 키
