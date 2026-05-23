"""viewer 직렬화 함수 — viewer.py 분할 (규칙 3 LoC).

ViewerTextDocument / ViewerBlock 를 JSON 직렬화 가능한 dict 로 변환.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.dart.docs.viewer import (
        PeriodRef,
        ViewerBlock,
        ViewerTextDocument,
        ViewerTextView,
    )


def _serializePeriodRef(period: PeriodRef | None) -> dict[str, Any] | None:
    if period is None:
        return None
    return {
        "label": period.label,
        "year": period.year,
        "quarter": period.quarter,
        "kind": period.kind,
        "sortKey": period.sortKey,
    }


def _serializeViewerTextView(view: ViewerTextView | None) -> dict[str, Any] | None:
    """Phase B 슬림화 — diff/digest serialize 폐기. body + status + period 만."""
    if view is None:
        return None
    return {
        "period": _serializePeriodRef(view.period),
        "prevPeriod": _serializePeriodRef(view.prevPeriod),
        "body": view.body,
        "status": view.status,
    }


def serializeViewerTextDocument(document: ViewerTextDocument | None) -> dict[str, Any] | None:
    """ViewerTextDocument를 JSON 직렬화 가능한 dict로 변환.

    Args:
        document: 인자.

    Raises:
        없음.

    Example:
        >>> serializeViewerTextDocument(...)

    Returns:
        dict[str, Any] 또는 None — 결과.
    """
    if document is None:
        return None

    return {
        "topic": document.topic,
        "mode": document.mode,
        "periods": [_serializePeriodRef(period) for period in document.periods],
        "latestPeriod": _serializePeriodRef(document.latestPeriod),
        "firstPeriod": _serializePeriodRef(document.firstPeriod),
        "sectionCount": document.sectionCount,
        "updatedCount": document.updatedCount,
        "newCount": document.newCount,
        "staleCount": document.staleCount,
        "stableCount": document.stableCount,
        "sections": [
            {
                "id": section.id,
                "order": section.order,
                "bodyBlock": section.bodyBlock,
                "headingPath": [
                    {
                        "block": heading.block,
                        "text": heading.text,
                        "period": _serializePeriodRef(heading.period),
                        "level": heading.level,
                    }
                    for heading in section.headingPath
                ],
                "latest": _serializeViewerTextView(section.latest),
                "latestPeriod": _serializePeriodRef(section.latestPeriod),
                "firstPeriod": _serializePeriodRef(section.firstPeriod),
                "periodCount": section.periodCount,
                "status": section.status,
                "latestChange": section.latestChange,
                "preview": section.preview,
                "timeline": [
                    {
                        "period": _serializePeriodRef(entry.period),
                        "prevPeriod": _serializePeriodRef(entry.prevPeriod),
                        "status": entry.status,
                    }
                    for entry in section.timeline
                ],
            }
            for section in document.sections
        ],
        "entries": [
            {
                "kind": entry.kind,
                "order": entry.order,
                "sectionId": entry.sectionId,
                "blockRef": entry.blockRef,
                "blockKind": entry.blockKind,
                "headingPath": [
                    {
                        "block": heading.block,
                        "text": heading.text,
                        "period": _serializePeriodRef(heading.period),
                        "level": heading.level,
                    }
                    for heading in entry.headingPath
                ],
            }
            for entry in document.entries
        ],
    }


def serializeViewerBlock(block: ViewerBlock) -> dict[str, Any]:
    """ViewerBlock을 JSON-직렬화 가능한 dict로 변환.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> serializeViewerBlock(...)

    Returns:
        dict[str, Any] — 결과.
    """
    result: dict[str, Any] = {
        "block": block.block,
        "kind": block.kind,
        "source": block.source,
        "meta": {
            "unit": block.meta.unit,
            "scale": block.meta.scale,
            "scaleDivisor": block.meta.scaleDivisor,
            "periods": block.meta.periods,
            "rowCount": block.meta.rowCount,
            "colCount": block.meta.colCount,
        },
    }

    if block.data is not None:
        result["data"] = _serializeDf(block.data)
    else:
        result["data"] = None

    # Phase B 슬림화 — changeSummary serialize 폐기. frontend 미사용.

    if block.rawMarkdown is not None:
        result["rawMarkdown"] = block.rawMarkdown
    else:
        result["rawMarkdown"] = None

    result["textType"] = block.textType

    return result


def _serializeDf(df: pl.DataFrame) -> dict[str, Any]:
    """DataFrame을 {columns, rows} 형태로 직렬화."""
    rows = df.to_dicts()
    for row in rows:
        for k, v in row.items():
            if isinstance(v, float):
                if v != v or v == float("inf") or v == float("-inf"):
                    row[k] = None
    return {
        "columns": df.columns,
        "rows": rows,
    }
