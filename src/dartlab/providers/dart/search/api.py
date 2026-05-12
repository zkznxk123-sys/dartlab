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


SEARCH_SCOPES: tuple[str, ...] = ("auto", "title", "content", "both")


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

    Capabilities:
        - 4 종 scope: ``"auto"`` (기본, title strict → content 보강) / ``"title"`` (ngram 만) /
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

    Guide:
        - "최근 공시 중 배당 키워드" → ``search("배당", limit=10)``.
        - "삼성전자 공시만" → ``search("...", corp="005930")``.
        - "내용 본문 검색" → ``scope="content"`` (예 "ESG 정책").
        - "제목 검색 (빠름)" → ``scope="title"``.
        - "title + content 같이" → ``scope="both"`` + ``scope`` 컬럼으로 source 구분.
        - 날짜 범위 → ``start="20240101", end="20241231"``.

    SeeAlso:
        - ``_searchTitle`` / ``_searchContent`` / ``_searchAuto`` (모듈 private) — scope 별 핸들러.
        - ``_resolveCorp`` (모듈 private) — corp 파라미터 → corpCode/stockCode 변환.
        - ``dartlab.providers.dart.search.ngramIndex.searchNgram`` — title scope 본체.
        - ``dartlab.providers.dart.search.fieldIndex.searchContent`` — content scope 본체.
        - ``SEARCH_SCOPES`` (모듈 상수) — 4 scope 허용값 SSOT.

    Requires:
        - polars — DataFrame.
        - dartlab.providers.dart.search.ngramIndex — title scope ngram 인덱스.
        - dartlab.providers.dart.search.fieldIndex — content scope BM25 인덱스.
        - (옵션) dartlab.core.listingResolver — corp 회사명 lookup.

    AIContext:
        Ask Workbench 의 "공시" / "최근 보고서" / "X 관련 공시" 질문 entry. AI 가 사용자 자연어
        를 query 로 그대로 전달, scope=auto 가 자동 분기. limit 조정으로 top 결과만 사용자에게
        제시. corp 가 US 회사명 (예 "Apple") 일 때 본 함수가 안내 info 반환 → caller 는 EDGAR
        검색 path 로 분기.

    LLM Specifications:
        AntiPatterns:
            - corp 회사명 lookup 실패 → 전체 검색 fallback (silent). caller 는 corp_name 컬럼
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

    if scope not in ("auto", "title", "content", "both"):
        raise ValueError(f"scope는 'auto', 'title', 'content', 'both' 중 하나. 받은 값: {scope!r}")

    corpCode, stockCode = _resolveCorp(corp)

    if scope == "title":
        result = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
    elif scope == "content":
        result = _searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit)
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


