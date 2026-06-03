"""OpenEdgar — SEC public API 편의 facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from dartlab.core.edgarClient import (
    EdgarClient,
    filingsFrame,
    getCompanyConceptJson,
    getCompanyFactsJson,
    getFrameJson,
    getSubmissionsJson,
    resolveIssuer,
    searchIssuers,
)
from dartlab.gather.edgar.saver import saveDocs as _saveDocs
from dartlab.gather.edgar.saver import saveFinance as _saveFinance


class OpenEdgar:
    """SEC public API facade.

    Examples
    --------
    >>> from dartlab import OpenEdgar
    >>> e = OpenEdgar()
    >>> aapl = e("AAPL")
    >>> aapl.info()
    >>> aapl.filings(forms=["10-K", "10-Q"])
    >>> aapl.saveFinance()
    """

    def __init__(
        self,
        *,
        userAgent: str | None = None,
        email: str | None = None,
    ):
        self._client = EdgarClient(userAgent=userAgent, email=email)

    def search(self, query: str, *, limit: int | None = None) -> pl.DataFrame:
        """티커 또는 회사명으로 SEC 등록 기업을 검색.

        Args:
            query: 검색어 (ticker 또는 회사명).
            limit: 최대 행 수. None 이면 무제한.

        Returns:
            매칭 DataFrame.

        Raises:
            없음.

        Example:
            >>> OpenEdgar().search("apple", limit=10)

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return searchIssuers(query, self._client, limit=limit)

    def company(self, tickerOrCik: str) -> dict[str, Any]:
        """티커 또는 CIK 로 기업 identity 정보를 조회.

        Args:
            tickerOrCik: ticker (``"AAPL"``) 또는 CIK (``"0000320193"``).

        Returns:
            ``{ticker, cik, title, ...}`` dict.

        Raises:
            ValueError: 매칭 기업 부재 시.

        Example:
            >>> OpenEdgar().company("AAPL")

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return resolveIssuer(tickerOrCik, self._client)

    def submissionsJson(self, tickerOrCik: str) -> dict[str, Any]:
        """SEC submissions API 원본 JSON 을 반환.

        Args:
            tickerOrCik: ticker 또는 CIK.

        Returns:
            원본 JSON dict.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> OpenEdgar().submissionsJson("AAPL")

        SeeAlso:
            - ``EdgarClient`` — 본 함수의 HTTP request backend.
            - ``OpenEdgar`` — 본 클래스의 facade.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - SEC EDGAR public API endpoint 위임 + 정규화 (submissions/companyfacts/concept/frame).
              User-Agent 헤더 필수 (SEC 표준) — API 키 불요.

        Guide:
            - "SEC EDGAR API 호출" → 본 메서드.
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal SEC API client — AI 가 직접 호출 시 rate limit (10 req/s) 주의.

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        cik = self.company(tickerOrCik)["cik"]
        return getSubmissionsJson(cik, self._client)

    def filings(
        self,
        tickerOrCik: str,
        *,
        forms: list[str] | tuple[str, ...] | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> pl.DataFrame:
        """정기보고서 (10-K/10-Q/20-F) 목록을 DataFrame 으로 반환.

        Args:
            tickerOrCik: ticker 또는 CIK.
            forms: form 유형 리스트 (None 이면 전체).
            since: 시작일.
            until: 종료일.

        Returns:
            ``form/filing_date/accession_no/...`` 컬럼 DataFrame.

        Raises:
            없음.

        Example:
            >>> OpenEdgar().filings("AAPL", forms=["10-K"])

        SeeAlso:
            - ``EdgarClient`` — 본 함수의 HTTP request backend.
            - ``OpenEdgar`` — 본 클래스의 facade.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - SEC EDGAR public API endpoint 위임 + 정규화 (submissions/companyfacts/concept/frame).
              User-Agent 헤더 필수 (SEC 표준) — API 키 불요.

        Guide:
            - "SEC EDGAR API 호출" → 본 메서드.
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal SEC API client — AI 가 직접 호출 시 rate limit (10 req/s) 주의.

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        info = self.company(tickerOrCik)
        submissions = getSubmissionsJson(info["cik"], self._client)
        return filingsFrame(
            submissions,
            ticker=info["ticker"],
            title=info["title"],
            forms=forms,
            since=since,
            until=until,
            client=self._client,
        )

    def companyFactsJson(self, tickerOrCik: str) -> dict[str, Any]:
        """회사의 전체 XBRL fact 데이터를 JSON 으로 반환.

        Args:
            tickerOrCik: ticker 또는 CIK.

        Returns:
            companyfacts API 원본 JSON.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> OpenEdgar().companyFactsJson("AAPL")

        SeeAlso:
            - ``EdgarClient`` — 본 함수의 HTTP request backend.
            - ``OpenEdgar`` — 본 클래스의 facade.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - SEC EDGAR public API endpoint 위임 + 정규화 (submissions/companyfacts/concept/frame).
              User-Agent 헤더 필수 (SEC 표준) — API 키 불요.

        Guide:
            - "SEC EDGAR API 호출" → 본 메서드.
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal SEC API client — AI 가 직접 호출 시 rate limit (10 req/s) 주의.

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        cik = self.company(tickerOrCik)["cik"]
        return getCompanyFactsJson(cik, self._client)

    def companyConceptJson(
        self,
        tickerOrCik: str,
        taxonomy: str,
        tag: str,
    ) -> dict[str, Any]:
        """특정 ``taxonomy``/``tag`` 조합의 concept 데이터를 JSON 으로 반환.

        Args:
            tickerOrCik: ticker 또는 CIK.
            taxonomy: XBRL taxonomy (예: ``"us-gaap"``).
            tag: XBRL tag (예: ``"Revenues"``).

        Returns:
            concept API 원본 JSON.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> OpenEdgar().companyConceptJson("AAPL", "us-gaap", "Revenues")

        SeeAlso:
            - ``EdgarClient`` — 본 함수의 HTTP request backend.
            - ``OpenEdgar`` — 본 클래스의 facade.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - SEC EDGAR public API endpoint 위임 + 정규화 (submissions/companyfacts/concept/frame).
              User-Agent 헤더 필수 (SEC 표준) — API 키 불요.

        Guide:
            - "SEC EDGAR API 호출" → 본 메서드.
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal SEC API client — AI 가 직접 호출 시 rate limit (10 req/s) 주의.

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        cik = self.company(tickerOrCik)["cik"]
        return getCompanyConceptJson(cik, taxonomy, tag, self._client)

    def frameJson(
        self,
        taxonomy: str,
        tag: str,
        unit: str,
        period: str,
    ) -> dict[str, Any]:
        """특정 기간의 전체 기업 XBRL frame 데이터를 JSON 으로 반환.

        Args:
            taxonomy: XBRL taxonomy.
            tag: XBRL tag.
            unit: unit (예: ``"USD"``).
            period: 기간 (예: ``"CY2024Q4I"``).

        Returns:
            frame API 원본 JSON (cross-sectional, 전 기업).

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> OpenEdgar().frameJson("us-gaap", "Revenues", "USD", "CY2024")

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return getFrameJson(taxonomy, tag, unit, period, self._client)

    def __call__(self, tickerOrCik: str) -> OpenEdgarCompany:
        return OpenEdgarCompany(self, tickerOrCik)

    def __repr__(self) -> str:
        return f"OpenEdgar(userAgent={self._client.userAgent!r})"


class OpenEdgarCompany:
    """회사 단위 EDGAR convenience proxy."""

    def __init__(self, edgar: OpenEdgar, tickerOrCik: str):
        self._edgar = edgar
        self._identity = edgar.company(tickerOrCik)

    @property
    def ticker(self) -> str:
        """회사 티커 심볼.

        Returns:
            ticker str.

        Raises:
            없음.

        Example:
            >>> e("AAPL").ticker
            'AAPL'

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return str(self._identity["ticker"])

    @property
    def cik(self) -> str:
        """SEC CIK 번호 (10 자리 zero-padded).

        Returns:
            CIK str.

        Raises:
            없음.

        Example:
            >>> e("AAPL").cik
            '0000320193'

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return str(self._identity["cik"])

    def info(self) -> dict[str, Any]:
        """기업 identity 정보 (ticker, cik, title 등) 를 dict 로 반환.

        Returns:
            ``{ticker, cik, title, ...}`` dict.

        Raises:
            없음.

        Example:
            >>> e("AAPL").info()

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return dict(self._identity)

    def submissionsJson(self) -> dict[str, Any]:
        """이 회사의 SEC submissions 원본 JSON 을 반환.

        Returns:
            원본 JSON dict.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> e("AAPL").submissionsJson()

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return getSubmissionsJson(self.cik, self._edgar._client)

    def filings(
        self,
        *,
        forms: list[str] | tuple[str, ...] | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> pl.DataFrame:
        """이 회사의 정기보고서 목록을 DataFrame 으로 반환.

        Args:
            forms: form 유형 리스트.
            since: 시작일.
            until: 종료일.

        Returns:
            ``form/filing_date/accession_no/...`` 컬럼 DataFrame.

        Raises:
            없음.

        Example:
            >>> e("AAPL").filings(forms=["10-K"])

        SeeAlso:
            - ``EdgarClient`` — 본 함수의 HTTP request backend.
            - ``OpenEdgar`` — 본 클래스의 facade.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - SEC EDGAR public API endpoint 위임 + 정규화 (submissions/companyfacts/concept/frame).
              User-Agent 헤더 필수 (SEC 표준) — API 키 불요.

        Guide:
            - "SEC EDGAR API 호출" → 본 메서드.
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 사용 X.

        AIContext:
            internal SEC API client — AI 가 직접 호출 시 rate limit (10 req/s) 주의.

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        submissions = self.submissionsJson()
        return filingsFrame(
            submissions,
            ticker=self.ticker,
            title=str(self._identity.get("title") or self.ticker),
            forms=forms,
            since=since,
            until=until,
            client=self._edgar._client,
        )

    def companyFactsJson(self) -> dict[str, Any]:
        """이 회사의 전체 XBRL fact 데이터를 JSON 으로 반환.

        Returns:
            companyfacts API 원본 JSON.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> e("AAPL").companyFactsJson()

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return getCompanyFactsJson(self.cik, self._edgar._client)

    def companyConceptJson(self, taxonomy: str, tag: str) -> dict[str, Any]:
        """이 회사의 특정 ``taxonomy``/``tag`` concept 데이터를 JSON 으로 반환.

        Args:
            taxonomy: XBRL taxonomy.
            tag: XBRL tag.

        Returns:
            concept API 원본 JSON.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> e("AAPL").companyConceptJson("us-gaap", "Revenues")

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return getCompanyConceptJson(self.cik, taxonomy, tag, self._edgar._client)

    def saveDocs(self, *, sinceYear: int = 2009) -> Path:
        """10-K/10-Q 문서를 수집하여 로컬 parquet 로 저장.

        Args:
            sinceYear: 시작 연도.

        Returns:
            저장된 parquet Path.

        Raises:
            ValueError: filing 부재 시 (``fetchEdgarDocs`` 위임).

        Example:
            >>> e("AAPL").saveDocs(sinceYear=2020)

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return _saveDocs(self.ticker, sinceYear=sinceYear)

    def saveFinance(self) -> Path:
        """XBRL companyfacts 를 수집하여 로컬 parquet 로 저장.

        Returns:
            저장된 parquet Path.

        Raises:
            httpx.HTTPError: 네트워크 오류 시.

        Example:
            >>> e("AAPL").saveFinance()

        LLM Specifications:
            AntiPatterns:
                - SEC User-Agent 헤더 미설정 → 403 Forbidden. EdgarClient 초기화 시 자동 주입.
                - rate limit (10 req/s) 초과 시 차단 — SEC 표준.
                - 빈 응답 (회사 부재) → caller 분기 의무.
            OutputSchema:
                - dict / pl.DataFrame — endpoint 별 정규화.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API (User-Agent 필수, 키 불요).
            Freshness:
                - SEC EDGAR 실시간 (분 단위).
            Dataflow:
                - 사용자 인자 → EdgarClient → SEC API → JSON 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR) 한정.
        """
        return _saveFinance(self.cik, client=self._edgar._client)

    def __repr__(self) -> str:
        return f"OpenEdgarCompany('{self.ticker}')"
