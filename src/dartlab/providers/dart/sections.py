"""sections — providers(L1) panel 공시 본문 정규화 뷰 + 표 추출 SSOT.

panel(providers L1) ``contentRaw`` 위에서 Company(L1)·scan(L1.5)·분석엔진(L2)이 공통으로
보는 normalized 섹션 뷰와 표 행 추출을 단일 SSOT 로 제공한다. docs.parquet 농장(127 파일
markdown 파서) 은퇴 — 입력은 panel ``contentRaw``(raw DART XML), 파싱은 본 모듈 한 곳.
어댑터를 각 엔진에 흩지 않고, 못 주던 표 추출도 드롭하지 않고 여기서 SSOT 로 재건한다.

**위치 = providers(L1)**: scan(L1.5 형제 cross 금지)·Company(L1)·L2 가 모두 하향/동일 레이어
import 하려면 frame(L1.5) 이 아닌 panel 과 같은 L1 이어야 한다. 의미 분류·점수화·룰 매칭은 L2.
"""

from __future__ import annotations

import polars as pl

# DART XML 표 셀 태그 — TD(데이터)·TH(헤더)·TE(타입 셀)·TU(단위/일자 셀).
_CELL_TAGS = frozenset({"TD", "TH", "TE", "TU"})


def sectionTexts(
    code: str,
    *,
    periods: list[str] | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """panel 섹션 본문 정규화 long 뷰 — docs sections 대체 SSOT.

    Args:
        code: 종목코드 (예 ``"005930"``).
        periods: 특정 period 만(파일 prune). None = 전체.
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        pl.DataFrame | None — [sectionLeaf, contentRaw, period, (chapter, disclosureKey)].
        artifact 부재 시 None. industry stage3·quant text alpha 입력.

    Example:
        >>> sectionTexts("005930", periods=["2025Q4"])  # doctest: +SKIP
    """
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


def sectionsWide(
    code: str,
    *,
    periods: list[str] | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """panel 섹션 본문 wide 뷰 — topic(sectionLeaf) 행 × period 열. sectionsDiff 입력 SSOT.

    docs sections wide 대체 — ``providers._common.diff.sectionsDiff`` 가 기대하는
    ``topic`` 행 × period 열 형태(셀=본문). 같은 (sectionLeaf, period) 블록은 결합.

    Args:
        code: 종목코드.
        periods: 특정 period 만. None = 전체.
        marketNs: 시장 namespace.

    Returns:
        pl.DataFrame | None — [topic, <period>...]. artifact 부재 시 None.

    Example:
        >>> sectionsWide("005930")  # doctest: +SKIP
    """
    df = sectionTexts(code, periods=periods, marketNs=marketNs)
    if df is None or df.is_empty():
        return None
    hasChapter = "chapter" in df.columns
    idx = ["chapter", "sectionLeaf"] if hasChapter else ["sectionLeaf"]
    # contentRaw 는 raw DART XML — wide 텍스트 뷰(diff/keyword/표시)는 태그 strip(plain).
    # raw XML 표 추출은 sectionTables/parseXmlTables 가 별도 사용.
    agg = df.group_by([*idx, "period"]).agg(
        pl.col("contentRaw").str.join("\n").str.replace_all(r"<[^>]+>", " ").alias("content")
    )
    wide = agg.pivot(values="content", index=idx, on="period")
    # topic = sectionLeaf 별칭 — sectionsDiff/keywordFrequency(topic 컬럼 기대) + dataDispatcher
    # (chapter/sectionLeaf 기대) 양쪽 소비 정합. source 컬럼은 docs(섹션 본문) 표기.
    return wide.with_columns(
        pl.col("sectionLeaf").alias("topic"),
        pl.lit("docs").alias("source"),
    )


def sectionTables(
    code: str,
    *,
    sectionPattern: str | None = None,
    period: str | None = None,
    marketNs: str = "kr",
) -> list[list[list[str]]]:
    """panel ``contentRaw``(raw DART XML) → 표 행 추출 SSOT (markdown 파서 대체).

    docs 농장의 markdown ``extractTables`` 를 대체 — panel contentRaw 는 raw DART XML
    (``<TABLE><TR><TD>``) 이라 동일 표 정보를 lxml 로 추출한다(드롭 0).

    Args:
        code: 종목코드.
        sectionPattern: sectionLeaf 필터 정규식 (예 ``"원재료"``). None = 전체.
        period: panel period (예 ``"2025Q4"``). None = 전체 period.
        marketNs: 시장 namespace.

    Returns:
        list[list[list[str]]] — 표 × 행 × 셀(텍스트). 표 없으면 빈 list.

    Example:
        >>> sectionTables("005930", sectionPattern="원재료", period="2025Q4")  # doctest: +SKIP
    """
    from dartlab.providers.dart.panel.read import readLong

    df = readLong(code, marketNs=marketNs, periods=[period] if period else None)
    if df is None or df.is_empty():
        return []
    if sectionPattern:
        df = df.filter(pl.col("sectionLeaf").str.contains(sectionPattern))
    tables: list[list[list[str]]] = []
    for cr in df["contentRaw"].to_list():
        if cr and "<TR" in cr:
            tables.extend(parseXmlTables(cr))
    return tables


def parseXmlTables(content: str) -> list[list[list[str]]]:
    """DART XML 본문 → 표 리스트(행 × 셀 텍스트). lxml recover 파싱.

    Args:
        content: panel ``contentRaw`` (raw DART XML 단편, 다중 root 허용).

    Returns:
        list[list[list[str]]] — 각 표는 행(list) × 셀(str). 헤더+데이터 ≥ 2 행 표만.

    Raises:
        없음 — 파싱 실패는 빈 list.

    Example:
        >>> parseXmlTables("<TABLE><TR><TD>a</TD><TD>b</TD></TR><TR><TD>1</TD><TD>2</TD></TR></TABLE>")
        [[['a', 'b'], ['1', '2']]]
    """
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
                    continue  # comment/PI skip
                if cell.tag in _CELL_TAGS:
                    cells.append("".join(cell.itertext()).strip())
            if cells:
                rows.append(cells)
        if len(rows) >= 2:
            tables.append(rows)
    return tables


__all__ = ["sectionTexts", "sectionsWide", "sectionTables", "parseXmlTables"]
