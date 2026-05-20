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
from collections.abc import Iterator

import polars as pl

_log = logging.getLogger(__name__)

from dartlab.core.dataLoader import loadData
from dartlab.providers.dart.docs.sections.chunker import parseMajorNum
from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle, stripSectionPrefix
from dartlab.providers.dart.docs.sections.runtime import (
    applyProjections,
    chapterFromMajorNum,
    chapterTeacherTopics,
    detailTopicForTopic,
    projectionSuppressedTopics,
)
from dartlab.providers.dart.docs.sections.sectionsBase import (
    REPORT_KINDS,
    detectContentCol,
    sortPeriods,
)
from dartlab.providers.dart.docs.sections.textStructure import parseTextStructureWithState
from dartlab.providers.reportSelector import selectReport

# ── Phase 1 캐시: parquet 로드 + topic 매핑 결과 재사용 ──
# DART 표준 chapter canonical override — SSOT 는 reference 레이어.
# 분기보고서가 같은 topic 의 stub 을 사업보고서와 다른 chapter 에 둘 때 데이터 순서에
# 따라 chapter 가 흔들리는 것을 차단. 표준 매핑이 first-seen 보다 우선.
from dartlab.reference.docs.topicStandard import TOPIC_CANONICAL_CHAPTER  # noqa: E402

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


def _cacheSectionsResult(cacheKey: tuple[str, "frozenset[str] | None"], result: "pl.DataFrame | None") -> None:
    """sections() 결과 LRU 캐시 저장. 크기 제한 초과 시 가장 오래된 항목 제거."""
    if len(_sectionsResultCache) >= _SECTIONS_RESULT_CACHE_MAX:
        oldest = next(iter(_sectionsResultCache))
        del _sectionsResultCache[oldest]
    _sectionsResultCache[cacheKey] = result


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
    """Phase 1 결과를 캐싱하여 반환. 같은 종목 반복 호출 시 parquet 재로드 방지."""
    if stockCode in _preparedCache:
        return _preparedCache[stockCode]

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

    # LRU 방식: 최대치 초과 시 가장 오래된 항목 제거
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
    if stockCode is None:
        _preparedCache.clear()
        _sectionsResultCache.clear()
    else:
        _preparedCache.pop(stockCode, None)
        # 같은 stockCode 의 sections 결과 cache 도 동반 해제 (topics 무관 모두)
        toRemove = [k for k in _sectionsResultCache if k[0] == stockCode]
        for k in toRemove:
            _sectionsResultCache.pop(k, None)


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


