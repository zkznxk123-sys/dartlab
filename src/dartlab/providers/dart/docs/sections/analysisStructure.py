"""sections analysis structure events/summary/changes/semanticCollisions — analysis.py 분할 (규칙 3 LoC).

`analysis.py` 1000 LoC 가 규칙 3 임계 (>800) 위반. structureEvents / structureSummary /
structureChanges / semanticCollisions (~336 줄) 를 본 모듈로 분리. 호출자 호환 —
analysis.py 재내보내기.
"""

from __future__ import annotations

import re

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.dart.docs.sections.analysis import (
    _allowedStructurePeriodLanes,
    _changedPaths,
    _emptyStructureChangesFrame,
    _emptyStructureEventsFrame,
    _emptyStructureSummaryFrame,
    _normalizeStructureGroupDtypes,
    _pathCollection,
    _periodLane,
    _structureGroupColumns,
    _structurePatternRank,
    _structurePeriodActivity,
    _structureTransitionType,
    projectFreqRows,
    semanticRegistry,
    structureRegistry,
)
from dartlab.providers.dart.docs.sections.sectionsBase import periodOrderValue, sortPeriods


def structureEvents(
    df: pl.DataFrame | None,
    *,
    topic: str | None = None,
    freqScope: str = "all",
    includeMixed: bool = True,
    changedOnly: bool = True,
    nodeType: str | None = None,
) -> pl.DataFrame:
    """기간 간 텍스트 구조 변화 이벤트(추가/삭제/변경)를 감지하여 반환한다.

    Args:
        df: 인자.
        topic: 인자.
        freqScope: 인자.
        includeMixed: 인자.
        changedOnly: 인자.

    Raises:
        없음.

    Example:
        >>> structureEvents(...)

    Returns:
        pl.DataFrame — 결과.
    """
    if isEmptyDf(df):
        return _emptyStructureEventsFrame()

    required = {"topic", "textComparablePathKey", "textSemanticPathKey", "segmentKey"}
    if not required.issubset(set(df.columns)):
        return _emptyStructureEventsFrame()

    scoped = df
    if freqScope != "all":
        scoped = projectFreqRows(scoped, freqScope=freqScope, includeMixed=includeMixed)
    if topic is not None:
        scoped = scoped.filter(pl.col("topic") == topic)
    if scoped.is_empty():
        return _emptyStructureEventsFrame()

    textScoped = scoped
    if "blockType" in textScoped.columns:
        textScoped = textScoped.filter(pl.col("blockType") == "text")
    if "textStructural" in textScoped.columns:
        textScoped = textScoped.filter(pl.col("textStructural") != False)  # noqa: E712
    normalizedNodeType = str(nodeType).strip().lower() if isinstance(nodeType, str) and nodeType.strip() else None
    if normalizedNodeType is not None and "textNodeType" in textScoped.columns:
        textScoped = textScoped.filter(pl.col("textNodeType") == normalizedNodeType)
    textScoped = textScoped.filter(
        pl.col("textComparablePathKey").is_not_null() & pl.col("textSemanticPathKey").is_not_null()
    )
    if textScoped.is_empty():
        return _emptyStructureEventsFrame()

    periodActivity = _structurePeriodActivity(textScoped, freqScope=freqScope)
    if periodActivity is None:
        return _emptyStructureEventsFrame()

    groupCols = _structureGroupColumns()
    rows: list[dict[str, object]] = []
    groupFrame = periodActivity.group_by(groupCols, maintain_order=True).agg(
        [
            pl.col("period").alias("periods"),
            pl.col("activeRawSemanticPaths").alias("pathsByPeriod"),
            pl.col("activePathCount").alias("pathCounts"),
        ]
    )
    for entry in groupFrame.iter_rows(named=True):
        periods = entry.get("periods")
        pathsByPeriod = entry.get("pathsByPeriod")
        pathCounts = entry.get("pathCounts")
        if not isinstance(periods, list) or not isinstance(pathsByPeriod, list) or not isinstance(pathCounts, list):
            continue
        lanes: dict[str, list[int]] = {}
        for idx, period in enumerate(periods):
            lane = _periodLane(period)
            if lane is None:
                continue
            lanes.setdefault(lane, []).append(idx)

        for lane, indices in lanes.items():
            if len(indices) < 2:
                continue
            for pos in range(1, len(indices)):
                fromIdx = indices[pos - 1]
                toIdx = indices[pos]
                fromPeriod = periods[fromIdx]
                toPeriod = periods[toIdx]
                fromPaths = _pathCollection(pathsByPeriod[fromIdx])
                toPaths = _pathCollection(pathsByPeriod[toIdx])
                if not isinstance(fromPeriod, str) or not isinstance(toPeriod, str) or not fromPaths or not toPaths:
                    continue
                eventType = _structureTransitionType(entry.get("textComparablePathKey"), fromPaths, toPaths)
                if changedOnly and eventType == "stable":
                    continue
                addedPaths, removedPaths = _changedPaths(fromPaths, toPaths)
                rows.append(
                    {
                        "topic": entry.get("topic"),
                        "textNodeType": entry.get("textNodeType"),
                        "textLevel": entry.get("textLevel"),
                        "freqScope": entry.get("freqScope"),
                        "textComparablePathKey": entry.get("textComparablePathKey"),
                        "textComparableParentPathKey": entry.get("textComparableParentPathKey"),
                        "periodLane": lane,
                        "fromPeriod": fromPeriod,
                        "toPeriod": toPeriod,
                        "fromPathCount": int(pathCounts[fromIdx]),
                        "toPathCount": int(pathCounts[toIdx]),
                        "fromPaths": fromPaths,
                        "toPaths": toPaths,
                        "addedPaths": addedPaths,
                        "removedPaths": removedPaths,
                        "eventType": eventType,
                    }
                )

    if not rows:
        return _emptyStructureEventsFrame()
    return pl.DataFrame(rows, schema=_emptyStructureEventsFrame().schema).sort(
        ["topic", "textComparablePathKey", "fromPeriod", "toPeriod", "textNodeType", "textLevel"]
    )


