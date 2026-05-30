"""사업보고서/분기보고서/반기보고서 섹션 청킹 파이프라인.

Company에서 호출되는 진입점.
기간별 섹션 청크를 생성하여 수평 비교 가능하게 한다.

period key 형식:
- "2024"   → 사업보고서 (연간)
- "2024Q1" → 1분기보고서
- "2024Q2" → 반기보고서
- "2024Q3" → 3분기보고서

반환 형식:
    (topic, blockType, blockOrder)(행) × period(열) DataFrame
    ┌──────────────┬───────────┬────────────┬────────┬──────────┬────────┐
    │ topic        │ blockType │ blockOrder │ 2025   │ 2025Q3   │ 2024   │
    ├──────────────┼───────────┼────────────┼────────┼──────────┼────────┤
    │ 사업의 개요  │ text      │ 0          │ 텍스트 │ 텍스트   │ 텍스트 │
    │ 사업의 개요  │ table     │ 1          │ 테이블 │ null     │ 테이블 │
    │ 사업의 개요  │ text      │ 2          │ 텍스트 │ null     │ 텍스트 │
    └──────────────┴───────────┴────────────┴────────┴──────────┴────────┘
"""

from __future__ import annotations

import gc
import logging
import os
import re
import threading

import polars as pl

_log = logging.getLogger(__name__)

from dartlab.providers.dart.docs.sections.runtime import (
    applyProjections,
    chapterTeacherTopics,
    detailTopicForTopic,
    projectionSuppressedTopics,
)
from dartlab.providers.dart.docs.sections.sectionsBase import (
    sortPeriods,
)

# ── Phase 1 캐시: parquet 로드 + topic 매핑 결과 재사용 ──
# DART 표준 chapter canonical override — SSOT 는 reference 레이어.
# 분기보고서가 같은 topic 의 stub 을 사업보고서와 다른 chapter 에 둘 때 데이터 순서에
# 따라 chapter 가 흔들리는 것을 차단. 표준 매핑이 first-seen 보다 우선.
from dartlab.providers.dart.docs.topicStandard import TOPIC_CANONICAL_CHAPTER  # noqa: E402

_preparedCache: dict[str, "_PreparedRows"] = {}
# _PreparedRows.periodRowsDf — 단일 polars DataFrame (모든 period row + _periodKey
# 컬럼). 이전 dict[str, list[dict]] 형태 → polars Rust arena 단일 보관 으로
# Python heap 의 dict 51000+ 누적 (~319MB for 005380) → polars DF (~100MB)
# 으로 3× 메모리 절감.
#
# DARTLAB_SECTIONS_CACHE 환경변수로 cache size 조정 (default 1). 다종목 batch
# (예 dashboard 빌더) 시 size 늘려 parquet 재로드 회피. 단 종목당 ~100MB Rust
# arena 보관이므로 메모리 trade-off 고려.
_PREPARED_CACHE_MAX = int(os.environ.get("DARTLAB_SECTIONS_CACHE", "1"))

# sections() 최종 출력 cache — Phase 2. _preparedCache (Phase 1) 위에 추가.
# sections() 본체가 매 호출마다 ~1.6s (SK하이닉스 기준 16 topic 전체 처리) 소요 →
# viewer 요청마다 새로 계산. 캐시 hit 시 0 비용.
# 키: (stockCode, frozenset(topics) | None). 값: 결과 DataFrame.
# 크기 제한: DARTLAB_SECTIONS_RESULT_CACHE env var. default 5.
_sectionsResultCache: dict[tuple[str, "frozenset[str] | None"], "pl.DataFrame | None"] = {}
_SECTIONS_RESULT_CACHE_MAX = int(os.environ.get("DARTLAB_SECTIONS_RESULT_CACHE", "5"))

# 모듈 레벨 dict 캐시 동시성 가드 — ThreadPool / async 호출 환경에서
# `next(iter(...))` + `del` 패턴이 lock 없이 진행되면 `KeyError` / mutation during
# iteration 가능. RLock 으로 read/evict/insert 직렬화. dashboard 빌더 같은
# 다중 스레드 호출자 안전.
_cacheLock = threading.RLock()

# `None` 자체가 sections() 의 valid 결과 (데이터 부재) 라서 `dict.get` 의
# `default=None` 으로 hit/miss 구분 불가. sentinel 로 miss 명시.
_CACHE_SENTINEL: object = object()


