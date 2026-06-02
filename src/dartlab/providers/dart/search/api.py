"""dart 공시 검색 public API 본체.

`dartlab.providers.dart.search` 패키지의 search/buildIndex/profile/pulse 등
모든 함수 정의 위치. `__init__.py` 는 thin re-export 만 (룰 4).

scope 분리 검색:
- title: report_nm + section_title ngram (제목형 쿼리)
- content: section_content word BM25 (본문형 쿼리)
- auto (기본): 자동 판별
"""

from __future__ import annotations

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


SEARCH_SCOPES: tuple[str, ...] = ("auto", "title", "content", "both", "news")


def search(
    query: str,
    *,
    corp: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 10,
    scope: str = "auto",
) -> pl.DataFrame:
    """KR DART 공시 검색 — title (ngram) + content (BM25) 스코프 조합 entry.
          ``"content"`` (BM25 만) / ``"both"`` (title + content 합치되 scope 컬럼 동행).
        - corp 파라미터로 회사 한정 — 6 자리 stockCode / 8 자리 corpCode / 회사명 (resolver lookup).
        - start/end 필터 — ``rcept_dt`` 컬럼 기준 YYYYMMDD 문자열 비교.
        - corp 가 US ticker (소문자 5 자 이하 영문) → 안내 info DataFrame 반환 (EDGAR 안내).
        - title strict (정확 매칭) ≥ limit → title 만, 아니면 content 로 보강 (rcept_no 중복 제거).

    Args:
        query: 검색어 (한국어/영어/숫자 혼합 OK). 공백 strip 후 자체 매칭.
        corp: 회사 한정. None → 전체 회사. 6 자리 숫자 = stockCode, 8 자리 숫자 = corpCode,
            그 외 문자열 = 회사명 resolver lookup. lookup 실패 → 전체 검색 fallback.
        start: ``rcept_dt`` 시작일 (YYYYMMDD). None → 미적용.
        end: ``rcept_dt`` 종료일 (YYYYMMDD). None → 미적용.
        limit: 결과 최대 row 수. 기본 10.
        scope: ``"auto"`` (default) / ``"title"`` / ``"content"`` / ``"both"``. 외 값 → ValueError.

    Returns:
        pl.DataFrame — 검색 결과. 일반 컬럼 = ``rcept_no``/``rcept_dt``/``corp_name``/
        ``report_nm``/``section_title``/``section_content`` 등 (인덱스에 따라 가변).
        scope=both/auto 결과는 ``scope`` 컬럼 ("title"/"content") 동행. corp 가 US ticker
        → ``info`` 컬럼만 있는 안내 DataFrame.

    Raises:
        ValueError: scope 가 4 종 외 값.

    Example:
        >>> from dartlab.providers.dart.search.api import search
        >>> df = search("배당", limit=5)
        >>> df.height >= 0
        True
        >>> df2 = search("AAPL", corp="AAPL")  # US ticker 안내
        >>> "info" in df2.columns
        True
              으로 결과 회사 검증 권장.
            - query 가 매우 짧음 (1~2 글자) → ngram 정밀도 저하 → false positive 많음.
            - scope="both" 결과에서 동일 rcept_no 가 title/content 양쪽에 등장 (중복 제거 X).
            - start/end 가 잘못된 형식 (예 "2024-01-01") → 비교 결과 부정확. YYYYMMDD 권장.
        OutputSchema:
            - rows: ≤ limit 개 또는 corp 안내 시 3 (info 컬럼만).
            - columns: 인덱스 의존. 공통 = rcept_no/rcept_dt/corp_name/report_nm.
            - scope=both/auto 시 ``scope`` 컬럼 추가.
        Prerequisites:
            - title index (ngram) + content index (BM25) 가 빌드되어 있어야 함 (``buildIndex``).
            - 인덱스 미빌드 → 결과 0 또는 KeyError. ``stats()`` 로 확인.
        Freshness:
            - ``collectMeta`` + ``fillContent`` + ``rebuildContent`` 운영 후 검색 가능.
            - 본 함수 자체는 무상태. 인덱스가 freshness 결정.
        Dataflow:
            - DART OpenAPI → allFilingsCollector → parquet → 인덱스 빌드 → 본 함수 → AI 답변.
        TargetMarkets:
            - KR (DART) 한정. EDGAR (US) 는 별도 API. US ticker 입력 시 안내 fallback.
    """
    if corp and not str(corp).isdigit() and len(corp) <= 6:
        return pl.DataFrame(
            {
                "info": [
                    f"'{corp}'은 US ticker입니다. dartlab.search()는 DART(한국) 공시 전용입니다.",
                    "SEC EDGAR 공시 검색: https://efts.sec.gov/LATEST/search-index?q=...",
                    "또는 Company('AAPL').docs.sections로 10-K/10-Q 섹션을 조회하세요.",
                ]
            }
        )

    if scope not in SEARCH_SCOPES:
        raise ValueError(f"scope는 {SEARCH_SCOPES} 중 하나. 받은 값: {scope!r}")

    corpCode, stockCode = _resolveCorp(corp)

    if scope == "title":
        result = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    elif scope == "content":
        result = _searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    elif scope == "news":
        result = _searchNews(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    elif scope == "auto":
        result = _searchAuto(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    else:  # both
        titleHits = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
        contentHits = _searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
        titleHits = titleHits.with_columns(pl.lit("title").alias("scope"))
        contentHits = contentHits.with_columns(pl.lit("content").alias("scope"))
        commonCols = [c for c in titleHits.columns if c in contentHits.columns]
        if commonCols:
            result = pl.concat([titleHits.select(commonCols), contentHits.select(commonCols)])
        else:
            result = titleHits

    if result.height > 0 and "rcept_dt" in result.columns:
        if start:
            result = result.filter(pl.col("rcept_dt") >= start)
        if end:
            result = result.filter(pl.col("rcept_dt") <= end)

    return result


def _searchTitle(query, *, corpCode, stockCode, limit):
    from dartlab.providers.dart.search.ngramIndex import searchNgram

    return searchNgram(query, corpCode=corpCode, stockCode=stockCode, limit=limit)


def _searchContent(query, *, corpCode, stockCode, limit):
    from dartlab.providers.dart.search.fieldIndex import searchContent

    return searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)


def _searchNews(query, *, corpCode, stockCode, limit):
    """뉴스 전용 — content 인덱스에서 source='news' 행만. corp 지정 시 0 건(뉴스 corp 매핑 없음)."""
    from dartlab.providers.dart.search.fieldIndex import searchContent

    df = searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit * 4)
    if df is None or df.height == 0 or "source" not in df.columns:
        return df
    return df.filter(pl.col("source") == "news").head(limit)


