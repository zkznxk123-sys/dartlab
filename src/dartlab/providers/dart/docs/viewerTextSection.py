"""viewer 텍스트 section 빌더 — viewer.py 분할 (규칙 3 LoC).

_buildTextView / _previewText / _buildTextSection / _normalizeTextLine /
_isStructuralHeadingLine / _splitSentences.
"""

from __future__ import annotations

import html
import re

from dartlab.providers.dart.docs.viewer import (
    ViewerBlock,
    ViewerTextHeading,
    ViewerTextSection,
    ViewerTextTimelineEntry,
    ViewerTextView,
    _classifyTextSectionStatus,
    _classifyTextViewStatus,
    _extractInlineHeadingLines,
    _findPreviousComparablePeriod,
    _headingLevel,
    _periodRef,
    _periodSortKey,
    _selectNearestPeriodText,
    _textPeriodMap,
)


def _buildTextView(
    *,
    period: str,
    periodMap: dict[str, str],
) -> ViewerTextView:
    """section 의 한 period snapshot — sections row cell value 그대로 (Phase B 슬림화).

    Phase B 슬림화: diff (position-anchored chunks) + digest (변경 요약 카드) 폐기.
    frontend SectionRow 가 `latest.body` 만 표시, `latest.diff`/`latest.digest`/`latest.status`
    미사용. ~30 라인 dead-code 회피.

    status 는 section-level (`section.timeline[].status`) 가 frontend 가 사용 — view-level
    status 는 미사용이라 stable default.
    """
    orderedPeriods = sorted(periodMap.keys(), key=_periodSortKey)
    _inlineHeadings, body = _extractInlineHeadingLines(periodMap[period])
    prevPeriod = _findPreviousComparablePeriod(orderedPeriods, period)
    return ViewerTextView(
        period=_periodRef(period),
        prevPeriod=_periodRef(prevPeriod) if prevPeriod is not None else None,
        body=body,
        status="stable",
    )


def _previewText(text: str | None, *, maxChars: int = 140) -> str | None:
    if text is None:
        return None
    paragraphs = _splitSentences(text)
    if not paragraphs:
        return None
    preview = " ".join(paragraphs[:2])
    if len(preview) <= maxChars:
        return preview
    return preview[: maxChars - 3].rstrip() + "..."


def _buildTextSection(
    *,
    topic: str,
    block: ViewerBlock,
    headingBlocks: list[ViewerBlock],
    order: int,
    topicLatestPeriod: str,
) -> ViewerTextSection | None:
    periodMap = _textPeriodMap(block)
    if not periodMap:
        return None

    periods = sorted(periodMap.keys(), key=_periodSortKey)
    latestPeriod = periods[-1]
    latestView = _buildTextView(period=latestPeriod, periodMap=periodMap)
    inlineHeadings, _ = _extractInlineHeadingLines(periodMap[latestPeriod])

    headingPath: list[ViewerTextHeading] = []
    for headingBlock in headingBlocks:
        headingPeriodMap = _textPeriodMap(headingBlock)
        # heading 의 *자체 latest* cell value 사용. 이전엔 latestPeriod (= section body
        # 의 latest) 기준으로 nearest fallback 했으나 section body period 와 heading
        # period 가 다를 때 fallback 으로 원문 외 텍스트 노출 회귀. strict + 자체 latest.
        chosenPeriod, headingText = _selectNearestPeriodText(headingPeriodMap, None)
        if headingText is None or chosenPeriod is None:
            continue
        headingPath.append(
            ViewerTextHeading(
                block=headingBlock.block,
                text=headingText,
                period=_periodRef(chosenPeriod),
                level=headingBlock.textLevel or _headingLevel(headingText),
            )
        )
    for headingText in inlineHeadings:
        headingPath.append(
            ViewerTextHeading(
                block=block.block,
                text=headingText,
                period=_periodRef(latestPeriod),
                level=_headingLevel(headingText),
            )
        )

    timeline: list[ViewerTextTimelineEntry] = []
    for period in sorted(periodMap.keys(), key=_periodSortKey, reverse=True):
        view = _buildTextView(period=period, periodMap=periodMap)
        timeline.append(
            ViewerTextTimelineEntry(
                period=view.period,
                prevPeriod=view.prevPeriod,
                status=view.status,
            )
        )

    return ViewerTextSection(
        id=f"{topic}:{block.block}",
        order=order,
        bodyBlock=block.block,
        headingPath=headingPath,
        latest=latestView,
        latestPeriod=_periodRef(latestPeriod),
        firstPeriod=_periodRef(periods[0]),
        periodCount=len(periods),
        status=_classifyTextSectionStatus(
            firstPeriod=periods[0],
            latestPeriod=latestPeriod,
            periodCount=len(periods),
            topicLatestPeriod=topicLatestPeriod,
            latestViewStatus=latestView.status,
        ),
        latestChange=None,
        preview=_previewText(latestView.body),
        timeline=timeline,
    )


# ── 문장 분리 + Inline Diff ──

_SENT_SPLIT_RE = re.compile(
    r"(?<=[다음임됨함음음])\.(?:\s|$)|"
    r"\n"
)


def _normalizeTextLine(line: str) -> str:
    """공시 원문 줄 단위 정규화."""
    text = html.unescape(line)
    text = text.replace("\u00a0", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def _isStructuralHeadingLine(line: str) -> bool:
    """본문 내부의 구조 heading line 여부."""
    if not line:
        return False
    if len(line) > 88:
        return False
    return bool(re.match(r"^\[.+\]$|^【.+】$|^[IVX]+\.\s|^\d+\.\s|^[가-힣]\.\s|^\(\d+\)\s|^\([가-힣]\)\s", line))


def _splitSentences(text: str) -> list[str]:
    """공시 본문을 logical paragraph 단위로 분리한다.

    - 단순 줄바꿈은 문단 연결로 본다.
    - heading line은 diff 대상에서 제외한다.
    - 빈 줄에서 문단을 끊는다.
    """
    if not text or not text.strip():
        return []

    # DART 비표준 entity `&cr;` (= carriage return) 를 진짜 줄바꿈으로 치환.
    # split("\n") 가 자연스러운 문단 경계로 처리하도록 사전 정규화.
    normalized = text.replace("&cr;", "\n").replace("&CR;", "\n")

    paragraphs: list[str] = []
    current: list[str] = []

    for rawLine in normalized.strip().split("\n"):
        line = _normalizeTextLine(rawLine)
        if not line:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        if _isStructuralHeadingLine(line):
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(line)

    if current:
        paragraphs.append(" ".join(current).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


# Phase B 슬림화 — _wordLevelDiff / _computeInlineDiff / _buildChangeSummary /
# _buildDigestDirect / _buildDigest / _extractNumericChanges / _buildAnnotatedBlame
# 일괄 폐기 (~330 라인). 모두 ChangeSummary / InlineDiff / ChangeDigest / AnnotatedLine
# dataclass 의존 — Phase B 1단계 호출 site 0 후 dead.

# Phase B 슬림화: _wordLevelDiff / _computeInlineDiff / _buildChangeSummary /
# _buildDigestDirect / _buildDigest / _extractNumericChanges / _buildAnnotatedBlame
# 일괄 폐기. ChangeSummary / InlineDiff / ChangeDigest / AnnotatedLine dataclass 동시 폐기.
# `_isSameReportType` 는 `_findPreviousComparablePeriod` 에서 계속 사용.
