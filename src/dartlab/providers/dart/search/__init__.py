"""공시 검색 엔진. *(alpha)*

scope 분리 검색:
- title: report_nm + section_title ngram (제목형 쿼리)
- content: section_content word BM25 (본문형 쿼리)
- auto (기본): 자동 판별

사용법::

    import dartlab

    dartlab.search("유상증자")                                # 제목 자동 매칭
    dartlab.search("반도체 HBM 투자")                          # 본문 자동 매칭
    dartlab.search("대표이사 변경", corp="005930")              # 종목 필터
    dartlab.search("환율 리스크", scope="content")              # 본문 검색 강제
"""

from __future__ import annotations

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


# 공개 scope 상수 — AI tool schema enum + 사용자 문서 단일 출처
SEARCH_SCOPES: tuple[str, ...] = ("auto", "title", "content", "both")


def search(
    query: str,
    *,
    corp: str | None = None,
    start: str | None = None,
    end: str | None = None,
    topK: int = 10,
    scope: str = "auto",
) -> pl.DataFrame:
    """공시 검색.

    scope 파라미터:
    - ``"auto"`` (기본): title 먼저 검색, topK 미달이면 content 결과로 보강.
      제목형/본문형 쿼리 모두 커버. 중복은 rcept_no 기준 제거.
    - ``"title"``: report_nm + section_title ngram (빠름, 제목형 쿼리용).
    - ``"content"``: section_content 본문 BM25 (개념/내용형 쿼리용).
    - ``"both"``: title + content 결과를 scope 컬럼과 함께 합쳐 반환.

    DART 공시 전용 — EDGAR 공시 검색은 SEC EDGAR Full-Text Search 이용.
    """
    # EDGAR ticker 감지 → 안내 메시지
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
        result = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, topK=topK)
    elif scope == "content":
        result = _searchContent(query, corpCode=corpCode, stockCode=stockCode, topK=topK)
    elif scope == "auto":
        result = _searchAuto(query, corpCode=corpCode, stockCode=stockCode, topK=topK)
    else:  # both
        titleHits = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, topK=topK)
        contentHits = _searchContent(query, corpCode=corpCode, stockCode=stockCode, topK=topK)
        titleHits = titleHits.with_columns(pl.lit("title").alias("scope"))
        contentHits = contentHits.with_columns(pl.lit("content").alias("scope"))
        commonCols = [c for c in titleHits.columns if c in contentHits.columns]
        if commonCols:
            result = pl.concat([titleHits.select(commonCols), contentHits.select(commonCols)])
        else:
            result = titleHits

    # 날짜 필터
    if result.height > 0 and "rcept_dt" in result.columns:
        if start:
            result = result.filter(pl.col("rcept_dt") >= start)
        if end:
            result = result.filter(pl.col("rcept_dt") <= end)

    return result


def _searchTitle(query, *, corpCode, stockCode, topK):
    from dartlab.providers.dart.search.ngramIndex import searchNgram

    return searchNgram(query, corpCode=corpCode, stockCode=stockCode, topK=topK)


def _searchContent(query, *, corpCode, stockCode, topK):
    from dartlab.providers.dart.search.fieldIndex import searchContent

    return searchContent(query, corpCode=corpCode, stockCode=stockCode, topK=topK)


def _searchAuto(query, *, corpCode, stockCode, topK):
    """auto 모드 — 쿼리 유형 자동 판별 후 맞는 엔진 선택.

    판별: 쿼리 전체가 어느 문서의 report_nm에 substring으로 들어가면 제목형,
    아니면 본문형으로 취급. 둘 다 실행해서 substring 히트가 있는 쪽을 우선.
    """
    titleHits = _searchTitle(query, corpCode=corpCode, stockCode=stockCode, topK=topK * 2)
    contentHits = _searchContent(query, corpCode=corpCode, stockCode=stockCode, topK=topK * 2)

    tValid = titleHits is not None and titleHits.height > 0 and "info" not in titleHits.columns
    cValid = contentHits is not None and contentHits.height > 0 and "info" not in contentHits.columns

    if not tValid and not cValid:
        return titleHits if titleHits is not None else contentHits
    if not cValid:
        return titleHits.head(topK)
    if not tValid:
        return contentHits.head(topK)

    # 쿼리 전체가 report_nm에 들어간 결과만 — 제목형 매칭의 정의
    queryNorm = query.strip()
    titleStrict = titleHits.filter(pl.col("report_nm").str.contains(queryNorm, literal=True))
    titleStrictCount = titleStrict.height

    commonCols = [c for c in titleHits.columns if c in contentHits.columns]

    if titleStrictCount >= topK:
        # 제목에 쿼리 전체 들어간 결과로 충분
        return titleStrict.select(commonCols).with_columns(pl.lit("title").alias("scope")).head(topK)

    # 제목 strict 부족 — content로 보강. rcept_no 중복 제거
    tagged_title = titleStrict.select(commonCols).with_columns(pl.lit("title").alias("scope"))
    tagged_content = contentHits.select(commonCols).with_columns(pl.lit("content").alias("scope"))
    if "rcept_no" in commonCols and titleStrictCount > 0:
        usedRcepts = set(titleStrict["rcept_no"].to_list())
        tagged_content = tagged_content.filter(~pl.col("rcept_no").is_in(list(usedRcepts)))

    needed = max(topK - titleStrictCount, 0)
    result = pl.concat([tagged_title, tagged_content.head(needed)])
    return result.head(topK)


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


