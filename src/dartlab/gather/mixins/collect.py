"""Gather collect mixin — 전체 도메인 병렬 수집 3 메서드."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..domains import loadDomain
from ..infra.http import runAsync
from ..marketConfig import getMarketConfig
from ..sources import insider as _insider
from ..sources import news as _news
from ..sources import sector as _sector
from ..types import GatherResult, GatherSnapshot, SectorInfo
from .context import GatherMixinContext

log = logging.getLogger(__name__)


class _GatherCollectMixin(GatherMixinContext):
    """전체 병렬 수집 메서드 모음 — Gather 클래스 3 메서드."""

    def collect(self, stockCode: str, *, market: str = "KR") -> GatherSnapshot:
        """전체 도메인 병렬 수집 -> GatherSnapshot.

        Capabilities:
            - asyncio.gather()로 모든 도메인(naver, naver_global, fmp 등) 동시 호출
            - 뉴스도 병렬 수집 (최근 7일)
            - 개별 도메인 실패 격리 — 나머지 결과로 스냅샷 생성
            - 10초 타임아웃 (부분 결과 반환)
            - TTL 캐시

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            GatherSnapshot — 도메인별 결과 + 뉴스 + 수집 시각.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — 도메인 실패는 격리, 10초 타임아웃 후 부분 결과.

        Example::

            g = getDefaultGather()
            snap = g.collect("005930")       # 삼성전자 전체 수집
            snap.price                       # PriceSnapshot
            snap.news                        # 뉴스 리스트
        """
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)
        cached = self._cache.getTyped(stockCode, "snapshot")
        if cached is not None:
            return cached  # type: ignore[return-value]

        snapshot = runAsync(self._collectAsync(stockCode, market))
        self._cache.putTyped(stockCode, "snapshot", snapshot)
        return snapshot

    async def _collectAsync(self, stockCode: str, market: str) -> GatherSnapshot:
        """내부 async 수집 — 도메인별 + 보조 데이터 병렬, 10초 타임아웃.

        Parameters
        ----------
        stock_code : str
            종목코드 ("005930") 또는 티커 ("AAPL").
        market : str
            "KR" 또는 "US".

        Returns
        -------
        GatherSnapshot
            stock_code : str — 종목코드.
            results : dict[str, GatherResult] — 도메인별 수집 결과.
            collected_at : str — 수집 시각 (ISO 8601 UTC).
            _news : list[NewsItem] — 최근 7일 뉴스.
            _sectorInfo : SectorInfo | None — 업종 분류.
            _insiderTrades : list[InsiderTrade] — 내부자 거래.
        """
        config = getMarketConfig(market)
        domains = list(dict.fromkeys(config.fallback_chain))  # 순서 유지 중복 제거

        domainTasks = [self._fetchDomainAsync(name, stockCode, market) for name in domains]
        newsTask = _news._fetchAsync(stockCode, market=market, days=7, client=self._client)
        sectorTask = _sector.fetch(stockCode, market=market, client=self._client)
        insiderTask = _insider.fetchInsiderTrading(stockCode, market=market, client=self._client)

        try:
            allResults = await asyncio.wait_for(
                asyncio.gather(
                    *domainTasks,
                    newsTask,
                    sectorTask,
                    insiderTask,
                    return_exceptions=True,
                ),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            log.warning("collect 10초 타임아웃 — 부분 결과 사용")
            allResults = [GatherResult(domain=d, error="timeout") for d in domains] + [[], None, []]

        nDomains = len(domains)
        domainResults = allResults[:nDomains]
        newsResult = allResults[nDomains]
        sectorResult = allResults[nDomains + 1]
        insiderResult = allResults[nDomains + 2]

        results: dict[str, GatherResult] = {}
        for name, raw in zip(domains, domainResults):
            if isinstance(raw, BaseException):
                log.warning("도메인 %s 수집 실패: %s", name, raw)
                results[name] = GatherResult(domain=name, error=str(raw))
            else:
                results[name] = raw

        newsItems: list = []
        if isinstance(newsResult, list):
            newsItems = newsResult

        return GatherSnapshot(
            stockCode=stockCode,
            results=results,
            collected_at=datetime.now(timezone.utc).isoformat(),
            _news=newsItems,
            _sectorInfo=sectorResult if isinstance(sectorResult, SectorInfo) else None,
            _insiderTrades=insiderResult if isinstance(insiderResult, list) else [],
        )

    async def _fetchDomainAsync(self, domainName: str, stockCode: str, market: str) -> GatherResult:
        """단일 도메인에서 모든 데이터 수집 (async).

        Parameters
        ----------
        domain_name : str
            도메인 모듈명 ("naver", "naver_global", "fmp" 등).
        stock_code : str
            종목코드 ("005930") 또는 티커 ("AAPL").
        market : str
            "KR" 또는 "US".

        Returns
        -------
        GatherResult
            domain : str — 도메인명.
            price : PriceSnapshot | None — 현재가 스냅샷.
            flow : FlowData | None — 수급 (fetch_all 도메인만).
            error : str | None — 에러 메시지 (실패 시).
        """
        module = loadDomain(domainName)
        # fetchAll 이 있는 도메인 (naver, naverGlobal)
        if hasattr(module, "fetchAll"):
            if domainName == "naver":
                return await module.fetchAll(stockCode, self._client)
            return await module.fetchAll(stockCode, self._client, market=market)
        # fetchPrice 만 있는 도메인 (naverGlobal, fmp)
        price = None
        if hasattr(module, "fetchPrice"):
            price = await module.fetchPrice(stockCode, self._client, market=market)
        return GatherResult(domain=domainName, price=price)
