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
    """Ngram 인덱스 빌드. allFilings + (선택) docs 통합.

    Args:
        parquetPaths: 인자.
        includeDocs: 인자.

    Raises:
        없음.

    Example:
        >>> buildIndex(...)

    Returns:
        <TODO: return desc> (int)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.search.ngramIndex import buildNgramIndex

    return buildNgramIndex(parquetPaths, includeDocs=includeDocs, **kwargs)


def rebuildIndex(**kwargs) -> int:
    """전체 인덱스 리빌드 — allFilings + docs 통합.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> rebuildIndex(...)

    Returns:
        <TODO: return desc> (int)
    """
    return buildIndex(includeDocs=True, **kwargs)


def rebuildContent(**kwargs) -> int:
    """content 인덱스 main 세그먼트 풀리빌드 (월 1회).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> rebuildContent(...)

    Returns:
        <TODO: return desc> (int)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildMain

    return rebuildMain(**kwargs)


def rebuildContentDelta(**kwargs) -> int:
    """content 인덱스 delta 세그먼트 빌드 (일 단위 증분).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> rebuildContentDelta(...)

    Returns:
        <TODO: return desc> (int)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildDelta

    return rebuildDelta(**kwargs)


def collectMeta(startDate: str, endDate: str, **kwargs) -> int:
    """공시 목록 수집 (Phase 1).

    Args:
        startDate: 인자.
        endDate: 인자.

    Raises:
        없음.

    Example:
        >>> collectMeta(...)

    Returns:
        <TODO: return desc> (int)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    return collectMetaRange(startDate, endDate, **kwargs)


def fillContent(period: str | None = None, **kwargs):
    """공시 원문 채우기 (Phase 2).

    Args:
        period: 인자.

    Raises:
        없음.

    Example:
        >>> fillContent(...)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
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
    """수집 + 인덱스 통합 통계.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> stats(...)

    Returns:
        <TODO: return desc> (dict)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.openapi.allFilingsCollector import stats as collectorStats
    from dartlab.providers.dart.search.ngramIndex import ngramStats

    result = collectorStats()
    result["stemIndex"] = ngramStats()

    return result


def pushIndex(**kwargs) -> str:
    """stemIndex를 HuggingFace에 업로드.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> pushIndex(...)

    Returns:
        <TODO: return desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.providers.dart.search.ngramIndex import pushStemIndex

    return pushStemIndex(**kwargs)


def pullIndex(**kwargs):
    """HuggingFace에서 검색 인덱스 다운로드 (stemIndex + contentIndex).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> pullIndex(...)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
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
    """유형×월 빈도 시계열 조회.

    Args:
        typeFilter: 인자.
        periodFilter: 인자.

    Raises:
        없음.

    Example:
        >>> timeline(...)

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
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