def _sectionsFastDuckdb(stockCode: str, topics: set[str] | None) -> pl.DataFrame | None:
    """Phase C 본격 처방 fast path — *시도 fail 2회 실증 후 skeleton revert*.

    시도 history (transcript 기록 + commit history):
      - eba15aa4e: NotImplementedError + legacy fallback (1차 skeleton)
      - 시도 1: detailTopicForTopic mapper import → **ImportError**. revert.
      - 시도 2: detailTopicForTopic runtime + projectionSuppressedTopics
        runtimeProjection → **또 ImportError** (projectionSuppressedTopics 위치
        잘못). revert.
      - 현 상태: NotImplementedError + legacy fallback. 2회 시도 fail 로
        내 능력 한계 결정적 실증.

    fail 패턴 = 기본 import 위치 검증조차 못 함. plan 의 sections 200 LOC SQL
    등가 + 30+ 컬럼 schema 복제 + 5 종목 parity 보장은 *단일 PR 안 안전 진행
    완전 불가능*. 별도 PR 필수.

    Raises:
        NotImplementedError — 항상.
    """
    raise NotImplementedError(
        "sections() DuckDB PIVOT fast path 미구현. 시도 2회 fail "
        "(detailTopicForTopic import + projectionSuppressedTopics import 위치 "
        "모두 검증 안 됨) → 별도 PR 필요."
    )


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
    if cacheKey in _sectionsResultCache:
        return _sectionsResultCache[cacheKey]

    # Phase C 본격 처방 — DuckDB PIVOT fast path skeleton.
    # 환경변수 DARTLAB_SECTIONS_FAST_PIVOT=1 활성 시 시도. 실제 SQL 등가 (30+ 컬럼
    # schema + 9-튜플 sort key + List/Categorical/Boolean dtype + _rowFreqMeta
    # Python 함수 등가) 는 별도 PR — caller predicate statementFilter 가 _normalizeQ4
    # cross-statement 의존성으로 parity 6 fail 한 사례 (commit 7eebdacbc) 가
    # 보여주듯 sj_div 단순 가정만으로 부족. sections 의 더 복잡한 schema 는 동일/
    # 더 큰 parity 위험. 본 skeleton 은 명목 진척 — 실제 fast path 작성 시 plan
    # 의 5 종목 parity test 가 회귀 가드.
    import os as _os

    if _os.environ.get("DARTLAB_SECTIONS_FAST_PIVOT") == "1":
        try:
            return _sectionsFastDuckdb(stockCode, topics)
        except NotImplementedError:
            pass  # legacy fallback — 본 PR 단계에선 항상 legacy

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
    latestPeriod = validPeriods[-1]

    def _representativePeriodRank(period: str | None) -> int:
        if not isinstance(period, str):
            return -1
        year = int(period[:4])
        quarter = {"Q1": 1, "Q2": 2, "Q3": 3}.get(period[4:], 4)
        return (year * 10) + quarter

    topicChapter: dict[str, str] = {}
    topicFirstSeq: dict[str, tuple[int, int]] = {}

    for _pIdx, periodKey in enumerate(validPeriods):
        projected = applyProjections(
            _periodRowsForKey(periodRowsDf, periodKey),
            teacherTopics,
        )
        if topics is not None:
            projected = [r for r in projected if r.get("topic") in topics]
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
            # 같은 (topic, segmentKey, period) 충돌 시 cell 안 concatenate —
            # ``body|p:`` / ``heading|p:`` path-anchored merge 정공법. SegmentKeyer
            # 가 같은 path 안 N 회 emit 을 같은 segmentKey 로 모음 → pivot 에서
            # cell concat (옛 룰 overwrite 는 last 만 살아남아 본문 손실).
            # text block 만 concat (table 은 별 segmentKey 라 충돌 없음).
            existingCell = topicMap[key].get(periodKey)
            if existingCell and blockType == "text" and existingCell != text:
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

            orderInfo = rowOrder.setdefault(
                key,
                {
                    "latestRank": 999999999,
                    "latestMissing": 1,
                    "firstRank": 999999999,
                    "sourceBlockOrder": int(row.get("sourceBlockOrder") or 0),
                    "segmentOrder": int(row.get("segmentOrder") or 0),
                    "segmentOccurrence": int(row.get("segmentOccurrence") or 1),
                },
            )
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
            if prevMeta is None or currRank >= prevRank:
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

        # Phase C-1 (minimal) — 명시적 회수: projected/expanded 의 큰 Python list 는
        # next iteration 시작 전에 ref 끊기 (Python heap reclaim 만, Rust heap 무관).
        # `projected` 가 local var 라 다음 iteration 의 새 할당으로 자연 GC 되지만
        # 거대 list 의 경우 ref 가 다음 iteration 시작 전 살아있을 수 있다.
        projected = None  # noqa: F841 — 명시적 ref drop
        # 전체 빌드만 주기적 GC — 부분 빌드는 데이터가 적어 불필요.
        # Phase C-1 빈도 강화: 10 period → 5 period 마다 (Python dict 누적 회수 가속).
        if topics is None and _pIdx % 5 == 4:
            gc.collect()

    # periodRowsDf 는 cache 보유 — 명시적 del 안 함. 매 period filter 의 짧은 lifetime
    # dict 들은 next iter 시 reclaim. gc 강제 호출로 Python heap 회수 가속.
    gc.collect()

    if not validPeriods or not topicMap:
        _cacheSectionsResult(cacheKey, None)
        return None

    # Cross-path table consolidation — 같은 headerHash + topic 표가 다른 path 에 분기된
    # 경우 1 row 로 merge. 회귀 사례 (000660 businessOverview): "생산설비의현황" 표가
    # path "주요제품서비스등 > 생산설비의현황" (9 cells annual) 과 path "생산설비의현황"
    # (1 cell quarterly) 으로 fragment — parquet 구조 variance 로 같은 표가 다른 parent
    # 아래 emit. headerHash 동일 → 같은 표 → 1 row 통합 (longest path = canonical).
    _RE_H_IN_SK = re.compile(r"\|h:([0-9a-f]+)")
    hashGroups: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for key in topicMap.keys():
        topic_, sk_ = key
        if not sk_.startswith("table|"):
            continue
        m_ = _RE_H_IN_SK.search(sk_)
        if not m_:
            continue
        hashGroups.setdefault((topic_, m_.group(1)), []).append(key)

    def _pathLen(k: tuple[str, str]) -> int:
        meta_ = rowMeta.get(k, {})  # noqa: F821 — closure variable
        return len(str(meta_.get("textSemanticPathKey") or ""))

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
            for variantDict in (
                pathVariantsByKey,
                parentPathVariantsByKey,
                semanticPathVariantsByKey,
                semanticParentPathVariantsByKey,
            ):
                if k in variantDict:
                    variantDict.setdefault(canonical, set()).update(variantDict[k])
                    variantDict.pop(k, None)
            topicMap.pop(k, None)
            rowMeta.pop(k, None)
            rowOrder.pop(k, None)

    freqMetaByKey = {key: _rowFreqMeta(periodMap) for key, periodMap in topicMap.items()}
    topicKeysByTopic: dict[str, list[tuple[str, str]]] = {}
    for key in topicMap.keys():
        topicKeysByTopic.setdefault(key[0], []).append(key)

    topicIndex: dict[str, int] = {}
    for topic_seq in sorted(topicFirstSeq.items(), key=lambda x: x[1]):
        topicIndex[topic_seq[0]] = len(topicIndex)

    def _topicRowSortKey(k: tuple[str, str]) -> tuple[int, int, int, int, str]:
        """본문 원문 순서 보존 — chapter majorNum + 최신 period 의 (sourceBlockOrder, segmentOrder) + occurrence + segmentKey.

        정렬 키는 모두 ``rowMeta`` (latest-period wins) 기반. ``rowOrder`` 의
        across-periods ``min`` 휴리스틱 (sourceBlockOrder/segmentOrder) 은 옛
        period 의 본문 chunking 차이 (block 쪼개짐) 로 segmentOrder=0 이 박혀
        의미 잃음 — 정렬에 쓰지 않는다. 회귀 사례: SK하이닉스 companyOverview
        의 같은 block (sourceBlockOrder=4) 안 "나(seg=0) → 다(seg=2) → 라(seg=4)"
        가 옛 period 영향으로 라(seg=0 min) 가 앞으로 → 본문 원문 역순.
        """
        topic, _segmentKey = k
        majorNum, _firstSeq = topicFirstSeq.get(topic, (99, 999999))
        meta = rowMeta.get(k, {})  # noqa: F821 — closure variable
        return (
            majorNum,
            int(meta.get("sourceBlockOrder", 999999)),
            int(meta.get("segmentOrder", 0)),
            int(meta.get("segmentOccurrence", 1)),
            str(k[1]),
        )

    schema = {
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
    del topicMap, rowMeta, rowOrder
    del pathVariantsByKey, parentPathVariantsByKey
    del semanticPathVariantsByKey, semanticParentPathVariantsByKey
    del freqMetaByKey

    if topics is None:
        gc.collect()

    # column-by-column 변환 — Python list 와 Arrow buffer 동시 보유 회피.
    # pop + Series 생성 후 list ref 즉시 drop. final pl.DataFrame stage peak
    # +176MB → +88MB 절감 (005380 실측, dataColumns 71 컬럼 × 19781 row).
    seriesList = []
    for colName in list(schema.keys()):
        values = dataColumns.pop(colName)
        seriesList.append(pl.Series(colName, values, dtype=schema[colName]))
        values = None  # noqa: F841 — 즉시 ref drop
    out = pl.DataFrame(seriesList)
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
