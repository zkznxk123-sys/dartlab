"""topicManifest builder — docsSectionsAnalyzer.py 분할 (룰 3 LoC).

`docsSectionsAnalyzer.py` 885 LoC 가 룰 3 임계 (>800) 위반. topicManifest 본체
(140 줄) 를 본 모듈의 module-level 함수로 분리. 클래스 메서드는 thin delegate.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf


def buildTopicManifest(*, stockCode: str, hasDocs: bool, cache: Any, emptyDf: pl.DataFrame) -> pl.DataFrame:
    """전체 topic 카탈로그 builder — `c.sections.analyzer.topicManifest()` 본체.

    Args:
        stockCode: 종목코드.
        hasDocs: docs parquet 보유 여부.
        cache: BoundedCache 인스턴스.
        emptyDf: docs 부재 / 데이터 0 시 반환할 빈 schema.

    Returns:
        wide DataFrame (chapter/order 정렬) 또는 emptyDf.

    Raises:
        없음.

    Example:
        >>> buildTopicManifest(stockCode="005930", hasDocs=True, cache=c._cache, emptyDf=...)
    """
    cacheKey = "_docsTopicManifest"
    if cacheKey in cache:
        return cache[cacheKey]
    if not hasDocs:
        cache[cacheKey] = emptyDf
        return emptyDf

    from dartlab.core.dataLoader import loadData

    raw = loadData(
        stockCode,
        category="docs",
        sinceYear=2016,
        columns=["year", "report_type", "rcept_date", "section_order", "section_title"],
    )
    requiredCols = {"year", "report_type", "section_order", "section_title"}
    if isEmptyDf(raw) or not requiredCols.issubset(set(raw.columns)):
        cache[cacheKey] = emptyDf
        return emptyDf

    from dartlab.providers._common.reportSelector import selectReport
    from dartlab.providers.dart.docs.sections.chunker import parseMajorNum
    from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle
    from dartlab.providers.dart.docs.sections.runtime import chapterFromMajorNum
    from dartlab.providers.dart.docs.sections.sectionsBase import REPORT_KINDS, periodOrderValue

    years = sorted({str(year) for year in raw["year"].drop_nulls().to_list()}, reverse=True)
    catalog: dict[str, dict[str, Any]] = {}

    for year in years:
        for reportKind, suffix in REPORT_KINDS:
            report = selectReport(raw, year, reportKind=reportKind)
            if isEmptyDf(report):
                continue

            periodKey = f"{year}{suffix}"
            scoped = (
                report.select(["section_order", "section_title"])
                .filter(pl.col("section_title").is_not_null())
                .sort("section_order")
            )
            if scoped.is_empty():
                continue

            currentChapter: str | None = None
            periodCounts: dict[str, int] = {}
            periodOrders: dict[str, int] = {}
            periodChapters: dict[str, str] = {}

            for row in scoped.iter_rows(named=True):
                rawTitle = str(row.get("section_title") or "").strip()
                if not rawTitle:
                    continue
                majorNum = parseMajorNum(rawTitle)
                if majorNum is not None:
                    currentChapter = chapterFromMajorNum(majorNum)
                topic = mapSectionTitle(rawTitle)
                if not topic:
                    continue
                sectionOrder = int(row.get("section_order") or 0)
                periodCounts[topic] = periodCounts.get(topic, 0) + 1
                periodOrders.setdefault(topic, sectionOrder)
                if currentChapter and topic not in periodChapters:
                    periodChapters[topic] = currentChapter

            for topic, blockCount in periodCounts.items():
                chapter = periodChapters.get(topic) or "XII"
                sectionOrder = periodOrders.get(topic, 0)
                latestKey = periodOrderValue(periodKey)
                entry = catalog.get(topic)
                if entry is None:
                    catalog[topic] = {
                        "order": sectionOrder,
                        "chapter": chapter,
                        "topic": topic,
                        "source": "docs",
                        "blocks": blockCount,
                        "periods": 1,
                        "latestPeriod": periodKey,
                        "_periods": {periodKey},
                        "_latestKey": latestKey,
                    }
                    continue

                entry["order"] = min(int(entry["order"]), sectionOrder)
                if chapter != "XII" and entry.get("chapter") == "XII":
                    entry["chapter"] = chapter
                entry["blocks"] = max(int(entry["blocks"]), blockCount)
                if periodKey not in entry["_periods"]:
                    entry["_periods"].add(periodKey)
                    entry["periods"] = len(entry["_periods"])
                if latestKey > int(entry["_latestKey"]):
                    entry["latestPeriod"] = periodKey
                    entry["_latestKey"] = latestKey

    rows = [
        {
            "order": int(entry["order"]),
            "chapter": str(entry["chapter"]),
            "topic": str(entry["topic"]),
            "source": str(entry["source"]),
            "blocks": int(entry["blocks"]),
            "periods": int(entry["periods"]),
            "latestPeriod": str(entry["latestPeriod"]),
        }
        for entry in catalog.values()
    ]
    if not rows:
        cache[cacheKey] = emptyDf
        return emptyDf

    from dartlab.providers.dart.company import _CHAPTER_ORDER

    result = (
        pl.DataFrame(rows, strict=False)
        .with_columns(pl.col("chapter").replace(_CHAPTER_ORDER).cast(pl.Int64).alias("_chapterOrder"))
        .sort(["_chapterOrder", "order", "topic"])
        .drop("_chapterOrder")
    )
    cache[cacheKey] = result
    return result
