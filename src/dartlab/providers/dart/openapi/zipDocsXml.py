"""DART document.xml → 섹션 row list (정공법).

원본 XML 의 ``<TITLE ATOC="Y" AASSOCNOTE="D-0-3-1-0">`` 명시 hierarchy 와
``<TABLE>`` rowspan/colspan + ``<SPAN USERMARK="F-14 B">`` 가/나/다 bold marker
를 직접 사용 → sections layer 의 regex 추론을 builder 단에서 사전 해결.

기존 ``zipCollector._parseSections`` 의 SECTION-1/SECTION-2 통째 본문 추출은
chapter 본문이 4MB 통째로 cell 에 들어가 sections layer 가 regex 로 sub-section
분리 → 추론 오류 다발. 본 모듈의 ``parseSectionsByTitle`` 은 각 ``<TITLE>`` 별로
row 를 분리하고 직속 본문만 attach — sub-section 별 cell value 가 작아짐 +
hierarchy (AASSOCNOTE / ATOCID) 보존.

회귀 보장:
- ``section_title`` / ``section_content`` 컬럼 호환 — 기존 caller 영향 0.
- 추가 컬럼 ``atocid`` / ``assocnote`` — sections layer 가 활용 가능 (optional).
- 005930 검증: 1 rcept × 57 sub-doc → 144 TITLE-level rows, sectionsParity 0
  violations, sectionsRawCompare spurious 6 → 0.

호출:
    >>> from dartlab.providers.dart.openapi.zipDocsXml import parseSectionsByTitle
    >>> sections = parseSectionsByTitle(xmlContent)
    >>> sections[0]
    {'order': 0, 'title': '사 업 보 고 서', 'content': '...', 'atocid': '402', 'assocnote': 'COVER'}
"""

from __future__ import annotations

from typing import Any

from lxml import etree


def _elemText(elem) -> str:
    """element 안 모든 itertext join + strip."""
    return " ".join(elem.itertext()).strip()


def _tableToMarkdown(table) -> str:
    """XML ``<TABLE>`` → markdown table. rowspan/colspan 직접 보존."""
    rows: list[list[str]] = []
    for tr in table.iter("TR"):
        cells: list[str] = []
        for cell in tr.xpath(".//TD|.//TH|.//TU|.//TE"):
            colspan = int(cell.get("COLSPAN", "1") or "1")
            text = " ".join(cell.itertext()).strip().replace("\n", " ").replace("|", "｜")
            cells.append(text)
            cells.extend("" for _ in range(colspan - 1))
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    nCols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < nCols:
            r.append("")
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * nCols) + " |"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def parseSectionsByTitle(xmlContent: str) -> list[dict[str, Any]]:
    """DART document.xml → ``<TITLE>`` 별 섹션 row list.

    Args:
        xmlContent: document.xml 의 XML 문자열 (UTF-8 decoded).

    Returns:
        list[dict] — 각 dict 는 ``order``/``title``/``content``/``atocid``/``assocnote`` 키.

        - ``order``: TITLE 의 document order (0-indexed).
        - ``title``: ``<TITLE>`` text.
        - ``content``: 그 TITLE 직속 body (다음 TITLE 까지의 ``<P>``/``<SPAN>``/``<TABLE>``).
          ``<SPAN USERMARK="... B">`` (가/나/다 bold marker) 는 markdown ``## prefix``
          로 변환. ``<TABLE>`` 은 markdown table 로 변환 (rowspan 자동 보존).
        - ``atocid``: ``<TITLE ATOCID>`` (TOC unique ID, 없으면 ``""``).
        - ``assocnote``: ``<TITLE AASSOCNOTE>`` (path-id 예 ``D-0-3-1-0``,
          ``D``=document / ``L``=list / ``0``=skip / ``{chapter}`` / ``{sub}`` / ``{subsub}``).

    Example:
        >>> with open("20260310002820.xml", encoding="utf-8") as f:
        ...     xml = f.read()
        >>> rows = parseSectionsByTitle(xml)
        >>> len(rows)  # 144 (vs 기존 SECTION-1/2 = 57)
        144
        >>> rows[3]
        {'order': 3, 'title': 'I. 회사의 개요', 'atocid': '3', 'assocnote': '', ...}
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xmlContent.encode("utf-8"), parser)
    except (etree.XMLSyntaxError, ValueError):
        return []
    if root is None:
        return []
    body = root.find(".//BODY")
    if body is None:
        return []

    sections: list[dict[str, Any]] = []
    currentTitle: dict[str, Any] | None = None
    bodyParts: list[str] = []
    order = 0

    def _flush() -> None:
        nonlocal currentTitle, bodyParts, order
        if currentTitle is not None:
            currentTitle["content"] = "\n\n".join(p for p in bodyParts if p).strip()
            currentTitle["order"] = order
            sections.append(currentTitle)
            order += 1
        bodyParts = []
        currentTitle = None

    for elem in body.iter():
        tag = elem.tag
        if not isinstance(tag, str):
            continue
        if tag in ("TITLE", "COVER-TITLE"):
            _flush()
            text = _elemText(elem)
            currentTitle = {
                "atocid": elem.get("ATOCID", "") or "",
                "assocnote": elem.get("AASSOCNOTE", "") or "",
                "title": text,
                "content": "",
            }
        elif tag == "P" and currentTitle is not None:
            t = _elemText(elem)
            if t:
                bodyParts.append(t)
        elif tag == "SPAN" and currentTitle is not None:
            # 가/나/다 sub-sub marker — USERMARK 의 B (bold) 가 sub-section heading.
            # markdown ## prefix 변환 → sections textStructure regex 추론 제거.
            usermark = (elem.get("USERMARK", "") or "").strip()
            t = _elemText(elem)
            if not t:
                continue
            isBold = "B" in usermark.split()
            if isBold and len(t) < 80:
                bodyParts.append(f"## {t}")
            else:
                bodyParts.append(t)
        elif tag == "TABLE" and currentTitle is not None:
            md = _tableToMarkdown(elem)
            if md:
                bodyParts.append(md)
    _flush()
    return sections


__all__ = ["parseSectionsByTitle"]