def _searchAuto(query, *, corpCode, stockCode, limit):
    """auto 모드 — 의미 검색(bm25 + type→본문 경험확장 gated fusion).

    실험 V233~V240 확정 recipe. 키워드가 못 잡는 동의·관련 공시를 경험확장으로 회복하되 bm25 신뢰도
    높은 질의는 키워드 신뢰(gated). meaning.json 미빌드 시 bm25 단독으로 graceful degrade.
    """
    from dartlab.providers.dart.search.semantic import searchSemantic

    result = searchSemantic(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    if result.height > 0 and "info" not in result.columns and "scope" not in result.columns:
        result = result.with_columns(pl.lit("auto").alias("scope"))
    return result


def _resolveCorp(corp: str | None) -> tuple[str | None, str | None]:
    """corp 파라미터 → (corpCode, stockCode) 변환."""
    if not corp:
        return None, None
    if len(corp) == 6 and corp.isdigit():
        return None, corp
    if len(corp) == 8 and corp.isdigit():
        return corp, None
    try:
        from dartlab.core.listingResolver import getListingResolver

        resolver = getListingResolver()
        match = resolver.search(corp) if resolver else None
        if match is not None and match.height > 0:
            return None, match["stock_code"][0]
    except (ImportError, KeyError, ValueError, AttributeError):
        pass
    return None, None


def buildIndex(parquetPaths: list[str] | None = None, *, includeDocs: bool = False, **kwargs) -> int:
    """Ngram (title) 인덱스 빌드 — allFilings parquet + (옵션) docs sections 통합.
          시 default allFilings.parquet 1 종 처리.
        - ``includeDocs=True`` → sections parquet 도 인덱싱 (제목 + section_title ngram).
        - 운영자 admin 함수 — 일반 사용자 (AI) 가 직접 호출 X.

    Args:
        parquetPaths: 인덱싱 대상 parquet 경로 list. None → default.
        includeDocs: True → sections 도 포함. 기본 False.
        **kwargs: ngramIndex.buildNgramIndex 로 forward.

    Returns:
        int — 인덱싱된 row 수.

    Example:
        >>> # buildIndex()  # default
        >>> # buildIndex(includeDocs=True)  # 전체

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.ngramIndex import buildNgramIndex

    return buildNgramIndex(parquetPaths, includeDocs=includeDocs, **kwargs)


def rebuildIndex(**kwargs) -> int:
    """전체 인덱스 리빌드 — ``buildIndex(includeDocs=True)`` 단축.

    Args:
        **kwargs: buildIndex 로 forward.

    Returns:
        int — 인덱싱 row 수.

    Example:
        >>> # rebuildIndex()

    Raises:
        없음.
    """
    return buildIndex(includeDocs=True, **kwargs)


def rebuildContent(**kwargs) -> int:
    """content (BM25) 인덱스의 main 세그먼트 풀빌드 — 월 1 회 운영.

    Args:
        **kwargs: fieldIndex.rebuildMain 로 forward.

    Returns:
        int — 빌드된 row 수.

    Example:
        >>> # rebuildContent()

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildMain

    return rebuildMain(**kwargs)


def rebuildContentDelta(**kwargs) -> int:
    """content (BM25) 인덱스의 delta 세그먼트 일간 증분 빌드.

    Args:
        **kwargs: fieldIndex.rebuildDelta 로 forward.

    Returns:
        int — 추가 인덱싱 row 수.

    Example:
        >>> # rebuildContentDelta()

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildDelta

    return rebuildDelta(**kwargs)


def prefetch(tier: str | None = None) -> dict:
    """검색 인덱스를 HF 에서 미리 받아둔다(워밍) — 첫 검색 cold start 완화.

    `dartlab.search()` 는 첫 호출 시 자동 lazy pull 하지만, prefetch 로 사전 다운로드 가능.
    `DARTLAB_NO_HF_DOWNLOAD=1` 이면 skip. 받은 뒤 indexInfo 반환.

    Args:
        tier: 받을 tier ("lite"/"full"). None 이면 env ``DARTLAB_SEARCH_TIER`` 또는 "lite".

    Returns:
        dict — indexInfo() 결과 (available/dataAsOf/nDocs/hasMeaning/hasDelta/schemaVersion/compatible).

    Raises:
        없음 (다운로드 실패는 graceful).

    Example:
        >>> # dartlab.search.prefetch()  # 또는 prefetch(tier="full")
    """
    from dartlab.providers.dart.search.fieldIndexRebuild import ensureContentIndex, indexInfo

    ensureContentIndex(tier=tier)
    return indexInfo()


def indexInfo() -> dict:
    """검색 인덱스 메타(dataAsOf/nDocs/의미확장 가용) 조회 — 신선도 확인.

    Args:
        (없음).

    Returns:
        dict — {available, dataAsOf, nDocs, hasMeaning, hasDelta}.

    Raises:
        없음.

    Example:
        >>> # indexInfo()
    """
    from dartlab.providers.dart.search.fieldIndexRebuild import indexInfo as _info

    return _info()


def buildMeaningGraph(**kwargs) -> int:
    """의미검색(scope=auto) 경험그래프 meaning.json build — allFilings type(report_nm)→본문 SPPMI.

    Args:
        **kwargs: fieldIndexRebuild.buildMeaningGraph 로 forward.

    Returns:
        int — 그래프 feature 노드 수.

    Raises:
        없음.

    Example:
        >>> # buildMeaningGraph()
    """
    from dartlab.providers.dart.search.fieldIndexRebuild import buildMeaningGraph as _build

    return _build(**kwargs)


def buildGateRef(**kwargs) -> float:
    """의미검색 gate 기준값 gateRef.json build — 코퍼스 median bm25 top1 (규모 적응).

    Args:
        **kwargs: fieldIndexRebuild.buildGateRef 로 forward.

    Returns:
        float — ref (median bm25 top1).

    Raises:
        없음.

    Example:
        >>> # buildGateRef()
    """
    from dartlab.providers.dart.search.fieldIndexRebuild import buildGateRef as _build

    return _build(**kwargs)


def collectMeta(startDate: str, endDate: str, **kwargs) -> int:
    """DART OpenAPI 공시 목록 수집 (Phase 1) — allFilingsCollector 위임.

    Args:
        startDate: 수집 시작일 (YYYYMMDD 문자열).
        endDate: 수집 종료일 (YYYYMMDD).
        **kwargs: collectMetaRange 로 forward.

    Returns:
        int — 수집된 공시 row 수.

    Example:
        >>> # collectMeta("20240101", "20240131")  # 2024 년 1 월

    Raises:
        없음.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    return collectMetaRange(startDate, endDate, **kwargs)


def fillContent(period: str | None = None, **kwargs):
    """공시 원문 (section_content) 채우기 (Phase 2) — Phase 1 메타 수집 이후 단계.

    Args:
        period: 기간 문자열 (예 "202401") 또는 None (전체).
        **kwargs: 위임 함수로 forward.

    Returns:
        allFilingsCollector 의 반환 형태 의존.

    Example:
        >>> # fillContent("202401")  # 2024 년 1 월
        >>> # fillContent()  # 전체 누락분

    Raises:
        없음.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import (
        fillContent as _fill,
    )
    from dartlab.providers.dart.openapi.allFilingsCollector import (
        fillContentAll as _fillAll,
    )

    if period:
        return _fill(period, **kwargs)
    return _fillAll(**kwargs)


def stats() -> dict:
    """수집 + 인덱스 통합 통계 — collector 통계 + ngramIndex 통계 merge.

    Args:
        없음.

    Returns:
        dict — collector stats + ``"stemIndex"`` (ngramStats 결과).

    Example:
        >>> # s = stats()
        >>> # "stemIndex" in s
        >>> # True

    Raises:
        없음.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import stats as collectorStats
    from dartlab.providers.dart.search.ngramIndex import ngramStats

    result = collectorStats()
    result["stemIndex"] = ngramStats()

    return result


def pushIndex(**kwargs) -> str:
    """stemIndex 를 HuggingFace Hub 에 업로드 — 운영자 publish 단계.

    Args:
        **kwargs: pushStemIndex 로 forward (예 repo_id, token 등).

    Returns:
        str — 업로드 URL 또는 HF commit hash (구현 의존).

    Example:
        >>> # pushIndex(repo_id="user/dartlab-index")

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.ngramIndex import pushStemIndex

    return pushStemIndex(**kwargs)


def pullIndex(**kwargs):
    """HuggingFace Hub 에서 검색 인덱스 다운로드 — stemIndex + contentIndex 통합.

    Args:
        **kwargs: pullStemIndex 로 forward.

    Returns:
        ngramResult — pullStemIndex 의 반환 (다운로드된 파일 수 또는 status).

    Example:
        >>> # pullIndex()

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.fieldIndex import pullContentIndex
    from dartlab.providers.dart.search.ngramIndex import pullStemIndex

    ngramResult = pullStemIndex(**kwargs)
    try:
        nContent = pullContentIndex()
        if nContent > 0:
            _log.info(f"  content 인덱스 {nContent}개 파일 다운로드")
    except (OSError, ConnectionError, ValueError) as e:
        # HF Hub 다운로드 실패 (네트워크/인증/파일 부재) — content 인덱스는 옵션, skip.
        _log.info(f"  content 인덱스 다운로드 건너뜀: {e}")
    return ngramResult


def profile(stockCode: str | None = None):
    """기업별 공시 프로필 조회 — 회사 1 개의 공시 유형 빈도 + 최근 cadence 메타.

    Args:
        stockCode: KR 종목코드 6 자리. None → 전체 회사 프로필 반환.

    Returns:
        pl.DataFrame 또는 dict — derived.loadProfile 의 반환 그대로 (인덱스 빌드 상태 의존).

    Example:
        >>> from dartlab.providers.dart.search.api import profile
        >>> p = profile("005930")  # 삼성전자 공시 프로필
        >>> p is not None
        True
              pipeline 실행 의무.
        OutputSchema:
            - derived.loadProfile 의 반환 형태 의존. 일반적으로 pl.DataFrame 또는 dict.
        Prerequisites:
            - derived/profile parquet 가 빌드되어 있어야.
        Freshness:
            - derived pipeline 실행 시점. 본 함수 자체는 무상태.
        Dataflow:
            - allFilings parquet → derived (profile/dna/pulse 빌드) → 본 함수 → caller.
        TargetMarkets:
            - KR (DART) 한정.

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.derived import loadProfile

    return loadProfile(stockCode)


def pulse(limit: int = 10) -> pl.DataFrame:
    """최근 월의 공시 유형별 건수 + 전월 대비 변화 — 시장 활동 펄스 (heartbeat).

    Args:
        limit: 반환 row 수 (top N 빈도 유형). 기본 10.

    Returns:
        pl.DataFrame — ``["typeCode", "typeName", "currentCount", "prevCount", "diff", ...]``
        columns. 정렬 = currentCount 내림차순.

    Example:
        >>> from dartlab.providers.dart.search.api import pulse
        >>> df = pulse(limit=5)
        >>> df.height >= 0
        True

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.derived import pulse as _pulse

    return _pulse(limit=limit)


def timeline(typeFilter: str | None = None, periodFilter: str | None = None) -> pl.DataFrame:
    """공시 유형 × 월 빈도 시계열 조회 — 시장 활동 시계열 (``pulse`` 의 시계열 확장).

    Args:
        typeFilter: 유형 코드 (또는 None = 전체).
        periodFilter: 기간 문자열 (예 "2024" / "2024-01") 또는 None.

    Returns:
        pl.DataFrame — ``["period", "typeCode", "count", ...]``. period 오름차순.

    Example:
        >>> from dartlab.providers.dart.search.api import timeline
        >>> df = timeline(typeFilter="A")  # 정기공시 시계열
        >>> df.height >= 0
        True

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.derived import loadTimeline

    return loadTimeline(typeFilter=typeFilter, periodFilter=periodFilter)


def dna(stockCode: str) -> dict:
    """회사 1 개의 Disclosure DNA — 114 차원 공시 유형 빈도 벡터.

    Args:
        stockCode: KR 종목코드 6 자리 (필수).

    Returns:
        dict — ``{"typeCode": count}`` 형태 또는 추가 메타. derived.dna 구현 의존.

    Example:
        >>> from dartlab.providers.dart.search.api import dna
        >>> v = dna("005930")
        >>> v is not None
        True

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.derived import dna as _dna

    return _dna(stockCode)


def similarCompanies(stockCode: str, limit: int = 5) -> pl.DataFrame:
    """공시 패턴이 유사한 기업 탐색 — DNA 벡터 코사인 유사도 top N.

    Args:
        stockCode: 기준 회사 KR 종목코드 6 자리 (필수).
        limit: 반환 회사 수. 기본 5.

    Returns:
        pl.DataFrame — ``["stockCode", "corpName", "similarity", ...]``. 유사도 내림차순.
        DNA parquet 미빌드 → 빈 DataFrame.

    Example:
        >>> from dartlab.providers.dart.search.api import similarCompanies
        >>> df = similarCompanies("005930", limit=5)
        >>> df.height <= 5
        True
          (의미 검증 caller 책임).

    Raises:
        없음.
    """
    from dartlab.providers.dart.search.derived import similarCompanies as _similar

    return _similar(stockCode, limit=limit)
