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
    pendingSubLines: set[str] = set()
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
        *,
        trackedSubLines: set[str] | None = None,
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
            if trackedSubLines is not None:
                for ln in blockText.splitlines():
                    s = ln.strip()
                    if s:
                        trackedSubLines.add(s)
        topicBlockCounts[topicKey] = nextBlockOrder

    def _registerPendingChapter() -> None:
        """chapter row 처리. sub-section 이 *없으면* 전체 등록 (lonely chapter).
        sub-section 이 *있으면* chapter content 의 block 중 sub-section 에 없는
        unique block 만 등록 — 옛 보고서의 chapter-only 표/본문 손실 차단."""
        nonlocal pendingChapter, pendingSubLines, idx
        if pendingChapter is None:
            pendingSubLines = set()
            return
        pTitle = str(pendingChapter.get("section_title") or "").strip()
        pContent = str(pendingChapter.get(contentCol) or "").strip()
        pMajor = parseMajorNum(pTitle)
        if pMajor is not None and pContent:
            ch = chapterFromMajorNum(pMajor)
            if ch is not None:
                rawT = stripSectionPrefix(pTitle)
                tp = mapSectionTitle(rawT)
                if not pendingSubLines:
                    _registerContent(ch, tp, rawT, pContent, pMajor)
                else:
                    uniqueBlocks: list[tuple[str, str]] = []
                    for blockType, blockText in _splitContentBlocks(pContent):
                        lines = [ln.strip() for ln in blockText.splitlines() if ln.strip()]
                        if not lines:
                            continue
                        missing = [ln for ln in lines if ln not in pendingSubLines]
                        # 8자 미만 line 만 있는 block 은 unique 후보에서 제외.
                        # pipeline.py 의 이전 ratio 50% 임계는 표 한두 줄 누락
                        # 케이스를 놓쳤음. 본 임계는 chapter-only 표 손실 차단 +
                        # sub-section 중복 차단의 균형점.
                        meaningful = [ln for ln in missing if len(ln) >= 8]
                        if meaningful:
                            uniqueBlocks.append((blockType, blockText))
                    if uniqueBlocks:
                        topicKey = (ch, tp)
                        nextBlockOrder = topicBlockCounts.get(topicKey, 0)
                        for blockType, blockText in uniqueBlocks:
                            chapters.append(ch)
                            topics.append(tp)
                            blockTypes.append(blockType)
                            blockOrders.append(nextBlockOrder)
                            sourceBlockOrders.append(nextBlockOrder)
                            texts.append(blockText)
                            majorNums.append(pMajor)
                            orderSeqs.append(idx)
                            sourceTopics.append(rawT)
                            nextBlockOrder += 1
                            idx += 1
                        topicBlockCounts[topicKey] = nextBlockOrder
        pendingChapter = None
        pendingSubLines = set()

    def _flushPending() -> None:
        _registerPendingChapter()

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
            pendingSubLines = set()
            continue
        if currentMajorNum is None:
            continue

        chapter = chapterFromMajorNum(currentMajorNum)
        if chapter is None:
            continue

        rawTitle = stripSectionPrefix(title)
        topic = mapSectionTitle(rawTitle)
        # section_title 자체를 content 앞에 prepend — text structure parser 가
        # heading 으로 인식하여 textPath 의 최상단에 박힘. placeholder도 자기
        # section heading 아래로 segmentKey 부여되어 cross-section alias 차단.
        contentWithTitle = f"{title}\n{content.strip()}"
        _registerContent(
            chapter,
            topic,
            rawTitle,
            contentWithTitle,
            currentMajorNum,
            trackedSubLines=pendingSubLines,
        )

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
