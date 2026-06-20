"""Build source/no-answer canary packs from a search artifact's metadata."""

from __future__ import annotations

import re
from typing import Any

import polars as pl

CANARY_PACK_VERSION = "artifact-source-v3"
NO_ANSWER_QUERY = "zzqwvxnotlistedalpha999"
NEWS_SOURCE_LANE_QUERY = "뉴스 기사"


def buildSourceCanaryPackFromMeta(
    meta: pl.DataFrame,
    *,
    maxRowsPerSource: int = 1,
    includeNoAnswer: bool = True,
) -> list[dict[str, Any]]:
    """Build a small source/no-answer canary pack from segment metadata.

    Args:
        meta: Segment metadata, usually ``main_meta.parquet``.
        maxRowsPerSource: Maximum positive canaries per source.
        includeNoAnswer: Add one deterministic no-answer trap.

    Returns:
        list[dict[str, Any]]: Canary rows suitable for manifest
        ``sourceCanaryPack``.

    Raises:
        None.

    Example:
        >>> buildSourceCanaryPackFromMeta(pl.DataFrame())[-1]["target"]
        'noAnswer'
    """
    rows: list[dict[str, Any]] = []
    seenBySource: dict[str, int] = {}
    if meta is not None and meta.height:
        sortCols = [col for col in ("source", "sourceDataAsOf", "rcept_dt", "rcept_no") if col in meta.columns]
        iterable = meta.sort(sortCols, descending=[False, True, True, False][: len(sortCols)]).iter_rows(named=True)
        for row in iterable:
            source = str(row.get("source") or "").strip()
            if not source:
                continue
            if seenBySource.get(source, 0) >= maxRowsPerSource:
                continue
            query = _queryForSource(source, _queryFromRow(row))
            if not query:
                continue
            sourceRef = str(row.get("sourceRef") or "").strip()
            item = {
                "query": query,
                "target": _targetForSource(source),
                "expectedSource": source,
                "expectedAnswerable": True,
                "requireAnswerable": True,
                "topK": 10,
            }
            if sourceRef and _canUseRowSourceRef(source):
                item["expectedSourceRef"] = sourceRef
            rows.append(item)
            seenBySource[source] = seenBySource.get(source, 0) + 1
    if includeNoAnswer:
        rows.append(
            {
                "query": NO_ANSWER_QUERY,
                "target": "noAnswer",
                "expectedAnswerable": False,
                "topK": 10,
            }
        )
    return rows


def _queryFromRow(row: dict[str, Any]) -> str:
    raw = str(row.get("evidenceText") or row.get("text") or row.get("section_title") or "").strip()
    text = re.sub(r"\s+", " ", raw)
    if not text:
        return ""
    words = text.split()
    if len(words) >= 3:
        return " ".join(words[: min(8, len(words))])[:80]
    return text[:40]


def _queryForSource(source: str, query: str) -> str:
    if not query:
        return ""
    if source in {"news", "newsPublic"}:
        return NEWS_SOURCE_LANE_QUERY
    if source in {"edgar-panel", "edgarPanel"}:
        return f"edgar filing {query}"[:120]
    if source in {"panel", "dartPanel"}:
        return f"사업보고서 본문 {query}"[:120]
    return f"공시 원문 {query}"[:120]


def _targetForSource(source: str) -> str:
    if source in {"news", "newsPublic"}:
        return "news"
    if source in {"edgar-panel", "edgarPanel"}:
        return "edgar"
    return "filing"


def _canUseRowSourceRef(source: str) -> bool:
    # allFilings 는 rcept_no 단위 doc 이 명확한 인용 단위라 expectedSourceRef 를 싣는다. 이 ref 는
    # publish selfcheck 가 *결정론 라운드트립*(meta 존재 + docLengths>0)으로 인용 무결성을 검증하는
    # 대상이며 BM25 랭킹 top-K 도달을 요구하지 않는다(localUpdate._sourceCanaryPackErrors 참조).
    return source in {"allFilings"}