def _representativePeriodRank(period: str | None) -> int:
    """rowMeta latest-period wins 비교용 rank. annual=4, Q1=1, Q2=2, Q3=3."""
    if not isinstance(period, str):
        return -1
    year = int(period[:4])
    quarter = {"Q1": 1, "Q2": 2, "Q3": 3}.get(period[4:], 4)
    return (year * 10) + quarter


def _accumulatePeriodRows(
    *,
    validPeriods: list[str],
    periodRowsDf: pl.DataFrame,
    teacherTopics: dict[str, str],
    topicsFilter: frozenset[str] | None,
    suppressed: dict[str, set[str]],
    fullBuild: bool,
    topicMap: dict[tuple[str, str], dict[str, str]],
    rowMeta: dict[tuple[str, str], dict[str, object]],
    rowOrder: dict[tuple[str, str], dict[str, int]],
    pathVariantsByKey: dict[tuple[str, str], set[str]],
    parentPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticParentPathVariantsByKey: dict[tuple[str, str], set[str]],
    topicChapter: dict[str, str],
    topicFirstSeq: dict[str, tuple[int, int]],
) -> None:
    """전 period × row 누적 — 7 parallel dict + topicChapter/topicFirstSeq in-place 갱신.

    period 별 ``applyProjections`` + ``_expandStructuredRows`` 후 row 단위 처리:
    - topic/segmentKey 검증 + suppressed/detailTopic filter
    - topicMap cell merge (text concat, heading first-seen)
    - 4 pathVariants 누적
    - rowOrder min-aggregation (sourceBlockOrder/segmentOrder/occurrence)
    - rowMeta latest-period wins (`_representativePeriodRank` 기반)

    GC: ``fullBuild`` 시 period 5 마다 gen 0 회수 + 종료 시 1 회 full GC.
    """
    if not validPeriods:
        return
    latestPeriod = validPeriods[-1]

    for _pIdx, periodKey in enumerate(validPeriods):
        projected = applyProjections(
            _periodRowsForKey(periodRowsDf, periodKey),
            teacherTopics,
        )
        if topicsFilter is not None:
            projected = [r for r in projected if r.get("topic") in topicsFilter]
        for row in _expandStructuredRows(projected):
            chapter = row["chapter"]
            topic = row["topic"]
            text = row["text"]
            blockType = row.get("blockType", "text")
            segmentKey = row.get("segmentKey")
            if not isinstance(chapter, str) or not isinstance(topic, str) or not isinstance(text, str):
                continue
            if not isinstance(blockType, str):
                blockType = "text"
            if not isinstance(segmentKey, str) or not segmentKey:
                continue
            if topic not in topicChapter:
                # canonical override 가 있으면 DART 표준 chapter 강제, 없으면 first-seen.
                topicChapter[topic] = TOPIC_CANONICAL_CHAPTER.get(topic, chapter)
            if topic in suppressed.get(chapter, set()):
                continue
            if detailTopicForTopic(topic) is not None:
                continue

            key = (topic, segmentKey)
            if key not in topicMap:
                topicMap[key] = {}
            # 같은 (topic, segmentKey, period) 충돌 시:
            #  - body: cell 안 concatenate — path-anchored merge (옛 last-wins overwrite
            #    는 본문 손실). text block 만 (table 은 별 segmentKey 라 충돌 없음).
            #  - heading: single label per row — 같은 path 의 다른 marker text
            #    ("(1) X" vs "1. X" 같은 marker 변형) 가 concat 되면 sections 의
            #    "같은 의미 같은 row" 원칙 위반. first-seen 유지 (period order 가 latest→
            #    oldest 라 첫 번째 = 가장 최신 marker).
            existingCell = topicMap[key].get(periodKey)
            textNodeType = row.get("textNodeType")
            if existingCell and blockType == "text" and existingCell != text:
                if textNodeType == "heading":
                    # heading: 첫 번째 (가장 최신 period 의 first-seen) marker 유지
                    pass
                else:
                    topicMap[key][periodKey] = existingCell + "\n\n" + text
            else:
                topicMap[key][periodKey] = text
            if isinstance(row.get("textPathKey"), str) and row.get("textPathKey"):
                pathVariantsByKey.setdefault(key, set()).add(str(row["textPathKey"]))
            if isinstance(row.get("textParentPathKey"), str) and row.get("textParentPathKey"):
                parentPathVariantsByKey.setdefault(key, set()).add(str(row["textParentPathKey"]))
            if isinstance(row.get("textSemanticPathKey"), str) and row.get("textSemanticPathKey"):
                semanticPathVariantsByKey.setdefault(key, set()).add(str(row["textSemanticPathKey"]))
            if isinstance(row.get("textSemanticParentPathKey"), str) and row.get("textSemanticParentPathKey"):
                semanticParentPathVariantsByKey.setdefault(key, set()).add(str(row["textSemanticParentPathKey"]))
            comparablePathKey, comparableParentPathKey = _comparablePathInfo(
                topic,
                str(row.get("textSemanticPathKey") or row.get("textPathKey") or "") or None,
            )
            majorNum = int(row.get("majorNum", 99))
            sortOrder = int(row.get("sortOrder", 999999))
            if topic not in topicFirstSeq or (majorNum, sortOrder) < topicFirstSeq[topic]:
                topicFirstSeq[topic] = (majorNum, sortOrder)

            # setdefault 의 default arg 는 hit/miss 무관 매번 평가 (28k row × dict literal
            # = ~30K 불필요 dict alloc). get + None 체크로 miss 시만 dict 생성.
            orderInfo = rowOrder.get(key)
            if orderInfo is None:
                orderInfo = {
                    "latestRank": 999999999,
                    "latestMissing": 1,
                    "firstRank": 999999999,
                    "sourceBlockOrder": int(row.get("sourceBlockOrder") or 0),
                    "segmentOrder": int(row.get("segmentOrder") or 0),
                    "segmentOccurrence": int(row.get("segmentOccurrence") or 1),
                }
                rowOrder[key] = orderInfo
            orderInfo["firstRank"] = min(orderInfo["firstRank"], sortOrder)
            orderInfo["sourceBlockOrder"] = min(orderInfo["sourceBlockOrder"], int(row.get("sourceBlockOrder") or 0))
            orderInfo["segmentOrder"] = min(orderInfo["segmentOrder"], int(row.get("segmentOrder") or 0))
            orderInfo["segmentOccurrence"] = min(orderInfo["segmentOccurrence"], int(row.get("segmentOccurrence") or 1))
            if periodKey == latestPeriod:
                orderInfo["latestMissing"] = 0
                orderInfo["latestRank"] = min(orderInfo["latestRank"], sortOrder)

            prevMeta = rowMeta.get(key)
            prevRank = _representativePeriodRank(prevMeta.get("_repPeriod")) if isinstance(prevMeta, dict) else -1
            currRank = _representativePeriodRank(periodKey)
            # strict greater — 같은 period 안 *첫 row* 만 박힘. 옛 ``>=`` 은 마지막
            # row 박아 caption+body 합본 segmentKey 의 sourceBlockOrder 가 *마지막*
            # caption block 값 → table block 뒤로 밀림 (sectionsAssembler 정렬 회귀).
            if prevMeta is None or currRank > prevRank:
                rowMeta[key] = {
                    "chapter": chapter,
                    "topic": topic,
                    "blockType": blockType,
                    "sourceBlockOrder": int(row.get("sourceBlockOrder") or 0),
                    "textNodeType": row.get("textNodeType"),
                    "textStructural": row.get("textStructural"),
                    "textLevel": int(row["textLevel"]) if isinstance(row.get("textLevel"), int) else None,
                    "textPath": row.get("textPath"),
                    "textPathKey": row.get("textPathKey"),
                    "textParentPathKey": row.get("textParentPathKey"),
                    "textSemanticPathKey": row.get("textSemanticPathKey"),
                    "textSemanticParentPathKey": row.get("textSemanticParentPathKey"),
                    "textComparablePathKey": comparablePathKey,
                    "textComparableParentPathKey": comparableParentPathKey,
                    "segmentKey": segmentKey,
                    "segmentOrder": int(row.get("segmentOrder") or 0),
                    "segmentOccurrence": int(row.get("segmentOccurrence") or 1),
                    "sourceTopic": row.get("sourceTopic"),
                    "_repPeriod": periodKey,
                }

        # 큰 Python list 의 ref 끊기 + 전체 빌드만 주기적 gen 0 GC (full GC 대비 ~5× 빠름).
        # 짧은 lifetime dict 가 대부분 gen 0 이라 효과 동일. 5 baseline profile (035720)
        # full GC 8 회 × ~60ms = 480ms → gen 0 GC ~80ms 로 축소.
        del projected
        if fullBuild and _pIdx % 5 == 4:
            gc.collect(0)

    # 함수 종료 시점 1 회 full GC — 누적된 gen 1+/2 회수.
    gc.collect()


