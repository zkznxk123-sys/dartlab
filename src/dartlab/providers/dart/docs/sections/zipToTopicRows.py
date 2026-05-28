"""zip XML → sections row 직접 (v4) — 태그 보존 + sub-section 수평화 동시.

plan snazzy-wibbling-origami v4 (6 cycle 실패 후 정공법).

알고리즘:
    1. parseSectionsByTitle 의 content (raw XML chunks join) 를 etree 로 다시 parse.
    2. top-level child element walk (P / SPAN / TABLE / TABLE-GROUP).
    3. heading marker 검출 → block boundary:
       - SPAN with USERMARK="...B..." (옛 가/나/다 bold marker)
       - P 의 첫 line 이 옛 _detectHeading 7-level (Roman/numeric/Korean/paren/circled/bracket)
    4. 각 block 의 raw XML = etree.tostring(elem) 그대로 (P/SPAN/USERMARK/TABLE/COLGROUP/
       ALIGN 모든 태그 + 속성 보존). plain text / markdown 변환 0.
    5. heading_stack 누적 → textPath / textSemanticPathKey (옛 _headingPathStringsCached 재사용).
    6. SegmentKeyer.forTextBody / forTextHeadingNode / forTableBlock — path-anchored
       cross-period invariant segmentKey.

옛 lossy chain 호출 0:
    xmlChunkToMixed / _reportRowsToTopicRows / _splitContentBlocks /
    _expandStructuredRows / _accumulatePeriodRows / _mergeFragmentTables.

회귀 가드 (6 cycle 실패의 직접 원인 차단):
    - content_raw = etree.tostring (raw XML 그대로). plain text / markdown 변환 X.
    - sub-section block 단위 row (옛 _expandStructuredRows row 수와 동등).
    - cross-period 매칭 = textSemanticPathKey + segmentKey (path-anchored).
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl
from lxml import etree

from dartlab.providers.dart.docs.sections.expansion import _headingPathStringsCached
from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle
from dartlab.providers.dart.docs.sections.segmentKeyer import SegmentKeyer
from dartlab.providers.dart.docs.sections.tableParser import tableHeaderHash
from dartlab.providers.dart.docs.sections.textStructure import (
    _detectHeading,
    _headingKey,
)
from dartlab.providers.dart.openapi.zipCollector import _extractMetaFromXml
from dartlab.providers.dart.openapi.zipDocsXml import parseSectionsByTitle

_log = logging.getLogger(__name__)

_NOTES_TOPICS = frozenset({"financialNotes", "consolidatedNotes"})

_ROW_SCHEMA: dict[str, pl.DataType] = {
    "topic": pl.Utf8,
    "blockType": pl.Utf8,
    "blockOrder": pl.Int32,
    "textLevel": pl.Int8,
    "textPath": pl.Utf8,
    "textSemanticPathKey": pl.Utf8,
    "segmentKey": pl.Utf8,
    "content_raw": pl.Utf8,
    "period": pl.Utf8,
    "rcept_no": pl.Utf8,
}


def zipToTopicRows(
    xml: str,
    *,
    rcptNo: str,
    stockCode: str,
) -> pl.DataFrame:
    """zip XML 1 개 → sections row DF (raw XML 보존 + sub-section block 분할).

    Args:
        xml: document.xml UTF-8 문자열.
        rcptNo: rcept_no.
        stockCode: 종목코드 (메타).

    Returns:
        sub-section block 단위 row DataFrame (10 컬럼). parse 실패 / 빈 zip 시 빈 DF.

    Raises:
        없음 — 실패 silent + log.warning.
    """
    if not xml or not xml.strip():
        return pl.DataFrame(schema=_ROW_SCHEMA)
    try:
        year, rcptDate, _reportType = _extractMetaFromXml(xml, rcptNo)
    except Exception as exc:  # noqa: BLE001
        _log.warning("zip meta 추출 실패 (%s/%s): %s", stockCode, rcptNo, exc)
        return pl.DataFrame(schema=_ROW_SCHEMA)

    period = _periodKeyFromMeta(year=year, rcptDate=rcptDate)
    sections = parseSectionsByTitle(xml)
    if not sections:
        return pl.DataFrame(schema=_ROW_SCHEMA)

    keyer = SegmentKeyer()
    parser = etree.XMLParser(recover=True, huge_tree=True)
    rows: list[dict[str, Any]] = []

    for sectionIdx, section in enumerate(sections):
        title = (section.get("title") or "").strip()
        rawChunks = section.get("content") or ""
        assocnote = section.get("assocnote") or ""
        if not title:
            continue
        topic = mapSectionTitle(title)
        if not topic:
            continue

        baseLevel = _levelFromAssocnote(assocnote) or 1
        isNotes = topic in _NOTES_TOPICS
        sectionRows = _walkSection(
            rawChunks=rawChunks,
            sectionTitle=title,
            sectionIdx=sectionIdx,
            baseLevel=baseLevel,
            topic=topic,
            isNotes=isNotes,
            period=period,
            rcptNo=rcptNo,
            keyer=keyer,
            parser=parser,
        )
        rows.extend(sectionRows)

    if not rows:
        return pl.DataFrame(schema=_ROW_SCHEMA)
    return pl.DataFrame(rows, schema=_ROW_SCHEMA)


def _walkSection(
    *,
    rawChunks: str,
    sectionTitle: str,
    sectionIdx: int,
    baseLevel: int,
    topic: str,
    isNotes: bool,
    period: str,
    rcptNo: str,
    keyer: SegmentKeyer,
    parser: etree.XMLParser,
) -> list[dict[str, Any]]:
    """1 section 의 raw XML → sub-section block row list.

    section.content 의 raw XML chunks 를 BODY 로 wrap + etree parse → top-level
    element walk + heading marker 검출 → block 단위 row emit.
    """
    if not rawChunks.strip():
        # 본문 없는 chapter heading row — section title 만 row 1 개.
        return [
            _makeRow(
                topic=topic,
                blockType="heading",
                blockOrder=sectionIdx * 10000,
                headingStack=[_makeHeading(sectionTitle, baseLevel)],
                contentRaw=f"<TITLE>{_escapeXml(sectionTitle)}</TITLE>",
                period=period,
                rcptNo=rcptNo,
                keyer=keyer,
                isNotes=isNotes,
            )
        ]

    try:
        body = etree.fromstring(f"<BODY>{rawChunks}</BODY>".encode("utf-8"), parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        _log.warning("section etree parse 실패 (%s/%s): %s", topic, sectionTitle, exc)
        return []
    if body is None:
        return []

    headingStack: list[dict[str, Any]] = [_makeHeading(sectionTitle, baseLevel)]
    blockBuffer: list[str] = []
    rows: list[dict[str, Any]] = []
    blockOrder = [sectionIdx * 10000]  # mutable for nested closure

    def flushBlock(blockType: str) -> None:
        """현재 blockBuffer 를 row 1 개로 emit + buffer reset."""
        if not blockBuffer:
            return
        rawXml = "".join(blockBuffer).strip()
        blockBuffer.clear()
        if not rawXml:
            return
        rows.append(
            _makeRow(
                topic=topic,
                blockType=blockType,
                blockOrder=blockOrder[0],
                headingStack=list(headingStack),
                contentRaw=rawXml,
                period=period,
                rcptNo=rcptNo,
                keyer=keyer,
                isNotes=isNotes,
            )
        )
        blockOrder[0] += 1

    for elem in body:
        tag = elem.tag if isinstance(elem.tag, str) else ""

        # table block — 별도 row, heading stack 상속
        if tag in ("TABLE", "TABLE-GROUP"):
            flushBlock("text")
            try:
                tableRaw = etree.tostring(elem, encoding="unicode").strip()
            except (ValueError, TypeError):
                continue
            if tableRaw:
                blockBuffer.append(tableRaw)
                flushBlock("table")
            continue

        # SPAN USERMARK B — 가/나/다 bold heading marker
        if tag == "SPAN":
            usermark = (elem.get("USERMARK", "") or "").strip()
            if "B" in usermark.split():
                label = " ".join(elem.itertext()).strip()
                if label and len(label) < 80:
                    flushBlock("text")
                    try:
                        rawXml = etree.tostring(elem, encoding="unicode").strip()
                    except (ValueError, TypeError):
                        rawXml = ""
                    if rawXml:
                        blockBuffer.append(rawXml)
                    newLevel = baseLevel + 1
                    _pushHeading(headingStack, label, newLevel)
                    flushBlock("heading")
                    continue

        # P element — 첫 line 이 heading marker (가/나/다/Roman/numeric/paren)
        if tag == "P":
            text = " ".join(elem.itertext()).strip()
            firstLine = text.split("\n", 1)[0] if text else ""
            heading = _detectHeading(firstLine) if firstLine else None
            if heading is not None:
                level, label, _structural = heading
                flushBlock("text")
                try:
                    rawXml = etree.tostring(elem, encoding="unicode").strip()
                except (ValueError, TypeError):
                    rawXml = ""
                if rawXml:
                    blockBuffer.append(rawXml)
                # section base + inline level offset
                newLevel = baseLevel + level
                _pushHeading(headingStack, label, newLevel)
                flushBlock("heading")
                continue

        # 일반 element (P body / SPAN body / 기타)
        try:
            rawXml = etree.tostring(elem, encoding="unicode").strip()
        except (ValueError, TypeError):
            continue
        if rawXml:
            blockBuffer.append(rawXml)

    flushBlock("text")
    return rows


def _makeHeading(label: str, level: int) -> dict[str, Any]:
    """heading stack 의 dict 양식 — label/key/semanticKey/level."""
    return {
        "label": label,
        "key": _headingKey(label),
        "semanticKey": label,
        "level": int(level),
    }


def _pushHeading(stack: list[dict[str, Any]], label: str, level: int) -> None:
    """heading stack 에 새 entry push — 같은/하위 level ancestor pop."""
    while stack and stack[-1]["level"] >= level:
        stack.pop()
    stack.append(_makeHeading(label, level))


def _makeRow(
    *,
    topic: str,
    blockType: str,
    blockOrder: int,
    headingStack: list[dict[str, Any]],
    contentRaw: str,
    period: str,
    rcptNo: str,
    keyer: SegmentKeyer,
    isNotes: bool,
) -> dict[str, Any]:
    """heading_stack + block 정보 → row dict (10 컬럼)."""
    pathTuple = tuple((str(h["label"]), str(h["key"]), str(h["semanticKey"])) for h in headingStack)
    (
        _labels,
        _keys,
        _semKeys,
        textPath,
        _textPathKey,
        _textParentPathKey,
        textSemanticPathKey,
        _textSemanticParentPathKey,
    ) = _headingPathStringsCached(pathTuple)
    textLevel = headingStack[-1]["level"] if headingStack else None

    if blockType == "table":
        headerHash = tableHeaderHash(contentRaw)
        notesHeadingKey = headingStack[-1]["semanticKey"] if (isNotes and headingStack) else None
        _, _, segKey = keyer.forTableBlock(
            topic,
            sourceBlockOrder=blockOrder,
            notesHeadingKey=notesHeadingKey,
            isNotesTopic=isNotes,
            textSemanticPathKey=textSemanticPathKey,
            headerHash=headerHash,
        )
    elif blockType == "heading":
        # heading 자체 row — heading_stack 의 마지막이 자기 자신.
        segBase = f"heading|p:{textSemanticPathKey or ''}"
        _, _, segKey = keyer.forTextHeadingNode(topic, segBase)
    else:  # text
        _, _, segKey = keyer.forTextBody(
            topic,
            textLevel=textLevel or 0,
            textSemanticPathKey=textSemanticPathKey,
        )

    return {
        "topic": topic,
        "blockType": blockType,
        "blockOrder": blockOrder,
        "textLevel": int(textLevel) if textLevel is not None else None,
        "textPath": textPath,
        "textSemanticPathKey": textSemanticPathKey,
        "segmentKey": segKey,
        "content_raw": contentRaw,
        "period": period,
        "rcept_no": rcptNo,
    }


def _periodKeyFromMeta(*, year: str, rcptDate: str) -> str:
    """meta → YYYYQn (annual=Q4 alias)."""
    if not year:
        return ""
    if not rcptDate or len(rcptDate) < 6:
        return f"{year}Q4"
    try:
        month = int(rcptDate[4:6])
    except ValueError:
        return f"{year}Q4"
    if 3 <= month <= 5:
        return f"{year}Q1"
    if 6 <= month <= 8:
        return f"{year}Q2"
    if 9 <= month <= 11:
        return f"{year}Q3"
    return f"{year}Q4"


def _levelFromAssocnote(assocnote: str) -> int | None:
    """AASSOCNOTE 'D-0-3-1-0' → non-zero token 수 (chapter depth)."""
    if not assocnote:
        return None
    tokens = assocnote.split("-")
    level = 0
    for tok in tokens[1:]:
        if tok != "0" and tok.isdigit():
            level += 1
    return level if level > 0 else None


def _escapeXml(text: str) -> str:
    """text → XML entity escape."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = ["zipToTopicRows"]