def _searchAuto(query, *, corpCode, stockCode, limit):
    """auto 모드 — 쿼리 유형 자동 판별 후 맞는 엔진 선택."""
    titleHits = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, limit=limit * 2)
    contentHits = _searchContent(query, corpCode=corpCode, stockCode=stockCode, limit=limit * 2)

    tValid = titleHits is not None and titleHits.height > 0 and "info" not in titleHits.columns
    cValid = contentHits is not None and contentHits.height > 0 and "info" not in contentHits.columns

    if not tValid and not cValid:
        return titleHits if titleHits is not None else contentHits
    if not cValid:
        return titleHits.head(limit)
    if not tValid:
        return contentHits.head(limit)

    queryNorm = query.strip()
    titleStrict = titleHits.filter(pl.col("report_nm").str.contains(queryNorm, literal=True))
    titleStrictCount = titleStrict.height

    commonCols = [c for c in titleHits.columns if c in contentHits.columns]

    if titleStrictCount >= limit:
        return titleStrict.select(commonCols).with_columns(pl.lit("title").alias("scope")).head(limit)

    tagged_title = titleStrict.select(commonCols).with_columns(pl.lit("title").alias("scope"))
    tagged_content = contentHits.select(commonCols).with_columns(pl.lit("content").alias("scope"))
    if "rcept_no" in commonCols and titleStrictCount > 0:
        usedRcepts = set(titleStrict["rcept_no"].to_list())
        tagged_content = tagged_content.filter(~pl.col("rcept_no").is_in(list(usedRcepts)))

    needed = max(limit - titleStrictCount, 0)
    result = pl.concat([tagged_title, tagged_content.head(needed)])
    return result.head(limit)


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

    Capabilities:
        - ``ngramIndex.buildNgramIndex`` wrapper — parquetPaths 지정 시 해당 파일들만, 미지정
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

    Guide:
        - "월 1 회 인덱스 풀 빌드" → ``rebuildIndex()`` (본 함수 includeDocs=True 호출).
        - "특정 parquet 만 인덱싱" → ``buildIndex(parquetPaths=[...])``.

    SeeAlso:
        - ``rebuildIndex`` — 본 함수의 includeDocs=True 단축.
        - ``dartlab.providers.dart.search.ngramIndex.buildNgramIndex`` — 본 함수 본체.
        - ``rebuildContent`` — content (BM25) 인덱스의 동등 함수.

    Requires:
        - dartlab.providers.dart.search.ngramIndex — buildNgramIndex SSOT.
        - allFilings parquet 또는 지정 parquet 가 존재.

    AIContext:
        admin 영역 — AI 가 직접 호출 X. 운영자가 정기적으로 인덱스 갱신할 때 사용. AI 가 "왜
        검색 결과 0" 질문 받으면 ``stats()`` 로 인덱스 빌드 상태 검사 권장.

    LLM Specifications:
        AntiPatterns:
            - 인덱스 빌드 중 (long-running) 다른 검색 호출 → 파편 응답 가능. 운영자가 lock 보장.
            - parquetPaths 가 존재하지 않으면 silent 0 또는 FileNotFoundError.
        OutputSchema:
            - 1 int — 인덱싱 row 수.
        Prerequisites:
            - allFilings parquet (또는 명시 parquetPaths) 가 존재.
        Freshness:
            - 본 함수 호출 시점에 인덱스 갱신.
        Dataflow:
            - allFilings parquet → 본 함수 → ngram 인덱스 → ``search`` 함수 사용.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.ngramIndex import buildNgramIndex

    return buildNgramIndex(parquetPaths, includeDocs=includeDocs, **kwargs)


def rebuildIndex(**kwargs) -> int:
    """전체 인덱스 리빌드 — ``buildIndex(includeDocs=True)`` 단축.

    Capabilities:
        - ``buildIndex`` 의 includeDocs=True 호출 wrapper.
        - allFilings + sections 합산 인덱싱.

    Args:
        **kwargs: buildIndex 로 forward.

    Returns:
        int — 인덱싱 row 수.

    Example:
        >>> # rebuildIndex()

    Guide:
        - 월 1 회 정기 full 빌드 → 본 함수.
        - delta 증분 빌드 → ``rebuildContentDelta``.

    SeeAlso:
        - ``buildIndex`` — 본 함수의 본체.
        - ``rebuildContent`` — content (BM25) 의 동등 함수.

    Requires:
        - dartlab.providers.dart.search.ngramIndex — buildNgramIndex 경유.

    AIContext:
        admin 함수, AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - buildIndex 와 동일.
        OutputSchema:
            - 1 int.
        Prerequisites:
            - buildIndex 와 동일.
        Freshness:
            - 본 함수 시점 인덱스 갱신.
        Dataflow:
            - allFilings + sections → 본 함수 → 인덱스.
        TargetMarkets:
            - KR (DART) 한정.
    """
    return buildIndex(includeDocs=True, **kwargs)