# 같은 headerHash + topic 표가 다른 path 에 분기된 fragment — segmentKey 안 `|h:<hash>` 부분 매칭.
_RE_TABLE_HEADER_HASH = re.compile(r"\|h:([0-9a-f]+)")


def _mergeFragmentTables(
    *,
    topicMap: dict[tuple[str, str], dict[str, str]],
    rowMeta: dict[tuple[str, str], dict[str, object]],
    rowOrder: dict[tuple[str, str], dict[str, int]],
    pathVariantsByKey: dict[tuple[str, str], set[str]],
    parentPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticPathVariantsByKey: dict[tuple[str, str], set[str]],
    semanticParentPathVariantsByKey: dict[tuple[str, str], set[str]],
) -> None:
    """Cross-path table consolidation — 같은 headerHash + topic 표를 longest path = canonical 로 통합.

    회귀 사례 (000660 businessOverview): "생산설비의현황" 표가 path "주요제품서비스등 >
    생산설비의현황" (9 cells annual) 과 path "생산설비의현황" (1 cell quarterly) 으로
    fragment — parquet 구조 variance 로 같은 표가 다른 parent 아래 emit. headerHash
    동일 → 같은 표 → 1 row 통합. 모든 mutation 은 인자 dict 에 in-place.
    """
    hashGroups: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for key in topicMap:
        topic_, sk_ = key
        if not sk_.startswith("table|"):
            continue
        m_ = _RE_TABLE_HEADER_HASH.search(sk_)
        if not m_:
            continue
        hashGroups.setdefault((topic_, m_.group(1)), []).append(key)

    def _pathLen(k: tuple[str, str]) -> int:
        meta_ = rowMeta.get(k, {})
        return len(str(meta_.get("textSemanticPathKey") or ""))

    variantDicts = (
        pathVariantsByKey,
        parentPathVariantsByKey,
        semanticPathVariantsByKey,
        semanticParentPathVariantsByKey,
    )
    for groupKeys in hashGroups.values():
        if len(groupKeys) <= 1:
            continue
        # canonical = longest semantic path (가장 구체적 context)
        canonical = max(groupKeys, key=_pathLen)
        for k in groupKeys:
            if k == canonical:
                continue
            # cell merge — canonical 우선, 부재 period 만 보충
            for period_, val_ in topicMap[k].items():
                if val_ and not topicMap[canonical].get(period_):
                    topicMap[canonical][period_] = val_
            # path variants 보존 — pivot 결과 textPathVariants 컬럼에 모든 variant 노출
            for variantDict in variantDicts:
                if k in variantDict:
                    variantDict.setdefault(canonical, set()).update(variantDict[k])
                    variantDict.pop(k, None)
            topicMap.pop(k, None)
            rowMeta.pop(k, None)
            rowOrder.pop(k, None)