# ── 인덱스 빌드 ──


def buildIndex(parquetPaths: list[str] | None = None, *, includeDocs: bool = False, **kwargs) -> int:
    """Ngram 인덱스 빌드. allFilings + (선택) docs 통합."""
    from dartlab.providers.dart.search.ngramIndex import buildNgramIndex

    return buildNgramIndex(parquetPaths, includeDocs=includeDocs, **kwargs)


def rebuildIndex(**kwargs) -> int:
    """전체 인덱스 리빌드 — allFilings + docs 통합. (~220초)"""
    return buildIndex(includeDocs=True, **kwargs)


# ── content 인덱스 (scope="content" 검색용) ──


def rebuildContent(**kwargs) -> int:
    """content 인덱스 main 세그먼트 풀리빌드 (월 1회).

    실험 116 검증: docs + allFilings 전체로 BM25 인덱스 구축.
    4M 문서 기준 약 18분 소요.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildMain

    return rebuildMain(**kwargs)


def rebuildContentDelta(**kwargs) -> int:
    """content 인덱스 delta 세그먼트 빌드 (일 단위 증분).

    최근 N일 allFilings만 인덱싱. main 이후 추가분 병합 검색용.
    """
    from dartlab.providers.dart.search.fieldIndex import rebuildDelta

    return rebuildDelta(**kwargs)


# ── 수집 편의 함수 ──


def collectMeta(startDate: str, endDate: str, **kwargs) -> int:
    """공시 목록 수집 (Phase 1)."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    return collectMetaRange(startDate, endDate, **kwargs)


def fillContent(date: str | None = None, **kwargs):
    """공시 원문 채우기 (Phase 2)."""
    from dartlab.providers.dart.openapi.allFilingsCollector import (
        fillContent as _fill,
    )
    from dartlab.providers.dart.openapi.allFilingsCollector import (
        fillContentAll as _fillAll,
    )

    if date:
        return _fill(date, **kwargs)
    return _fillAll(**kwargs)


def stats() -> dict:
    """수집 + 인덱스 통합 통계."""
    from dartlab.providers.dart.openapi.allFilingsCollector import stats as collectorStats
    from dartlab.providers.dart.search.ngramIndex import ngramStats

    result = collectorStats()
    result["stemIndex"] = ngramStats()

    return result


def pushIndex(**kwargs) -> str:
    """stemIndex를 HuggingFace에 업로드."""
    from dartlab.providers.dart.search.ngramIndex import pushStemIndex

    return pushStemIndex(**kwargs)


def pullIndex(**kwargs):
    """HuggingFace에서 검색 인덱스 다운로드 (stemIndex + contentIndex)."""
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


# ── 파생 지식 API ──


def profile(stockCode: str | None = None):
    """기업별 공시 프로필 조회.

    stockCode 지정 시 해당 기업의 공시 요약 dict 반환.
    미지정 시 전체 DataFrame 반환.
    """
    from dartlab.providers.dart.search.derived import loadProfile

    return loadProfile(stockCode)


def pulse(topK: int = 10) -> pl.DataFrame:
    """최근 월의 공시 유형별 건수 + 전월 대비 변화."""
    from dartlab.providers.dart.search.derived import pulse as _pulse

    return _pulse(topK=topK)


def timeline(typeFilter: str | None = None, periodFilter: str | None = None) -> pl.DataFrame:
    """유형×월 빈도 시계열 조회."""
    from dartlab.providers.dart.search.derived import loadTimeline

    return loadTimeline(typeFilter=typeFilter, periodFilter=periodFilter)


def dna(stockCode: str) -> dict:
    """기업의 Disclosure DNA (114차원 유형 빈도 벡터)."""
    from dartlab.providers.dart.search.derived import dna as _dna

    return _dna(stockCode)


def similarCompanies(stockCode: str, topK: int = 5) -> pl.DataFrame:
    """공시 패턴이 유사한 기업 탐색 (코사인 유사도)."""
    from dartlab.providers.dart.search.derived import similarCompanies as _similar

    return _similar(stockCode, topK=topK)
