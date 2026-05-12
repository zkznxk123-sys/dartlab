"""웹 검색 백엔드 -- Tavily API.

TAVILY_API_KEY 환경변수가 있으면 검색 가능, 없으면 빈 리스트 반환.
검색 실패가 AI 분석 파이프라인을 죽이지 않도록 graceful degradation.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from ..infra.cache import GatherCache
from ..infra.resilience import circuitBreaker as _cb
from ..infra.resilience import healthTracker as _ht

log = logging.getLogger(__name__)

TTL_SEARCH = 1800  # 30분

_MAX_RESULTS = 8


@dataclass(frozen=True, slots=True)
class SearchResult:
    """검색 결과 단일 항목."""

    title: str
    url: str
    snippet: str
    source: str
    published: str | None = None


# ── 모듈 레벨 캐시 싱글턴 ──

_cache = GatherCache(maxEntries=100)


# ── Tavily 백엔드 ──


def _tavilyAvailable() -> bool:
    """Tavily 검색 백엔드 사용 가능 여부 확인.

    TAVILY_API_KEY 환경변수 존재 + tavily 패키지 import 가능 여부를 모두 검사한다.

    Returns
    -------
    bool
        True이면 Tavily 검색 가능, False이면 키 미설정 또는 SDK 미설치.
    """
    if not os.environ.get("TAVILY_API_KEY"):
        return False
    try:
        import tavily  # noqa: F401

        return True
    except ImportError:
        return False


def _searchTavily(
    query: str, *, maxResults: int = _MAX_RESULTS, days: int | None = None, topic: str = "general"
) -> list[SearchResult]:
    """Tavily API로 웹 검색 실행.

    Parameters
    ----------
    query : str
        검색 쿼리 문자열.
    maxResults : int
        최대 반환 결과 수 (개). 기본 8.
    days : int | None
        최근 N일 이내 결과만 반환. None이면 제한 없음.
    topic : str
        검색 토픽. ``"general"`` 또는 ``"news"``.

    Returns
    -------
    list[SearchResult]
        title : str — 제목
        url : str — 페이지 URL
        snippet : str — 요약 텍스트
        source : str — ``"tavily"``
        published : str | None — 발행일
    """
    from tavily import TavilyClient

    client = TavilyClient(apiKey=os.environ["TAVILY_API_KEY"])
    kwargs: dict = {
        "query": query,
        "max_results": maxResults,
        "search_depth": "basic",
        "include_answer": False,
    }
    if topic != "general":
        kwargs["topic"] = topic
    if days is not None and days > 0:
        kwargs["days"] = days

    resp = client.search(**kwargs)
    results: list[SearchResult] = []
    for item in resp.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source="tavily",
                published=item.get("published_date"),
            )
        )
    return results


# ── 통합 검색 API ──


def webSearch(
    query: str,
    *,
    maxResults: int = _MAX_RESULTS,
    days: int | None = None,
) -> list[SearchResult]:
    """웹 검색. Tavily API 키가 없으면 빈 리스트.

    Capabilities:
        - Tavily API 검색 (key 있으면)
        - 캐시 30분
        - circuit breaker — 연속 실패 시 자동 차단

    AIContext:
        - AI 엔진의 외부 검색 도구 (workbench 가 호출)

    Guide:
        TAVILY_API_KEY env 필수. 미설정 시 빈 리스트 (silent fallback).

    When:
        AI 가 외부 검색 evidence 필요 시.

    How:
        query → Tavily → SearchResult list → cache.

    Requires:
        TAVILY_API_KEY env.

    Parameters
    ----------
    query : str
        검색 쿼리 문자열.
    maxResults : int
        최대 반환 결과 수 (개). 기본 8.
    days : int | None
        최근 N일 이내 결과만. None이면 전체 기간.

    Returns
    -------
    list[SearchResult]
        title : str — 제목
        url : str — 페이지 URL
        snippet : str — 요약 텍스트
        source : str — ``"tavily"``
        published : str | None — 발행일
        캐시 TTL 30분. Tavily 미설정 시 빈 리스트.

    Raises
    ------
    없음
        Tavily 내부 예외 (OSError/ValueError/KeyError/RuntimeError) 는 빈 리스트 + circuit breaker.

    Example
    -------
    >>> hits = webSearch("samsung electronics", maxResults=5)

    See Also:
        ``newsSearch`` — 뉴스 전용 검색.
    """
    cacheKey = f"search:{query}:{maxResults}:{days}"
    cached = _cache.get(cacheKey)
    if cached is not None:
        return cached  # type: ignore[return-value]

    results: list[SearchResult] = []

    if _tavilyAvailable() and not _cb.isOpen("tavily"):
        t0 = time.monotonic()
        try:
            results = _searchTavily(query, maxResults=maxResults, days=days)
            _cb.recordSuccess("tavily")
            _ht.record(source="tavily", success=True, latency=time.monotonic() - t0)
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            log.warning("Tavily 검색 실패: %s", e)
            _cb.recordFailure("tavily")
            _ht.record(source="tavily", success=False, latency=time.monotonic() - t0)

    if results:
        _cache.put(cacheKey, results, TTL_SEARCH)

    return results


def newsSearch(
    query: str,
    *,
    maxResults: int = _MAX_RESULTS,
    days: int | None = None,
) -> list[SearchResult]:
    """뉴스 검색. Tavily topic=news.

    Capabilities:
        - Tavily news 전용 검색
        - 캐시 30분
        - circuit breaker

    AIContext:
        - AI 엔진의 외부 뉴스 검색 (catalyst 분석 도구)

    Guide:
        webSearch 와 분리 — topic=news 로 신선도 ↑ 결과.

    When:
        catalyst / event-driven 분석의 외부 뉴스 fetch 시.

    How:
        query → Tavily(topic=news) → SearchResult list.

    Requires:
        TAVILY_API_KEY env.

    Parameters
    ----------
    query : str
        검색 쿼리 문자열.
    maxResults : int
        최대 반환 결과 수 (개). 기본 8.
    days : int | None
        최근 N일 이내 뉴스만. None이면 전체 기간.

    Returns
    -------
    list[SearchResult]
        title : str — 뉴스 제목
        url : str — 기사 URL
        snippet : str — 요약 텍스트
        source : str — ``"tavily"``
        published : str | None — 발행일
        캐시 TTL 30분. Tavily 미설정 시 빈 리스트.

    Raises
    ------
    없음
        Tavily 내부 예외 (OSError/ValueError/KeyError/RuntimeError) 는 빈 리스트 + circuit breaker.

    Example
    -------
    >>> news = newsSearch("samsung", maxResults=10, days=7)

    See Also:
        ``webSearch`` — general 검색.
    """
    cacheKey = f"news_search:{query}:{maxResults}:{days}"
    cached = _cache.get(cacheKey)
    if cached is not None:
        return cached  # type: ignore[return-value]

    results: list[SearchResult] = []

    if _tavilyAvailable() and not _cb.isOpen("tavily"):
        t0 = time.monotonic()
        try:
            results = _searchTavily(query, maxResults=maxResults, days=days, topic="news")
            _cb.recordSuccess("tavily")
            _ht.record(source="tavily", success=True, latency=time.monotonic() - t0)
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            log.warning("Tavily 뉴스 검색 실패: %s", e)
            _cb.recordFailure("tavily")
            _ht.record(source="tavily", success=False, latency=time.monotonic() - t0)

    if results:
        _cache.put(cacheKey, results, TTL_SEARCH)

    return results


def searchAvailable(*, limit: int | None = None) -> dict[str, bool]:
    """검색 백엔드 가용성 확인.

    Capabilities:
        - 백엔드별 boolean 가용성 dict
        - "any" 키로 종합 가용성 통합

    AIContext:
        - AI 가 검색 가능 여부 사전 확인 시 호출

    Guide:
        TAVILY_API_KEY 미설정 시 tavily=False. 추후 backend 추가 시 키 확장.

    When:
        AI 의 사전 capability discovery 시.

    How:
        backend별 _tavilyAvailable 등 check → bool dict.

    Requires:
        없음 (env check).

    Parameters
    ----------
    limit : int | None
        백엔드 능력 진단 함수라 무시된다. 인터페이스 호환 목적으로만 존재.

    Returns
    -------
    dict[str, bool]
        tavily : bool — Tavily 백엔드 사용 가능 여부
        any : bool — 하나 이상의 백엔드 사용 가능 여부

    Raises
    ------
    없음
        backend 진단 함수 — 모든 실패는 False 로 표현.

    Example
    -------
    >>> caps = searchAvailable()
    >>> caps["tavily"]

    See Also:
        ``webSearch``/``newsSearch`` — capability 후 호출 대상.
    """
    del limit
    tavily = _tavilyAvailable()
    return {
        "tavily": tavily,
        "any": tavily,
    }


def formatResults(results: list[SearchResult], *, maxChars: int = 4000) -> str:
    """검색 결과를 LLM 컨텍스트용 마크다운으로 포맷.

    Capabilities:
        - SearchResult list → 마크다운 문자열
        - maxChars 초과 시 truncate

    AIContext:
        - AI 엔진이 검색 결과를 prompt context 로 직렬화할 때 사용

    Guide:
        본문 untrusted 마커는 caller 의 책임 — 본 함수는 단순 직렬화만.

    When:
        webSearch/newsSearch 결과를 prompt 에 주입 직전.

    How:
        results → "## title\\nURL\\nsnippet" 패턴 → truncate.

    Requires:
        없음 (순수 문자열 조작).

    Parameters
    ----------
    results : list[SearchResult]
        포맷할 검색 결과 목록.
    maxChars : int
        최대 출력 문자 수 (자). 기본 4000. 초과 시 나머지 생략.

    Returns
    -------
    str
        마크다운 형식 문자열. 결과 없으면 ``"(검색 결과 없음)"``.

    Raises
    ------
    없음
        포맷팅 전용 — 입력 list 가 비어 있으면 안내 문자열 반환.

    Example
    -------
    >>> txt = formatResults(results, maxChars=2000)

    See Also:
        ``webSearch``/``newsSearch`` — results 의 source.
    """
    if not results:
        return "(검색 결과 없음)"

    lines: list[str] = []
    total = 0
    for i, r in enumerate(results, 1):
        entry = f"**{i}. [{r.title}]({r.url})**"
        if r.published:
            entry += f" ({r.published})"
        entry += f"\n{r.snippet}\n"
        if total + len(entry) > maxChars:
            lines.append(f"... ({len(results) - i + 1}건 생략)")
            break
        lines.append(entry)
        total += len(entry)

    return "\n".join(lines)
