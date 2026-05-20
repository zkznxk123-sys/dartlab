"""subset → 9 컬럼 topic row DataFrame 변환 + content block 분해.

``_reportRowsToTopicRows(subset, contentCol)`` 가 sections 의 핵심 청킹:
section_title 의 chapter 헤딩 / sub-section 구분, ``_splitContentBlocks`` 로
text / table 분리, chapter row 본문 안 unique block 만 lonely 등록 (8자
임계 dedup) 로 chapter-only 표 손실 차단.

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수들을 re-import.
"""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.docs.sections.chunker import parseMajorNum
from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle, stripSectionPrefix
from dartlab.providers.dart.docs.sections.runtime import chapterFromMajorNum


def _splitContentBlocks(content: str) -> list[tuple[str, str]]:
    """content를 원문 순서대로 text/table block으로 분해."""
    strippedContent = content.strip()
    if not strippedContent:
        return []
    if "|" not in strippedContent:
        return [("text", strippedContent)]

    rows: list[tuple[str, str]] = []
    rowsAppend = rows.append
    buffer: list[str] = []
    currentKind: str | None = None

    def _flush(kind: str | None) -> None:
        nonlocal buffer
        if kind is None or not buffer:
            buffer = []
            return
        text = "\n".join(buffer).strip()
        if text:
            rowsAppend((kind, text))
        buffer = []

    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            if currentKind == "table":
                _flush(currentKind)
                currentKind = None
            elif currentKind == "text" and buffer:
                buffer.append("")
            continue

        nextKind = "table" if stripped.startswith("|") else "text"
        if currentKind is None:
            currentKind = nextKind
            buffer.append(stripped)
            continue

        if nextKind != currentKind:
            _flush(currentKind)
            currentKind = nextKind
        buffer.append(stripped)

    _flush(currentKind)
    return rows


_REPORT_ROW_SCHEMA: dict[str, pl.DataType] = {
    "chapter": pl.Utf8,
    "topic": pl.Utf8,
    "blockType": pl.Utf8,
    "blockOrder": pl.Int64,
    "sourceBlockOrder": pl.Int64,
    "text": pl.Utf8,
    "majorNum": pl.Int64,
    "orderSeq": pl.Int64,
    "sourceTopic": pl.Utf8,
}


def _reportRowsToTopicRows(
    subset: pl.DataFrame,
    contentCol: str,
) -> pl.DataFrame:
    """row 별 dict 누적 → 9 컬럼 list 누적 + polars DataFrame 반환.

    이전 list[dict] 누적은 51167 dict × ~3KB = ~163MB Python heap 의 최대
    leak source. 9 컬럼 list 누적 + 한 번 polars 변환으로 Python heap 회피.
    """
    chapters: list[str] = []
    topics: list[str] = []
    blockTypes: list[str] = []
    blockOrders: list[int] = []
    sourceBlockOrders: list[int] = []
    texts: list[str] = []
    majorNums: list[int] = []
    orderSeqs: list[int] = []
    sourceTopics: list[str] = []

    topicBlockCounts: dict[tuple[str, str], int] = {}
    currentMajorNum: int | None = None
    idx = 0
    pendingChapter: dict[str, object] | None = None
    chapterSubCount: dict[int, int] = {}
    if subset.is_empty():
        return pl.DataFrame(schema=_REPORT_ROW_SCHEMA)

    cols = subset.columns
    titleIdx = cols.index("section_title")
    contentIdx = cols.index(contentCol)

    def _registerContent(
        ch: str,
        tp: str,
        rawT: str,
        content: str,
        majorNum: int,
    ) -> None:
        nonlocal idx
        topicKey = (ch, tp)
        nextBlockOrder = topicBlockCounts.get(topicKey, 0)
        for blockType, blockText in _splitContentBlocks(content):
            chapters.append(ch)
            topics.append(tp)
            blockTypes.append(blockType)
            blockOrders.append(nextBlockOrder)
            sourceBlockOrders.append(nextBlockOrder)
            texts.append(blockText)
            majorNums.append(majorNum)
            orderSeqs.append(idx)
            sourceTopics.append(rawT)
            nextBlockOrder += 1
            idx += 1
        topicBlockCounts[topicKey] = nextBlockOrder

    def _flushPending() -> None:
        """chapter section 본문 등록 — sub-section 이 *없을 때만* (lonely chapter fallback).

        sub-section 이 있으면 chapter 본문은 sub 합본 (중복) — skip 으로 chapter mix
        차단. KB금융 같이 chapter 본문이 거의 비어있고 sub 도 없는 경우만 lonely
        등록. 옛 unique line 휴리스틱 (8자 임계 line 비교) 은 chapter header line
        ("I. 회사의 개요") 이 sub 본문에 없어 unique 로 잡혀 chapter 본문 통째
        등록 → chapter mix 회귀 — 본 fix 로 폐기.
        """
        nonlocal pendingChapter, idx
        if pendingChapter is None:
            return
        pTitle = str(pendingChapter.get("section_title") or "").strip()
        pContent = str(pendingChapter.get(contentCol) or "").strip()
        pMajor = parseMajorNum(pTitle)
        pendingChapter = None
        if pMajor is None or not pContent:
            return
        if chapterSubCount.get(pMajor, 0) > 0:
            # sub-section 본문 이미 등록됨 — chapter section 은 redundant.
            return
        ch = chapterFromMajorNum(pMajor)
        if ch is None:
            return
        rawT = stripSectionPrefix(pTitle)
        tp = mapSectionTitle(rawT)
        _registerContent(ch, tp, rawT, pContent, pMajor)

    for values in subset.iter_rows():
        title = str(values[titleIdx] or "").strip()
        content = str(values[contentIdx] or "")
        if not title or not content.strip():
            continue

        record = {
            "section_title": title,
            contentCol: content,
        }

        majorNum = parseMajorNum(title)
        if majorNum is not None:
            _flushPending()
            currentMajorNum = majorNum
            pendingChapter = record
            continue
        if currentMajorNum is None:
            continue

        chapter = chapterFromMajorNum(currentMajorNum)
        if chapter is None:
            continue

        rawTitle = stripSectionPrefix(title)
        topic = mapSectionTitle(rawTitle)
        _registerContent(
            chapter,
            topic,
            rawTitle,
            content.strip(),
            currentMajorNum,
        )
        chapterSubCount[currentMajorNum] = chapterSubCount.get(currentMajorNum, 0) + 1

    _flushPending()

    return pl.DataFrame(
        {
            "chapter": chapters,
            "topic": topics,
            "blockType": blockTypes,
            "blockOrder": blockOrders,
            "sourceBlockOrder": sourceBlockOrders,
            "text": texts,
            "majorNum": majorNums,
            "orderSeq": orderSeqs,
            "sourceTopic": sourceTopics,
        },
        schema=_REPORT_ROW_SCHEMA,
    )