def rebuildContent(**kwargs) -> int:
    """content (BM25) 인덱스의 main 세그먼트 풀빌드 — 월 1 회 운영.

    Capabilities:
        - ``fieldIndex.rebuildMain`` wrapper — main 세그먼트 전체 재빌드.
        - delta 세그먼트는 별도 (``rebuildContentDelta``).
        - 두 세그먼트 분리 = main (월간 풀빌드) + delta (일간 증분).

    Args:
        **kwargs: fieldIndex.rebuildMain 로 forward.

    Returns:
        int — 빌드된 row 수.

    Example:
        >>> # rebuildContent()

    Guide:
        - 매월 1 일 cron → 본 함수.
        - 일간 증분 → ``rebuildContentDelta``.

    SeeAlso:
        - ``rebuildContentDelta`` — delta 세그먼트의 동등 함수.
        - ``dartlab.providers.dart.search.fieldIndex.rebuildMain`` — 본 함수 본체.
        - ``rebuildIndex`` — ngram (title) 의 동등 함수.

    Requires:
        - dartlab.providers.dart.search.fieldIndex — rebuildMain SSOT.

    AIContext:
        admin 함수.

    LLM Specifications:
        AntiPatterns:
            - main 빌드 중 search content scope 호출 → 불완전 응답.
        OutputSchema:
            - 1 int.
        Prerequisites:
            - allFilings + section_content parquet 존재.
        Freshness:
            - 본 함수 호출 시점.
        Dataflow:
            - parquet → 본 함수 → main 세그먼트.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildMain

    return rebuildMain(**kwargs)


def rebuildContentDelta(**kwargs) -> int:
    """content (BM25) 인덱스의 delta 세그먼트 일간 증분 빌드.

    Capabilities:
        - ``fieldIndex.rebuildDelta`` wrapper — 마지막 main 빌드 이후 신규 row 만 증분.
        - 매일 cron 으로 호출 (빠름, 5~10 분).

    Args:
        **kwargs: fieldIndex.rebuildDelta 로 forward.

    Returns:
        int — 추가 인덱싱 row 수.

    Example:
        >>> # rebuildContentDelta()

    Guide:
        - 매일 cron → 본 함수.
        - 월간 main 빌드 → ``rebuildContent``.

    SeeAlso:
        - ``rebuildContent`` — main 세그먼트.
        - ``dartlab.providers.dart.search.fieldIndex.rebuildDelta`` — 본 함수 본체.

    Requires:
        - dartlab.providers.dart.search.fieldIndex — rebuildDelta SSOT.

    AIContext:
        admin 함수.

    LLM Specifications:
        AntiPatterns:
            - main 빌드 안 됐는데 delta 만 빌드 → search content 결과 부정확.
        OutputSchema:
            - 1 int.
        Prerequisites:
            - main 세그먼트 빌드 완료. 신규 parquet row 존재.
        Freshness:
            - 본 함수 호출 시점.
        Dataflow:
            - parquet (신규 row) → 본 함수 → delta 세그먼트.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildDelta

    return rebuildDelta(**kwargs)