def structureSummary(
    df: pl.DataFrame | None,
    *,
    topic: str | None = None,
    freqScope: str = "all",
    includeMixed: bool = True,
    nodeType: str | None = None,
) -> pl.DataFrame:
    """구조 레지스트리와 이벤트를 결합한 경로별 요약 DataFrame을 반환한다.

    Args:
        df: 인자.
        topic: 인자.
        freqScope: 인자.
        includeMixed: 인자.
        nodeType: 인자.

    Raises:
        없음.

    Example:
        >>> structureSummary(...)

    Returns:
        pl.DataFrame — 결과.
    """
    registry = structureRegistry(
        df,
        topic=topic,
        freqScope=freqScope,
        includeMixed=includeMixed,
        nodeType=nodeType,
    )
    if registry.is_empty():
        return _emptyStructureSummaryFrame()

    groupCols = _structureGroupColumns()
    summary = registry.select(
        groupCols
        + [
            "structurePattern",
            "hasCollision",
            "activePeriodCount",
            "activePeriods",
            "latestPathCount",
            "multiPathPeriods",
        ]
    ).with_columns(
        [
            pl.col("activePeriods").list.last().alias("latestPeriod"),
            pl.col("activePeriods")
            .list.last()
            .map_elements(_periodLane, return_dtype=pl.Utf8)
            .alias("latestPeriodLane"),
        ]
    )
    summary = _normalizeStructureGroupDtypes(summary)

    events = structureEvents(
        df,
        topic=topic,
        freqScope=freqScope,
        includeMixed=includeMixed,
        changedOnly=True,
        nodeType=nodeType,
    )
    if not events.is_empty():
        eventSummary = (
            events.with_columns(
                pl.col("toPeriod").map_elements(periodOrderValue, return_dtype=pl.Int64).alias("toOrder")
            )
            .sort(groupCols + ["toOrder"])
            .group_by(groupCols, maintain_order=True)
            .agg(
                [
                    pl.len().alias("eventCount"),
                    pl.col("eventType").last().alias("latestEventType"),
                    pl.col("fromPeriod").last().alias("latestEventFromPeriod"),
                    pl.col("toPeriod").last().alias("latestEventToPeriod"),
                    pl.col("periodLane").last().alias("latestEventLane"),
                ]
            )
        )
        eventSummary = _normalizeStructureGroupDtypes(eventSummary)
        summary = summary.join(eventSummary, on=groupCols, how="left", nulls_equal=True)
    else:
        summary = summary.with_columns(
            [
                pl.lit(0).cast(pl.Int64).alias("eventCount"),
                pl.lit(None, dtype=pl.Utf8).alias("latestEventType"),
                pl.lit(None, dtype=pl.Utf8).alias("latestEventFromPeriod"),
                pl.lit(None, dtype=pl.Utf8).alias("latestEventToPeriod"),
                pl.lit(None, dtype=pl.Utf8).alias("latestEventLane"),
            ]
        )

    if "eventCount" in summary.columns:
        summary = summary.with_columns(pl.col("eventCount").fill_null(0))

    for colName in ["latestEventType", "latestEventFromPeriod", "latestEventToPeriod", "latestEventLane"]:
        if colName not in summary.columns:
            summary = summary.with_columns(pl.lit(None, dtype=pl.Utf8).alias(colName))

    return summary.sort(["topic", "textComparablePathKey", "textNodeType", "textLevel", "freqScope"])