# ── _assembleSectionsDataFrame + _SECTIONS_SCHEMA_FIXED 는 sectionsAssembler.py 로 분리 (룰 3 LoC).
from dartlab.providers.dart.docs.sections.sectionsAssembler import (  # noqa: E402, F401
    _SECTIONS_SCHEMA_FIXED,
    _assembleSectionsDataFrame,
)


def _cacheSectionsResult(cacheKey: tuple[str, "frozenset[str] | None"], result: "pl.DataFrame | None") -> None:
    """sections() 결과 LRU + 디스크 캐시 저장. 크기 제한 초과 시 가장 오래된 항목 제거.

    Phase 3 추가: 디스크 캐시 (data/dart/sectionsCache/{code}_{hash}.parquet) 도 동시
    저장. 프로세스 재시작 후에도 build cost 회피.
    """
    from dartlab.providers.dart.docs.sections.diskCache import saveDiskCache as _saveDiskCache

    with _cacheLock:
        if len(_sectionsResultCache) >= _SECTIONS_RESULT_CACHE_MAX:
            oldest = next(iter(_sectionsResultCache))
            del _sectionsResultCache[oldest]
        _sectionsResultCache[cacheKey] = result
    # 디스크 캐시 동행 저장 — None 이면 saveDiskCache 가 skip. lock 밖에서 IO 수행.
    if result is not None:
        _saveDiskCache(cacheKey[0], cacheKey[1], result)


class _PreparedRows:
    """Phase 1 결과 — parquet 로드 + _reportRowsToTopicRows (polars DF 누적) + teacherTopics.

    periodRowsDf 컬럼: chapter / topic / blockType / blockOrder / sourceBlockOrder /
    text / majorNum / orderSeq / sourceTopic / _periodKey.
    """

    __slots__ = ("periodRowsDf", "validPeriods", "teacherTopics")

    def __init__(
        self,
        periodRowsDf: pl.DataFrame,
        validPeriods: list[str],
        teacherTopics: dict[str, str],
    ):
        self.periodRowsDf = periodRowsDf
        self.validPeriods = validPeriods
        self.teacherTopics = teacherTopics


