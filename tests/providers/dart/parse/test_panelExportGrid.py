"""panelExportGrid (공시 표 → export 격자 DIP impl) 순수 헬퍼 단위테스트.

Company 미로드(OOM 회피) — _selectRow(synthetic polars)·_gridToCells(synthetic 병합 격자)만.
realData panelTableGrid 는 별도 marker(미포함 — 본 파일은 unit 만).
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.core.panelTableAccessor import getPanelTableAccessor
from dartlab.providers.dart.parse.htmlTableParser import HtmlTableCell
from dartlab.providers.dart.parse.panelExportGrid import (
    _gridToCells,
    _latestPeriodWithContent,
    _selectRow,
)

pytestmark = pytest.mark.unit


def _wide() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "chapter": ["I.", "I.", "II."],
            "sectionLeaf": ["1.", "1.", "2."],
            "blockLeaf": ["", "", "tbl"],
            "leafType": ["table", "table", "table"],
            "leafSeq": [1, 0, 0],
            "2025Q4": ["<a>", "<b>", "<c>"],
            "2025Q3": [None, "<b3>", None],
        }
    )


def test_selectRow_filters_provided_fields() -> None:
    ids = {
        "chapter": "I.",
        "sectionLeaf": "1.",
        "blockLeaf": "",
        "leafType": "table",
        "disclosureKey": None,
        "scope": None,
        "leafSeq": 1,
    }
    row = _selectRow(_wide(), ids)
    assert row is not None
    assert row["2025Q4"] == "<a>"


def test_selectRow_leafSeq_disambiguates_to_first() -> None:
    # leafSeq 미지정(None) + 같은 섹션 2행 → leafSeq 오름차순 첫(0) 행.
    ids = {
        "chapter": "I.",
        "sectionLeaf": "1.",
        "blockLeaf": "",
        "leafType": "table",
        "disclosureKey": None,
        "scope": None,
        "leafSeq": None,
    }
    row = _selectRow(_wide(), ids)
    assert row is not None
    assert row["2025Q4"] == "<b>"  # leafSeq=0 행


def test_selectRow_no_match_returns_none() -> None:
    ids = {"chapter": "ZZZ", "sectionLeaf": "", "blockLeaf": "", "leafType": "table"}
    assert _selectRow(_wide(), ids) is None


def test_latestPeriodWithContent_skips_id_cols_and_empty() -> None:
    row = {"chapter": "I.", "leafSeq": 0, "2025Q4": "", "2025Q3": "<x>"}
    wide = pl.DataFrame({"chapter": ["I."], "leafSeq": [0], "2025Q4": [""], "2025Q3": ["<x>"]})
    assert _latestPeriodWithContent(wide, row) == "2025Q3"


def test_gridToCells_merge_anchor_span_and_coerce() -> None:
    # colspan=2 헤더(같은 인스턴스 2좌표) + 숫자/괄호음수 정합.
    header = HtmlTableCell(text="구분", colspan=2, rowspan=1, isHeader=True)
    num = HtmlTableCell(text="1,234", align="right")
    neg = HtmlTableCell(text="(5)")
    grid = [[header, header], [num, neg]]
    cells = _gridToCells(grid)
    byval = {c.value: c for c in cells}
    assert byval["구분"].colspan == 2 and byval["구분"].rowspan == 1 and byval["구분"].isHeader
    assert 1234 in byval  # 숫자 정합
    assert byval[1234].align == "right"
    assert -5 in byval  # 괄호 음수 정합
    assert byval["구분"].row == 0 and byval["구분"].col == 0  # 앵커 top-left


def test_accessor_registered() -> None:
    acc = getPanelTableAccessor()
    assert acc is not None
    assert hasattr(acc, "panelTableGrid")
