"""sections 파생 뷰 생성 helpers."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle, stripSectionPrefix
from dartlab.providers.dart.docs.sections.pipeline import iterPeriodSubsets
from dartlab.providers.dart.docs.sections.sectionsBase import (
    periodOrderValue,
    sortPeriods,
)

RE_MAJOR = re.compile(r"^([가-힣])\.\s*(.+)$")
RE_MINOR = re.compile(r"^\((\d+)\)\s*(.+)$")


def normalizeTitle(title: str) -> str:
    """section title에서 업종 접두사를 제거하고 정규화한다.

    Args:
        title: 인자.

    Raises:
        없음.

    Example:
        >>> normalizeTitle(...)

    Returns:
        str — 변환 결과.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    return stripSectionPrefix((title or "").strip())


def isBoilerplateTopic(topic: str) -> bool:
    """보일러플레이트 topic(표지, 확인서 등)인지 판별한다.

    Args:
        topic: 인자.

    Raises:
        없음.

    Example:
        >>> isBoilerplateTopic(...)

    Returns:
        bool — 판정 결과.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    return topic in {
        "사업보고서",
        "분기보고서",
        "반기보고서",
        "정정신고(보고)",
        "ceoConfirmation",
    }


def isPlaceholderBlock(blockText: str) -> bool:
    """분기/반기보고서 미기재 안내 문구인지 판별한다.

    Args:
        blockText: 인자.

    Raises:
        없음.

    Example:
        >>> isPlaceholderBlock(...)

    Returns:
        bool — 판정 결과.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    text = blockText.strip()
    if not text:
        return False
    phrases = (
        "분기보고서에 기재하지 않습니다",
        "반기보고서에 기재하지 않습니다",
        "반기ㆍ사업보고서에 기재 예정",
        "반기·사업보고서에 기재 예정",
        "기업공시서식 작성기준에 따라 분기보고서에 기재하지 않습니다",
    )
    return any(phrase in text for phrase in phrases)


