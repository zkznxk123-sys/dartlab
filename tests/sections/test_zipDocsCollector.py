"""ZipDocsCollector.rebuildFromZips 검증 — offline streaming 빌더 정공법.

회귀 보장:
- parseSectionsByTitle nested <TABLE><P> 중복 차단 (zipDocsXml.py 수정)
- _tableToMarkdown nested TABLE TR/cell .// xpath 중복 차단
- splitLargeContent + pa.string() schema 호환 (cell > 1MB row 분할)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from pathlib import Path

import polars as pl

from dartlab.providers.dart.openapi.zipDocsXml import (
    MAX_CELL_BYTES,
    parseSectionsByTitle,
    splitLargeContent,
)


def test_splitLargeContent_below_threshold_returns_single():
    assert splitLargeContent("hello", maxBytes=100) == ["hello"]


def test_splitLargeContent_paragraph_boundary():
    text = "a" * 600 + "\n\n" + "b" * 600
    parts = splitLargeContent(text, maxBytes=1000)
    assert len(parts) == 2
    assert all(len(p) <= 1000 for p in parts)


def test_splitLargeContent_line_fallback():
    # 한 paragraph 자체 maxBytes 초과 → line 단위 분할
    text = ("a" * 500 + "\n") * 4
    parts = splitLargeContent(text, maxBytes=1000)
    assert all(len(p) <= 1000 for p in parts)
    assert "".join(parts).replace("\n", "").count("a") == 2000


def test_parseSectionsByTitle_no_nested_duplication():
    # nested TABLE 안 P/SPAN 이 외부 leaf 로 다시 처리되면 안 됨
    xml = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT>
<BODY>
<TITLE ATOC="Y" ATOCID="1" AASSOCNOTE="D-0-1-0">테스트 섹션</TITLE>
<P>외부 P 본문</P>
<TABLE>
<TR><TD><P>내부 P (중복되면 안 됨)</P></TD><TD>cell2</TD></TR>
</TABLE>
</BODY>
</DOCUMENT>
"""
    rows = parseSectionsByTitle(xml)
    assert len(rows) == 1
    content = rows[0]["content"]
    # "내부 P" 는 markdown table cell 안에만 (외부 P 로 중복 X)
    assert content.count("내부 P") == 1
    assert "외부 P 본문" in content
    assert rows[0]["atocid"] == "1"
    assert rows[0]["assocnote"] == "D-0-1-0"


def test_parseSectionsByTitle_nested_table_no_explosion():
    # nested TABLE 의 TR 이 외부 _tableToMarkdown 의 .//TR 로 캡쳐되어 폭증하던 회귀
    inner_rows = "".join(f"<TR><TD>inner-{i}</TD></TR>" for i in range(50))
    xml = f"""<?xml version="1.0"?>
<DOCUMENT><BODY>
<TITLE>중첩 표</TITLE>
<TABLE>
<TR><TD>outer cell <TABLE>{inner_rows}</TABLE></TD></TR>
<TR><TD>outer row 2</TD></TR>
</TABLE>
</BODY></DOCUMENT>
"""
    rows = parseSectionsByTitle(xml)
    assert len(rows) == 1
    content = rows[0]["content"]
    # outer markdown table 만 2 row (3 lines: header + sep + 2 data). nested TR 50개가
    # 외부 row 로 폭증하지 않아야.
    md_lines = [ln for ln in content.split("\n") if ln.startswith("|")]
    # outer TABLE 2 row (TR1 + TR2) → markdown 3 lines (header=TR1 + sep + TR2).
    # nested TABLE 50 TR 가 외부 row 로 폭증하면 52 lines.
    assert len(md_lines) == 3
    assert content.count("inner-") == 50  # nested cell text 는 outer cell 안 inline


def test_parseSectionsByTitle_span_bold_markdown_heading():
    xml = """<?xml version="1.0"?>
<DOCUMENT><BODY>
<TITLE>섹션</TITLE>
<SPAN USERMARK="F-14 B">가. 첫번째 항목</SPAN>
<P>본문 내용</P>
</BODY></DOCUMENT>
"""
    rows = parseSectionsByTitle(xml)
    assert len(rows) == 1
    assert "## 가. 첫번째 항목" in rows[0]["content"]
    assert "본문 내용" in rows[0]["content"]


@pytest.mark.skipif(
    not Path("data/dart/original/docs/005930").exists(),
    reason="local zip cache required",
)
def test_rebuildFromZips_005930_smoke(tmp_path):
    from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

    collector = ZipDocsCollector("005930", corpCode="00126380", corpName="삼성전자")
    out = tmp_path / "005930.parquet"
    written = collector.rebuildFromZips(outPath=out)
    assert written > 0
    df = pl.read_parquet(out)
    assert df.shape[0] == written
    assert {"atocid", "assocnote"}.issubset(df.columns)
    # cell split 검증 — 모든 row 의 section_content < MAX_CELL_BYTES
    max_len = df["section_content"].str.len_chars().max()
    assert max_len <= MAX_CELL_BYTES
