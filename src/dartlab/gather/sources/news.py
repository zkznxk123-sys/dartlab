"""기업별 뉴스 수집 — Google News RSS (async, Gather 인프라 통합)."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import unescape

import polars as pl

from ..infra.resilience import circuitBreaker as _circuit_breaker
from ..infra.resilience import healthTracker as _health_tracker
from ..types import NewsItem

log = logging.getLogger(__name__)

_KR_RSS = "https://news.google.com/rss/search?q={query}+when:{days}d&hl=ko&gl=KR&ceid=KR:ko"
_US_RSS = "https://news.google.com/rss/search?q={query}+stock+when:{days}d&hl=en-US&gl=US&ceid=US:en"

_SOURCE_NAME = "google_news"

_EMPTY_SCHEMA = {"date": pl.Date, "title": pl.Utf8, "source": pl.Utf8, "url": pl.Utf8}


def _parseDate(dateStr: str) -> datetime | None:
    """RSS pubDate 문자열을 datetime으로 파싱.

    RFC 822 형식 두 가지(timezone 약어 / offset)를 순서대로 시도한다.

    Parameters
    ----------
    dateStr : str
        RSS ``<pubDate>`` 값 (예: ``"Tue, 15 Apr 2026 09:30:00 GMT"``).

    Returns
    -------
    datetime | None
        파싱 성공 시 datetime 객체, 모든 포맷 실패 시 None.
    """
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(dateStr, fmt)
        except ValueError:
            continue
    return None


def _parseRss(data: str, *, days: int = 30) -> list[NewsItem]:
    """RSS XML 문자열을 파싱하여 NewsItem 리스트로 변환.

    cutoff(현재 시각 - days) 이전 기사는 제외한다.
    XML 파싱 실패 시 빈 리스트를 반환한다.

    Parameters
    ----------
    data : str
        RSS XML 원본 문자열.
    days : int, optional
        최근 N일 이내 기사만 포함 (기본 30일).

    Returns
    -------
    list[NewsItem]
        date : str — 발행일 (``"YYYY-MM-DD"`` 형식).
        title : str — 기사 제목 (HTML 엔티티 디코딩 완료).
        source : str — 언론사명.
        url : str — 기사 링크.
    """
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return items

    cutoff = datetime.now() - timedelta(days=days)
    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pubDate = item.findtext("pubDate", "")
        source = item.findtext("source", "")
        dt = _parseDate(pubDate)
        if dt and dt.replace(tzinfo=None) >= cutoff:
            items.append(
                NewsItem(
                    date=str(dt.date()),
                    title=unescape(title),
                    source=source,
                    url=link,
                )
            )
    return items


async def _fetchAsync(
    query: str,
    *,
    market: str = "KR",
    days: int = 30,
    client=None,
) -> list[NewsItem]:
    """뉴스 수집 (async) — GatherHttpClient 사용, circuit breaker 적용.

    Parameters
    ----------
    query : str
        검색 쿼리 (기업명 또는 티커).
    market : str
        시장 코드. ``"KR"`` (한국어) 또는 ``"US"`` (영문). 기본 ``"KR"``.
    days : int
        최근 N일 이내 뉴스만 수집 (일). 기본 30.
    client
        GatherHttpClient 인스턴스. None이면 임시 httpx.AsyncClient 사용.

    Returns
    -------
    list[NewsItem]
        date : str — 발행일 (YYYY-MM-DD)
        title : str — 기사 제목
        source : str — 언론사명
        url : str — 기사 링크
        circuit breaker open 또는 수집 실패 시 빈 리스트.
    """
    if _circuit_breaker.isOpen(_SOURCE_NAME):
        log.debug("news circuit breaker open — skip")
        return []

    template = _KR_RSS if market == "KR" else _US_RSS
    url = template.format(query=query, days=days)

    t0 = time.monotonic()
    try:
        if client is not None:
            resp = await client.get(url, timeout=10.0)
            data = resp.text
        else:
            import httpx

            async with httpx.AsyncClient(follow_redirects=True) as ac:
                resp = await ac.get(url, timeout=10.0)
                resp.raise_for_status()
                data = resp.text

        items = _parseRss(data, days=days)
        latency = time.monotonic() - t0
        _circuit_breaker.recordSuccess(_SOURCE_NAME)
        _health_tracker.record(_SOURCE_NAME, success=True, latency=latency)
        return items
    except (ImportError, OSError, TimeoutError, ValueError, ConnectionError) as exc:
        latency = time.monotonic() - t0
        _circuit_breaker.recordFailure(_SOURCE_NAME)
        _health_tracker.record(_SOURCE_NAME, success=False, latency=latency)
        log.debug("news fetch 실패: %s", exc)
        return []


def toDataFrame(items: list[NewsItem]) -> pl.DataFrame:
    """NewsItem 리스트 → pl.DataFrame 변환.

    Parameters
    ----------
    items : list[NewsItem]
        변환할 뉴스 항목 리스트.

    Returns
    -------
    pl.DataFrame
        date : date — 발행일
        title : str — 기사 제목
        source : str — 언론사명
        url : str — 기사 링크
        최신순 정렬. 빈 리스트이면 빈 DataFrame (동일 스키마).

    Raises
    ------
    없음
        빈 리스트는 빈 DataFrame 반환.

    Example
    -------
    >>> items = [NewsItem(date="2024-01-01", title="t", source="s", url="u")]
    >>> toDataFrame(items)
    """
    if not items:
        return pl.DataFrame(schema=_EMPTY_SCHEMA)
    rows = [{"date": i.date, "title": i.title, "source": i.source, "url": i.url} for i in items]
    df = pl.DataFrame(rows)
    if "date" in df.columns:
        df = df.with_columns(pl.col("date").cast(pl.Date))
        df = df.sort("date", descending=True)
    return df


def fetchNews(
    query: str,
    *,
    market: str = "KR",
    days: int = 30,
    limit: int | None = None,
) -> pl.DataFrame:
    """기업명/티커로 뉴스 검색 (동기 래퍼, 하위호환).

    Args:
        query: 기업명 또는 티커.
        market: "KR" 또는 "US".
        days: 최근 N일.
        limit: 반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns:
        (date, title, source, url) DataFrame.

    Raises:
        없음 — Google News RSS 파싱 실패는 빈 DataFrame 반환.

    Example:
        >>> df = fetchNews("삼성전자", market="KR", days=7, limit=10)
    """
    from ..infra.http import runAsync

    items = runAsync(_fetchAsync(query, market=market, days=days))
    df = toDataFrame(items)
    if limit is not None and limit > 0:
        return df.head(limit)
    return df