def structureChanges(
    df: pl.DataFrame | None,
    *,
    topic: str | None = None,
    freqScope: str = "all",
    includeMixed: bool = True,
    nodeType: str | None = None,
    latestOnly: bool = True,
    changedOnly: bool = True,
) -> pl.DataFrame:
    """구조 변경이 감지된 경로를 최신 기간 기준으로 필터링하여 반환한다.

    Args:
        df: 인자.
        topic: 인자.
        freqScope: 인자.
        includeMixed: 인자.
        nodeType: 인자.

    Raises:
        없음.

    Example:
        >>> structureChanges(...)

    Returns:
        pl.DataFrame — 결과.
    """
    summary = structureSummary(
        df,
        topic=topic,
        freqScope=freqScope,
        includeMixed=includeMixed,
        nodeType=nodeType,
    )
    if summary.is_empty():
        return _emptyStructureChangesFrame()

    allowedAnchorLanes = _allowedStructurePeriodLanes(freqScope)
    latestPeriods = [
        period
        for period in summary["latestPeriod"].to_list()
        if isinstance(period, str)
        and period
        and (allowedAnchorLanes is None or _periodLane(period) in allowedAnchorLanes)
    ]
    anchorPeriod = max(latestPeriods, key=periodOrderValue) if latestPeriods else None
    anchorLane = _periodLane(anchorPeriod)

    changes = summary.with_columns(
        [
            pl.lit(anchorPeriod, dtype=pl.Utf8).alias("anchorPeriod"),
            pl.lit(anchorLane, dtype=pl.Utf8).alias("anchorPeriodLane"),
            (pl.col("latestPeriod") == anchorPeriod).alias("isLatest"),
            (pl.col("latestPeriod") != anchorPeriod).alias("isStale"),
            pl.col("structurePattern").map_elements(_structurePatternRank, return_dtype=pl.Int64).alias("_patternRank"),
        ]
    )

    if changedOnly:
        changes = changes.filter(pl.col("eventCount") > 0)
    if latestOnly:
        changes = changes.filter(pl.col("isLatest"))
    if changes.is_empty():
        return _emptyStructureChangesFrame()

    return (
        changes.sort(
            ["isLatest", "eventCount", "_patternRank", "latestPathCount", "textComparablePathKey"],
            descending=[True, True, True, True, False],
        )
        .drop("_patternRank")
        .select(_emptyStructureChangesFrame().columns)
    )


def semanticCollisions(
    df: pl.DataFrame | None,
    *,
    topic: str | None = None,
    freqScope: str = "all",
    includeMixed: bool = True,
) -> pl.DataFrame:
    """semantic registry에서 raw path 충돌 그룹만 반환한다.

    Args:
        df: 인자.
        topic: 인자.
        freqScope: 인자.
        includeMixed: 인자.

    Raises:
        없음.

    Example:
        >>> semanticCollisions(...)

    Returns:
        pl.DataFrame — 결과.
    """
    registry = semanticRegistry(df, topic=topic, freqScope=freqScope, includeMixed=includeMixed)
    if registry.is_empty():
        return registry
    return registry.filter(pl.col("hasCollision"))
