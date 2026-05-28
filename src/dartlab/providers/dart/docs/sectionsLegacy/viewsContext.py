"""sections context 슬라이스 뷰 — splitContextText / splitMarkdownTable / contextSlices.

views.py 1175 LoC 분할 (룰 3 LoC 임계 회피). 본 모듈은 retrievalBlocks 결과를
LLM 컨텍스트 한계 (예 1800 자) 이하 슬라이스로 분할.
"""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.docs.sectionsLegacy.viewsRetrieval import retrievalBlocks


def splitContextText(text: str, maxChars: int) -> list[str]:
    """텍스트를 maxChars 이하의 줄 단위 청크로 분할한다.

    Args:
        text: 인자.
        maxChars: 인자.

    Raises:
        없음.

    Example:
        >>> splitContextText(...)

    Returns:
        list[str] — 슬라이스 리스트.

    SeeAlso:
        - ``viewsRetrieval`` / ``views.py`` — 분할 모듈.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections retrievalBlocks → maxChars 슬라이스 분할 → contextSlices DataFrame.

    Guide:
        - 사용자 API 는 ``c.contextSlices`` — 본 모듈 직접 호출 X.

    AIContext:
        internal context slice view — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections contextSlices 분리.
            - maxChars 너무 작음 (< 500) → 슬라이스 너무 많음.
        OutputSchema:
            - list[str] / pl.DataFrame — 함수별.
        Prerequisites:
            - retrievalBlocks 결과.
        Freshness:
            - sections 갱신 시점.
        Dataflow:
            - retrievalBlocks → maxChars 슬라이스 → contextSlices DataFrame.
        TargetMarkets:
            - KR (DART) context slice.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= maxChars:
        return [text]
    parts: list[str] = []
    lines = text.splitlines()
    buffer: list[str] = []
    currentLen = 0
    for line in lines:
        extra = len(line) + (1 if buffer else 0)
        if buffer and currentLen + extra > maxChars:
            parts.append("\n".join(buffer).strip())
            buffer = [line]
            currentLen = len(line)
        else:
            buffer.append(line)
            currentLen += extra
    if buffer:
        parts.append("\n".join(buffer).strip())
    return [part for part in parts if part]


def splitMarkdownTable(text: str, maxChars: int) -> list[str]:
    """마크다운 테이블을 헤더를 유지하며 maxChars 이하 청크로 분할한다.

    Args:
        text: 인자.
        maxChars: 인자.

    Raises:
        없음.

    Example:
        >>> splitMarkdownTable(...)

    Returns:
        list[str] — 슬라이스 리스트.

    SeeAlso:
        - ``viewsRetrieval`` / ``views.py`` — 분할 모듈.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections retrievalBlocks → maxChars 슬라이스 분할 → contextSlices DataFrame.

    Guide:
        - 사용자 API 는 ``c.contextSlices`` — 본 모듈 직접 호출 X.

    AIContext:
        internal context slice view — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections contextSlices 분리.
            - maxChars 너무 작음 (< 500) → 슬라이스 너무 많음.
        OutputSchema:
            - list[str] / pl.DataFrame — 함수별.
        Prerequisites:
            - retrievalBlocks 결과.
        Freshness:
            - sections 갱신 시점.
        Dataflow:
            - retrievalBlocks → maxChars 슬라이스 → contextSlices DataFrame.
        TargetMarkets:
            - KR (DART) context slice.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    joined = "\n".join(lines).strip()
    if len(joined) <= maxChars:
        return [joined]

    header = lines[:2]
    body = lines[2:] if len(lines) > 2 else []
    if not body:
        return [joined]

    parts: list[str] = []
    current: list[str] = []
    for line in body:
        candidate = "\n".join(header + current + [line]).strip()
        if current and len(candidate) > maxChars:
            parts.append("\n".join(header + current).strip())
            current = [line]
            continue
        current.append(line)
    if current:
        parts.append("\n".join(header + current).strip())
    return [part for part in parts if part]


def contextSlices(stockCode: str, *, maxChars: int = 1800) -> pl.DataFrame:
    """retrievalBlocks를 maxChars 이하 슬라이스로 분할한 LLM 컨텍스트용 DataFrame을 생성한다.

    Args:
        stockCode: 인자.
        maxChars: 인자.

    Raises:
        없음.

    Example:
        >>> contextSlices(...)

    Returns:
        pl.DataFrame — contextSlices 결과.

    SeeAlso:
        - ``viewsRetrieval`` / ``views.py`` — 분할 모듈.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections retrievalBlocks → maxChars 슬라이스 분할 → contextSlices DataFrame.

    Guide:
        - 사용자 API 는 ``c.contextSlices`` — 본 모듈 직접 호출 X.

    AIContext:
        internal context slice view — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections contextSlices 분리.
            - maxChars 너무 작음 (< 500) → 슬라이스 너무 많음.
        OutputSchema:
            - list[str] / pl.DataFrame — 함수별.
        Prerequisites:
            - retrievalBlocks 결과.
        Freshness:
            - sections 갱신 시점.
        Dataflow:
            - retrievalBlocks → maxChars 슬라이스 → contextSlices DataFrame.
        TargetMarkets:
            - KR (DART) context slice.
    """
    blocks = retrievalBlocks(stockCode)
    rows: list[dict[str, object]] = []
    for record in blocks.to_dicts():
        isSemantic = record.get("semanticTopic") is not None or record.get("detailTopic") is not None
        if record.get("isBoilerplate") or (record.get("isPlaceholder") and not isSemantic):
            continue
        blockText = str(record["blockText"] or "")
        if record["blockType"] == "table":
            parts = splitMarkdownTable(blockText, maxChars)
        else:
            parts = splitContextText(blockText, maxChars)
        for idx, part in enumerate(parts):
            rows.append(
                {
                    "stockCode": stockCode,
                    "period": record["period"],
                    "periodOrder": record["periodOrder"],
                    "topic": record["topic"],
                    "sourceTopic": record.get("sourceTopic"),
                    "cellKey": record.get("cellKey"),
                    "semanticTopic": record.get("semanticTopic"),
                    "detailTopic": record.get("detailTopic"),
                    "blockType": record["blockType"],
                    "blockLabel": record["blockLabel"],
                    "sliceIdx": idx,
                    "sliceText": part,
                    "chars": len(part),
                    "isSemantic": isSemantic,
                    "isTable": record["blockType"] == "table",
                    "isBoilerplate": record.get("isBoilerplate"),
                    "isPlaceholder": record.get("isPlaceholder"),
                    "blockPriority": record.get("blockPriority"),
                }
            )
    df = pl.DataFrame(
        rows,
        schema={
            "stockCode": pl.Utf8,
            "period": pl.Utf8,
            "periodOrder": pl.Int64,
            "topic": pl.Utf8,
            "sourceTopic": pl.Utf8,
            "cellKey": pl.Utf8,
            "semanticTopic": pl.Utf8,
            "detailTopic": pl.Utf8,
            "blockType": pl.Utf8,
            "blockLabel": pl.Utf8,
            "sliceIdx": pl.Int64,
            "sliceText": pl.Utf8,
            "chars": pl.Int64,
            "isSemantic": pl.Boolean,
            "isTable": pl.Boolean,
            "isBoilerplate": pl.Boolean,
            "isPlaceholder": pl.Boolean,
            "blockPriority": pl.Int64,
        },
        strict=False,
    )
    return df.sort(
        ["periodOrder", "blockPriority", "topic", "sliceIdx"],
        descending=[True, True, False, False],
    )
