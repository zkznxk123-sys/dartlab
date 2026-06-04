"""sections() wide DataFrame assembler — pipeline.py 분할 (룰 3 LoC).

`pipeline.py` 881 LoC 가 룰 3 임계 (>800) 위반. wide DataFrame 조립 단계
(`_SECTIONS_SCHEMA_FIXED` + `_assembleSectionsDataFrame` 합 ~200 줄) 을 본
모듈로 분리. caller compat — pipeline.py 가 re-export.
"""

from __future__ import annotations

import gc

import polars as pl

from dartlab.providers.dart.docs.sections.freqMeta import _rowFreqMeta
from dartlab.providers.dart.topicStandard import TOPIC_CANONICAL_CHAPTER

# final wide DataFrame 의 schema — 30 fixed columns + period dynamic columns.
_SECTIONS_SCHEMA_FIXED: dict[str, pl.DataType] = {
    "chapter": pl.Categorical,
    "topic": pl.Categorical,
    "blockType": pl.Categorical,
    "blockOrder": pl.Int64,
    "sourceBlockOrder": pl.Int64,
    "textNodeType": pl.Categorical,
    "textStructural": pl.Boolean,
    "textLevel": pl.Int64,
    "textPath": pl.Categorical,
    "textPathKey": pl.Categorical,
    "textParentPathKey": pl.Categorical,
    "textPathVariantCount": pl.Int64,
    "textPathVariants": pl.List(pl.Utf8),
    "textParentPathVariants": pl.List(pl.Utf8),
    "textSemanticPathKey": pl.Categorical,
    "textSemanticParentPathKey": pl.Categorical,
    "textComparablePathKey": pl.Categorical,
    "textComparableParentPathKey": pl.Categorical,
    "textSemanticPathVariants": pl.List(pl.Utf8),
    "textSemanticParentPathVariants": pl.List(pl.Utf8),
    "segmentKey": pl.Categorical,
    "segmentOrder": pl.Int64,
    "segmentOccurrence": pl.Int64,
    "freqKey": pl.Categorical,
    "freqScope": pl.Categorical,
    "annualPeriodCount": pl.Int64,
    "quarterlyPeriodCount": pl.Int64,
    "latestAnnualPeriod": pl.Categorical,
    "latestQuarterlyPeriod": pl.Categorical,
    "sourceTopic": pl.Categorical,
}


