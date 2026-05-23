"""sections wide 보드 polars 등가 (DuckDB 없이).

``_sectionsPolarsOnly(stockCode, topics)`` — Phase 1 (per-period row 생성) →
pivot last-wins + 충돌 카운터 → Phase 2 의 5 group_by + agg →
Phase 3 join → Phase 4 freqMeta → Phase 5 sort → Phase 6 blockOrder
재부여 → Phase 7 schema cast.

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수를 re-import.

parity test: ``tests/providers/dart/docs/test_sectionsPolarsParity.py``
(5 종목 × shape/dtypes/values strict equals).
"""

from __future__ import annotations

import gc
import logging
import os

import polars as pl

from dartlab.providers.dart.docs.sections.expansion import _expandStructuredRows
from dartlab.providers.dart.docs.sections.pathNormalizer import _comparablePathInfo
from dartlab.providers.dart.docs.topicStandard import TOPIC_CANONICAL_CHAPTER

_log = logging.getLogger("dartlab.providers.dart.docs.sections.pipeline")


def _periodRowsForKey(periodRowsDf: pl.DataFrame, periodKey: str) -> list[dict[str, object]]:
    """단일 period 의 dict list 추출 — 짧은 lifetime materialize."""
    if periodRowsDf.is_empty():
        return []
    return periodRowsDf.filter(pl.col("_periodKey") == periodKey).drop("_periodKey").to_dicts()