def collectMeta(startDate: str, endDate: str, **kwargs) -> int:
    """DART OpenAPI 공시 목록 수집 (Phase 1) — allFilingsCollector 위임.

    Capabilities:
        - ``openapi.allFilingsCollector.collectMetaRange`` wrapper — 기간 (YYYYMMDD) 의 공시 메타 수집.
        - 본문 (section_content) 은 Phase 2 (``fillContent``) 에서 별도.
        - 운영자 admin 함수 — DART OpenAPI rate limit 의무.

    Args:
        startDate: 수집 시작일 (YYYYMMDD 문자열).
        endDate: 수집 종료일 (YYYYMMDD).
        **kwargs: collectMetaRange 로 forward.

    Returns:
        int — 수집된 공시 row 수.

    Example:
        >>> # collectMeta("20240101", "20240131")  # 2024 년 1 월

    Guide:
        - 매월 1 일 cron → 전월 메타 수집.
        - 본문 같이 → ``fillContent`` 별도 호출.

    SeeAlso:
        - ``fillContent`` — Phase 2 본문 수집.
        - ``dartlab.providers.dart.openapi.allFilingsCollector.collectMetaRange`` — 본 함수 본체.

    Requires:
        - dartlab.providers.dart.openapi.allFilingsCollector — collectMetaRange SSOT.
        - DART OpenAPI key 환경변수 (DART_API_KEY).

    AIContext:
        admin 함수.

    LLM Specifications:
        AntiPatterns:
            - DART_API_KEY 미설정 → ValueError.
            - startDate > endDate → 0.
            - rate limit 초과 → 일시 차단 (운영자 retry).
        OutputSchema:
            - 1 int.
        Prerequisites:
            - DART OpenAPI key.
        Freshness:
            - 본 함수 호출 시점 데이터.
        Dataflow:
            - DART OpenAPI → 본 함수 → allFilings parquet.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    return collectMetaRange(startDate, endDate, **kwargs)


def fillContent(period: str | None = None, **kwargs):
    """공시 원문 (section_content) 채우기 (Phase 2) — Phase 1 메타 수집 이후 단계.

    Capabilities:
        - period 지정 시 ``fillContent(period)`` (특정 기간), 미지정 시 ``fillContentAll()``.
        - 메타 row 중 section_content 누락된 것만 채움.

    Args:
        period: 기간 문자열 (예 "202401") 또는 None (전체).
        **kwargs: 위임 함수로 forward.

    Returns:
        allFilingsCollector 의 반환 형태 의존.

    Example:
        >>> # fillContent("202401")  # 2024 년 1 월
        >>> # fillContent()  # 전체 누락분

    Guide:
        - 매월 1 일 cron, 메타 수집 직후 → 본 함수 ``period=전월``.
        - 본문 결락 보수 → ``fillContent()`` (전체).

    SeeAlso:
        - ``collectMeta`` — Phase 1 메타 수집.
        - ``dartlab.providers.dart.openapi.allFilingsCollector.fillContent`` / ``fillContentAll`` — 본 함수 본체.

    Requires:
        - dartlab.providers.dart.openapi.allFilingsCollector — fillContent / fillContentAll.
        - DART OpenAPI key.

    AIContext:
        admin 함수.

    LLM Specifications:
        AntiPatterns:
            - Phase 1 (메타) 미실행 → 채울 row 없음.
            - rate limit 초과 → 일시 차단.
        OutputSchema:
            - 위임 반환 형태 의존.
        Prerequisites:
            - Phase 1 완료 + DART OpenAPI key.
        Freshness:
            - 본 함수 호출 시점.
        Dataflow:
            - DART OpenAPI 본문 endpoint → 본 함수 → allFilings parquet (section_content 컬럼).
        TargetMarkets:
            - KR (DART) 한정.
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

    Capabilities:
        - ``allFilingsCollector.stats()`` 결과 dict 에 ``"stemIndex"`` 키로 ngramStats 추가.
        - 운영자가 "지금 인덱스/parquet 상태" 한 번에 확인.

    Args:
        없음.

    Returns:
        dict — collector stats + ``"stemIndex"`` (ngramStats 결과).

    Example:
        >>> # s = stats()
        >>> # "stemIndex" in s
        >>> # True

    Guide:
        - "검색 결과 비어 있다" 디버깅 → 본 함수로 인덱스 row 수 확인.
        - 운영 대시보드 → 본 함수 결과 시각화.

    SeeAlso:
        - ``buildIndex`` / ``rebuildContent`` — 인덱스 생성.
        - ``dartlab.providers.dart.openapi.allFilingsCollector.stats`` — collector 통계.
        - ``dartlab.providers.dart.search.ngramIndex.ngramStats`` — ngram 통계.

    Requires:
        - dartlab.providers.dart.openapi.allFilingsCollector — stats.
        - dartlab.providers.dart.search.ngramIndex — ngramStats.

    AIContext:
        AI 가 "검색 결과 0" 질문 받으면 본 함수 호출 → 인덱스 빌드 여부 확인 후 운영자 안내.

    LLM Specifications:
        AntiPatterns:
            - 인덱스/parquet 결락 → 일부 키 누락. caller 는 dict.get 사용.
        OutputSchema:
            - dict — collector 키 + ``"stemIndex"``.
        Prerequisites:
            - 본 함수 자체 사전조건 없음. 결과는 인덱스/parquet 상태 의존.
        Freshness:
            - 본 함수 호출 시점.
        Dataflow:
            - collector.stats + ngramStats → merge → 본 함수.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import stats as collectorStats
    from dartlab.providers.dart.search.ngramIndex import ngramStats

    result = collectorStats()
    result["stemIndex"] = ngramStats()

    return result