def _assembleSectionsDataFrame(
    *,
    validPeriods: list[str],
    topicMap: dict[tuple[str, str], dict[str, str]],
    rowMeta: dict[tuple[str, str], dict[str, object]],
    rowOrder: dict[tuple[str, str], dict[str, int]],
    topicChapter: dict[str, str],
    topicFirstSeq: dict[str, tuple[int, int]],
    pathVariantsByKey: dict[tuple[str, str], set[str]],
    parentPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticParentPathVariantsByKey: dict[tuple[str, str], set[str]],
    fullBuild: bool,
) -> pl.DataFrame:
    """누적된 dict 들을 wide pl.DataFrame 으로 조립.

    조립 패턴: column-by-column 변환 — Python list 와 Arrow buffer 동시 보유 회피.
    pop + Series 생성 후 list ref 즉시 drop. final pl.DataFrame stage peak +176MB
    → +88MB 절감 (005380 실측, 71 컬럼 × 19781 row). 정렬 키는 `_topicRowSortKey`
    (chapter majorNum + 최신 period sourceBlockOrder/segmentOrder/occurrence). 호출
    후 인자 dict 들은 모두 소비됨 (caller 가 del 불필요).
    """
    freqMetaByKey = {key: _rowFreqMeta(periodMap) for key, periodMap in topicMap.items()}
    topicKeysByTopic: dict[str, list[tuple[str, str]]] = {}
    for key in topicMap:
        topicKeysByTopic.setdefault(key[0], []).append(key)

    def _topicRowSortKey(k: tuple[str, str]) -> tuple[int, int, int, int, str]:
        """본문 원문 순서 보존 — chapter majorNum + 최신 period 첫 row sourceBlockOrder.

        정렬 키는 ``rowMeta`` (latest-period 의 *첫 등장* row) 기반. ``_accumulatePeriodRows``
        가 같은 (key, period) 안 첫 row 만 박도록 (currRank > prevRank, strict greater)
        수정 — 같은 segmentKey 의 caption + body text 들이 cell concat 시 *첫 caption
        의 sourceBlockOrder* 박혀 table block 들과 alternating 정상 정렬 보장.

        회귀 사례 (005930 consolidatedNotes_04 financialInstruments): 옛 ``>=``
        구현은 같은 period 안 마지막 row 박아 body 합본 row 의 sourceBlockOrder=8
        → 모든 table (src=1/3/5/7) 뒤로 밀려남. 옛 ``rowOrder.sourceBlockOrder``
        min 휴리스틱은 옛 period chunking 차이로 잘못된 min (옛 SK하이닉스
        companyOverview 회귀) — 정렬에 쓰지 않는다.
        """
        topic, _segmentKey = k
        majorNum, _firstSeq = topicFirstSeq.get(topic, (99, 999999))
        meta = rowMeta.get(k, {})
        return (
            majorNum,
            int(meta.get("sourceBlockOrder", 999999)),
            int(meta.get("segmentOrder", 0)),
            int(meta.get("segmentOccurrence", 1)),
            str(k[1]),
        )

    schema: dict[str, pl.DataType] = dict(_SECTIONS_SCHEMA_FIXED)
    for p in validPeriods:
        schema[p] = pl.Categorical

    dataColumns: dict[str, list[object]] = {col: [] for col in schema}
    sortedTopics = [topic for topic, _ in sorted(topicFirstSeq.items(), key=lambda x: x[1])]

    for topic in sortedTopics:
        topicKeys = sorted(topicKeysByTopic.get(topic, []), key=_topicRowSortKey)
        for blockOrder, key in enumerate(topicKeys):
            meta = rowMeta.get(key, {})
            orderInfo = rowOrder.get(key, {})
            freqMeta = freqMetaByKey.get(key, {})
            pathVariants = sorted(pathVariantsByKey.get(key, set()))
            parentPathVariants = sorted(parentPathVariantsByKey.get(key, set()))
            semanticPathVariants = sorted(semanticPathVariantsByKey.get(key, set()))
            semanticParentPathVariants = sorted(semanticParentPathVariantsByKey.get(key, set()))

            # canonical override 가 있으면 강제, 없으면 topicChapter (first-seen) 사용.
            dataColumns["chapter"].append(TOPIC_CANONICAL_CHAPTER.get(topic, topicChapter.get(topic)))
            dataColumns["topic"].append(topic)
            dataColumns["blockType"].append(str(meta.get("blockType") or "text"))
            dataColumns["blockOrder"].append(blockOrder)
            dataColumns["sourceBlockOrder"].append(
                int(orderInfo.get("sourceBlockOrder") or meta.get("sourceBlockOrder") or 0)
            )
            dataColumns["textNodeType"].append(
                str(meta["textNodeType"]) if isinstance(meta.get("textNodeType"), str) else None
            )
            dataColumns["textStructural"].append(
                bool(meta["textStructural"]) if isinstance(meta.get("textStructural"), bool) else None
            )
            dataColumns["textLevel"].append(int(meta["textLevel"]) if isinstance(meta.get("textLevel"), int) else None)
            dataColumns["textPath"].append(str(meta["textPath"]) if isinstance(meta.get("textPath"), str) else None)
            dataColumns["textPathKey"].append(
                str(meta["textPathKey"]) if isinstance(meta.get("textPathKey"), str) else None
            )
            dataColumns["textParentPathKey"].append(
                str(meta["textParentPathKey"]) if isinstance(meta.get("textParentPathKey"), str) else None
            )
            dataColumns["textPathVariantCount"].append(len(pathVariants))
            dataColumns["textPathVariants"].append(pathVariants or None)
            dataColumns["textParentPathVariants"].append(parentPathVariants or None)
            dataColumns["textSemanticPathKey"].append(
                str(meta["textSemanticPathKey"]) if isinstance(meta.get("textSemanticPathKey"), str) else None
            )
            dataColumns["textSemanticParentPathKey"].append(
                str(meta["textSemanticParentPathKey"])
                if isinstance(meta.get("textSemanticParentPathKey"), str)
                else None
            )
            dataColumns["textComparablePathKey"].append(
                str(meta["textComparablePathKey"]) if isinstance(meta.get("textComparablePathKey"), str) else None
            )
            dataColumns["textComparableParentPathKey"].append(
                str(meta["textComparableParentPathKey"])
                if isinstance(meta.get("textComparableParentPathKey"), str)
                else None
            )
            dataColumns["textSemanticPathVariants"].append(semanticPathVariants or None)
            dataColumns["textSemanticParentPathVariants"].append(semanticParentPathVariants or None)
            dataColumns["segmentKey"].append(str(meta.get("segmentKey") or ""))
            dataColumns["segmentOrder"].append(int(meta.get("segmentOrder") or 0))
            dataColumns["segmentOccurrence"].append(
                int(orderInfo.get("segmentOccurrence") or meta.get("segmentOccurrence") or 1)
            )
            dataColumns["freqKey"].append(str(freqMeta.get("freqKey") or "none"))
            dataColumns["freqScope"].append(str(freqMeta.get("freqScope") or "none"))
            dataColumns["annualPeriodCount"].append(int(freqMeta.get("annualPeriodCount") or 0))
            dataColumns["quarterlyPeriodCount"].append(int(freqMeta.get("quarterlyPeriodCount") or 0))
            dataColumns["latestAnnualPeriod"].append(
                str(freqMeta["latestAnnualPeriod"]) if isinstance(freqMeta.get("latestAnnualPeriod"), str) else None
            )
            dataColumns["latestQuarterlyPeriod"].append(
                str(freqMeta["latestQuarterlyPeriod"])
                if isinstance(freqMeta.get("latestQuarterlyPeriod"), str)
                else None
            )
            dataColumns["sourceTopic"].append(
                str(meta["sourceTopic"]) if isinstance(meta.get("sourceTopic"), str) else None
            )
            periodMap = topicMap.pop(key, None)
            if periodMap:
                for period in validPeriods:
                    dataColumns[period].append(periodMap.get(period))
            else:
                for period in validPeriods:
                    dataColumns[period].append(None)
            # 소비한 중간 dict 항목 즉시 해제
            rowMeta.pop(key, None)
            rowOrder.pop(key, None)
            pathVariantsByKey.pop(key, None)
            parentPathVariantsByKey.pop(key, None)
            semanticPathVariantsByKey.pop(key, None)
            semanticParentPathVariantsByKey.pop(key, None)
            freqMetaByKey.pop(key, None)

    # 메모리 해제: DataFrame 생성 전 잔여 dict 퇴출
    topicMap.clear()
    rowMeta.clear()
    rowOrder.clear()
    pathVariantsByKey.clear()
    parentPathVariantsByKey.clear()
    semanticPathVariantsByKey.clear()
    semanticParentPathVariantsByKey.clear()
    freqMetaByKey.clear()

    if fullBuild:
        gc.collect()

    # column-by-column 변환 — Python list 와 Arrow buffer 동시 보유 회피.
    # pop + Series 생성 후 list ref 즉시 drop. final pl.DataFrame stage peak
    # +176MB → +88MB 절감 (005380 실측, dataColumns 71 컬럼 × 19781 row).
    seriesList = []
    for colName in list(schema.keys()):
        values = dataColumns.pop(colName)
        seriesList.append(pl.Series(colName, values, dtype=schema[colName]))
        del values  # 즉시 ref drop
    return pl.DataFrame(seriesList)
