"""공시뷰어 presentation layer.

Company.panel()와 프론트엔드 사이의 변환 레이어.
sections 원본 데이터를 프론트엔드가 바로 렌더링할 수 있는 구조로 변환한다.

핵심:
- 블록 분류: finance / report / text / structured / raw_markdown
- finance topic은 sections 우회 → 속도 보장
- text 블록에 changeSummary + inline diff 포함
- 블록 메타데이터 (단위, 스케일, periods 등)
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company

_PERIOD_RE = re.compile(r"^\d{4}(Q[1-4])?$")
_FINANCE_TOPICS = frozenset({"BS", "IS", "CIS", "CF", "SCE", "ratios"})
# Phase B 슬림화 — _MAX_DIFF_PAIRS / _MAX_ANNOTATE_PERIODS 폐기 (changeSummary 의존).


def _isPeriod(name: str) -> bool:
    return bool(_PERIOD_RE.fullmatch(name))


def _periodCols(df: pl.DataFrame) -> list[str]:
    return [c for c in df.columns if _isPeriod(c)]


BlockKind = Literal["text", "structured", "raw_markdown", "finance", "report"]
TextSectionStatus = Literal["stable", "updated", "new", "stale"]
TextViewStatus = Literal["stable", "updated", "new"]
PeriodKind = Literal["annual", "quarterly"]
# Phase B 슬림화 — DiffChunkKind 폐기 (ViewerDiffChunk 의존).


@dataclass
class BlockMeta:
    """블록 표시 메타데이터."""

    unit: str | None = None
    scale: str | None = None
    scaleDivisor: float = 1.0
    periods: list[str] = field(default_factory=list)
    rowCount: int = 0
    colCount: int = 0


# Phase B 슬림화 — InlineDiff/AnnotatedLine/ChangeDigest/ChangeDigestItem/ChangeSummary/
# ViewerDiffChunk dataclass 일괄 폐기. frontend 가 모두 미사용 (sections cell value 그대로
# 소비). 관련 함수 (_buildChangeSummary / _computeInlineDiff / _buildDigest /
# _buildAnnotatedBlame / _serializeChangeDigest / _serializeViewerDiffChunk) 도 동시 폐기.


@dataclass
class ViewerBlock:
    """프론트엔드가 소비하는 블록 단위."""

    block: int
    kind: BlockKind
    source: str
    data: pl.DataFrame | None = None
    meta: BlockMeta = field(default_factory=BlockMeta)
    rawMarkdown: dict[str, str] | None = None
    textType: str | None = None  # "heading" | "body" | None (non-text)
    textLevel: int | None = None  # sections textLevel (heading 계층 1~4)


@dataclass
class PeriodRef:
    """절대 기간 라벨의 canonical 표현."""

    label: str
    year: int
    quarter: int | None = None
    kind: PeriodKind = "annual"
    sortKey: int = 0


@dataclass
class ViewerTextHeading:
    """body section을 위한 구조 anchor heading."""

    block: int
    text: str
    period: PeriodRef
    level: int = 0  # heading 계층 (1~4, 0=unknown)


@dataclass
class ViewerTextView:
    """특정 period snapshot — sections row cell value 그대로 (Phase B 슬림화).

    이전 diff (ViewerDiffChunk list) / digest (ChangeDigest) 폐기 — frontend SectionRow
    가 body 만 사용, position-anchored diff / 변경 요약 카드 미사용.
    """

    period: PeriodRef
    prevPeriod: PeriodRef | None = None
    body: str = ""
    status: TextViewStatus = "stable"


@dataclass
class ViewerTextTimelineEntry:
    """section 상단 timeline item."""

    period: PeriodRef
    prevPeriod: PeriodRef | None = None
    status: TextViewStatus = "stable"


@dataclass
class ViewerTextSection:
    """텍스트 전용 보고서의 본문 섹션."""

    id: str
    order: int
    bodyBlock: int
    headingPath: list[ViewerTextHeading] = field(default_factory=list)
    latest: ViewerTextView | None = None
    latestPeriod: PeriodRef | None = None
    firstPeriod: PeriodRef | None = None
    periodCount: int = 0
    status: TextSectionStatus = "stable"
    latestChange: str | None = None
    preview: str | None = None
    timeline: list[ViewerTextTimelineEntry] = field(default_factory=list)


@dataclass
class ViewerDocumentEntry:
    """textDocument의 통합 항목 — text section 또는 non-text block 참조."""

    kind: str  # "section" | "block_ref"
    order: int  # blockOrder 기반 정렬 키
    sectionId: str | None = None  # kind="section"일 때 — sections[].id
    blockRef: int | None = None  # kind="block_ref"일 때 — blocks[].block 번호
    blockKind: str | None = None  # "structured" | "finance" | "raw_markdown" 등
    headingPath: list[ViewerTextHeading] = field(default_factory=list)
    # 본 entry 가 어느 heading 들 아래 박혀야 하는지의 ancestor list.
    # text body 의 ViewerTextSection.headingPath 와 동등 — 표/structured/finance
    # block 위에도 동일 heading 계층 표시할 수 있게 SSOT. viewer.py 의
    # pendingHeadings level-pop 누적에서 snapshot.


@dataclass
class ViewerTextDocument:
    """인터리브 문서 — text section과 non-text block을 원본 순서대로."""

    topic: str
    mode: str = "timeline_text"
    periods: list[PeriodRef] = field(default_factory=list)
    latestPeriod: PeriodRef | None = None
    firstPeriod: PeriodRef | None = None
    sectionCount: int = 0
    updatedCount: int = 0
    newCount: int = 0
    staleCount: int = 0
    stableCount: int = 0
    sections: list[ViewerTextSection] = field(default_factory=list)
    entries: list[ViewerDocumentEntry] = field(default_factory=list)


# ── 메인 진입점 ──


def viewerBlocks(company: Company, topic: str) -> list[ViewerBlock]:
    """topic의 모든 블록을 ViewerBlock 리스트로 반환.

    Args:
        company: 인자.
        topic: 인자.

    Raises:
        없음.

    Example:
        >>> viewerBlocks(...)

    Returns:
        list[ViewerBlock] — 블록 리스트.
    """
    if topic in _FINANCE_TOPICS:
        blk = _buildFinanceBlock(company, topic)
        return [blk] if blk else []

    sec = company.sections
    if sec is None:
        return []

    topicFrame = sec.filter(pl.col("topic") == topic)
    if topicFrame.is_empty():
        return []

    periodCols = _periodCols(topicFrame)
    blocks: list[ViewerBlock] = []

    if "blockOrder" not in topicFrame.columns:
        return []

    blockOrders = topicFrame["blockOrder"].unique().sort().to_list()

    for bo in blockOrders:
        boRows = topicFrame.filter(pl.col("blockOrder") == bo)
        bt = boRows["blockType"][0] if "blockType" in boRows.columns else "text"
        source = boRows["source"][0] if "source" in boRows.columns else "docs"

        if source == "finance":
            blk = _buildFinanceBlock(company, topic)
            if blk:
                blk.block = bo
                blocks.append(blk)
        elif source == "report":
            blk = _buildReportBlock(company, topic, bo)
            if blk:
                blocks.append(blk)
        elif bt == "text":
            blk = _buildTextBlock(boRows, bo, periodCols)
            if blk:
                blocks.append(blk)
        elif bt == "table":
            blk = _buildTableBlock(company, topic, topicFrame, bo, periodCols)
            if blk:
                blocks.append(blk)

    return blocks


def viewerTextDocument(topic: str, blocks: list[ViewerBlock]) -> ViewerTextDocument | None:
    """인터리브 문서 — text section과 non-text block을 원본 순서대로 구성.

    - body text block → ViewerTextSection (timeline/diff 포함)
    - heading block → 다음 body의 headingPath로 흡수
    - non-text block → ViewerDocumentEntry(kind="block_ref")로 원본 위치 보존
    - entries가 원본 blockOrder 순서를 그대로 유지

    Args:
        topic: 인자.
        blocks: 인자.

    Raises:
        없음.

    Example:
        >>> viewerTextDocument(...)

    Returns:
        ViewerTextDocument 또는 None — 텍스트 문서.
    """
    textBlocks = [b for b in blocks if b.kind == "text"]
    if not textBlocks:
        # text가 없어도 non-text block만으로 entries 구성 가능
        nonTextBlocks = [b for b in blocks if b.kind != "text"]
        if not nonTextBlocks:
            return None
        entries = [
            ViewerDocumentEntry(
                kind="block_ref",
                order=b.block,
                blockRef=b.block,
                blockKind=b.kind,
            )
            for b in sorted(nonTextBlocks, key=lambda item: item.block)
        ]
        return ViewerTextDocument(topic=topic, entries=entries)

    textPeriods = sorted(
        {period for block in textBlocks for period in _textPeriodMap(block).keys()},
        key=_periodSortKey,
    )
    if not textPeriods:
        return None

    topicLatestPeriod = textPeriods[-1]
    sections: list[ViewerTextSection] = []
    entries: list[ViewerDocumentEntry] = []
    # heading stack (level-pop 누적) — 새 heading 만나면 같거나 더 깊은 level 을 pop 후 push.
    # body/table 등 consumer 만나면 stack snapshot 만 attach, *reset 안 함* — chapter ancestor
    # 가 sub-section table 위에도 살아남음.
    # 이전 reset 패턴은 첫 body 가 모든 heading 을 먹어버려 후속 표 위에 chapter 표시 0.
    # 같은 chapter 안 sub heading 사이에서는 같은 level pop 으로 자연 교체.
    pendingHeadings: list[ViewerBlock] = []

    def _materializeHeadingPath(blocksList: list[ViewerBlock]) -> list[ViewerTextHeading]:
        """ViewerBlock 들을 ViewerTextHeading 으로 변환 — heading 의 *전체 latest* cell value 사용.

        이전엔 _selectNearestPeriodText(map, topicLatestPeriod) 가 nearest fallback 으로
        target 에 cell 없으면 다른 period 값으로 추측 → 원문에 없는 텍스트가 흘러나가는
        회귀. fallback 폐기 후 strict 만 — 단 heading 의 자체 latest cell value 가 있으면
        그것 사용 (heading 의 본문 내 실재 표기).
        """
        out: list[ViewerTextHeading] = []
        for headingBlock in blocksList:
            headingPeriodMap = _textPeriodMap(headingBlock)
            chosenPeriod, headingText = _selectNearestPeriodText(headingPeriodMap, None)
            if headingText is None or chosenPeriod is None:
                continue
            out.append(
                ViewerTextHeading(
                    block=headingBlock.block,
                    text=headingText,
                    period=_periodRef(chosenPeriod),
                    level=headingBlock.textLevel or _headingLevel(headingText),
                )
            )
        return out

    def _blockHeadingLevel(block: ViewerBlock) -> int:
        if isinstance(block.textLevel, int) and block.textLevel > 0:
            return block.textLevel
        periodMap = _textPeriodMap(block)
        _, headingText = _selectNearestPeriodText(periodMap, None)
        return _headingLevel(headingText or "") or 99

    def _pushHeadingLevelPop(block: ViewerBlock) -> None:
        """heading block push — 같거나 더 깊은 level 은 pop 후 추가 (chapter ancestor 살리기)."""
        newLevel = _blockHeadingLevel(block)
        while pendingHeadings:
            topLevel = _blockHeadingLevel(pendingHeadings[-1])
            if topLevel >= newLevel:
                pendingHeadings.pop()
            else:
                break
        pendingHeadings.append(block)

    for block in sorted(blocks, key=lambda item: item.block):
        if block.kind == "text" and block.textType == "heading":
            _pushHeadingLevelPop(block)
            continue

        if block.kind == "text" and block.textType == "body":
            section = _buildTextSection(
                topic=topic,
                block=block,
                headingBlocks=pendingHeadings,
                order=len(sections),
                topicLatestPeriod=topicLatestPeriod,
            )
            if section is not None:
                sections.append(section)
                entries.append(
                    ViewerDocumentEntry(
                        kind="section",
                        order=block.block,
                        sectionId=section.id,
                        headingPath=list(section.headingPath),
                    )
                )
            continue

        entryHeadingPath = _materializeHeadingPath(pendingHeadings)
        entries.append(
            ViewerDocumentEntry(
                kind="block_ref",
                order=block.block,
                blockRef=block.block,
                blockKind=block.kind,
                headingPath=entryHeadingPath,
            )
        )

    if not sections and not entries:
        return None

    updatedCount = sum(1 for s in sections if s.status == "updated")
    newCount = sum(1 for s in sections if s.status == "new")
    staleCount = sum(1 for s in sections if s.status == "stale")
    stableCount = sum(1 for s in sections if s.status == "stable")

    return ViewerTextDocument(
        topic=topic,
        periods=[_periodRef(period) for period in sorted(textPeriods, key=_periodSortKey, reverse=True)],
        latestPeriod=_periodRef(textPeriods[-1]),
        firstPeriod=_periodRef(textPeriods[0]),
        sectionCount=len(sections),
        updatedCount=updatedCount,
        newCount=newCount,
        staleCount=staleCount,
        stableCount=stableCount,
        sections=sections,
        entries=entries,
    )


# ── Finance 블록 ──


def _buildFinanceBlock(company: Company, topic: str) -> ViewerBlock | None:
    """finance topic을 sections 우회하여 직접 로드."""
    df = company._showFinanceTopic(topic)
    if df is None or not isinstance(df, pl.DataFrame):
        return None

    if topic in {"IS", "BS", "CIS", "CF", "SCE"} and "항목" in df.columns:
        df = company._cleanFinanceDataFrame(df, topic)

    periods = _periodCols(df)
    # 기간 역순 정렬 (최신 먼저)
    sortedPeriods = sorted(periods, key=_periodSortKey, reverse=True)
    nonPeriodCols = [c for c in df.columns if c not in periods]
    df = df.select(nonPeriodCols + sortedPeriods)
    periods = sortedPeriods
    scale, divisor = _detectScale(df, periods)

    return ViewerBlock(
        block=0,
        kind="finance",
        source="finance",
        data=df,
        meta=BlockMeta(
            unit="원",
            scale=scale,
            scaleDivisor=divisor,
            periods=periods,
            rowCount=df.height,
            colCount=len(df.columns),
        ),
    )


# ── Report 블록 ──


def _buildReportBlock(company: Company, topic: str, bo: int) -> ViewerBlock | None:
    """report source 블록."""
    df = company._showReportTopic(topic)
    if df is None or not isinstance(df, pl.DataFrame):
        return None

    periods = _periodCols(df)
    # 기간 역순 정렬 (최신 먼저) — finance/structured와 일관성
    sortedPeriods = sorted(periods, key=_periodSortKey, reverse=True)
    nonPeriodCols = [c for c in df.columns if c not in periods]
    df = df.select(nonPeriodCols + sortedPeriods)
    periods = sortedPeriods

    return ViewerBlock(
        block=bo,
        kind="report",
        source="report",
        data=df,
        meta=BlockMeta(
            periods=periods,
            rowCount=df.height,
            colCount=len(df.columns),
        ),
    )


# ── Text 블록 ──


def _classifyTextType(text: str) -> str:
    """text 블록을 heading(소제목) vs body(서술형)로 분류."""
    if not text or not text.strip():
        return "heading"
    lines = [l for l in text.strip().split("\n") if l.strip()]
    lineCount = len(lines)
    charCount = sum(len(l) for l in lines)

    if lineCount <= 2 and charCount <= 80:
        return "heading"
    return "body"


def _buildTextBlock(boRows: pl.DataFrame, bo: int, periodCols: list[str]) -> ViewerBlock | None:
    """text 블록 — sections row 의 period × cell 값 그대로 보유.

    Phase B 슬림화: changeSummary (inline diff + annotated blame) 생성 폐기.
    frontend 가 미사용 (SectionRow 가 paragraphs 만 표시), backend ~700 라인 dead code.
    """
    keepCols = [c for c in periodCols if c in boRows.columns]
    nonNullCols = [c for c in keepCols if boRows[c].null_count() < boRows.height]
    if not nonNullCols:
        return None

    textDf = boRows.select(nonNullCols)

    row = boRows.row(0, named=True)
    latestText = str(row.get(nonNullCols[-1], ""))
    textType = str(row.get("textNodeType") or "")
    if textType not in {"heading", "body"}:
        textType = _classifyTextType(latestText)
    if row.get("textStructural") is False and textType == "heading":
        textType = "body"

    rawLevel = row.get("textLevel")
    textLevel = int(rawLevel) if rawLevel is not None and rawLevel == rawLevel else None

    return ViewerBlock(
        block=bo,
        kind="text",
        source="docs",
        data=textDf,
        meta=BlockMeta(
            periods=nonNullCols,
            rowCount=1,
            colCount=len(nonNullCols),
        ),
        textType=textType,
        textLevel=textLevel,
    )


def _textPeriodMap(block: ViewerBlock) -> dict[str, str]:
    """text block의 period -> text 매핑.

    DART raw 본문에 섞인 비표준 `&cr;` 를 줄바꿈으로, 표준 HTML entity
    (`&amp;` 등) 를 디코드 — 본문 그대로 사람이 읽는 prose 가 되도록.
    """
    if isEmptyDf(block.data):
        return {}
    row = block.data.row(0, named=True)
    result: dict[str, str] = {}
    for key, value in row.items():
        if not _isPeriod(str(key)):
            continue
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        text = text.replace("&cr;", "\n").replace("&CR;", "\n")
        text = html.unescape(text)
        result[str(key)] = text
    return result


def _periodRef(period: str) -> PeriodRef:
    """기간 문자열을 canonical ref로 변환."""
    year, quarter = _periodSortKey(period)
    quarterVal = quarter if quarter < 5 else None
    return PeriodRef(
        label=period,
        year=year,
        quarter=quarterVal,
        kind="quarterly" if quarterVal is not None else "annual",
        sortKey=(year * 10) + quarter,
    )


def _selectNearestPeriodText(
    periodMap: dict[str, str], targetPeriod: str | None = None
) -> tuple[str | None, str | None]:
    """targetPeriod 에 정확히 매치되는 cell value 반환. 매치 없으면 (None, None).

    이전 nearest fallback (이전 period 또는 전체 최신 으로 추측) 폐기. 그 fallback
    이 원문에 없는 텍스트를 다른 period 의 cell value 로 흘려보내 사용자 화면에
    "본문에 없는 heading 표시" 회귀를 만들었음. sections SSOT 원칙 — 그 period 에
    cell value 없으면 표시 X. fallback 0.

    targetPeriod=None 일 때만 전체 latest 반환 — 기간 무관 단순 "가장 최신 값"
    필요할 때 (예 sections preview, 기본 cell choose).
    """
    if not periodMap:
        return (None, None)

    if targetPeriod is None:
        periods = sorted(periodMap.keys(), key=_periodSortKey)
        chosen = periods[-1]
        return (chosen, periodMap[chosen])

    if targetPeriod in periodMap:
        return (targetPeriod, periodMap[targetPeriod])

    # strict — fallback 0. 그 period 에 진짜 값 없으면 None.
    return (None, None)


def _classifyTextSectionStatus(
    firstPeriod: str,
    latestPeriod: str,
    periodCount: int,
    topicLatestPeriod: str,
    latestViewStatus: TextViewStatus | None = None,
) -> TextSectionStatus:
    """Phase B 슬림화 — ChangeSummary 의존 폐기. 단순 stale/new/stable 분류."""
    if latestPeriod != topicLatestPeriod:
        return "stale"
    if periodCount == 1 and firstPeriod == latestPeriod:
        return "new"
    if latestViewStatus == "updated":
        return "updated"
    return "stable"


def _classifyTextViewStatus(
    *,
    currentText: str,
    prevText: str | None,
) -> TextViewStatus:
    if prevText is None:
        return "new"
    if currentText == prevText:
        return "stable"
    return "updated"


def _findPreviousComparablePeriod(periods: list[str], currentPeriod: str) -> str | None:
    """현재 period의 직전 동주기 period를 찾는다."""
    for period in reversed(periods):
        if _periodSortKey(period) >= _periodSortKey(currentPeriod):
            continue
        if _isSameReportType(period, currentPeriod):
            return period
    return None


# Phase B 슬림화 — _appendDiffChunk / _buildPositionAnchoredDiff 폐기
# (ViewerDiffChunk 와 함께). diff chunks frontend 미사용.


def _headingLevel(line: str) -> int:
    """한글 공시 heading 패턴에서 계층 레벨 추출. 0=unknown."""
    import re

    if re.match(r"^[IVX]+\.\s", line):
        return 1
    if re.match(r"^[가나다라마바사아자차카타파하]\.\s", line):
        return 1
    if re.match(r"^\[.+\]$", line) or re.match(r"^【.+】$", line):
        return 1
    if re.match(r"^\d+\.\s", line):
        return 2
    if re.match(r"^\(\d+\)\s", line) or re.match(r"^\([가-힣]\)\s", line):
        return 3
    if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s", line):
        return 4
    return 0


_HEADING_RE = re.compile(r"^\[.+\]$|^【.+】$|^[가-힣]\.\s|^\d+\.\s|^\(\d+\)\s|^\([가-힣]\)\s")


def _extractInlineHeadingLines(text: str) -> tuple[list[str], str]:
    """body 앞머리의 짧은 heading line을 구조 anchor로 분리한다."""
    if not text or not text.strip():
        return ([], "")

    headings: list[str] = []
    bodyLines: list[str] = []
    bodyStarted = False

    for rawLine in text.splitlines():
        line = rawLine.strip()
        if not line:
            if bodyStarted:
                bodyLines.append("")
            continue
        if not bodyStarted and len(line) <= 72 and _HEADING_RE.match(line):
            headings.append(line)
            continue
        bodyStarted = True
        bodyLines.append(line)

    bodyText = "\n".join(bodyLines).strip()
    if not bodyText:
        return ([], text.strip())
    return (headings, bodyText)


def _isSameReportType(p1: str, p2: str) -> bool:
    """같은 보고서 유형인지 (연간↔연간, Q1↔Q1 등)."""
    q1 = re.search(r"Q(\d)", p1)
    q2 = re.search(r"Q(\d)", p2)
    if q1 is None and q2 is None:
        return True
    if q1 and q2:
        return q1.group(1) == q2.group(1)
    return False


# ── Table 블록 ──


# ── 재내보내기 (분리: viewerSerialize.py · viewerTable.py · viewerTextSection.py) ──
from dartlab.providers.dart.viewerSerialize import (  # noqa: E402  re-export
    _serializeDf,
    _serializePeriodRef,
    _serializeViewerTextView,
    serializeViewerBlock,
    serializeViewerTextDocument,
)
from dartlab.providers.dart.viewerTable import (  # noqa: E402  re-export
    _buildRawMarkdownBlock,
    _buildTableBlock,
    _cleanStructuredTable,
    _detectScale,
    _hasPipeCells,
    _isRawMarkdown,
    _periodSortKey,
)
from dartlab.providers.dart.viewerTextSection import (  # noqa: E402  re-export
    _buildTextSection,
    _buildTextView,
    _isStructuralHeadingLine,
    _normalizeTextLine,
    _previewText,
    _splitSentences,
)