def pushIndex(**kwargs) -> str:
    """stemIndex 를 HuggingFace Hub 에 업로드 — 운영자 publish 단계.

    Capabilities:
        - ``ngramIndex.pushStemIndex`` wrapper — HF Hub repo 로 인덱스 업로드.
        - 일반 사용자는 ``pullIndex`` 로 다운로드만, push 는 운영자 한정.

    Args:
        **kwargs: pushStemIndex 로 forward (예 repo_id, token 등).

    Returns:
        str — 업로드 URL 또는 HF commit hash (구현 의존).

    Example:
        >>> # pushIndex(repo_id="user/dartlab-index")

    Guide:
        - 인덱스 정기 갱신 후 → 본 함수로 publish → 사용자 ``pullIndex`` 동기화.

    SeeAlso:
        - ``pullIndex`` — 본 함수의 역방향 (download).
        - ``dartlab.providers.dart.search.ngramIndex.pushStemIndex`` — 본 함수 본체.

    Requires:
        - dartlab.providers.dart.search.ngramIndex — pushStemIndex.
        - HF_TOKEN 환경변수 (또는 kwargs token).

    AIContext:
        admin 함수.

    LLM Specifications:
        AntiPatterns:
            - HF_TOKEN 미설정 → 401.
            - repo_id 누락 → ValueError.
        OutputSchema:
            - 1 str.
        Prerequisites:
            - HF account + write 권한.
        Freshness:
            - 본 함수 호출 시점.
        Dataflow:
            - local stemIndex → 본 함수 → HF Hub.
        TargetMarkets:
            - KR (DART) 한정 (인덱스 자체가 DART 데이터).
    """
    from dartlab.providers.dart.search.ngramIndex import pushStemIndex

    return pushStemIndex(**kwargs)


