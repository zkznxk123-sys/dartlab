"""EDGAR tableHorizontalizer HTML native parse 가드 — PR-E8 plan delegated-prancing-tower.

본 PR-E8 단독 검증:
- ``parseHtmlTable`` 가 ``<table>`` 의 cell 그리드 (rowspan/colspan expansion) 정확
- rowspan/colspan native 인식 — markdown 변환 lossy 회복
- ``parseHtmlTables`` 가 multiple table 순서 보존
- HTML 부재 / table 부재 / out-of-range index → None / 빈 list
"""

from __future__ import annotations

from dartlab.providers.edgar.parse.tableHorizontalizer import (
    parseHtmlTable,
    parseHtmlTables,
)


def test_parse_simple_table() -> None:
    """단순 2x2 표."""
    html = "<table><tr><td>a</td><td>b</td></tr><tr><td>1</td><td>2</td></tr></table>"
    df = parseHtmlTable(html)
    assert df is not None
    assert df.shape == (2, 2)
    assert df.row(0) == ("a", "b")
    assert df.row(1) == ("1", "2")


def test_parse_rowspan_expansion() -> None:
    """rowspan=2 cell 이 두 row 에 걸쳐 그리드 채움."""
    html = """
    <table>
      <tr><td rowspan="2">A</td><td>B</td></tr>
      <tr><td>C</td></tr>
    </table>
    """
    df = parseHtmlTable(html)
    assert df is not None
    assert df.shape == (2, 2)
    # row 0: A | B
    assert df.row(0) == ("A", "B")
    # row 1: A (rowspan) | C
    assert df.row(1) == ("A", "C")


def test_parse_colspan_expansion() -> None:
    """colspan=3 cell 이 같은 row 3 컬럼 채움."""
    html = """
    <table>
      <tr><td colspan="3">Header</td></tr>
      <tr><td>x</td><td>y</td><td>z</td></tr>
    </table>
    """
    df = parseHtmlTable(html)
    assert df is not None
    assert df.shape == (2, 3)
    assert df.row(0) == ("Header", "Header", "Header")
    assert df.row(1) == ("x", "y", "z")


def test_parse_align_text_extracted() -> None:
    """ALIGN 속성 있는 cell 의 text 정상 추출 (속성 무시는 의도된 단순화)."""
    html = '<table><tr><td align="right">100</td><td align="left">a</td></tr></table>'
    df = parseHtmlTable(html)
    assert df is not None
    assert df.row(0) == ("100", "a")


def test_parse_empty_html_returns_none() -> None:
    assert parseHtmlTable("") is None
    assert parseHtmlTable("<p>no table</p>") is None
    assert parseHtmlTable(None) is None  # type: ignore[arg-type]


def test_parse_out_of_range_index() -> None:
    html = "<table><tr><td>x</td></tr></table>"
    assert parseHtmlTable(html, tableIndex=5) is None


def test_parse_multiple_tables_order() -> None:
    html = """
    <div>
      <table><tr><td>first</td></tr></table>
      <p>between</p>
      <table><tr><td>second</td></tr></table>
    </div>
    """
    tables = parseHtmlTables(html)
    assert len(tables) == 2
    assert tables[0].row(0) == ("first",)
    assert tables[1].row(0) == ("second",)


def test_parse_tables_empty_html() -> None:
    assert parseHtmlTables("") == []
    assert parseHtmlTables("<p>nothing</p>") == []


def test_parse_mixed_rowspan_colspan() -> None:
    """rowspan + colspan 결합."""
    html = """
    <table>
      <tr><td rowspan="2" colspan="2">Block</td><td>X</td></tr>
      <tr><td>Y</td></tr>
      <tr><td>1</td><td>2</td><td>3</td></tr>
    </table>
    """
    df = parseHtmlTable(html)
    assert df is not None
    assert df.shape == (3, 3)
    # row 0: Block | Block | X
    assert df.row(0) == ("Block", "Block", "X")
    # row 1: Block | Block | Y
    assert df.row(1) == ("Block", "Block", "Y")
    # row 2: 1 | 2 | 3
    assert df.row(2) == ("1", "2", "3")
