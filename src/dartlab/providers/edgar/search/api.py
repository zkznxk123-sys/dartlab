"""EDGAR Full-Text Search API thin wrapper.

SEC 공식 제공 ``https://efts.sec.gov/LATEST/search-index`` 호출 + 응답 정규화.
dart 측은 자체 ngram + BM25 인덱스 (4266 줄) 빌드하지만, SEC 는 공식 API 제공
하므로 EDGAR search 는 thin wrapper 만 필요 (본질적 비대칭 정당).

사용:
    >>> from dartlab.providers.edgar.search.api import search
    >>> df = search("revenue recognition", limit=10)
"""

from __future__ import annotations

import httpx
import polars as pl

_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
_DEFAULT_TIMEOUT = 30.0
_USER_AGENT_FALLBACK = "DartLab dartlab@dartlab.dev"


def _userAgent() -> str:
    """SEC fair-use 강행 — User-Agent 필수 (이름 + email)."""
    try:
        from dartlab.providers.edgar.openapi.client import DEFAULT_USER_AGENT

        return DEFAULT_USER_AGENT
    except ImportError:
        return _USER_AGENT_FALLBACK


def search(
    query: str,
    *,
    cik: str | None = None,
    forms: list[str] | None = None,
    dateRange: tuple[str, str] | None = None,
    limit: int = 10,
) -> pl.DataFrame:
    """SEC EDGAR Full-Text Search — 공식 API thin wrapper.

    SEC 의 ``efts.sec.gov/LATEST/search-index`` GET 호출 + 응답 hits 를 polars
    DataFrame 으로 정규화. dart 측의 자체 인덱스 빌드 (ngram + BM25) 와 본질
    비대칭 — SEC 가 인덱스를 호스팅하므로 client 는 query 만 보내고 결과 받음.

    Args:
        query: 검색어 (영어 권장, 한글도 OK 단 매칭 결과 적음).
        cik: 회사 CIK (10-zero-padded) 한정. None = 전체.
        forms: 양식 type list (예 ``["10-K", "10-Q"]``). None = 전체.
        dateRange: ``(startYYYY-MM-DD, endYYYY-MM-DD)`` 또는 None.
        limit: 결과 최대 hits 수 (SEC max 10000, 권장 ≤ 100).

    Returns:
        pl.DataFrame — 검색 결과. 컬럼: ``accession`` / ``cik`` / ``ticker`` /
        ``companyName`` / ``formType`` / ``fileDate`` / ``snippet``. 결과 0 건 →
        빈 DataFrame.

    Raises:
        httpx.HTTPError: 네트워크 실패 또는 SEC 4xx/5xx.

    Example:
        >>> df = search("revenue recognition", forms=["10-K"], limit=5)  # doctest: +SKIP
        >>> df.columns  # doctest: +SKIP
        ['accession', 'cik', 'ticker', 'companyName', 'formType', 'fileDate', 'snippet']
    """
    params: dict[str, str] = {"q": query.strip()}
    if cik:
        params["ciks"] = cik.zfill(10)
    if forms:
        params["forms"] = ",".join(forms)
    if dateRange:
        params["dateRange"] = "custom"
        params["startdt"] = dateRange[0]
        params["enddt"] = dateRange[1]

    headers = {"User-Agent": _userAgent()}
    resp = httpx.get(_BASE_URL, params=params, headers=headers, timeout=_DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        return pl.DataFrame()

    rows: list[dict[str, object]] = []
    for hit in hits[:limit]:
        src = hit.get("_source", {})
        rows.append(
            {
                "accession": hit.get("_id", ""),
                "cik": (src.get("ciks") or [""])[0],
                "ticker": (src.get("tickers") or [""])[0],
                "companyName": (src.get("display_names") or [""])[0],
                "formType": src.get("form", ""),
                "fileDate": src.get("file_date", ""),
                "snippet": (src.get("excerpts") or [""])[0] if src.get("excerpts") else "",
            }
        )
    return pl.DataFrame(rows)


def fetchHits(
    query: str,
    *,
    cik: str | None = None,
    forms: list[str] | None = None,
    dateRange: tuple[str, str] | None = None,
    limit: int = 10,
) -> pl.DataFrame:
    """``search`` 의 fetch-prefix alias — 룰 8/10 (fetch + iter pair) 호환.

    Args:
        query: 검색어.
        cik: 회사 CIK.
        forms: 양식 type list.
        dateRange: ``(startYYYY-MM-DD, endYYYY-MM-DD)``.
        limit: 결과 최대 hits 수.

    Returns:
        pl.DataFrame — ``search`` 와 동일 schema.

    Raises:
        httpx.HTTPError: SEC API 실패.

    Example:
        >>> fetchHits("revenue", limit=5)  # doctest: +SKIP
    """
    return search(query, cik=cik, forms=forms, dateRange=dateRange, limit=limit)


def iterHits(
    query: str,
    *,
    cik: str | None = None,
    forms: list[str] | None = None,
    dateRange: tuple[str, str] | None = None,
    pageSize: int = 100,
    maxPages: int = 10,
):
    """``fetchHits`` 의 streaming pair — page 단위 yield (룰 10 iter pair).

    Args:
        query: 검색어.
        cik: 회사 CIK.
        forms: 양식 type list.
        dateRange: ``(startYYYY-MM-DD, endYYYY-MM-DD)``.
        pageSize: page 당 hits 수.
        maxPages: 최대 page 수 (안전 가드).

    Yields:
        pl.DataFrame — page 단위 결과 (각 ≤ pageSize row).

    Raises:
        httpx.HTTPError: SEC API 실패.

    Example:
        >>> for page in iterHits("revenue", maxPages=3):
        ...     pass  # doctest: +SKIP
    """
    headers = {"User-Agent": _userAgent()}
    for page in range(maxPages):
        params: dict[str, str] = {"q": query.strip(), "from": str(page * pageSize)}
        if cik:
            params["ciks"] = cik.zfill(10)
        if forms:
            params["forms"] = ",".join(forms)
        if dateRange:
            params["dateRange"] = "custom"
            params["startdt"] = dateRange[0]
            params["enddt"] = dateRange[1]
        resp = httpx.get(_BASE_URL, params=params, headers=headers, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            return
        rows: list[dict[str, object]] = []
        for hit in hits[:pageSize]:
            src = hit.get("_source", {})
            rows.append(
                {
                    "accession": hit.get("_id", ""),
                    "cik": (src.get("ciks") or [""])[0],
                    "ticker": (src.get("tickers") or [""])[0],
                    "companyName": (src.get("display_names") or [""])[0],
                    "formType": src.get("form", ""),
                    "fileDate": src.get("file_date", ""),
                    "snippet": (src.get("excerpts") or [""])[0] if src.get("excerpts") else "",
                }
            )
        yield pl.DataFrame(rows)
        if len(hits) < pageSize:
            return  # 마지막 page