def pullIndex(**kwargs):
    """HuggingFace Hub 에서 검색 인덱스 다운로드 — stemIndex + contentIndex 통합.

    Capabilities:
        - ``ngramIndex.pullStemIndex`` 1 차 + ``fieldIndex.pullContentIndex`` 2 차.
        - contentIndex 다운로드 실패는 silent log + skip (stem 만으로도 title scope 동작).
        - 새 환경에서 ``buildIndex`` 안 돌리고 빠르게 검색 시작 가능.

    Args:
        **kwargs: pullStemIndex 로 forward.

    Returns:
        ngramResult — pullStemIndex 의 반환 (다운로드된 파일 수 또는 status).

    Example:
        >>> # pullIndex()

    Guide:
        - 새 PC 세팅 직후 → 본 함수.
        - 인덱스 빌드 (운영자 환경) → ``buildIndex`` + ``rebuildContent`` 직접.

    SeeAlso:
        - ``pushIndex`` — 본 함수의 역방향 (upload).
        - ``dartlab.providers.dart.search.ngramIndex.pullStemIndex`` — stem 다운로드.
        - ``dartlab.providers.dart.search.fieldIndex.pullContentIndex`` — content 다운로드.

    Requires:
        - dartlab.providers.dart.search.ngramIndex / fieldIndex.
        - HF cache 가능 환경 (디스크 공간).

    AIContext:
        AI 가 "검색 결과 0" 인데 인덱스 미빌드 상태면 본 함수 안내. 새 사용자 setup 경로.

    LLM Specifications:
        AntiPatterns:
            - HF Hub 접근 불가 (오프라인) → 다운로드 실패.
            - 디스크 공간 부족 → IOError.
        OutputSchema:
            - ngramResult — pullStemIndex 반환 의존.
        Prerequisites:
            - 네트워크 접근.
        Freshness:
            - HF Hub 의 최신 published 인덱스 기준.
        Dataflow:
            - HF Hub → 본 함수 → local stemIndex + contentIndex.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.fieldIndex import pullContentIndex
    from dartlab.providers.dart.search.ngramIndex import pullStemIndex

    ngramResult = pullStemIndex(**kwargs)
    try:
        nContent = pullContentIndex()
        if nContent > 0:
            _log.info(f"  content 인덱스 {nContent}개 파일 다운로드")
    except Exception as e:
        _log.info(f"  content 인덱스 다운로드 건너뜀: {e}")
    return ngramResult


def profile(stockCode: str | None = None):
    """기업별 공시 프로필 조회 — 회사 1 개의 공시 유형 빈도 + 최근 cadence 메타.

    Capabilities:
        - ``loadProfile`` (derived) wrapper — 사전 빌드된 profile parquet 에서 stockCode 행 조회.
        - stockCode=None → 전체 프로필 (모든 회사) 반환.
        - 공시 유형별 누적 건수 + 최근 활동 메트릭 동행.

    Args:
        stockCode: KR 종목코드 6 자리. None → 전체 회사 프로필 반환.

    Returns:
        pl.DataFrame 또는 dict — derived.loadProfile 의 반환 그대로 (인덱스 빌드 상태 의존).

    Example:
        >>> from dartlab.providers.dart.search.api import profile
        >>> p = profile("005930")  # 삼성전자 공시 프로필
        >>> p is not None
        True

    Guide:
        - "삼성전자가 어떤 공시 유형을 자주 내냐" → ``profile("005930")``.
        - "전체 회사 프로필 lookup table" → ``profile()`` (None).
        - 유사 회사 탐색 → ``similarCompanies(stockCode)`` 사용 (본 함수 결과의 cosine).

    SeeAlso:
        - ``dna`` — 회사 1 개의 114 차원 disclosure DNA 벡터.
        - ``similarCompanies`` — 본 함수 결과 기반 유사도 검색.
        - ``pulse`` / ``timeline`` — 시계열 메트릭 (회사 무관 또는 type 별).
        - ``dartlab.providers.dart.search.derived.loadProfile`` — 본 함수 본체.

    Requires:
        - polars — DataFrame.
        - dartlab.providers.dart.search.derived — ``loadProfile`` SSOT.
        - profile parquet 가 빌드되어 있어야 (사전 derived pipeline).

    AIContext:
        Workbench "이 회사 어떤 공시 자주 내냐" / "회사 캐릭터" 질문 처리 시 entry. AI 가 빈도
        벡터를 자연어로 변환 ("연 N 회 정기보고서 + 분기마다 임시공시"). dna/similarCompanies
        와 같이 회사 캐릭터 분석 토픽 군에 속함.

    LLM Specifications:
        AntiPatterns:
            - stockCode 형식이 6 자리 숫자 외 (예 영문 ticker) → loadProfile 결과 빈 row.
            - profile parquet 미빌드 → FileNotFoundError 또는 빈 결과. 운영자가 derived
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
    """
    from dartlab.providers.dart.search.derived import loadProfile

    return loadProfile(stockCode)


def pulse(limit: int = 10) -> pl.DataFrame:
    """최근 월의 공시 유형별 건수 + 전월 대비 변화 — 시장 활동 펄스 (heartbeat).

    Capabilities:
        - ``derived.pulse`` wrapper — 사전 집계된 monthly aggregation 에서 최근 월 + 전월 추출.
        - 유형별 (114 종) 건수 + diff 컬럼 반환.
        - limit 으로 top N 유형만 (기본 10).

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

    Guide:
        - "지난달 가장 많이 나온 공시 유형" → ``pulse(limit=10)``.
        - "유형별 시계열 (12 개월)" → ``timeline(typeFilter="A")``.
        - 회사 1 개 펄스 → ``profile(stockCode)`` 또는 ``dna(stockCode)``.

    SeeAlso:
        - ``timeline`` — 유형 × 월 빈도 시계열 (본 함수의 시계열 버전).
        - ``profile`` — 회사 1 개의 누적 프로필 (시장 전체 X).
        - ``dartlab.providers.dart.search.derived.pulse`` — 본 함수 본체.

    Requires:
        - polars — DataFrame.
        - dartlab.providers.dart.search.derived — ``pulse`` SSOT.
        - monthly aggregation parquet 가 빌드되어 있어야.

    AIContext:
        Workbench "최근 시장 분위기" / "이번 달 무슨 공시 많이 나왔냐" 질문 entry. 결과 row
        에 diff 컬럼이 있어 AI 가 "전월 대비 X 배 증가/감소" 류 답변 가능. 시장 거시 토픽 군.

    LLM Specifications:
        AntiPatterns:
            - monthly aggregation 미빌드 → 빈 결과 또는 FileNotFoundError.
            - limit 매우 큼 (≥ 114) → 모든 유형 반환, 일부는 currentCount=0.
        OutputSchema:
            - rows: ≤ limit.
            - columns: typeCode/typeName/currentCount/prevCount/diff.
        Prerequisites:
            - derived monthly aggregation 빌드.
        Freshness:
            - derived 갱신 시점. 본 함수 무상태.
        Dataflow:
            - allFilings parquet → derived (monthly aggregate) → 본 함수 → AI 답변.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.derived import pulse as _pulse

    return _pulse(limit=limit)


