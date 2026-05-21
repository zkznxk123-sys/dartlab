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

import re
from typing import Any

from lxml import etree

_MULTISPACE_RE = re.compile(r"\s+")


def _elemText(elem) -> str:
    """element 안 모든 itertext concat (no separator) + 다중 공백 정리 + strip.

    DART XML 의 ``<P>`` 안에는 ``<SPAN>`` 가 word-wrap 단위로 다수 분할된다 (시각적
    한 줄당 한 SPAN). 회귀 사례 (005930 분기보고서):
        ``<SPAN>지역별로 보면, 국내</SPAN><SPAN>에서</SPAN><SPAN>는 </SPAN>``
    ``" ".join`` 로 join 시 "지역별로 보면, 국내 에서 는" 처럼 공백 추가 → 의도
    "지역별로 보면, 국내에서는" 망가짐. 단어 끊김도 동일 (예 "메모리" →
    ``<SPAN>메</SPAN><SPAN>모리</SPAN>`` → " 메 모리").

    concat 후 multiple-space → single space 정리. 영어 단어 사이 SPAN boundary 의
    경우 source 의 공백이 SPAN 안 trailing/leading 에 포함되어 있어 손실 없음.
    """
    raw = "".join(elem.itertext())
    return _MULTISPACE_RE.sub(" ", raw).strip()


def _findDirectTRs(table):
    """``<TABLE>`` 직속 + ``<TBODY>``/``<THEAD>``/``<TFOOT>`` 안 TR 만 (nested TABLE 의 TR 제외)."""
    for child in table:
        if not isinstance(child.tag, str):
            continue
        if child.tag == "TR":
            yield child
        elif child.tag in ("TBODY", "THEAD", "TFOOT"):
            for sub in child:
                if isinstance(sub.tag, str) and sub.tag == "TR":
                    yield sub


def _tableToMarkdown(table) -> str:
    """XML ``<TABLE>`` → markdown table. rowspan/colspan 직접 보존.

    nested ``<TABLE>`` 차단 — 외부 TR / cell 만. nested table cell 내용은
    itertext 로 inline (별도 row 안 만듦). 회귀 차단: 기존 ``iter('TR')`` +
    ``.//TD`` 가 nested table 의 TR/cell 까지 외부에 포함시켜 한 table 420MB+
    markdown 폭발 (035720 회귀).
    """
    rows: list[list[str]] = []
    for tr in _findDirectTRs(table):
        cells: list[str] = []
        for cell in tr:
            if not isinstance(cell.tag, str) or cell.tag not in ("TD", "TH", "TU", "TE"):
                continue
            colspan = int(cell.get("COLSPAN", "1") or "1")
            # cell 의 itertext 는 nested TABLE 의 cell text 도 포함 (flat inline)
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

    # 명시 DFS — leaf 처리 후 descendant 안 들어감. body.iter() 재귀가 <TABLE> 안
    # <P>, <P> 안 <SPAN> 을 중복 처리하던 회귀 (035720 표 다수 종목 100x 폭증) 차단.
    def _walk(elem) -> None:
        nonlocal currentTitle
        tag = elem.tag
        if not isinstance(tag, str):
            return
        if tag in ("TITLE", "COVER-TITLE"):
            _flush()
            currentTitle = {
                "atocid": elem.get("ATOCID", "") or "",
                "assocnote": elem.get("AASSOCNOTE", "") or "",
                "title": _elemText(elem),
                "content": "",
            }
            return  # descendants 는 title text 안에 이미 흡수
        if tag == "P":
            if currentTitle is not None:
                t = _elemText(elem)
                if t:
                    bodyParts.append(t)
            return  # P 안 SPAN 중복 차단
        if tag == "SPAN":
            if currentTitle is not None:
                usermark = (elem.get("USERMARK", "") or "").strip()
                t = _elemText(elem)
                if t:
                    isBold = "B" in usermark.split()
                    if isBold and len(t) < 80:
                        bodyParts.append(f"## {t}")
                    else:
                        bodyParts.append(t)
            return
        if tag == "TABLE":
            if currentTitle is not None:
                md = _tableToMarkdown(elem)
                if md:
                    bodyParts.append(md)
            return  # TABLE 안 P/SPAN 중복 차단
        # container — descend
        for child in elem:
            _walk(child)

    for child in body:
        _walk(child)
    _flush()
    return sections


# 한 row 의 section_content 최대 size. 초과 시 markdown paragraph (\n\n) 또는 line
# 단위 split → multiple row 분할. 회귀 차단: polars row_tuples 의 PyObject 변환이
# 4MB+ string 에서 panic. 1MB 안전선 채택 (sections chunker MAX_CHUNK_CHARS 4KB 보다
# 크지만 polars 안전선 + pa.string() 32-bit offset 의 column total 한도 회피).
MAX_CELL_BYTES = 1_000_000


def splitLargeContent(text: str, maxBytes: int = MAX_CELL_BYTES) -> list[str]:
    """text 가 maxBytes 초과 시 paragraph (``\\n\\n``) → line 단위로 분할.

    회귀 사례: 4MB+ string 의 polars ``row_tuples`` PyObject 변환 panic. 본 helper
    가 1MB 안전선으로 split → multiple row 분할 (같은 atocid/assocnote 유지,
    section_order 만 split index 만큼 증가).

    Args:
        text: 원본 string.
        maxBytes: per-cell 최대 char 수 (기본 1MB).

    Returns:
        분할된 list[str] — 각 원소 ≤ maxBytes char.
    """
    if len(text) <= maxBytes:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    bufLen = 0
    for para in text.split("\n\n"):
        pLen = len(para)
        if pLen > maxBytes:
            if buf:
                parts.append("\n\n".join(buf))
                buf = []
                bufLen = 0
            lineBuf: list[str] = []
            lineLen = 0
            for ln in para.split("\n"):
                if lineLen + len(ln) + 1 > maxBytes and lineBuf:
                    parts.append("\n".join(lineBuf))
                    lineBuf = []
                    lineLen = 0
                lineBuf.append(ln)
                lineLen += len(ln) + 1
            if lineBuf:
                parts.append("\n".join(lineBuf))
            continue
        if bufLen + pLen + 2 > maxBytes and buf:
            parts.append("\n\n".join(buf))
            buf = []
            bufLen = 0
        buf.append(para)
        bufLen += pLen + 2
    if buf:
        parts.append("\n\n".join(buf))
    return parts


__all__ = ["parseSectionsByTitle", "splitLargeContent", "MAX_CELL_BYTES"]
