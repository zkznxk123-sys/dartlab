"""htmlTableParser — HTML <table> native parsing 회귀 가드.

plan snazzy-wibbling-origami PR-5c. content_table_struct 컬럼 (PR-5b) 의 HTML 표를
finance pipeline 입력으로 변환. ALIGN/colspan/rowspan 모두 보존.
"""

from __future__ import annotations

import pytest

from dartlab.providers.dart.parse.htmlTableParser import (
    HtmlTable,
    HtmlTableCell,
    cellGrid,
    extractItemValuePairs,
    parseHtmlTable,
)

pytestmark = [pytest.mark.unit]


def test_parse_basic_table():
    html = '<table><tr><th>구분</th><th>금액</th></tr><tr><td>매출</td><td align="right">100</td></tr></table>'
    parsed = parseHtmlTable(html)
    assert parsed is not None
    assert len(parsed.rows) == 2
    assert parsed.headerRowCount == 1
    assert parsed.rows[0].cells[0].isHeader is True
    assert parsed.rows[1].cells[1].align == "right"
    assert parsed.rows[1].cells[1].text == "100"


def test_parse_returns_none_for_empty():
    assert parseHtmlTable("") is None
    assert parseHtmlTable("no table here") is None
    assert parseHtmlTable("<table></table>") is None


def test_parse_handles_malformed_html():
    # 따옴표 누락 등 lxml recover 모드 처리
    html = "<table><tr><td align=right>val</td></tr></table>"
    parsed = parseHtmlTable(html)
    assert parsed is not None
    assert parsed.rows[0].cells[0].align == "right"


def test_parse_preserves_colspan_rowspan():
    html = '<table><tr><td colspan="2" rowspan="3">병합</td></tr></table>'
    parsed = parseHtmlTable(html)
    assert parsed is not None
    assert parsed.rows[0].cells[0].colspan == 2
    assert parsed.rows[0].cells[0].rowspan == 3
    assert parsed.maxCols == 2


def test_parse_multi_row_header():
    # 첫 2 row 가 th, 3 번째부터 td
    html = (
        "<table>"
        "<tr><th>2024</th><th>2025</th></tr>"
        "<tr><th>Q4</th><th>Q1</th></tr>"
        "<tr><td>100</td><td>110</td></tr>"
        "</table>"
    )
    parsed = parseHtmlTable(html)
    assert parsed is not None
    assert parsed.headerRowCount == 2


def test_extract_item_value_pairs():
    html = (
        "<table>"
        "<tr><th>구분</th><th>금액</th></tr>"
        '<tr><td>매출</td><td align="right">100</td></tr>'
        '<tr><td>영업이익</td><td align="right">20</td></tr>'
        "</table>"
    )
    pairs = extractItemValuePairs(html)
    assert pairs == {"매출": "100", "영업이익": "20"}


def test_extract_item_value_pairs_skip_header():
    # header (th) row 는 자동 skip
    html = "<table><tr><th>A</th><th>B</th></tr><tr><td>X</td><td>1</td></tr></table>"
    pairs = extractItemValuePairs(html)
    assert "A" not in pairs
    assert pairs == {"X": "1"}


def test_extract_empty_html():
    assert extractItemValuePairs("") == {}
    assert extractItemValuePairs("not a table") == {}


def test_cell_grid_basic():
    html = "<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>"
    grid = cellGrid(html)
    assert len(grid) == 2
    assert len(grid[0]) == 2
    assert grid[0][0].text == "A"
    assert grid[1][1].text == "D"


def test_cell_grid_colspan_expands():
    html = '<table><tr><td colspan="3">병합</td></tr><tr><td>A</td><td>B</td><td>C</td></tr></table>'
    grid = cellGrid(html)
    assert len(grid[0]) == 3
    # 같은 cell instance 가 3 col 차지
    assert grid[0][0] is grid[0][1] is grid[0][2]
    assert grid[0][0].text == "병합"


def test_cell_grid_rowspan_carries():
    html = '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'
    grid = cellGrid(html)
    assert len(grid) == 2
    # row 0: A, B
    # row 1: A (rowspan carry), C
    assert grid[1][0].text == "A"
    assert grid[1][1].text == "C"
    assert grid[0][0] is grid[1][0]  # same instance


def test_cell_grid_empty_on_invalid():
    assert cellGrid("") == []
    assert cellGrid("no table") == []