def timeline(typeFilter: str | None = None, periodFilter: str | None = None) -> pl.DataFrame:
    """공시 유형 × 월 빈도 시계열 조회 — 시장 활동 시계열 (``pulse`` 의 시계열 확장).

    Capabilities:
        - ``derived.loadTimeline`` wrapper — 사전 집계된 monthly time series 에서 필터.
        - typeFilter (예 "A" 정기공시 / "B" 주요사항보고) 로 특정 유형만.
        - periodFilter (예 "2024") 로 특정 연도/월만.

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

    Guide:
        - "정기공시 월별 추세" → ``timeline(typeFilter="A")``.
        - "2024 년 전체" → ``timeline(periodFilter="2024")``.
        - 최근 월 1 개만 → ``pulse``.

    SeeAlso:
        - ``pulse`` — 최근 월 시장 펄스 (시계열 X).
        - ``dartlab.providers.dart.search.derived.loadTimeline`` — 본 함수 본체.

    Requires:
        - polars — DataFrame.
        - dartlab.providers.dart.search.derived — loadTimeline.

    AIContext:
        Workbench "최근 N 년 X 유형 추세" 질문 entry. AI 가 결과를 line chart 또는 자연어 trend
        설명으로 변환 ("2024 년 1 분기 임시공시 증가").

    LLM Specifications:
        AntiPatterns:
            - timeFilter 가 정의된 유형 코드 외 → 빈 결과 (silent).
            - periodFilter 형식 다양 (예 "2024" vs "2024-01") → derived 구현 의존.
        OutputSchema:
            - pl.DataFrame — period/typeCode/count.
        Prerequisites:
            - derived timeline parquet 빌드.
        Freshness:
            - derived 갱신 시점.
        Dataflow:
            - allFilings → derived monthly time series → 본 함수 → AI 답변.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.derived import loadTimeline

    return loadTimeline(typeFilter=typeFilter, periodFilter=periodFilter)


def dna(stockCode: str) -> dict:
    """회사 1 개의 Disclosure DNA — 114 차원 공시 유형 빈도 벡터.

    Capabilities:
        - ``derived.dna`` wrapper — stockCode 의 114 차원 유형 빈도 벡터 반환.
        - 회사 캐릭터 정량화 — "정기공시 중심형" vs "임시공시 활발형" 등 패턴 분석 base.
        - similarCompanies 의 cosine 유사도 계산 input.

    Args:
        stockCode: KR 종목코드 6 자리 (필수).

    Returns:
        dict — ``{"typeCode": count}`` 형태 또는 추가 메타. derived.dna 구현 의존.

    Example:
        >>> from dartlab.providers.dart.search.api import dna
        >>> v = dna("005930")
        >>> v is not None
        True

    Guide:
        - "삼성전자가 어떤 공시 패턴" → ``dna("005930")``.
        - "유사 패턴 회사" → ``similarCompanies("005930")`` (본 함수 결과 cosine).
        - "회사 캐릭터 시각화" → 본 함수 + radar chart.

    SeeAlso:
        - ``similarCompanies`` — 본 함수 결과 기반 유사도 검색.
        - ``profile`` — 같은 도메인의 다른 view (frequency + cadence).
        - ``dartlab.providers.dart.search.derived.dna`` — 본 함수 본체.

    Requires:
        - polars — derived 의 내부 의존.
        - dartlab.providers.dart.search.derived — ``dna`` SSOT.
        - DNA parquet 가 빌드되어 있어야.

    AIContext:
        Workbench "이 회사 공시 패턴 어떻게 되냐" 질문 entry. 결과 벡터를 AI 가 자연어로 변환
        — "분기/반기/사업보고서 정기 + 인수합병 (M&A) 류 임시공시 활발". 정량 벡터라
        similarCompanies / profile / pulse 와 dataflow 연결.

    LLM Specifications:
        AntiPatterns:
            - stockCode 형식 오류 → 빈 dict 또는 KeyError. 6 자리 숫자 검증 caller 책임.
            - DNA parquet 미빌드 → FileNotFoundError. 운영자 derived pipeline 의무.
        OutputSchema:
            - dict — derived.dna 구현 의존. 일반적으로 typeCode → count.
        Prerequisites:
            - derived DNA parquet 빌드.
        Freshness:
            - derived 갱신 시점.
        Dataflow:
            - allFilings parquet → derived DNA → 본 함수 → similarCompanies / AI 답변.
        TargetMarkets:
            - KR (DART) 한정.
    """
    from dartlab.providers.dart.search.derived import dna as _dna

    return _dna(stockCode)


def similarCompanies(stockCode: str, limit: int = 5) -> pl.DataFrame:
    """공시 패턴이 유사한 기업 탐색 — DNA 벡터 코사인 유사도 top N.

    Capabilities:
        - ``derived.similarCompanies`` wrapper — 입력 stockCode 의 DNA 와 모든 회사 DNA cosine 계산.
        - 자기 자신 제외 + 유사도 내림차순 top N 반환.
        - 결과 row = 회사 1 개 + similarity score + 공시 빈도 메타.

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

    Guide:
        - "삼성전자와 공시 패턴 비슷한 회사" → ``similarCompanies("005930")``.
        - "특정 회사 군집 분석" → top N 반복 호출 → graph 구축.
        - 결과 회사가 같은 산업 (전자) 일 수도 있고, 같은 공시 cadence 회사일 수도 있음
          (의미 검증 caller 책임).

    SeeAlso:
        - ``dna`` — 본 함수의 cosine 계산 input.
        - ``profile`` — 본 함수 결과의 각 회사 상세 프로필.
        - ``dartlab.providers.dart.search.derived.similarCompanies`` — 본 함수 본체.

    Requires:
        - polars — DataFrame.
        - dartlab.providers.dart.search.derived — ``similarCompanies`` SSOT.
        - DNA parquet + similarity matrix (또는 in-memory cosine).

    AIContext:
        Workbench "삼성전자 비슷한 공시 패턴 회사" / "similar to X" 질문 entry. 결과는 산업
        분류 (KSIC) 와 일치하지 않을 수 있음 — 공시 패턴이 유사하면 다른 산업도 등장. AI 가
        결과를 "공시 빈도/유형이 비슷한" 으로 명시해 의미 혼동 방지.

    LLM Specifications:
        AntiPatterns:
            - 신규 상장 회사 (공시 적음) → DNA 벡터가 sparse → 유사도 부정확.
            - limit ≥ 100 → 본 함수가 모든 회사 cosine 계산 → 느림.
            - DNA parquet 미빌드 → 빈 결과.
        OutputSchema:
            - rows: ≤ limit.
            - columns: stockCode/corpName/similarity (Float, 0~1) 등.
            - 정렬: similarity 내림차순.
        Prerequisites:
            - derived DNA + similarity 빌드.
        Freshness:
            - derived 갱신 시점.
        Dataflow:
            - allFilings → derived DNA → similarity matrix → 본 함수 → AI 답변.
        TargetMarkets:
            - KR (DART) 한정. EDGAR similarCompanies 는 미지원 (별도 SEC 코퍼스 필요).
    """
    from dartlab.providers.dart.search.derived import similarCompanies as _similar

    return _similar(stockCode, limit=limit)
