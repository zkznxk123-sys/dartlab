"""DART panel text helper tests."""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.panel import text as textMod


def test_parse_panel_xml_tables_extracts_cell_text() -> None:
    content = """
    <TABLE>
      <TR><TH>계정</TH><TH>금액</TH></TR>
      <TR><TD>매출액</TD><TD>100</TD></TR>
    </TABLE>
    """

    assert textMod.parsePanelXmlTables(content) == [[["계정", "금액"], ["매출액", "100"]]]


def test_panel_text_wide_reads_panel_long(monkeypatch) -> None:
    df = pl.DataFrame(
        {
            "sectionLeaf": ["사업의 개요", "사업의 개요"],
            "contentRaw": ["<P>첫 문장</P>", "<P>둘째 문장</P>"],
            "period": ["2024Q4", "2024Q4"],
            "chapter": ["II. 사업의 내용", "II. 사업의 내용"],
            "disclosureKey": [None, None],
            "blockOrder": [1, 2],
            "rceptNo": ["202503310001", "202503310001"],
        }
    )

    def fakeReadLong(code: str, *, marketNs: str, periods: list[str] | None = None) -> pl.DataFrame:
        assert code == "005930"
        assert marketNs == "kr"
        assert periods == ["2024Q4"]
        return df

    monkeypatch.setattr("dartlab.providers.dart.panel.read.readLong", fakeReadLong)

    wide = textMod.panelTextWide("005930", periods=["2024Q4"])

    assert wide is not None
    assert wide.select("topic").to_series().to_list() == ["사업의 개요"]
    assert wide.select("source").to_series().to_list() == ["panel"]
    assert "첫 문장" in wide.select("2024Q4").item()