def blockPriority(
    blockType: str,
    semanticTopic: str | None,
    detailTopic: str | None,
    isBoilerplate: bool,
    isPlaceholder: bool,
) -> int:
    """블록의 정보 가치에 따라 우선순위 점수(0~5)를 반환한다.

    Args:
        blockType: 인자.
        semanticTopic: 인자.
        detailTopic: 인자.
        isBoilerplate: 인자.
        isPlaceholder: 인자.

    Raises:
        없음.

    Example:
        >>> blockPriority(...)

    Returns:
        int — 결과 수.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    if isBoilerplate:
        return 0
    if isPlaceholder:
        return 0
    if detailTopic:
        return 5
    if semanticTopic:
        return 4
    if blockType == "text":
        return 3
    if blockType == "heading":
        return 2
    return 1


def classifyContent(content: str) -> tuple[int, int, int]:
    """마크다운 콘텐츠의 텍스트/테이블/헤딩 줄 수를 세어 반환한다.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> classifyContent(...)

    Returns:
        tuple[int, int, int] — 3 정수 결과.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    table_lines = 0
    heading_lines = 0
    text_lines = 0
    for raw in (content or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("|"):
            table_lines += 1
            continue
        if RE_MAJOR.match(line) or RE_MINOR.match(line):
            heading_lines += 1
            continue
        text_lines += 1
    return text_lines, table_lines, heading_lines


def buildMarkdownBlocks(stockCode: str) -> pl.DataFrame:
    """종목의 전 기간 parquet에서 section별 마크다운 블록 DataFrame을 생성한다.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> buildMarkdownBlocks(...)

    Returns:
        pl.DataFrame — 결과.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    rows: list[dict[str, object]] = []

    for period, _reportKind, ccol, subset in iterPeriodSubsets(stockCode):
        for record in subset.to_dicts():
            rawTitle = normalizeTitle(str(record["section_title"] or ""))
            if not rawTitle:
                continue
            content = str(record[ccol] or "")
            textLines, tableLines, headingLines = classifyContent(content)
            rows.append(
                {
                    "stockCode": stockCode,
                    "period": period,
                    "periodOrder": periodOrderValue(period),
                    "sectionOrder": int(record["section_order"]),
                    "rawTitle": rawTitle,
                    "topic": mapSectionTitle(rawTitle),
                    "rawMarkdown": content,
                    "textLines": textLines,
                    "tableLines": tableLines,
                    "headingLines": headingLines,
                }
            )

    return pl.DataFrame(rows)


def buildMarkdownWide(blocks: pl.DataFrame) -> pl.DataFrame:
    """마크다운 블록을 topic x period wide 형태로 피벗한다.

    Args:
        blocks: 인자.

    Raises:
        없음.

    Example:
        >>> buildMarkdownWide(...)

    Returns:
        pl.DataFrame — 결과.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    if blocks.height == 0:
        return pl.DataFrame()

    merged = (
        blocks.group_by(["topic", "period"])
        .agg(
            pl.col("rawMarkdown").implode().list.join("\n\n").alias("rawMarkdown"),
            pl.col("rawTitle").n_unique().alias("rawTitleVariants"),
            pl.col("sectionOrder").min().alias("firstOrder"),
        )
        .sort(["firstOrder", "topic", "period"])
    )

    periods = sortPeriods(merged.get_column("period").unique().to_list())
    wide = merged.select(["topic", "period", "rawMarkdown"]).pivot(
        on="period", index="topic", values="rawMarkdown"
    )  # polars-streaming-unsupported: pivot
    existing = [period for period in periods if period in wide.columns]
    return wide.select(["topic", *existing])


def splitMarkdownBlocks(content: str) -> list[dict[str, object]]:
    """마크다운 원문을 heading/text/table 블록 단위로 분리한다.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> splitMarkdownBlocks(...)

    Returns:
        list[dict[str, object]] — 결과 dict 리스트.

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    rows: list[dict[str, object]] = []
    currentLabel = "(root)"
    textBuffer: list[str] = []
    tableBuffer: list[str] = []
    blockIndex = 0

    def flushText() -> None:
        """flushText — TODO 한국어 동작 설명.

        Raises:
            없음.

        Example:
            >>> flushText(...)

        SeeAlso:
            - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - sections 파생 뷰 helper — title 정규화 / major/minor 분할 / 마크다운 빌드.

        Guide:
            - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

        AIContext:
            internal views helper — AI 직접 호출 X.
        """
        nonlocal textBuffer, blockIndex
        text = "\n".join(textBuffer).strip()
        if text:
            rows.append(
                {
                    "blockIdx": blockIndex,
                    "blockType": "text",
                    "blockLabel": currentLabel,
                    "blockText": text,
                    "tableLines": 0,
                }
            )
            blockIndex += 1
        textBuffer = []

    def flushTable() -> None:
        """flushTable — TODO 한국어 동작 설명.

        Raises:
            없음.

        Example:
            >>> flushTable(...)

        SeeAlso:
            - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - sections 파생 뷰 helper — title 정규화 / major/minor 분할 / 마크다운 빌드.

        Guide:
            - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

        AIContext:
            internal views helper — AI 직접 호출 X.
        """
        nonlocal tableBuffer, blockIndex
        text = "\n".join(tableBuffer).strip()
        if text:
            rows.append(
                {
                    "blockIdx": blockIndex,
                    "blockType": "table",
                    "blockLabel": currentLabel,
                    "blockText": text,
                    "tableLines": len(tableBuffer),
                }
            )
            blockIndex += 1
        tableBuffer = []

    def flushAll() -> None:
        """flushAll — TODO 한국어 동작 설명.

        Raises:
            없음.

        Example:
            >>> flushAll(...)

        SeeAlso:
            - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - sections 파생 뷰 helper — title 정규화 / major/minor 분할 / 마크다운 빌드.

        Guide:
            - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

        AIContext:
            internal views helper — AI 직접 호출 X.
        """
        flushText()
        flushTable()

    for raw in content.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flushTable()
            if textBuffer:
                textBuffer.append("")
            continue
        if stripped.startswith("|"):
            flushText()
            tableBuffer.append(stripped)
            continue
        if RE_MAJOR.match(stripped) or RE_MINOR.match(stripped):
            flushAll()
            currentLabel = stripped
            rows.append(
                {
                    "blockIdx": blockIndex,
                    "blockType": "heading",
                    "blockLabel": stripped,
                    "blockText": stripped,
                    "tableLines": 0,
                }
            )
            blockIndex += 1
            continue
        flushTable()
        textBuffer.append(stripped)

    flushAll()
    return rows


def saveView(df: pl.DataFrame, path: Path) -> None:
    """DataFrame을 parquet 파일로 저장한다.

    Args:
        df: 인자.
        path: 인자.

    Raises:
        없음.

    Example:
        >>> saveView(...)

    SeeAlso:
        - ``viewsRetrieval`` / ``viewsContext`` — retrieval/context 분리 위임.
        - ``pipeline.py`` — sections 빌더.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections 파생 뷰 (마크다운 빌더 / 청크 / 컨텍스트 슬라이스 / 검색 블록) helpers.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal views — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - sections → 파생 뷰 (마크다운 빌더 / 청크 분할 등).
        TargetMarkets:
            - KR (DART) sections 파생 뷰.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)


# ── 분할 (룰 3 LoC) ───────────────────────────────────────────────
# views.py 1175 LoC → 본 파일 + viewsRetrieval + viewsContext 3 파일로 분할.
# 외부 caller 호환 위해 본 모듈에서 re-export.
from dartlab.providers.dart.docs.sections.viewsContext import (
    contextSlices,
    splitContextText,
    splitMarkdownTable,
)
from dartlab.providers.dart.docs.sections.viewsRetrieval import retrievalBlocks

__all__ = [
    "blockPriority",
    "buildMarkdownBlocks",
    "buildMarkdownWide",
    "classifyContent",
    "contextSlices",
    "isBoilerplateTopic",
    "isPlaceholderBlock",
    "normalizeTitle",
    "retrievalBlocks",
    "saveView",
    "splitContextText",
    "splitMarkdownBlocks",
    "splitMarkdownTable",
]
