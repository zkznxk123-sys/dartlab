"""sections artifact 의 content_plain / content_table_struct 컬럼 회귀 가드.

plan snazzy-wibbling-origami PR-5a/b. D.1 분석 모듈 (sentiment/risk/search 등) 의 plain
text 입력 + D.2 finance pipeline 의 HTML 표 구조 입력 분리 SSOT.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.docs.sectionsLegacy.sectionsBuilder import _extractTableStruct, wideToLong

pytestmark = [pytest.mark.unit]


def test_extract_table_struct_basic():
    mixed = '## 헤딩\n본문 문단\n<table><tr><td align="right">100</td></tr></table>\n표 다음 본문'
    assert _extractTableStruct(mixed) == '<table><tr><td align="right">100</td></tr></table>'


def test_extract_table_struct_empty_when_no_table():
    assert _extractTableStruct("## 헤딩\n본문만") == ""
    assert _extractTableStruct("") == ""
    assert _extractTableStruct("plain text") == ""


def test_extract_table_struct_multi_tables_joined():
    multi = "<table><tr><td>A</td></tr></table>\n중간\n<table><tr><td>B</td></tr></table>"
    result = _extractTableStruct(multi)
    assert "<table><tr><td>A</td></tr></table>" in result
    assert "<table><tr><td>B</td></tr></table>" in result


def test_extract_table_struct_preserves_attributes():
    # rowspan/colspan/align/valign 모두 보존
    xml = '<table><tr><td colspan="2" align="right" rowspan="3" valign="middle">N</td></tr></table>'
    assert _extractTableStruct(xml) == xml


def test_wide_to_long_includes_both_aux_columns():
    wide = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["table"],
            "blockOrder": [0],
            "2025": ['<table><tr><td align="right">100</td></tr></table>'],
        }
    )
    long = wideToLong(wide)
    assert {"content", "content_plain", "content_table_struct"}.issubset(set(long.columns))


def test_wide_to_long_addTableStruct_opt_out():
    wide = pl.DataFrame({"topic": ["A"], "blockType": ["t"], "blockOrder": [0], "2025": ["x"]})
    long = wideToLong(wide, addTableStruct=False)
    assert "content_table_struct" not in long.columns


def test_wide_to_long_addPlain_opt_out():
    wide = pl.DataFrame({"topic": ["A"], "blockType": ["t"], "blockOrder": [0], "2025": ["x"]})
    long = wideToLong(wide, addPlain=False)
    assert "content_plain" not in long.columns


def test_content_plain_strips_html_tags():
    wide = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["table"],
            "blockOrder": [0],
            "2025": ['<table><tr><td align="right">100</td></tr></table>'],
        }
    )
    long = wideToLong(wide)
    plain = long["content_plain"][0]
    assert "<table" not in plain
    assert "<td" not in plain
    assert "100" in plain


def test_text_only_row_has_empty_table_struct():
    wide = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["text"],
            "blockOrder": [0],
            "2025": ["## 헤딩\n본문만"],
        }
    )
    long = wideToLong(wide)
    assert long["content_table_struct"][0] == ""
