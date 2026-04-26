"""DART Company 의 index 헬퍼 backend.

Company.index property 가 호출하는 _indexFinanceRows / _indexDocsRows /
_indexReportRows 3 helper 의 본체. 각 helper 는 Company internal state 다수에
의존 (self._cache, self._has*, self._docs, self._report, self._chapterForTopic 등)
하므로 module-level 함수로 이전 시 첫 인자 ``company`` 로 받는다.

Module-level builders:
    indexFinanceRows  — finance 영역 index rows (BS/IS/CIS/CF/SCE + ratios)
    indexDocsRows     — docs sections 기반 index rows
    indexReportRows   — report API_TYPES 기반 index rows
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.dart._utils import _isPeriodColumn, _shapeString

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


# Chapter ordering (company.py 와 동일 — 변경 시 동기화 필요)
_CHAPTER_TITLES: dict[str, str] = {
    "I": "I. 회사의 개요",
    "II": "II. 사업의 내용",
    "III": "III. 재무에 관한 사항",
    "IV": "IV. 이사의 경영진단",
    "V": "V. 회계감사인의 감사의견 등",
    "VI": "VI. 이사회 등 회사의 기관에 관한 사항",
    "VII": "VII. 주주에 관한 사항",
    "VIII": "VIII. 임원 및 직원 등에 관한 사항",
    "IX": "IX. 계열회사 등에 관한 사항",
    "X": "X. 이해관계자와의 거래내용",
    "XI": "XI. 그 밖에 투자자 보호를 위하여 필요한 사항",
    "안내": "안내",
}
_CHAPTER_ORDER: dict[str, int] = {chapter: idx for idx, chapter in enumerate(_CHAPTER_TITLES, start=1)}


def indexFinanceRows(company: Company) -> list[dict[str, Any]]:
    """finance 영역의 index rows — BS/IS/CIS/CF/SCE + ratios."""
    rows: list[dict[str, Any]] = []
    _STMT_ORDER = {"BS": 0, "IS": 1, "CIS": 2, "CF": 3, "SCE": 4}
    for stmt in ("BS", "IS", "CIS", "CF", "SCE"):
        df = getattr(company, stmt, None)
        if df is None:
            continue
        periodCols = [c for c in df.columns if _isPeriodColumn(c)]
        periods = (
            f"{periodCols[0]}..{periodCols[-1]}" if len(periodCols) > 1 else (periodCols[0] if periodCols else "-")
        )
        rows.append(
            {
                "chapter": _CHAPTER_TITLES.get("III", "III"),
                "topic": stmt,
                "label": company._topicLabel(stmt),
                "kind": "finance",
                "source": "finance",
                "periods": periods,
                "shape": _shapeString(df),
                "preview": f"{df.height} accounts",
                "_sortKey": (3, _STMT_ORDER[stmt]),
            }
        )

    rsPair = company._ratioSeries() if company._hasFinance else None
    if rsPair is not None:
        series, years = rsPair
        ratioData = series.get("RATIO", {})
        from dartlab.core.finance.ratios import RATIO_CATEGORIES

        metricCount = sum(
            1
            for _, fields in RATIO_CATEGORIES
            for f in fields
            if ratioData.get(f) and any(v is not None for v in ratioData[f])
        )
        periods = f"{years[0]}..{years[-1]}" if len(years) > 1 else (years[0] if years else "-")
        rows.append(
            {
                "chapter": _CHAPTER_TITLES.get("III", "III"),
                "topic": "ratios",
                "label": "재무비율",
                "kind": "finance",
                "source": "finance",
                "periods": periods,
                "shape": f"{metricCount}x{len(years) + 2}",
                "preview": f"{metricCount} metrics",
                "_sortKey": (3, 5),
            }
        )
    return rows


def indexDocsRows(company: Company) -> list[dict[str, Any]]:
    """docs 영역의 index rows — sections 기반."""
    if not company._hasDocs:
        return []

    from dartlab.providers.dart.docs.sections import displayPeriod, formatPeriodRange, sortPeriods
    from dartlab.providers.dart.docs.sections.pipeline import (
        _expandStructuredRows,
        _reportRowsToTopicRows,
        _rowFreqMeta,
        applyProjections,
        chapterTeacherTopics,
        detailTopicForTopic,
        iterPeriodSubsets,
        projectionSuppressedTopics,
    )

    topicMap: dict[tuple[str, str], dict[str, str]] = {}
    rowOrder: dict[tuple[str, str], dict[str, int | str | None]] = {}
    periodRows: dict[str, list[dict[str, object]]] = {}
    validPeriods: list[str] = []
    latestAnnualRows: list[dict[str, object]] | None = None
    suppressed = projectionSuppressedTopics()

    for periodKey, reportKind, contentCol, subset in iterPeriodSubsets(company.stockCode):
        validPeriods.append(periodKey)
        topicRows = _reportRowsToTopicRows(subset, contentCol)
        periodRows[periodKey] = topicRows
        if reportKind == "annual" and latestAnnualRows is None:
            latestAnnualRows = topicRows

    if not validPeriods:
        return []

    teacherTopics = chapterTeacherTopics(latestAnnualRows or [])
    validPeriods = sortPeriods(validPeriods)
    latestPeriod = validPeriods[-1]

    def representativePeriodRank(period: str | None) -> int:
        if not isinstance(period, str):
            return -1
        year = int(period[:4])
        quarter = {"Q1": 1, "Q2": 2, "Q3": 3}.get(period[4:], 4)
        return (year * 10) + quarter

    topicChapter: dict[str, str] = {}
    topicFirstSeq: dict[str, tuple[int, int]] = {}

    for periodIdx, periodKey in enumerate(validPeriods):
        projected = applyProjections(periodRows.pop(periodKey, []), teacherTopics)
        for row in _expandStructuredRows(projected):
            chapter = row.get("chapter")
            topic = row.get("topic")
            text = row.get("text")
            blockType = row.get("blockType", "text")
            segmentKey = row.get("segmentKey")
            if not isinstance(chapter, str) or not isinstance(topic, str) or not isinstance(text, str):
                continue
            if topic not in topicChapter:
                topicChapter[topic] = chapter
            if topic in suppressed.get(chapter, set()):
                continue
            if detailTopicForTopic(topic) is not None:
                continue
            if not isinstance(blockType, str):
                blockType = "text"
            if not isinstance(segmentKey, str) or not segmentKey:
                continue

            key = (topic, segmentKey)
            topicMap.setdefault(key, {})[periodKey] = text

            majorNum = int(row.get("majorNum", 99))
            sortOrder = int(row.get("sortOrder", 999999))
            if topic not in topicFirstSeq or (majorNum, sortOrder) < topicFirstSeq[topic]:
                topicFirstSeq[topic] = (majorNum, sortOrder)

            orderInfo = rowOrder.setdefault(
                key,
                {
                    "latestRank": 999999999,
                    "latestMissing": 1,
                    "firstRank": 999999999,
                    "sourceBlockOrder": int(row.get("sourceBlockOrder") or 0),
                    "segmentOrder": int(row.get("segmentOrder") or 0),
                    "segmentOccurrence": int(row.get("segmentOccurrence") or 1),
                    "_repPeriod": None,
                },
            )
            orderInfo["firstRank"] = min(int(orderInfo["firstRank"]), sortOrder)
            orderInfo["sourceBlockOrder"] = min(
                int(orderInfo["sourceBlockOrder"]), int(row.get("sourceBlockOrder") or 0)
            )
            orderInfo["segmentOrder"] = min(int(orderInfo["segmentOrder"]), int(row.get("segmentOrder") or 0))
            orderInfo["segmentOccurrence"] = min(
                int(orderInfo["segmentOccurrence"]), int(row.get("segmentOccurrence") or 1)
            )
            if periodKey == latestPeriod:
                orderInfo["latestMissing"] = 0
                orderInfo["latestRank"] = min(int(orderInfo["latestRank"]), sortOrder)

            prevRank = representativePeriodRank(orderInfo.get("_repPeriod"))
            currRank = representativePeriodRank(periodKey)
            if currRank >= prevRank:
                orderInfo["_repPeriod"] = periodKey

        if periodIdx % 4 == 3:
            gc.collect()

    if not topicMap:
        return []

    freqMetaByKey = {key: _rowFreqMeta(periodMap) for key, periodMap in topicMap.items()}
    topicKeysByTopic: dict[str, list[tuple[str, str]]] = {}
    for key in topicMap:
        topicKeysByTopic.setdefault(key[0], []).append(key)

    topicIndex: dict[str, int] = {}
    for topic, _seq in sorted(topicFirstSeq.items(), key=lambda item: item[1]):
        topicIndex[topic] = len(topicIndex)

    freqPriority = {"mixed": 0, "annual": 1, "quarterly": 2, "none": 3}

    def topicRowSortKey(key: tuple[str, str]) -> tuple[int, int, int, int, int, int, int, int, str]:
        topic, segmentKey = key
        majorNum, firstSeq = topicFirstSeq.get(topic, (99, 999999))
        topicIdx = topicIndex.get(topic, 999999)
        info = rowOrder.get(key, {})
        freqMeta = freqMetaByKey.get(key, {})
        return (
            majorNum,
            firstSeq,
            topicIdx,
            freqPriority.get(str(freqMeta.get("freqScope") or "none"), 9),
            int(info.get("latestMissing", 1)),
            int(info.get("latestRank", 999999999)),
            int(info.get("firstRank", 999999999)),
            int(info.get("segmentOccurrence", 1)),
            str(segmentKey),
        )

    descendingPeriods = sortPeriods(validPeriods, descending=True)
    periodRange = formatPeriodRange(descendingPeriods, descending=True, annualAsQ4=True)
    sortedTopics = [topic for topic, _seq in sorted(topicFirstSeq.items(), key=lambda item: item[1])]

    rows: list[dict[str, Any]] = []
    for rowIdx, topic in enumerate(sortedTopics):
        topicKeys = sorted(topicKeysByTopic.get(topic, []), key=topicRowSortKey)
        periodCount = 0
        preview = "-"
        for period in descendingPeriods:
            firstText: str | None = None
            anyNonNull = False
            for key in topicKeys:
                value = topicMap.get(key, {}).get(period)
                if value is None:
                    continue
                anyNonNull = True
                if firstText is None:
                    firstText = str(value)
            if anyNonNull:
                periodCount += 1
                if preview == "-" and firstText is not None:
                    previewText = firstText.replace("\n", " ").strip()[:80]
                    preview = f"{displayPeriod(period, annualAsQ4=True)}: {previewText}"

        chapter = topicChapter.get(topic) or company._chapterForTopic(topic)
        chapterNum = _CHAPTER_ORDER.get(chapter, 12)
        rows.append(
            {
                "chapter": _CHAPTER_TITLES.get(chapter, chapter),
                "topic": topic,
                "label": company._topicLabel(topic),
                "kind": "docs",
                "source": "docs",
                "periods": periodRange,
                "shape": f"{periodCount}기간",
                "preview": preview,
                "_sortKey": (chapterNum, 100 + rowIdx),
            }
        )
    return rows


def indexReportRows(company: Company, *, existingTopics: set[str] | None = None) -> list[dict[str, Any]]:
    """report 영역의 index rows — API_TYPES 기반."""
    rows: list[dict[str, Any]] = []
    if not company._hasReport:
        return rows

    from dartlab.providers.dart.report.types import API_TYPE_LABELS, API_TYPES

    existing = existingTopics or set()
    for rIdx, apiType in enumerate(API_TYPES):
        if apiType in existing:
            continue
        df = company._report.extract(apiType)
        if isEmptyDf(df):
            continue
        chapter = company._chapterForTopic(apiType)
        chapterNum = _CHAPTER_ORDER.get(chapter, 12)
        rows.append(
            {
                "chapter": _CHAPTER_TITLES.get(chapter, chapter),
                "topic": apiType,
                "label": API_TYPE_LABELS.get(apiType, apiType),
                "kind": "report",
                "source": "report",
                "periods": "-",
                "shape": _shapeString(df),
                "preview": API_TYPE_LABELS.get(apiType, apiType),
                "_sortKey": (chapterNum, 200 + rIdx),
            }
        )
    return rows
