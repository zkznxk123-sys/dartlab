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


def _normalizeRowspanShift(tableMd: str) -> str:
    """markdown table 의 rowspan continuation 빈 cell 누락 정규화.

    회귀 사례 (005930 census table):
        | 구 분 | 자회사 | 사 유 |
        | --- | --- | --- |
        | 신규연결 | RAINBOW... | 지분취득 |
        | Harman... | 설립 |  |          ← col 0 비어야 하는데 col 0 에 내용, col 2 empty
        | Viper... | 인수 |  |            ← 같은 shift 패턴

    원본 parquet 가 HTML rowspan="N" 셀 continuation 을 markdown 변환 시 빈 cell
    pad 누락 → 모든 후속 row 가 왼쪽으로 1 칸 shift.

    detection: header N 컬럼, body row 중 N 컬럼 이면서 마지막 cell empty + 첫 cell
    non-empty 인 row 가 *전체 body row 의 30% 이상* 이면 shift 패턴 판정. 해당 row
    들의 cells 를 right-shift 1 (빈 cell pad at position 0, drop last empty cell).

    회피 case (shift X): legit 한 row 별 trailing-empty (예: 마지막 col 이 "비고"
    이고 비고 누락 row 가 많은 경우) — 이 경우 shift 안 함 (앞 row 들도 같은 패턴).
    """
    # 핫 패스 short-circuit — shift signature (`|  |` / `| |` trailing empty cell)
    # 가 3 회 미만이면 shift 패턴 임계 (30%) 만족 불가능. 5 baseline profile 에서
    # 59k 호출 × 1.6ms = 94s 소비 → 대부분 case (shift X) 의 full parse 회피.
    quickMarker = tableMd.count("|  |") + tableMd.count("| |")
    if quickMarker < 3:
        return tableMd

    lines = tableMd.split("\n")
    if len(lines) < 4:
        return tableMd

    # 단일 패스 parse — line index 별 cells (table line 만). 비 table 은 cellsByIdx 에 없음.
    cellsByIdx: dict[int, list[str]] = {}
    isSepByIdx: dict[int, bool] = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        cellsByIdx[i] = cells
        # separator (---:- only) 검사
        isSep = any(cells) and all(not c or set(c) <= {"-", ":"} for c in cells)
        isSepByIdx[i] = isSep

    # 첫 valid header (non-separator, ≥3 cols, all non-empty)
    headerCols: int | None = None
    headerIdx = -1
    for i, cells in cellsByIdx.items():
        if isSepByIdx[i]:
            continue
        if len(cells) >= 3 and all(cells):
            headerCols = len(cells)
            headerIdx = i
            break
    if headerCols is None or headerCols < 3:
        return tableMd

    # body rows (header 이후, col count 일치, non-separator)
    bodyIdxs = [
        i for i, cells in cellsByIdx.items() if i > headerIdx and not isSepByIdx[i] and len(cells) == headerCols
    ]
    if len(bodyIdxs) < 3:
        return tableMd

    # shift candidate: last cell empty + first non-empty + middle all non-empty
    shiftIdxs: list[int] = []
    for i in bodyIdxs:
        cells = cellsByIdx[i]
        if cells[-1] != "":
            continue
        if cells[0] == "":
            continue
        # middle cells all non-empty
        if any(not c for c in cells[1:-1]):
            continue
        shiftIdxs.append(i)
    if len(shiftIdxs) * 10 < len(bodyIdxs) * 3:  # < 30% — int 비교로 float 회피
        return tableMd

    # shift 적용 — 해당 idx 의 line 만 rewrite
    rewritten = list(lines)
    for i in shiftIdxs:
        cells = cellsByIdx[i]
        newCells = [""] + cells[:-1]
        rewritten[i] = "| " + " | ".join(newCells) + " |"
    return "\n".join(rewritten)


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
            if kind == "table":
                text = _normalizeRowspanShift(text)
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
    chapterSubContents: dict[int, list[str]] = {}
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
        """chapter section 본문 등록 — sub-section 본문 substring 제외 후 *남은 unique* 만.

        Roman chapter section ("I. 회사의 개요") 본문은 보통 그 chapter 의 sub-section
        들 (1. 회사의 개요 / 2. 회사의 연혁 / ...) 본문의 합본 — 그대로 등록하면
        다른 chapter (회사의 연혁/자본금/주식의 총수 등) 본문이 같은 topic 안 mix
        들어옴.

        정공법: chapter 본문에서 등록된 sub 본문 substring 들을 제거 → 남은
        unique 부분 (예: chapter 본문에만 있는 추가 설명) 만 추출하여 등록. sub
        없는 lonely chapter (KB금융 chapter intro 같은 case) 는 통째 등록.

        옛 unique line 휴리스틱 (8자 임계 line 비교) 은 chapter header line ("I. 회사의 개요")
        이 sub 본문에 없어 unique 로 잡혀 chapter 본문 통째 등록 → chapter mix 회귀.
        substring 비교는 sub 본문 전체가 chapter 본문에 *그대로 포함* 된 경우 정확히 제거.
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
        ch = chapterFromMajorNum(pMajor)
        if ch is None:
            return
        rawT = stripSectionPrefix(pTitle)
        tp = mapSectionTitle(rawT)

        subContents = chapterSubContents.get(pMajor, [])
        if not subContents:
            # sub-section 0 → lonely chapter 통째 등록
            _registerContent(ch, tp, rawT, pContent, pMajor)
            return

        # sub 본문 substring 제거 — 긴 것 먼저 (중복 제거 안전)
        remainder = pContent
        for sub in sorted(subContents, key=len, reverse=True):
            if sub and sub in remainder:
                remainder = remainder.replace(sub, "\n")
        # heading-only line / 짧은 noise 제거 후 의미있는 잔여 본문만
        meaningfulLines = [ln.strip() for ln in remainder.splitlines() if len(ln.strip()) >= 8]
        if not meaningfulLines:
            return
        meaningfulText = "\n".join(meaningfulLines).strip()
        if len(meaningfulText) < 20:
            return
        _registerContent(ch, tp, rawT, meaningfulText, pMajor)

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
            # chapter heading row 별도 emit — section_title "1. 회사의 개요" / "2. 회사의 연혁"
            # 자체를 sections frame 의 textLevel=2 heading row 로 등록. expansion.py 의
            # parseTextStructureWithState 가 stack root 로 인식 → 후속 sub-heading 의
            # textPath 가 chapter level 부터 시작 (예 "회사의 개요 > 연결대상 종속회사 개황 > ...").
            # 이전엔 chapter title 이 textPath stack seed 로만 쓰이고 별도 row 안 됨 → sections
            # frame 에 chapter level row 부재 (원본 그대로 보존 위배).
            chapterForRoman = chapterFromMajorNum(majorNum)
            if chapterForRoman is not None:
                chapterLabel = stripSectionPrefix(title)
                chapterTopic = mapSectionTitle(chapterLabel)
                if chapterTopic:
                    _registerContent(
                        chapterForRoman,
                        chapterTopic,
                        chapterLabel,
                        title,
                        majorNum,
                    )
            continue
        if currentMajorNum is None:
            continue

        chapter = chapterFromMajorNum(currentMajorNum)
        if chapter is None:
            continue

        rawTitle = stripSectionPrefix(title)
        topic = mapSectionTitle(rawTitle)
        cleanedContent = content.strip()
        _registerContent(
            chapter,
            topic,
            rawTitle,
            cleanedContent,
            currentMajorNum,
        )
        chapterSubContents.setdefault(currentMajorNum, []).append(cleanedContent)

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
