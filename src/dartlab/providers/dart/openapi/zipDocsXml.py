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


def _escapeHtml(text: str) -> str:
    """raw text → HTML entity escape (`& < >`)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _tableToMarkdown(table) -> str:
    """XML ``<TABLE>`` → HTML table 문자열. rowspan/colspan attribute 보존.

    이전 구현은 markdown table 문법 (`| ... |`) 출력이라 GFM 이 rowspan 미지원 →
    DART HTML 의 multi-row header (`<th rowspan>`) 가 평탄화돼 stair-step row 다수.
    회귀 사례 (005930 차입금/재고자산 multi-row header 시각 깨짐).

    본 구현은 HTML 그대로 출력 (`<table><tr><td rowspan colspan>...`) — frontend 가
    sanitize 후 raw HTML 렌더하면 원본 DART 표 시각 fidelity 100% 회복.

    함수명은 호환 위해 ``_tableToMarkdown`` 유지 (caller 영향 0). 출력 형식 변경만.
    downstream ``classifyContent`` / ``buildMarkdownBlocks`` 의 table line 검출은
    `<table` prefix 도 인식하도록 동행 수정.

    nested ``<TABLE>`` 차단 — 외부 TR / cell 만. nested table cell 내용은
    itertext 로 inline (별도 row 안 만듦). 회귀 차단: 기존 ``iter('TR')`` +
    ``.//TD`` 가 nested table 의 TR/cell 까지 외부에 포함시켜 한 table 420MB+
    markdown 폭발 (035720 회귀).
    """
    # 1차 pass — TR/cell 수집. 단일 cell (1 row × 1 col, rowspan/colspan 없음) 은
    # DART XML 의 paragraph framing 양식 (`<TABLE><TR><TD>본문...</TD></TR></TABLE>`)
    # 으로 시각상 table 아님. 그대로 HTML table 로 emit 하면 좁은 viewer column 에서
    # 본문이 한 cell 안 한 줄로 펼쳐져 가로 스크롤 트리거. 본 1×1 case 는 plain text
    # 만 emit (paragraph 와 동일 wrap 동작).
    collected: list[list[tuple[str, str, str, str]]] = []  # rows of [(tag, colspan, rowspan, text)]
    for tr in _findDirectTRs(table):
        cells: list[tuple[str, str, str, str]] = []
        for cell in tr:
            if not isinstance(cell.tag, str) or cell.tag not in ("TD", "TH", "TU", "TE"):
                continue
            tag = "th" if cell.tag in ("TH", "TU") else "td"
            colspan = cell.get("COLSPAN", "1") or "1"
            rowspan = cell.get("ROWSPAN", "1") or "1"
            text = " ".join(cell.itertext()).strip().replace("\n", " ")
            cells.append((tag, colspan, rowspan, text))
        if cells:
            collected.append(cells)
    if not collected:
        return ""

    # 단일 cell paragraph framing — 1 row × 1 col + 병합 없음 → plain text
    if len(collected) == 1 and len(collected[0]) == 1:
        only = collected[0][0]
        if only[1] in ("1", "") and only[2] in ("1", ""):
            return only[3]

    out: list[str] = ["<table>"]
    for cells in collected:
        rowOut: list[str] = ["<tr>"]
        for tag, colspan, rowspan, text in cells:
            attrs = ""
            if colspan and colspan != "1":
                attrs += f' colspan="{int(colspan)}"'
            if rowspan and rowspan != "1":
                attrs += f' rowspan="{int(rowspan)}"'
            rowOut.append(f"<{tag}{attrs}>{_escapeHtml(text)}</{tag}>")
        rowOut.append("</tr>")
        out.append("".join(rowOut))
    out.append("</table>")
    return "\n".join(out)


# Phase B-5: DART XML 의 `<P>` word-wrap 분할 결함 복원. 한 시각적 line 의 단어들이
# 다수 `<P>` 로 부서져 있는 패턴 (예: <P>사업부문별</P><P>현황</P>) 을 같은 line 으로
# 합침. 회귀 사례: "사업부문별" / "현황" 두 P 가 sections layer 의 textPath build 에서
# "사업부문별 > " (현황 잘림) 으로 잘려나가던 것을 "사업부문별현황" 한 단위로 복원.
_SENTENCE_END_SUFFIX = ("다.", "요.", "니다.", ".", "?", "!", ")", "]", ":", ";", "다", "요")
_P_MERGE_MAX_LEN = 20


def _mergeShortPs(parts: list[str], maxLen: int = _P_MERGE_MAX_LEN) -> list[str]:
    """인접한 짧은 P 들을 같은 line 으로 합침 (DART XML word-wrap 결함 복원).

    조건 모두 만족 시 prev + curr 합침 (공백 0):
    1. prev 와 curr 둘 다 ``maxLen`` 이하 (default 20 chars).
    2. prev 가 sentence-end (다./요./니다././?/!/)/].).) 가 아님.
    3. prev 와 curr 둘 다 markdown heading prefix (``## ``) 아님.
    4. prev 와 curr 둘 다 markdown table prefix (``|``) 아님.

    word-wrap 인 경우 source XML 에 공백 의도가 없으므로 ``join("")`` 사용 — Phase B-4
    의 SPAN concat 과 동일 원칙.
    """
    if len(parts) <= 1:
        return parts
    result: list[str] = []
    buf = parts[0]
    for nxt in parts[1:]:
        if _canMergePs(buf, nxt, maxLen):
            buf = buf + nxt
        else:
            result.append(buf)
            buf = nxt
    result.append(buf)
    return result


def _canMergePs(prev: str, nxt: str, maxLen: int) -> bool:
    """두 P 가 word-wrap 결함으로 분할된 case 인지 판정."""
    if not prev or not nxt:
        return False
    if len(prev) > maxLen or len(nxt) > maxLen:
        return False
    if prev.startswith("## ") or nxt.startswith("## "):
        return False
    if prev.startswith("|") or nxt.startswith("|"):
        return False
    if prev.endswith(_SENTENCE_END_SUFFIX):
        return False
    return True


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

    Raises:
        없음.

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
            merged = _mergeShortPs(bodyParts)
            currentTitle["content"] = "\n\n".join(p for p in merged if p).strip()
            currentTitle["order"] = order
            sections.append(currentTitle)
            order += 1
        bodyParts = []
        currentTitle = None

    # 명시 DFS — leaf 처리 후 descendant 안 들어감. body.iter() 재귀가 <TABLE> 안
    # <P>, <P> 안 <SPAN> 을 중복 처리하던 회귀 (035720 표 다수 종목 100x 폭증) 차단.
    #
    # 2026-05-26 회귀 fix: ``TABLE-GROUP`` 안 TITLE 들은 별개 section row 로 emit 하지 않고
    # parent TITLE 본문에 ``## heading`` 으로 흡수. 옛 zipCollector._parseSections 양식과 호환 —
    # sections pipeline 의 ``_reportRowsToTopicRows`` 가 Roman chapter 안 sub-section 추적할 때
    # TABLE-GROUP 안 sub-sub TITLE 이 별개 row 면 currentMajorNum 추적 깨져 차입금/사채 등
    # notes sub-section 본문이 drop. parent 본문 안 ``## heading`` + content 로 흡수해 split.
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
        if tag == "TABLE-GROUP":
            # TABLE-GROUP 안 nested TITLE / P / SPAN / TABLE 들을 *parent TITLE 의 본문*
            # 에 흡수. nested TITLE 은 ``## heading`` 으로, TABLE 은 HTML 그대로 합쳐서
            # 옛 sections pipeline 의 chunking 이 chapter 안 sub-section 으로 인식 가능.
            if currentTitle is not None:
                for descendant in elem.iter():
                    dtag = descendant.tag
                    if not isinstance(dtag, str):
                        continue
                    if dtag in ("TITLE", "COVER-TITLE"):
                        t = _elemText(descendant)
                        if t:
                            bodyParts.append(f"## {t}")
                    elif dtag == "TABLE":
                        # nested table 의 outer wrapper 만 처리 — ancestor TABLE-GROUP 인 case
                        # 만 (다중 TABLE-GROUP nesting 의 inner TABLE-GROUP 안 TABLE 은 skip).
                        # 단순화: TABLE 자체 처리 (콘텐츠 중복은 ``_tableToMarkdown`` 의 nested
                        # 차단 로직 가 막음).
                        # iter() 가 모든 descendant 를 yield 하므로 outer + nested 모두 보이지만
                        # _tableToMarkdown 가 _findDirectTRs 로 outer 만 보고 nested 내용은
                        # itertext flat inline 처리. 중복 없음.
                        # 단 같은 outer 가 여러 번 등장하면 중복 → 처리: parent 가 TABLE-GROUP
                        # 인 TABLE 만 (1-depth nested).
                        parent = descendant.getparent()
                        if parent is not None and parent.tag == "TABLE-GROUP":
                            md = _tableToMarkdown(descendant)
                            if md:
                                bodyParts.append(md)
                    elif dtag == "P":
                        parent = descendant.getparent()
                        # parent 가 TABLE-GROUP 인 P 만 (TABLE 안 P 중복 차단)
                        if parent is not None and parent.tag == "TABLE-GROUP":
                            t = _elemText(descendant)
                            if t:
                                bodyParts.append(t)
            return  # TABLE-GROUP descendants 는 위에서 다 처리
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

    Raises:
        없음.

    Example:
        >>> chunks = splitLargeContent("..." * 500000)
        >>> all(len(c) <= MAX_CELL_BYTES for c in chunks)
        True
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
