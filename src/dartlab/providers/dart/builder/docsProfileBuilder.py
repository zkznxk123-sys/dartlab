"""DART Company sections / profile / chapter 메타 helpers.

Company.sections / _profileTable / _chapterMap / _chapterForTopic / _topicLabel 본체를
facade 에서 분리. Company facade 는 thin delegate.

sections 는 docs + finance + report 3 source 통합 지도. show/trace/diff 의 근간.

Module-level constants:
    _STATIC_CHAPTER_MAP — topic → chapter (II~XII) 정적 매핑

Module-level functions:
    buildSections      — sections property 본체 (3 source 병합)
    profileTable       — section profile artifact (캐시)
    chapterMap         — static + profile-derived 매핑 (캐시)
    chapterForTopic    — topic → chapter (notes XI / unknown XII fallback)
    topicLabel         — topic → 한글 라벨 (CIS/SCE 우선 + registry/_TOPIC_LABELS)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.providers.dart.checks import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


# DART 정기보고서 표준 (사업보고서) chapter 매핑. 분기보고서가 stub 을 다른 chapter
# 에 두는 케이스가 있어 분포 기반 추론이 불가 — 표준 명시가 단일 진실값.
_STATIC_CHAPTER_MAP: dict[str, str] = {
    # I. 회사의 개요
    "companyOverview": "I",       # 1. 회사의 개요
    "companyHistory": "I",        # 2. 회사의 연혁
    "capitalChange": "I",         # 3. 자본금 변동사항 (← 옛 매핑 VII 오류 교정)
    "shareCapital": "I",          # 4. 주식의 총수 등
    "articlesOfIncorporation": "I",  # 5. 정관에 관한 사항
    # III. 재무에 관한 사항
    "BS": "III",
    "IS": "III",
    "CIS": "III",
    "CF": "III",
    "SCE": "III",
    "ratios": "III",
    "fsSummary": "III",           # 1. 요약재무정보
    "consolidatedStatements": "III",  # 2. 연결재무제표
    "consolidatedNotes": "III",   # 3. 연결재무제표 주석
    "financialStatements": "III", # 4. 재무제표
    "financialNotes": "III",      # 5. 재무제표 주석
    "dividend": "III",            # 6. 배당에 관한 사항 (← 누락 채움)
    # V. 회계감사인의 감사의견 등
    "audit": "V",
    "auditOpinion": "V",
    "auditContract": "V",
    "nonAuditContract": "V",
    # VI. 이사회 등 회사의 기관에 관한 사항
    "outsideDirector": "VI",
    # VII. 주주에 관한 사항
    "majorHolder": "VII",
    "majorHolderChange": "VII",
    "minorityHolder": "VII",
    "treasuryStock": "VII",
    "stockTotal": "VII",
    "shareholderMeeting": "VII",
    # VIII. 임원 및 직원 등에 관한 사항
    "employee": "VIII",
    "executive": "VIII",
    "topPay": "VIII",
    "unregisteredExecutivePay": "VIII",
    "executivePayAllTotal": "VIII",
    "executivePayIndividual": "VIII",
    "executivePayByType": "VIII",
    "executivePayTotal": "VIII",
    # IX. 계열회사 등에 관한 사항
    "investedCompany": "IX",
    "relatedPartyTx": "IX",
    # X. 그 밖에 투자자 보호를 위하여 필요한 사항
    "publicOfferingUsage": "X",
    "privateOfferingUsage": "X",
    "corporateBond": "X",
    "shortTermBond": "X",
}


def profileTable(company: Company) -> pl.DataFrame | None:
    """section profile artifact 로드 (캐시).

    Args:
        company: Company 인스턴스.

    Returns:
        ``loadSectionProfileTable()`` 결과 또는 None.

    Raises:
        없음.

    Example:
        >>> profileTable(c)

    SeeAlso:
        - ``Company.sections`` / ``buildSections`` — public surface 와 본체.
        - ``docsIndexBuilder`` — index 빌더 (sections 보완).

    Requires:
        - dartlab
        - polars

    Capabilities:
        - DART Company.sections / profileTable / chapterMap / chapterForTopic / topicLabel 본체.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections builder — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company facade (c.sections/c._profileTable) 위임.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs/finance/report parquet.
        Freshness:
            - 데이터 갱신 시점.
        Dataflow:
            - 3 source → buildSections → profile/chapter 매핑 → 본 함수.
        TargetMarkets:
            - KR (DART) sections + profile.
    """
    cacheKey = "_sectionProfileTable"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    from dartlab.providers.dart.docs.sections.artifacts import loadSectionProfileTable

    table = loadSectionProfileTable()
    company._cache[cacheKey] = table
    return table


def chapterMap(company: Company) -> dict[str, str]:
    """topic → chapter (II~XII) 매핑 — static + profile-derived 결합.

    Args:
        company: Company 인스턴스.

    Returns:
        ``{topic: chapter}`` dict.

    Raises:
        없음.

    Example:
        >>> chapterMap(c)["BS"]
        'III'

    SeeAlso:
        - ``Company.sections`` / ``buildSections`` — public surface 와 본체.
        - ``docsIndexBuilder`` — index 빌더 (sections 보완).

    Requires:
        - dartlab
        - polars

    Capabilities:
        - DART Company.sections / profileTable / chapterMap / chapterForTopic / topicLabel 본체.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections builder — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company facade (c.sections/c._profileTable) 위임.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs/finance/report parquet.
        Freshness:
            - 데이터 갱신 시점.
        Dataflow:
            - 3 source → buildSections → profile/chapter 매핑 → 본 함수.
        TargetMarkets:
            - KR (DART) sections + profile.
    """
    cacheKey = "_chapterMap"
    if cacheKey in company._cache:
        return company._cache[cacheKey]

    mapping: dict[str, str] = dict(_STATIC_CHAPTER_MAP)

    table = profileTable(company)
    if table is not None and not table.is_empty():
        canonicalCol = "canonicalTopic" if "canonicalTopic" in table.columns else "topic"
        grouped = (
            table.filter(pl.col(canonicalCol).is_not_null(), pl.col("chapter").is_not_null())
            .group_by([canonicalCol, "chapter"])
            .agg(pl.len().alias("count"))
            .sort(["count", canonicalCol], descending=[True, False])
        )
        for row in grouped.iter_rows(named=True):
            topic = row.get(canonicalCol)
            chapter = row.get("chapter")
            if isinstance(topic, str) and isinstance(chapter, str) and topic not in mapping:
                mapping[topic] = chapter

    company._cache[cacheKey] = mapping
    return mapping


def chapterForTopic(company: Company, topic: str) -> str:
    """topic → chapter — notes XI / unknown XII fallback.

    Args:
        company: Company 인스턴스.
        topic: topic 이름.

    Returns:
        chapter str (II~XII).

    Raises:
        없음.

    Example:
        >>> chapterForTopic(c, "executive")
        'VIII'

    SeeAlso:
        - ``Company.sections`` / ``buildSections`` — public surface 와 본체.
        - ``docsIndexBuilder`` — index 빌더 (sections 보완).

    Requires:
        - dartlab
        - polars

    Capabilities:
        - DART Company.sections / profileTable / chapterMap / chapterForTopic / topicLabel 본체.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections builder — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company facade (c.sections/c._profileTable) 위임.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs/finance/report parquet.
        Freshness:
            - 데이터 갱신 시점.
        Dataflow:
            - 3 source → buildSections → profile/chapter 매핑 → 본 함수.
        TargetMarkets:
            - KR (DART) sections + profile.
    """
    cm = chapterMap(company)
    if topic in cm:
        return cm[topic]
    if company._notesAccessor is not None:
        from dartlab.providers.dart.docs.notes import _REGISTRY as _NOTES_REGISTRY

        if topic in _NOTES_REGISTRY:
            return "XI"
    return "XII"


def topicLabel(company: Company, topic: str) -> str:
    """topic → 한글 라벨 — CIS/SCE 우선 + registry/``_TOPIC_LABELS``.

    Args:
        company: Company 인스턴스.
        topic: topic 이름.

    Returns:
        한글 라벨 (미매핑 시 topic 그대로 반환).

    Raises:
        없음.

    Example:
        >>> topicLabel(c, "CIS")
        '포괄손익계산서'

    SeeAlso:
        - ``Company.sections`` / ``buildSections`` — public surface 와 본체.
        - ``docsIndexBuilder`` — index 빌더 (sections 보완).

    Requires:
        - dartlab
        - polars

    Capabilities:
        - DART Company.sections / profileTable / chapterMap / chapterForTopic / topicLabel 본체.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections builder — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company facade (c.sections/c._profileTable) 위임.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs/finance/report parquet.
        Freshness:
            - 데이터 갱신 시점.
        Dataflow:
            - 3 source → buildSections → profile/chapter 매핑 → 본 함수.
        TargetMarkets:
            - KR (DART) sections + profile.
    """
    from dartlab.core.registry import getEntry as _getEntry
    from dartlab.providers.dart.company import _TOPIC_LABELS, _getAllProperties

    if topic == "CIS":
        return "포괄손익계산서"
    if topic == "SCE":
        return "자본변동표"
    if topic in _TOPIC_LABELS:
        return _TOPIC_LABELS[topic]
    entry = _getEntry(topic)
    if entry is not None:
        return entry.label
    for name, label in _getAllProperties():
        if name == topic:
            return label
    return topic


def buildSections(company: Company) -> pl.DataFrame | None:
    """sections — docs + finance + report 통합 지도 (``c.sections`` property 본체).

    docs sections 행을 기본 골격으로, finance/report 행을 chapter/topic 정렬 위치에 삽입.
    docs 에 없는 finance/report topic 은 해당 chapter 의 마지막에 orphan 삽입. 결과는
    period 컬럼 내림차순 정렬.

    Args:
        company: Company 인스턴스.

    Returns:
        통합 sections DataFrame (BoundedCache) 또는 None (docs sections 부재).

    Raises:
        없음 (report merge 실패는 logger warning 후 계속 진행).

    Example:
        >>> sections = buildSections(c)

    SeeAlso:
        - ``Company.sections`` / ``buildSections`` — public surface 와 본체.
        - ``docsIndexBuilder`` — index 빌더 (sections 보완).

    Requires:
        - dartlab
        - polars

    Capabilities:
        - DART Company.sections / profileTable / chapterMap / chapterForTopic / topicLabel 본체.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections builder — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — Company facade (c.sections/c._profileTable) 위임.
        OutputSchema:
            - pl.DataFrame / dict / str — 함수별.
        Prerequisites:
            - 본 회사 docs/finance/report parquet.
        Freshness:
            - 데이터 갱신 시점.
        Dataflow:
            - 3 source → buildSections → profile/chapter 매핑 → 본 함수.
        TargetMarkets:
            - KR (DART) sections + profile.
    """
    from dartlab.providers.dart.company import _CHAPTER_TITLES, _topicForApiType
    from dartlab.providers.dart.docs.sections import reorderPeriodColumns

    cacheKey = "_sections"
    if cacheKey in company._cache:
        return company._cache[cacheKey]

    sectionsSource = company._docs.sections
    if sectionsSource is None:
        company._hintOnce("sections", "sections", "docs")
        company._cache[cacheKey] = None
        return None

    docsSec = sectionsSource.raw
    if docsSec is None:
        company._hintOnce("sections", "sections", "docs")
        company._cache[cacheKey] = None
        return None
    periodCols = [c for c in docsSec.columns if _isPeriodColumn(c)]
    cm = chapterMap(company)

    if "source" not in docsSec.columns:
        docsSec = docsSec.with_columns(pl.lit("docs").alias("source"))

    docsSchema = dict(docsSec.schema)
    if "source" not in docsSchema:
        docsSchema["source"] = pl.Utf8
    metaCols = [c for c in docsSec.columns if c not in periodCols]

    # finance/report에서 추가할 행 수집
    # key: topic → (chapter, source, maxBlockOrder)
    topicExtras: dict[str, list[dict[str, Any]]] = {}

    def _baseExtraRow(*, chapter: str, topic: str, source: str) -> dict[str, Any]:
        row = {col: None for col in metaCols}
        row.update(
            {
                "chapter": chapter,
                "topic": topic,
                "blockType": "table",
                "source": source,
            }
        )
        for p in periodCols:
            row[p] = None
        return row

    if company._hasFinance:
        for ft in ("BS", "IS", "CIS", "CF", "SCE"):
            if getattr(company._finance, ft, None) is not None:
                topicExtras.setdefault(ft, []).append(_baseExtraRow(chapter="III", topic=ft, source="finance"))
        if company._ratioSeries() is not None:
            topicExtras.setdefault("ratios", []).append(_baseExtraRow(chapter="III", topic="ratios", source="finance"))

    if company.rawReport is not None:
        try:
            for apiType in company._report.availableApiTypes:
                topic = _topicForApiType(apiType)
                chapter = cm.get(topic, "X")
                topicExtras.setdefault(topic, []).append(_baseExtraRow(chapter=chapter, topic=topic, source="report"))
        except (ValueError, KeyError, AttributeError) as e:
            import logging

            logging.getLogger(__name__).warning("sections report merge failed for %s: %s", company.stockCode, e)

    if not topicExtras:
        company._cache[cacheKey] = docsSec
        return docsSec

    # topic 순서대로 순회하면서 extra 행을 끼워넣기
    docsTopics = docsSec.get_column("topic").drop_nulls().unique(maintain_order=True).to_list()

    schema = docsSchema

    result_frames: list[pl.DataFrame] = []
    insertedExtras: set[str] = set()

    for topic in docsTopics:
        # 이 topic의 docs 행
        topicDocs = docsSec.filter(pl.col("topic") == topic)
        result_frames.append(topicDocs)

        # 이 topic에 대응하는 extra 행 → docs 블록 뒤에 append
        if topic in topicExtras:
            maxBo = topicDocs["blockOrder"].max()
            nextBo = (maxBo + 1) if maxBo is not None else 0
            for extra in topicExtras[topic]:
                extra["blockOrder"] = nextBo
                nextBo += 1
            result_frames.append(pl.DataFrame(topicExtras[topic], schema=schema))
            insertedExtras.add(topic)

    # docs에 없는 extra topic → 해당 chapter 위치에 독립 삽입
    orphanRows: list[dict[str, Any]] = []
    for topic, extras in topicExtras.items():
        if topic in insertedExtras:
            continue
        for extra in extras:
            extra["blockOrder"] = 0
            orphanRows.append(extra)

    if orphanRows:
        # chapter별로 그룹핑해서 해당 chapter의 마지막에 삽입
        orphanDf = pl.DataFrame(orphanRows, schema=schema)
        # result_frames 끝에 chapter 순서로 삽입
        for ch in _CHAPTER_TITLES.keys():
            chOrphans = orphanDf.filter(pl.col("chapter") == ch)
            if not chOrphans.is_empty():
                # 해당 chapter의 마지막 위치 찾기
                insertIdx = len(result_frames)
                for i, f in enumerate(result_frames):
                    if "chapter" in f.columns:
                        chapters = f["chapter"].to_list()
                        if ch in chapters:
                            insertIdx = i + 1
                result_frames.insert(insertIdx, chOrphans)

    if not result_frames:
        result = reorderPeriodColumns(docsSec, descending=True, annualAsQ4=True)
        company._cache[cacheKey] = result
        return result

    merged = pl.concat(result_frames, how="diagonal_relaxed")
    merged = reorderPeriodColumns(merged, descending=True, annualAsQ4=True)
    company._cache[cacheKey] = merged
    return merged