from dartlab.providers.dart.docs.sections.aggregation import (  # noqa: F401
    _periodRowsForKey,
)


def _getPrepared(stockCode: str) -> _PreparedRows:
    """Phase 1 결과를 캐싱하여 반환. 같은 종목 반복 호출 시 parquet 재로드 방지.

    캐시 계층 — in-memory LRU (process 수명) → disk IPC + JSON sidecar (process
    restart resilience) → cold build (xmlChunkToMixed 11s + 421MB peak). disk
    cache hit 시 mmap RSS 위임 + 50ms 안 reload (cold rebuild 의 0.5%).
    """
    with _cacheLock:
        cached = _preparedCache.get(stockCode)
    if cached is not None:
        return cached

    # Phase 1 disk cache — process restart 후 첫 호출도 XML parsing 11s 우회.
    from dartlab.providers.dart.docs.sections.diskCache import (
        loadPreparedDiskCache as _loadPreparedDiskCache,
    )

    diskHit = _loadPreparedDiskCache(stockCode)
    if diskHit is not None:
        periodRowsDfHit, validPeriodsHit, teacherTopicsHit = diskHit
        preparedHit = _PreparedRows(periodRowsDfHit, validPeriodsHit, teacherTopicsHit)
        with _cacheLock:
            existingHit = _preparedCache.get(stockCode)
            if existingHit is not None:
                return existingHit
            if len(_preparedCache) >= _PREPARED_CACHE_MAX:
                oldestHit = next(iter(_preparedCache))
                del _preparedCache[oldestHit]
            _preparedCache[stockCode] = preparedHit
        return preparedHit

    validPeriods: list[str] = []
    latestAnnualRows: list[dict[str, object]] | None = None
    # period 별 DataFrame 을 list 에 모은 뒤 단일 pl.concat 으로 결합.
    # 이전 vstack 반복 (~31 period O(N) 마다 새 frame 복사) → O(N×periods) Python
    # heap 압박. 단일 concat 은 polars 내부 chunk 단위 zero-copy → 메모리·시간 둘 다 절감.
    periodFrames: list[pl.DataFrame] = []

    for periodKey, reportKind, ccol, subset in iterPeriodSubsets(stockCode):
        validPeriods.append(periodKey)
        topicDf = _reportRowsToTopicRows(subset, ccol)
        if reportKind == "annual" and latestAnnualRows is None:
            # chapterTeacherTopics 가 list[dict] 가정 — 첫 annual 만 변환 (작음)
            latestAnnualRows = topicDf.to_dicts() if topicDf.height > 0 else []
        if topicDf.height > 0:
            periodFrames.append(topicDf.with_columns(pl.lit(periodKey).alias("_periodKey")))
        topicDf = None  # noqa: F841 — 명시적 ref drop

    teacherTopics = chapterTeacherTopics(latestAnnualRows or [])
    latestAnnualRows = None  # noqa: F841
    validPeriods = sortPeriods(validPeriods)

    if not periodFrames:
        periodRowsDf = pl.DataFrame()
    else:
        periodRowsDf = pl.concat(periodFrames, how="vertical").rechunk()
    periodFrames = []  # noqa: F841 — drop frame refs
    gc.collect()

    prepared = _PreparedRows(periodRowsDf, validPeriods, teacherTopics)

    # Phase 1 disk cache write — 다음 process restart 첫 호출이 mmap reload 로 50ms.
    # write 비용 ~30~50ms (zstd IPC compression), build 한 후 1 회. None / 빈 DF 면 skip.
    try:
        from dartlab.providers.dart.docs.sections.diskCache import (
            savePreparedDiskCache as _savePreparedDiskCache,
        )

        _savePreparedDiskCache(stockCode, periodRowsDf, validPeriods, teacherTopics)
    except Exception as exc:  # noqa: BLE001 — disk cache write 실패가 build 자체 실패로 번지면 안 됨
        _log.warning("preparedDiskCache save 실패 %s (%s) — in-memory only", stockCode, exc)

    # LRU 방식: 최대치 초과 시 가장 오래된 항목 제거. lock 가드 — concurrent build race 차단.
    with _cacheLock:
        # 동시 빌드: 다른 스레드가 먼저 채웠다면 중복 작업 회피하고 그쪽 결과 채택.
        existing = _preparedCache.get(stockCode)
        if existing is not None:
            return existing
        if len(_preparedCache) >= _PREPARED_CACHE_MAX:
            oldest = next(iter(_preparedCache))
            del _preparedCache[oldest]
        _preparedCache[stockCode] = prepared
    return prepared


