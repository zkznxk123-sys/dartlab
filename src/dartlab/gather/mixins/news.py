"""Gather news/dartDoc mixin — 뉴스 RSS + DART 공시 원문 2 메서드."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from ..infra.http import runAsync
from ..infra.telemetry import emitGatherFetch
from ..sources import news as _news
from .context import GatherMixinContext


class _GatherNewsMixin(GatherMixinContext):
    """뉴스 + DART 공시 원문 메서드 모음 — Gather 클래스 2 메서드."""

    def news(self, query: str, *, market: str = "KR", days: int = 30) -> "pl.DataFrame":
        """뉴스 검색 (Google News RSS).

        Capabilities:
            - Google News RSS 기반 뉴스 수집
            - KR/US 시장별 검색
            - 기간 제한 (기본 30일)
            - circuit breaker + TTL 캐시 (DARTLAB_TTL_NEWS override)
            - DataFrame: title, link, published, source 컬럼

        AIContext:
            - sentiment / event-driven 분석의 외부 신호 원천
            - 본문은 untrusted external — provider 가 [EXTERNAL CONTENT START] 마커 적용

        Guide:
            query 는 자유 문자열 (종목명 + 키워드 조합 가능). KR/US Google News
            언어 분기.

        When:
            sentiment / event 분석 / catalyst 모니터링 시.

        How:
            query + market → Google News RSS → DataFrame.

        Args:
            query: 검색어 (종목명, 키워드 등).
            market: "KR" 또는 "US". 기본 "KR".
            days: 최근 N일 뉴스. 기본 30.

        Returns:
            pl.DataFrame — title, link, published, source 컬럼.
            결과 없으면 빈 DataFrame.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — RSS 파싱 실패는 빈 DataFrame.

        Example::

            g = getDefaultGather()
            g.news("삼성전자")                # KR 뉴스 30일
            g.news("Apple", market="US")     # US 뉴스 30일
            g.news("반도체", days=7)          # 최근 7일

        See Also:
            ``dartDoc`` — DART 공시 본문 (RSS 가 아닌 viewer 직접).
        """
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{query}:{market}:news"
            cached = self._cache.getTyped(cache_key, "news")
            if cached is not None:
                cacheHit = True
                return cached  # type: ignore[return-value]
            items = runAsync(_news._fetchAsync(query, market=market, days=days, client=self._client))
            df = _news.toDataFrame(items)
            if not df.is_empty():
                self._cache.putTyped(cache_key, "news", df)
            return df
        finally:
            emitGatherFetch("news", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def dartDoc(self, rceptNo: str) -> "pl.DataFrame":
        """DART 공시 viewer 원문 fetch (14자리 rcept_no, 무인증).

        Capabilities:
            - 14자리 rcept_no 만으로 공시 원문 fetch
            - viewer 인덱스 페이지 (dsaf001/main.do) sub-doc 목차 파싱
            - 각 섹션 HTML → 텍스트 (테이블 마크다운 보존)
            - API key 불필요 (providers/dart/openapi 와 분리)
            - rate limit + circuit breaker + TTL 캐시 (gather/infra 자동)

        Args:
            rceptNo: 14자리 접수번호 (예: "20240315000123").

        Returns:
            pl.DataFrame — section_order, title, url, text 컬럼.

        Requires:
            네트워크 (dart viewer 무인증 접근).

        Raises:
            InvalidRceptNoError: rceptNo 가 14자리 숫자 아님.
            DocumentNotFoundError: viewer 가 sub-doc 을 반환하지 않음.

        Untrusted Body:
            viewer 본문은 외부 1차 출처지만 AI 엔진 소비 시
            ``Ref.sourceType="external"`` 마커로 감싸야 한다 (호출자 책임).

        Example::

            g = getDefaultGather()
            df = g.dartDoc("20240315000123")
        """
        t0 = time.monotonic()
        try:
            from dartlab.gather.dart.viewer import fetch as _fetchDartDoc

            return _fetchDartDoc(rceptNo, client=self._client)
        finally:
            emitGatherFetch("dartDoc", (time.monotonic() - t0) * 1000, cacheHit=False, market="KR")
