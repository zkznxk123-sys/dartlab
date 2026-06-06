"""panel text/table read helpers.

DART 공시 본문 소비자는 panel artifact 의 ``contentRaw`` 만 읽는다. 이 모듈은
panel 패키지 내부의 얇은 read helper 이며, 공개 Company 표면은 계속
``Company.panel`` 이다.
"""

from __future__ import annotations

import polars as pl

_CELL_TAGS = frozenset({"TD", "TH", "TE", "TU"})


def panelTextRows(
    code: str,
    *,
    periods: list[str] | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """panel long rows projected to text-bearing columns."""
    from dartlab.providers.dart.panel.read import readLong

    df = readLong(code, marketNs=marketNs, periods=periods)
    if df is None or df.is_empty():
        return None
    cols = [
        c
        for c in ("sectionLeaf", "contentRaw", "period", "chapter", "disclosureKey", "blockOrder", "rceptNo")
        if c in df.columns
    ]
    return df.select(cols)


def panelTextWide(
    code: str,
    *,
    periods: list[str] | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """panel text wide view for diff/keyword consumers."""
    df = panelTextRows(code, periods=periods, marketNs=marketNs)
    if df is None or df.is_empty():
        return None
    hasChapter = "chapter" in df.columns
    idx = ["chapter", "sectionLeaf"] if hasChapter else ["sectionLeaf"]
    agg = df.group_by([*idx, "period"]).agg(
        pl.col("contentRaw").str.join("\n").str.replace_all(r"<[^>]+>", " ").alias("content")
    )
    wide = agg.pivot(values="content", index=idx, on="period")
    return wide.with_columns(
        pl.col("sectionLeaf").alias("topic"),
        pl.lit("panel").alias("source"),
    )


def panelXmlTables(
    code: str,
    *,
    sectionPattern: str | None = None,
    period: str | None = None,
    marketNs: str = "kr",
) -> list[list[list[str]]]:
    """Extract XML tables from panel ``contentRaw``."""
    from dartlab.providers.dart.panel.read import readLong

    df = readLong(code, marketNs=marketNs, periods=[period] if period else None)
    if df is None or df.is_empty():
        return []
    if sectionPattern:
        df = df.filter(pl.col("sectionLeaf").str.contains(sectionPattern))
    tables: list[list[list[str]]] = []
    for cr in df["contentRaw"].to_list():
        if cr and "<TR" in cr:
            tables.extend(parsePanelXmlTables(cr))
    return tables


def panelTableRows(
    code: str,
    *,
    sectionPattern: str | None = None,
    period: str | None = None,
    marketNs: str = "kr",
) -> list[dict[str, str]]:
    """Extract XML tables from panel and flatten each table by its header row."""
    from dartlab.providers.dart.tableRows import tableToRowDicts

    rows: list[dict[str, str]] = []
    for table in panelXmlTables(code, sectionPattern=sectionPattern, period=period, marketNs=marketNs):
        rows.extend(tableToRowDicts(table))
    return rows


def parsePanelXmlTables(content: str) -> list[list[list[str]]]:
    """Parse DART XML fragment into tables represented as rows and cell text."""
    from lxml import etree

    parser = etree.XMLParser(recover=True, resolve_entities=False)
    try:
        root = etree.fromstring(f"<root>{content}</root>", parser=parser)
    except (etree.XMLSyntaxError, ValueError):
        return []
    if root is None:
        return []
    tables: list[list[list[str]]] = []
    for tableEl in root.iter("TABLE"):
        rows: list[list[str]] = []
        for tr in tableEl.iter("TR"):
            cells: list[str] = []
            for cell in tr:
                if not isinstance(cell.tag, str):
                    continue
                if cell.tag in _CELL_TAGS:
                    cells.append("".join(cell.itertext()).strip())
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            tables.append(rows)
    return tables


__all__ = [
    "panelTextRows",
    "panelTextWide",
    "panelXmlTables",
    "panelTableRows",
    "parsePanelXmlTables",
]