def clearPreparedCache(stockCode: str | None = None) -> None:
    """Phase 1 캐시 해제. stockCode=None이면 전체 해제.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> clearPreparedCache(...)

    SeeAlso:
        - ``chunker`` / ``runtime`` / ``views`` / ``analysis`` — sections sub modules.

    Requires:
        - dartlab
        - gc
        - polars

    Capabilities:
        - 사업/분기/반기 보고서 sections 청킹 + 수평화 (topic × period 보드).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections pipeline — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company.sections 위임.
            - period key 형식 변형 ("2024-Q1") → 매칭 X. "2024Q1" strict.
        OutputSchema:
            - pl.DataFrame (topic × period 보드) / Iterator — 함수별.
        Prerequisites:
            - 본 회사 docs parquet.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - docs parquet → 청킹 → 수평화 → 본 함수.
        TargetMarkets:
            - KR (DART) sections pipeline.
    """
    with _cacheLock:
        if stockCode is None:
            _preparedCache.clear()
            _sectionsResultCache.clear()
        else:
            _preparedCache.pop(stockCode, None)
            # 같은 stockCode 의 sections 결과 cache 도 동반 해제 (topics 무관 모두)
            toRemove = [k for k in _sectionsResultCache if k[0] == stockCode]
            for k in toRemove:
                _sectionsResultCache.pop(k, None)


from dartlab.providers.dart.docs.sections.aggregation import (  # noqa: F401
    _sectionsPolarsOnly,
)
from dartlab.providers.dart.docs.sections.expansion import (  # noqa: F401
    _NOTES_TOPICS,
    _expandStructuredRows,
)
from dartlab.providers.dart.docs.sections.freqMeta import (  # noqa: F401
    _freqSortKey,
    _periodFreq,
    _rowFreqMeta,
)
from dartlab.providers.dart.docs.sections.pathNormalizer import (  # noqa: F401
    _BUSINESS_OVERVIEW_COMPARABLE_ROOTS,
    _BUSINESS_UNIT_SEGMENT_LITERALS,
    _RE_BUSINESS_UNIT_SEGMENT,
    _RE_BUSINESS_UNIT_SHORT,
    _STRUCTURE_SLOT_ALIASES,
    _comparablePathInfo,
    _isBusinessUnitSegment,
    _joinPathSegments,
    _normalizeComparableSegment,
    _splitPathSegments,
)
from dartlab.providers.dart.docs.sections.periodIter import (  # noqa: F401
    _SECTIONS_REQUIRED_COLS,
    _periodSortKey,
    iterPeriodSubsets,
)
from dartlab.providers.dart.docs.sections.reportRows import (  # noqa: F401
    _REPORT_ROW_SCHEMA,
    _reportRowsToTopicRows,
    _splitContentBlocks,
)

# ── 분석 함수들은 analysis.py로 이동 ──
# projectFreqRows, semanticRegistry, semanticCollisions,
# structureRegistry, structureCollisions, structureEvents,
# structureSummary, structureChanges