def _sectionsPolarsOnly(stockCode: str, topics: set[str] | None) -> pl.DataFrame | None:
    """sections() polars-only 등가 (DuckDB 없이).

    parity test: ``tests/providers/dart/docs/test_sectionsPolarsParity.py``
    (5 종목 × shape/dtypes/values strict equals).
    """
    from dartlab.providers.dart.docs.sections.pipeline import _getPrepared
    from dartlab.providers.dart.docs.sections.runtime import detailTopicForTopic, projectionSuppressedTopics
    from dartlab.providers.dart.docs.sections.runtimeProjection import applyProjections

    prepared = _getPrepared(stockCode)
    validPeriods = prepared.validPeriods
    teacherTopics = prepared.teacherTopics
    suppressed = projectionSuppressedTopics()
    periodRowsDf = prepared.periodRowsDf

    if not validPeriods:
        return None

    latestPeriod = validPeriods[-1]

    def _periodToRank(p: str) -> int:
        year = int(p[:4])
        quarter = {"Q1": 1, "Q2": 2, "Q3": 3}.get(p[4:], 4)
        return (year * 10) + quarter

    periodDfs: list[pl.DataFrame] = []
    rowIdxCounter = 0

    for pIdx, periodKey in enumerate(validPeriods):
        projected = applyProjections(_periodRowsForKey(periodRowsDf, periodKey), teacherTopics)
        if topics is not None:
            projected = [r for r in projected if r.get("topic") in topics]

        rows: list[dict[str, object]] = []
        repRank = _periodToRank(periodKey)
        isLatest = periodKey == latestPeriod

        for row in _expandStructuredRows(projected):
            chapter = row.get("chapter")
            topic = row.get("topic")
            text = row.get("text")
            blockType = row.get("blockType", "text")
            segmentKey = row.get("segmentKey")
            if not isinstance(chapter, str) or not isinstance(topic, str) or not isinstance(text, str):
                continue
            if not isinstance(blockType, str):
                blockType = "text"
            if not isinstance(segmentKey, str) or not segmentKey:
                continue
            if topic in suppressed.get(chapter, set()):
                continue
            if detailTopicForTopic(topic) is not None:
                continue

            comparablePathKey, comparableParentPathKey = _comparablePathInfo(
                topic,
                str(row.get("textSemanticPathKey") or row.get("textPathKey") or "") or None,
            )
            rows.append(
                {
                    "_rowIdx": rowIdxCounter,
                    "_repRank": repRank,
                    "_isLatest": isLatest,
                    "periodKey": periodKey,
                    "chapter": chapter,
                    "topic": topic,
                    "segmentKey": segmentKey,
                    "text": text,
                    "blockType": blockType,
                    "textNodeType": row.get("textNodeType") if isinstance(row.get("textNodeType"), str) else None,
                    "textStructural": row.get("textStructural")
                    if isinstance(row.get("textStructural"), bool)
                    else None,
                    "textLevel": int(row["textLevel"]) if isinstance(row.get("textLevel"), int) else None,
                    "textPath": row.get("textPath") if isinstance(row.get("textPath"), str) else None,
                    "textPathKey": row.get("textPathKey") if isinstance(row.get("textPathKey"), str) else None,
                    "textParentPathKey": row.get("textParentPathKey")
                    if isinstance(row.get("textParentPathKey"), str)
                    else None,
                    "textSemanticPathKey": row.get("textSemanticPathKey")
                    if isinstance(row.get("textSemanticPathKey"), str)
                    else None,
                    "textSemanticParentPathKey": row.get("textSemanticParentPathKey")
                    if isinstance(row.get("textSemanticParentPathKey"), str)
                    else None,
                    "textComparablePathKey": comparablePathKey,
                    "textComparableParentPathKey": comparableParentPathKey,
                    "sortOrder": int(row.get("sortOrder", 999999)),
                    "sourceBlockOrder": int(row.get("sourceBlockOrder") or 0),
                    "segmentOrder": int(row.get("segmentOrder") or 0),
                    "segmentOccurrence": int(row.get("segmentOccurrence") or 1),
                    "majorNum": int(row.get("majorNum", 99)),
                    "sourceTopic": str(row.get("sourceTopic")) if isinstance(row.get("sourceTopic"), str) else None,
                }
            )
            rowIdxCounter += 1

        if rows:
            periodDfs.append(pl.from_dicts(rows))
        rows = None  # noqa: F841 — 명시적 ref drop
        projected = None  # noqa: F841

        # gc.collect() 빈도 — 종목 005380 (~51k row, 31 period) 기준 period 당
        # ~10MB Python heap 누적. period 별 dict 누적 → polars 변환 시점 ref drop
        # 후 gc 가 dict 메모리 회수. 빈도 ↑ 시 회수 더 자주, CPU overhead 미미.
        if topics is None and pIdx % 3 == 2:
            gc.collect()

    if not periodDfs:
        return None

    df = pl.concat(periodDfs, how="diagonal_relaxed")
    periodDfs = None  # noqa: F841
    gc.collect()

    # pivot last-wins 충돌 가시화 — (topic, segmentKey, periodKey) 중복 row 가
    # 있으면 _rowIdx 마지막 text 만 살아남음 (silent loss).
    # DARTLAB_SECTIONS_STRICT=1 환경변수 시 ValueError 승격.
    collisionDf = df.group_by(["topic", "segmentKey", "periodKey"]).len().filter(pl.col("len") > 1)
    collisionCount = collisionDf.height
    if collisionCount > 0:
        samples = collisionDf.head(3).to_dicts()
        msg = (
            f"sections pivot 충돌 {collisionCount} 건 — (topic, segmentKey, periodKey) "
            f"중복 키. _rowIdx 마지막만 보존. 샘플: {samples}"
        )
        if os.environ.get("DARTLAB_SECTIONS_STRICT") == "1":
            raise ValueError(msg)
        _log.warning(msg)

    pivotDf = df.sort(["_rowIdx"]).pivot(
        values="text",
        index=["topic", "segmentKey"],
        on="periodKey",
        aggregate_function="last",
    )
    for p in validPeriods:
        if p not in pivotDf.columns:
            pivotDf = pivotDf.with_columns(pl.lit(None).cast(pl.Utf8).alias(p))

    df = df.drop("text")
    gc.collect()

    # Phase 2: per-(topic, segmentKey) aggregations — meta + order + path 3 group_by
    # → 단일 group_by 통합 (operation.sectionsRefactor §6 후보 B). dfSorted 위에서:
    #   - last() (meta) — _repRank/_rowIdx 정렬 후 최신 period 마지막 row
    #   - min() (order) — 정렬과 무관
    #   - .filter().unique().sort() (path) — 정렬과 무관
    keysDf = df.select(["topic", "segmentKey"]).unique()

    dfSorted = df.sort(["_repRank", "_rowIdx"])

    def _pathAgg(col: str) -> pl.Expr:
        return pl.col(col).filter(pl.col(col).is_not_null() & (pl.col(col) != "")).unique().sort()

    metaOrderPathDf = (
        dfSorted.group_by(["topic", "segmentKey"])
        .agg(
            [
                # meta — last() (dfSorted 마지막 = 최신 period 마지막 row)
                pl.col("blockType").last(),
                pl.col("textNodeType").last(),
                pl.col("textStructural").last(),
                pl.col("textLevel").last(),
                pl.col("textPath").last(),
                pl.col("textPathKey").last(),
                pl.col("textParentPathKey").last(),
                pl.col("textSemanticPathKey").last(),
                pl.col("textSemanticParentPathKey").last(),
                pl.col("textComparablePathKey").last(),
                pl.col("textComparableParentPathKey").last(),
                pl.col("sourceBlockOrder").last().alias("_metaSourceBlockOrder"),
                pl.col("segmentOrder").last().alias("_metaSegmentOrder"),
                pl.col("segmentOccurrence").last().alias("_metaSegmentOccurrence"),
                pl.col("sourceTopic").last(),
                # order — min()
                pl.col("sortOrder").min().alias("firstRank"),
                pl.col("sourceBlockOrder").min().alias("_orderSourceBlockOrder"),
                pl.col("segmentOrder").min().alias("_orderSegmentOrder"),
                pl.col("segmentOccurrence").min().alias("_orderSegmentOccurrence"),
                pl.when(pl.col("_isLatest")).then(pl.col("sortOrder")).otherwise(None).min().alias("_latestRankRaw"),
                pl.when(pl.col("_isLatest")).then(0).otherwise(1).min().alias("latestMissing"),
                # path variants
                _pathAgg("textPathKey").alias("textPathVariants"),
                _pathAgg("textParentPathKey").alias("textParentPathVariants"),
                _pathAgg("textSemanticPathKey").alias("textSemanticPathVariants"),
                _pathAgg("textSemanticParentPathKey").alias("textSemanticParentPathVariants"),
            ]
        )
        .with_columns(
            [
                pl.col("_latestRankRaw").fill_null(999999999).alias("latestRank"),
                pl.col("textPathVariants").list.len().cast(pl.Int64).alias("textPathVariantCount"),
            ]
        )
        .drop("_latestRankRaw")
    )

    topicChapterDf = (
        df.sort("_rowIdx")
        .group_by("topic", maintain_order=False)
        .first()
        .select(["topic", "chapter"])
        .rename({"chapter": "_topicChapter"})
    )

    topicFirstSeqDf = (
        df.sort(["majorNum", "sortOrder"])
        .group_by("topic", maintain_order=False)
        .first()
        .select(["topic", "majorNum", "sortOrder"])
        .rename({"majorNum": "_topicMajorNum", "sortOrder": "_topicFirstSeq"})
    )

    topicIndexDf = (
        topicFirstSeqDf.sort(["_topicMajorNum", "_topicFirstSeq"])
        .with_row_index("_topicIndex", offset=0)
        .with_columns(pl.col("_topicIndex").cast(pl.Int64))
        .select(["topic", "_topicIndex"])
    )

    # Phase 3: join all
    result = (
        keysDf.join(metaOrderPathDf, on=["topic", "segmentKey"], how="left")
        .join(topicChapterDf, on="topic", how="left")
        .join(topicFirstSeqDf, on="topic", how="left")
        .join(topicIndexDf, on="topic", how="left")
        .join(pivotDf, on=["topic", "segmentKey"], how="left")
    )

    # Phase 4: freqMeta
    annualCols = [p for p in validPeriods if not p.endswith(("Q1", "Q2", "Q3", "Q4"))]
    quarterlyCols = [p for p in validPeriods if p.endswith(("Q1", "Q2", "Q3", "Q4"))]

    def _validCell(col: str) -> pl.Expr:
        return pl.col(col).is_not_null() & (pl.col(col).cast(pl.Utf8).str.strip_chars() != "")

    if annualCols:
        annualCountExpr = pl.sum_horizontal([_validCell(p).cast(pl.Int64) for p in annualCols])
    else:
        annualCountExpr = pl.lit(0).cast(pl.Int64)
    if quarterlyCols:
        quarterlyCountExpr = pl.sum_horizontal([_validCell(p).cast(pl.Int64) for p in quarterlyCols])
    else:
        quarterlyCountExpr = pl.lit(0).cast(pl.Int64)

    if annualCols:
        latestAnnualExpr = pl.coalesce(
            [pl.when(_validCell(p)).then(pl.lit(p)).otherwise(None) for p in sorted(annualCols, reverse=True)]
        )
    else:
        latestAnnualExpr = pl.lit(None).cast(pl.Utf8)
    if quarterlyCols:
        latestQuarterlyExpr = pl.coalesce(
            [pl.when(_validCell(p)).then(pl.lit(p)).otherwise(None) for p in sorted(quarterlyCols, reverse=True)]
        )
    else:
        latestQuarterlyExpr = pl.lit(None).cast(pl.Utf8)

    result = result.with_columns(
        [
            annualCountExpr.alias("annualPeriodCount"),
            quarterlyCountExpr.alias("quarterlyPeriodCount"),
            latestAnnualExpr.alias("latestAnnualPeriod"),
            latestQuarterlyExpr.alias("latestQuarterlyPeriod"),
        ]
    )

    freqScopeExpr = (
        pl.when((pl.col("annualPeriodCount") > 0) & (pl.col("quarterlyPeriodCount") > 0))
        .then(pl.lit("mixed"))
        .when(pl.col("annualPeriodCount") > 0)
        .then(pl.lit("annual"))
        .when(pl.col("quarterlyPeriodCount") > 0)
        .then(pl.lit("quarterly"))
        .otherwise(pl.lit("none"))
    )

    def _hasFreq(freqName: str) -> pl.Expr:
        if freqName == "annual":
            cols = annualCols
        else:
            qSuffix = freqName.upper()
            cols = [p for p in quarterlyCols if p.endswith(qSuffix)]
        if not cols:
            return pl.lit(False)
        return pl.any_horizontal([_validCell(c) for c in cols])

    freqCategories = ["annual", "q1", "q2", "q3", "q4"]
    freqKeyListExpr = pl.concat_list(
        [pl.when(_hasFreq(f)).then(pl.lit(f)).otherwise(pl.lit(None, dtype=pl.Utf8)) for f in freqCategories]
    ).list.drop_nulls()
    freqKeyExpr = freqKeyListExpr.list.join(",")
    freqKeyFinalExpr = (
        pl.when((pl.col("annualPeriodCount") == 0) & (pl.col("quarterlyPeriodCount") == 0))
        .then(pl.lit("none"))
        .otherwise(freqKeyExpr)
    )

    result = result.with_columns(
        [
            freqScopeExpr.alias("freqScope"),
            freqKeyFinalExpr.alias("freqKey"),
        ]
    )

    # Phase 5: sort 9-tuple
    freqScopePriorityExpr = (
        pl.when(pl.col("freqScope") == "mixed")
        .then(0)
        .when(pl.col("freqScope") == "annual")
        .then(1)
        .when(pl.col("freqScope") == "quarterly")
        .then(2)
        .when(pl.col("freqScope") == "none")
        .then(3)
        .otherwise(9)
        .cast(pl.Int64)
    )
    result = result.with_columns(freqScopePriorityExpr.alias("_freqScopePriority")).sort(
        [
            "_topicMajorNum",
            "_topicFirstSeq",
            "_topicIndex",
            "_freqScopePriority",
            "latestMissing",
            "latestRank",
            "firstRank",
            "_orderSegmentOccurrence",
            "segmentKey",
        ]
    )

    # Phase 6: blockOrder per topic (0-indexed)
    result = result.with_columns(
        (pl.cum_count("segmentKey").over("topic", mapping_strategy="group_to_rows") - 1)
        .cast(pl.Int64)
        .alias("blockOrder")
    )

    # Phase 7: final schema cast — chapter canonical override + 3 fallback chains.
    chapter_expr: pl.Expr = pl.col("_topicChapter")
    for topic_key, canonical_chapter in TOPIC_CANONICAL_CHAPTER.items():
        chapter_expr = pl.when(pl.col("topic") == topic_key).then(pl.lit(canonical_chapter)).otherwise(chapter_expr)
    result = result.with_columns(
        [
            chapter_expr.alias("chapter"),
            (
                pl.when(pl.col("_orderSourceBlockOrder") != 0)
                .then(pl.col("_orderSourceBlockOrder"))
                .when(pl.col("_metaSourceBlockOrder") != 0)
                .then(pl.col("_metaSourceBlockOrder"))
                .otherwise(pl.lit(0))
                .cast(pl.Int64)
                .alias("sourceBlockOrder")
            ),
            (
                pl.when(pl.col("_orderSegmentOccurrence") != 0)
                .then(pl.col("_orderSegmentOccurrence"))
                .when(pl.col("_metaSegmentOccurrence") != 0)
                .then(pl.col("_metaSegmentOccurrence"))
                .otherwise(pl.lit(1))
                .cast(pl.Int64)
                .alias("segmentOccurrence")
            ),
            pl.col("_metaSegmentOrder").cast(pl.Int64).alias("segmentOrder"),
            pl.col("blockType").fill_null("text").alias("blockType"),
        ]
    )

    finalCols = [
        "chapter",
        "topic",
        "blockType",
        "blockOrder",
        "sourceBlockOrder",
        "textNodeType",
        "textStructural",
        "textLevel",
        "textPath",
        "textPathKey",
        "textParentPathKey",
        "textPathVariantCount",
        "textPathVariants",
        "textParentPathVariants",
        "textSemanticPathKey",
        "textSemanticParentPathKey",
        "textComparablePathKey",
        "textComparableParentPathKey",
        "textSemanticPathVariants",
        "textSemanticParentPathVariants",
        "segmentKey",
        "segmentOrder",
        "segmentOccurrence",
        "freqKey",
        "freqScope",
        "annualPeriodCount",
        "quarterlyPeriodCount",
        "latestAnnualPeriod",
        "latestQuarterlyPeriod",
        "sourceTopic",
    ] + list(validPeriods)

    listCols = (
        "textPathVariants",
        "textParentPathVariants",
        "textSemanticPathVariants",
        "textSemanticParentPathVariants",
    )
    intCols = (
        "blockOrder",
        "sourceBlockOrder",
        "textLevel",
        "textPathVariantCount",
        "segmentOrder",
        "segmentOccurrence",
        "annualPeriodCount",
        "quarterlyPeriodCount",
    )

    castExprs: list[pl.Expr] = []
    for col in finalCols:
        if col in intCols:
            castExprs.append(pl.col(col).cast(pl.Int64).alias(col))
        elif col == "textStructural":
            castExprs.append(pl.col(col).cast(pl.Boolean).alias(col))
        elif col in listCols:
            castExprs.append(
                pl.when(pl.col(col).list.len() == 0)
                .then(pl.lit(None, dtype=pl.List(pl.Utf8)))
                .otherwise(pl.col(col).cast(pl.List(pl.Utf8)))
                .alias(col)
            )
        else:
            castExprs.append(pl.col(col).cast(pl.Utf8).cast(pl.Categorical).alias(col))

    result = result.select(castExprs)
    gc.collect()
    return result
