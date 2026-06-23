"""SEC EDGAR submissions 전 form 열거 — gather 자체포함 (keyless).

「공시 오리지널 수집」 모듈이 ``gather ↛ providers`` 규칙을 지키며 자체포함되도록,
SEC submissions JSON 파싱을 모듈 안에서 직접 한다. providers
``edgar/openapi/submissions.py`` 의 ``findRegularFilings`` 와 달리 **form 필터가
없다** — 10-K/10-Q뿐 아니라 8-K·DEF 14A·S-1·Form 4 등 **전 form** 을 열거한다
(원본 백업은 정기·비정기 전부).

SEC 는 인증 키가 없다 — User-Agent(연락처 포함)만 요구. 키풀/per-IP 로직 불필요.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

# SEC 정책 — 식별 가능한 연락처 User-Agent 필수(미설정 시 403). providers edgar 와 동일.
_HEADERS = {"User-Agent": "DartLab eddmpython@gmail.com"}
_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_BROWSE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
_REQUEST_INTERVAL = 0.2  # SEC 10 req/s 한도 — 5 req/s 로 보수적

# ticker → cik 맵 (프로세스 1회 fetch 캐시)
_TICKER_MAP: dict[str, str] | None = None
# company_tickers.json 누락 ticker 의 browse-edgar fallback 결과(음성 포함) 프로세스 캐시
_CIK_FALLBACK: dict[str, str | None] = {}


def _getJson(url: str) -> dict[str, Any]:
    """SEC JSON GET(User-Agent + interval). 404/빈응답은 빈 dict.

    Args:
        url: 요청 URL.

    Returns:
        dict — JSON 응답. 404/디코드 실패 시 빈 dict.

    Raises:
        httpx.HTTPError: 네트워크/HTTP(404 제외) 오류.

    Example:
        >>> _getJson("https://data.sec.gov/submissions/CIK0000320193.json")  # doctest: +SKIP
    """
    time.sleep(_REQUEST_INTERVAL)
    resp = httpx.get(url, headers=_HEADERS, timeout=30, follow_redirects=True)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()


def resolveCik(ticker: str) -> str:
    """ticker → 10자리 CIK (SEC company_tickers.json, 프로세스 캐시).

    Capabilities:
        - SEC 공개 ``company_tickers.json`` 으로 ticker 를 zero-padded 10자리 CIK 로
          해석. 첫 호출 시 맵 1회 fetch 후 캐시. 이미 CIK(숫자)면 정규화만.

    Args:
        ticker: US ticker(예: ``"AAPL"``) 또는 CIK 숫자 문자열.

    Returns:
        str — 10자리 zero-padded CIK.

    Raises:
        ValueError: 미등록 ticker.
        httpx.HTTPError: company_tickers.json fetch 실패.

    Example:
        >>> resolveCik("AAPL")  # doctest: +SKIP
        '0000320193'

    Guide:
        - 대량 호출 전 한 번 호출하면 이후는 캐시 hit(네트워크 0).

    SeeAlso:
        - ``listAllFilings`` — 본 함수로 CIK 해석 후 submissions 열거.

    Requires:
        - 인터넷 + SEC User-Agent(연락처).

    When:
        - EDGAR 원본 수집 시작 시 ticker 를 CIK(전 form 통합 키)로 해석할 때.

    How:
        - 숫자면 zfill(10), 아니면 company_tickers.json 맵(1회 fetch 캐시) lookup.

    AIContext:
        내부 식별자 해석 — AI 가 US 회사 원본 수집 시 ticker 입력 허용.

    LLM Specifications:
        AntiPatterns:
            - User-Agent 미설정 X — SEC 403.
            - ticker 소문자/공백 그대로 X — 내부에서 upper/strip.
        OutputSchema:
            - str(10자리 CIK).
        Prerequisites:
            - 인터넷 + ticker 또는 CIK.
        Freshness:
            - company_tickers.json 일 단위 갱신(프로세스 캐시).
        Dataflow:
            - ticker → company_tickers.json → cik10.
        TargetMarkets:
            - US(SEC EDGAR).
    """
    raw = str(ticker).strip()
    if raw.isdigit():
        return raw.zfill(10)

    global _TICKER_MAP
    if _TICKER_MAP is None:
        data = _getJson(_TICKERS_URL)
        mapping: dict[str, str] = {}
        for entry in data.values():
            t = str(entry.get("ticker", "")).upper()
            cikStr = str(entry.get("cik_str", "")).strip()
            if t and cikStr:
                mapping[t] = cikStr.zfill(10)
        _TICKER_MAP = mapping

    cik = _TICKER_MAP.get(raw.upper())
    if not cik:
        cik = _browseEdgarCik(raw.upper())  # company_tickers.json 누락 filer fallback
    if not cik:
        raise ValueError(f"ticker '{ticker}' 의 CIK 를 SEC company_tickers/browse-edgar 에서 찾을 수 없음")
    return cik


def _browseEdgarCik(ticker: str) -> str | None:
    """company_tickers.json 누락 ticker → browse-edgar 인덱스로 CIK 해소(fallback).

    Capabilities:
        - SEC ``company_tickers.json`` 은 일부 활성 filer(예: Coterra ``CTRA``,
          Hologic ``HOLX``)를 누락한다. browse-edgar ``getcompany&ticker=`` 조회는
          이들도 CIK 를 돌려주는 SEC 정본 ticker 인덱스다. 음성 결과까지 프로세스
          캐시해 같은 run 안 재시도 네트워크 비용을 막는다.

    Args:
        ticker: 대문자 US ticker.

    Returns:
        str | None — 10자리 zero-padded CIK, 미해소 시 None.

    Raises:
        없음 — 네트워크/파싱 실패는 None(상위 resolveCik 가 ValueError 판정).

    Example:
        >>> _browseEdgarCik("CTRA")  # doctest: +SKIP
        '0000858470'

    Guide:
        - resolveCik 의 company_tickers.json miss 경로에서만 호출(정상 ticker 는 도달 X).

    SeeAlso:
        - ``resolveCik`` — 1차 company_tickers.json, miss 시 본 fallback.

    Requires:
        - 인터넷 + SEC User-Agent.

    When:
        - sp500/universe 에 있으나 company_tickers.json 에 없는 filer 를 만났을 때.

    How:
        - browse-edgar atom 응답에서 ``CIK=NNNN`` 또는 ``<cik>NNNN</cik>`` 추출 후 zfill(10).

    AIContext:
        내부 식별자 해석 보강 — AI 호출 표면 변화 없음(resolveCik 투명 fallback).

    LLM Specifications:
        AntiPatterns:
            - 정상 ticker 에 직접 호출 X — company_tickers.json 우선.
        OutputSchema:
            - str(10자리 CIK) | None.
        Prerequisites:
            - 인터넷 + SEC User-Agent.
        Freshness:
            - browse-edgar 인덱스 실시간(프로세스 캐시).
        Dataflow:
            - ticker → browse-edgar atom → cik10.
        TargetMarkets:
            - US(SEC EDGAR).
    """
    if ticker in _CIK_FALLBACK:
        return _CIK_FALLBACK[ticker]
    time.sleep(_REQUEST_INTERVAL)
    url = f"{_BROWSE_URL}?action=getcompany&ticker={ticker}&type=10-K&dateb=&owner=include&count=1&output=atom"
    cik: str | None = None
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=30, follow_redirects=True)
        if resp.status_code == 200:
            m = re.search(r"CIK=(\d+)", resp.text) or re.search(r"<cik>(\d+)</cik>", resp.text)
            if m:
                cik = m.group(1).zfill(10)
    except httpx.HTTPError:
        cik = None
    _CIK_FALLBACK[ticker] = cik
    return cik


def _mergeFilings(submissions: dict[str, Any], sinceYear: int) -> dict[str, list[Any]]:
    """submissions.recent + older paginated 파일을 form 컬럼 dict 로 병합.

    Args:
        submissions: ``CIK{n}.json`` 결과.
        sinceYear: 이 연도 이전 older 파일은 skip.

    Returns:
        dict[str, list] — 병합된 컬럼(form/accessionNumber/filingDate/...).

    Raises:
        httpx.HTTPError: older 페이지 fetch 실패.

    Example:
        >>> _mergeFilings(subs, "0000320193", 2009)  # doctest: +SKIP
    """
    recent = submissions.get("filings", {}).get("recent", {})
    merged: dict[str, list[Any]] = {k: list(v) for k, v in recent.items()}
    for fileInfo in submissions.get("filings", {}).get("files", []):
        filingTo = str(fileInfo.get("filingTo") or "")
        if filingTo[:4].isdigit() and int(filingTo[:4]) < sinceYear:
            continue
        name = str(fileInfo.get("name") or "")
        if not name:
            continue
        extra = _getJson(f"{_SUBMISSIONS_BASE}/{name}")
        for key in merged:
            if key in extra:
                merged[key].extend(extra[key])
    return merged


def _submissionTextUrl(cik: str, accessionNo: str) -> str:
    """full submission ``.txt`` URL 구성(전 문서 + SGML 헤더).

    Args:
        cik: 10자리 CIK.
        accessionNo: ``YYYYMMDD-NN-NNNNNN`` 형식 접수번호.

    Returns:
        str — ``{Archives}/{cik}/{accNoDash}/{accession}.txt``.

    Raises:
        없음.

    Example:
        >>> _submissionTextUrl("0000320193", "0000320193-24-000123")[-4:]
        '.txt'
    """
    accNoDash = accessionNo.replace("-", "")
    return f"{_ARCHIVES_BASE}/{cik}/{accNoDash}/{accessionNo}.txt"


def listAllFilings(
    cikOrTicker: str,
    *,
    sinceYear: int = 2009,
    forms: list[str] | tuple[str, ...] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """한 발행자의 **전 form** 공시 목록 — 정기·비정기 모두(form 필터 없음).

    Capabilities:
        - SEC submissions API 의 recent + older paginated 를 병합해 전 form 공시를
          열거(10-K/10-Q/8-K/DEF 14A/S-1/Form 4 등 전부). ``forms`` 지정 시 그 set 만.
          각 행에 full submission ``.txt`` URL 동봉 → panel 빌드가 메모리 fetch 로 즉시 소비.

    Args:
        cikOrTicker: ticker(``"AAPL"``) 또는 CIK 숫자.
        sinceYear: 시작 연도(이전 older 페이지/행 skip). 기본 2009.
        forms: form 화이트리스트(예: ``["8-K"]``). None 이면 **전 form**.
        limit: 최신 N 건 상한(가장 오래된 것부터 정렬 후 tail). None 이면 전체(백업 기본).

    Returns:
        list[dict] — filing dict list(filing_date ASC). 각 dict 키: ``cik`` · ``form`` ·
        ``filing_date`` · ``accession_no`` · ``primary_document`` · ``txt_url`` · ``year``.

    Raises:
        ValueError: 미등록 ticker.
        httpx.HTTPError: submissions API fetch 실패.

    Example:
        >>> rows = listAllFilings("AAPL", sinceYear=2024, forms=["8-K"])  # doctest: +SKIP
        >>> rows[0]["txt_url"].endswith(".txt")  # doctest: +SKIP
        True

    Guide:
        - 전 form 은 종목당 수백~수천 건 — ``forms``/``sinceYear`` 로 범위 조절.

    SeeAlso:
        - ``collect.fetchFilingTexts`` — 본 목록의 ``txt_url`` 을 저장 없이 메모리 text 로 fetch.
        - ``providers.edgar.openapi.submissions.findRegularFilings`` — 정기 4종 한정 원본(import 안 함).

    Requires:
        - 인터넷 + SEC User-Agent.

    When:
        - 한 발행자의 전 form(정기+비정기) panel 빌드 입력을 열거할 때.

    How:
        - CIK 해석 → submissions JSON(recent+older 병합) → form/sinceYear/limit 필터 → txt_url 구성.

    AIContext:
        US 회사 전 공시 열거 — panel build 입력. 본문은 untrusted(해석 별도).

    LLM Specifications:
        AntiPatterns:
            - 정기보고서만 가정 X — 본 함수는 전 form(8-K 등 비정기 포함).
            - User-Agent 미설정 X — SEC 403.
            - 전 form 대량을 무필터 호출 시 종목당 수천 건 — forms/sinceYear 권장.
        OutputSchema:
            - list[dict](filing_date ASC), 각 dict cik/form/filing_date/accession_no/txt_url/...
        Prerequisites:
            - 인터넷 + ticker/CIK.
        Freshness:
            - SEC 실시간(제출 후 분 단위).
        Dataflow:
            - cik → submissions(recent+older 병합) → form/since 필터 → txt_url 구성.
        TargetMarkets:
            - US(SEC EDGAR) 전 form.
    """
    cik = resolveCik(cikOrTicker)
    submissions = _getJson(f"{_SUBMISSIONS_BASE}/CIK{cik}.json")
    if not submissions:
        return []

    merged = _mergeFilings(submissions, sinceYear)
    formSet = {f.upper() for f in forms} if forms else None

    formList = merged.get("form", [])
    accessions = merged.get("accessionNumber", [])
    filingDates = merged.get("filingDate", [])
    primaryDocs = merged.get("primaryDocument", [])

    rows: list[dict[str, Any]] = []
    for idx, formType in enumerate(formList):
        formText = str(formType or "")
        if formSet is not None and formText.upper() not in formSet:
            continue
        filingDate = str(filingDates[idx] if idx < len(filingDates) else "") or ""
        if len(filingDate) < 4 or not filingDate[:4].isdigit():
            continue
        if int(filingDate[:4]) < sinceYear:
            continue
        accession = str(accessions[idx] if idx < len(accessions) else "") or ""
        if not accession:
            continue
        rows.append(
            {
                "cik": cik,
                "form": formText,
                "filing_date": filingDate,
                "accession_no": accession,
                "primary_document": str(primaryDocs[idx] if idx < len(primaryDocs) else "") or None,
                "txt_url": _submissionTextUrl(cik, accession),
                "year": filingDate[:4],
            }
        )

    rows.sort(key=lambda r: (r["filing_date"], r["accession_no"]))
    if limit is not None and limit > 0:
        rows = rows[-limit:]
    return rows