def sections(stockCode: str, topics: set[str] | None = None) -> pl.DataFrame | None:
    """전 기간 사업/분기/반기 보고서 섹션 보드 — (topic, blockType, blockOrder) × period.

    DART 정기공시 (사업보고서/분기보고서/반기보고서) 의 16 topic (사업개요/주요제품/원재료/
    매출실적/생산능력/주요계약/연구개발/기타투자/임직원/주주/배당/이사회/감사/계열사/
    공시정책/위험) 을 **수평화 (wide) 보드** 로 반환. 행 = topic × blockType (text/table) ×
    blockOrder, 열 = period (``"2024Q4"`` / ``"2024Q3"`` / ...).

    텍스트와 테이블을 ``blockType`` 으로 분리 — 같은 topic 이라도 text 행과 table 행이
    별도 row. table 은 markdown table syntax (cell ``|`` separator) 그대로 보존.

    Args:
        stockCode: 종목코드 (6 자리, 예: ``"005930"``).
        topics: 필요한 topic 집합 (예: ``{"businessOverview", "mainProducts"}``).
            None 이면 16 topic 전체. set 으로 명시 시 처리 비용 절감.

    Returns:
        pl.DataFrame — 행 = ``(topic, blockType, blockOrder)`` 멀티 키, 열 = period 컬럼들.
        값 = str (텍스트 또는 markdown table). period 미공시 분기 cell = None.

        데이터 부재 (parquet 없음 / period 0) 시 None.

    Raises:
        없음. parquet 부재 시 None 반환 (예외 X).

    Example:
        >>> df = sections("005930", topics={"businessOverview"})
        >>> df.select(["topic", "blockType", "blockOrder", "2024Q4"]).head()

    SeeAlso:
        - ``_getPrepared`` — period × topic 정규화 캐시.
        - ``chunker`` — text 블록 청킹.
        - ``views.buildMarkdownBlocks`` — markdown block builder.
        - ``analysis`` — sections 후속 분석.
        - ``runtime`` / ``runtimeProjection`` — runtime topic 매핑.
        - ``mapper`` — chapter/title → topic 16 매핑.

    Requires:
        - polars
        - gc (대량 row 처리 후 회수)
        - dartlab.providers.dart.docs.sections.* (chunker/views/runtime/mapper)

    Capabilities:
        - DART 사업/분기/반기 보고서 16 topic 정형화 + 수평화 wide 보드.
        - text + table 분리 — caller 가 blockType 으로 필터 가능.
        - period 별 변화 추적 — YoY/QoQ disclosure delta 분석 기반.
        - 다회 호출 시 ``_getPrepared`` LRU 캐시.

    Guide:
        - 사용자 API 는 ``c.sections`` / ``c.show("businessOverview")`` — 본 함수 backend.
        - 다종목 batch 시 stockCode 반복 호출해도 ``_getPrepared`` cache hit.
        - 특정 topic 만 필요 시 ``topics={"X"}`` 명시 — 전체 16 topic 처리 비용 절감.
        - "최신 분기 사업개요" → ``df.select([..., latestPeriod])`` 컬럼 선택.

    AIContext:
        Ask Workbench docs core — LLM 이 회사 사업 구조 파악 시 entry.
        ``c.sections.show("businessOverview")`` 후속 ``c.notes()`` / ``c.search()`` 호출.

    LLM Specifications:
        AntiPatterns:
            - 본 함수 직접 호출 X — ``c.sections`` / ``c.show("X")`` 위임.
            - period key 형식 변형 ("2024-Q1") → 매칭 X. "2024Q1" strict (no dash).
            - 16 topic 외 키 호출 → 빈 결과. mapper 의 ``CHAPTER_TO_TOPIC`` 매핑 사전 확인.
            - ``topics=None`` 다종목 발굴 호출 → 16 topic 전수 처리 비용 → 폭주. 명시 필수.
            - period 컬럼 cell 이 None 인 경우 = 해당 분기 미공시 (분기보고서 미출원).
              caller 가 None 체크 또는 ``fill_null`` 처리 의무.
        OutputSchema:
            - pl.DataFrame — 행 키 (``topic`` / ``blockType`` / ``blockOrder``) +
              period 컬럼들 (``"2024Q4"`` / ``"2024Q3"`` / ... 가변).
            - 셀 = str (텍스트 또는 markdown table syntax).
            - None — parquet 부재 / period 0.
        Prerequisites:
            - ``docs/{stockCode}.parquet`` (DART 사업보고서 raw + chunked).
            - ``mapper.CHAPTER_TO_TOPIC`` 매핑 사전 (16 topic 정의).
            - ``runtimeProjection.projectionSuppressedTopics`` (suppress list).
        Freshness:
            - DART 정기공시 cadence: 사업보고서 (연 1 회, 3 월), 반기 (8 월), 분기 (5/11 월).
            - parquet 은 공시 후 ETL ~ 24h 지연.
        Dataflow:
            - stockCode → ``_getPrepared`` (LRU, period × topic row 정규화)
            - → 16 topic chapter 매핑 (``mapper`` 의 정렬된 chapter 룰)
            - → text/table blockType 분리 (``_splitContentBlocks``)
            - → period × topic × blockOrder pivot (``_reportRowsToTopicRows``)
            - → suppressed topic 제거 + 정렬 → wide pl.DataFrame.
        TargetMarkets:
            - KR (DART) — 사업/분기/반기 보고서 정기공시 한정.
    """
    # Phase 2 결과 cache — 같은 (stockCode, topics) 호출 0 비용.
    cacheKey: tuple[str, "frozenset[str] | None"] = (
        stockCode,
        frozenset(topics) if topics is not None else None,
    )
    with _cacheLock:
        cached = _sectionsResultCache.get(cacheKey, _CACHE_SENTINEL)
    if cached is not _CACHE_SENTINEL:
        return cached  # type: ignore[return-value]
    # Phase 3 디스크 캐시 — 프로세스 재시작 후에도 build cost 회피. docs.parquet
    # 보다 새로운 cache 만 신뢰 (sectionsCache/{code}_{hash}.parquet).
    from dartlab.providers.dart.docs.sections.diskCache import loadDiskCache as _loadDiskCache

    diskCached = _loadDiskCache(stockCode, cacheKey[1])
    if diskCached is not None:
        with _cacheLock:
            _sectionsResultCache[cacheKey] = diskCached
        return diskCached

    topicMap: dict[tuple[str, str], dict[str, str]] = {}
    rowMeta: dict[tuple[str, str], dict[str, object]] = {}
    rowOrder: dict[tuple[str, str], dict[str, int]] = {}
    pathVariantsByKey: dict[tuple[str, str], set[str]] = {}
    parentPathVariantsByKey: dict[tuple[str, str], set[str]] = {}
    semanticPathVariantsByKey: dict[tuple[str, str], set[str]] = {}
    semanticParentPathVariantsByKey: dict[tuple[str, str], set[str]] = {}
    suppressed = projectionSuppressedTopics()

    prepared = _getPrepared(stockCode)
    validPeriods = prepared.validPeriods
    teacherTopics = prepared.teacherTopics
    # periodRowsDf 는 단일 polars DataFrame — 매 period 별 filter + to_dicts 로 짧은
    # lifetime 변환. 이전 dict[periodKey, list[dict]] 사본 (~319MB) → polars DF
    # (~100MB) 로 ~3× 메모리 절감 + period 별 dict 짧은 lifetime.
    periodRowsDf = prepared.periodRowsDf

    topicChapter: dict[str, str] = {}
    topicFirstSeq: dict[str, tuple[int, int]] = {}

    _accumulatePeriodRows(
        validPeriods=validPeriods,
        periodRowsDf=periodRowsDf,
        teacherTopics=teacherTopics,
        topicsFilter=frozenset(topics) if topics is not None else None,
        suppressed=suppressed,
        fullBuild=topics is None,
        topicMap=topicMap,
        rowMeta=rowMeta,
        rowOrder=rowOrder,
        pathVariantsByKey=pathVariantsByKey,
        parentPathVariantsByKey=parentPathVariantsByKey,
        semanticPathVariantsByKey=semanticPathVariantsByKey,
        semanticParentPathVariantsByKey=semanticParentPathVariantsByKey,
        topicChapter=topicChapter,
        topicFirstSeq=topicFirstSeq,
    )

    if not validPeriods or not topicMap:
        _cacheSectionsResult(cacheKey, None)
        return None

    _mergeFragmentTables(
        topicMap=topicMap,
        rowMeta=rowMeta,
        rowOrder=rowOrder,
        pathVariantsByKey=pathVariantsByKey,
        parentPathVariantsByKey=parentPathVariantsByKey,
        semanticPathVariantsByKey=semanticPathVariantsByKey,
        semanticParentPathVariantsByKey=semanticParentPathVariantsByKey,
    )

    out = _assembleSectionsDataFrame(
        validPeriods=validPeriods,
        topicMap=topicMap,
        rowMeta=rowMeta,
        rowOrder=rowOrder,
        topicChapter=topicChapter,
        topicFirstSeq=topicFirstSeq,
        pathVariantsByKey=pathVariantsByKey,
        parentPathVariantsByKey=parentPathVariantsByKey,
        semanticPathVariantsByKey=semanticPathVariantsByKey,
        semanticParentPathVariantsByKey=semanticParentPathVariantsByKey,
        fullBuild=topics is None,
    )
    finalOut = _dropChapterCatchAllDuplicates(out)
    _cacheSectionsResult(cacheKey, finalOut)
    return finalOut


# chapter title catch-all 매칭 — sectionMappings.json 의 "I. 회사의 개요" / "II. 사업의 내용"
# 류 룰이 만든 sourceTopic. specific leaf row 가 같은 (chapter, sourceBlockOrder) 로 존재하면
# catch-all 쪽은 중복 — 1.회사의 개요 leaf 화면이 4.주식의 총수 표를 머금는 회귀 차단.
from dartlab.providers.dart.docs.sections.dedupCleanup import (  # noqa: F401
    _CHAPTER_CATCH_ALL_RE,
    _dropChapterCatchAllDuplicates,
)
from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle  # noqa: F401, E402
