"""Gather info mixin — 회사 정보 (배당/분할/업종/내부자/지분/피어) 7 메서드."""

from __future__ import annotations

import logging

from ..infra.http import runAsync
from ..sources import insider as _insider
from ..sources import ownership as _ownership
from ..sources import sector as _sector
from ..types import InsiderTrade, InstitutionOwnership, MajorHolder, SectorInfo, SourceUnavailableError

log = logging.getLogger(__name__)


class _GatherInfoMixin:
    """회사 정보 조회 메서드 모음 — Gather 클래스 7 메서드."""

    def dividends(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """배당 이력 조회.

        Capabilities:
            - fallback 체인: naver_global -> FMP
            - 배당일, 배당금, 배당수익률 등
            - circuit breaker 적용
            - TTL 캐시

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[dict] — 배당 이력 (date, dividend 등). 없으면 빈 리스트.

        Requires:
            없음 (공개 API).

        Example::

            g = getDefaultGather()
            g.dividends("005930")              # 삼성전자 배당 이력
            g.dividends("AAPL", market="US")   # Apple 배당 이력
        """
        cache_key = f"{stockCode}:{market}:dividends"
        cached = self._cache.getTyped(cache_key, "dividends")
        if cached is not None:
            return cached  # type: ignore[return-value]
        from ..domains import DIVIDENDS_FALLBACK, loadDomain
        from ..infra.resilience import circuitBreaker as _cb

        for source in DIVIDENDS_FALLBACK:
            if _cb.isOpen(source):
                continue
            try:
                module = loadDomain(source)
                if not hasattr(module, "fetchDividends"):
                    continue
                result = runAsync(module.fetchDividends(stockCode, self._client, market=market))
                if result:
                    _cb.recordSuccess(source)
                    self._cache.putTyped(cache_key, "dividends", result)
                    return result
            except (SourceUnavailableError, ImportError, OSError, AttributeError) as exc:
                _cb.recordFailure(source)
                log.warning("dividends %s 실패 (%s): %s", source, stockCode, exc)
                continue
        return []

    def splits(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """액면분할/병합 이력 조회.

        Capabilities:
            - fallback 체인: naver_global -> FMP
            - 분할일, 분할비율 등
            - circuit breaker 적용
            - TTL 캐시

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[dict] — 분할 이력 (date, ratio 등). 없으면 빈 리스트.

        Requires:
            없음 (공개 API).

        Example::

            g = getDefaultGather()
            g.splits("005930")              # 삼성전자 분할 이력
            g.splits("AAPL", market="US")   # Apple 분할 이력
        """
        cache_key = f"{stockCode}:{market}:splits"
        cached = self._cache.getTyped(cache_key, "splits")
        if cached is not None:
            return cached  # type: ignore[return-value]
        from ..domains import DIVIDENDS_FALLBACK, loadDomain
        from ..infra.resilience import circuitBreaker as _cb

        for source in DIVIDENDS_FALLBACK:
            if _cb.isOpen(source):
                continue
            try:
                module = loadDomain(source)
                if not hasattr(module, "fetchSplits"):
                    continue
                result = runAsync(module.fetchSplits(stockCode, self._client, market=market))
                if result:
                    _cb.recordSuccess(source)
                    self._cache.putTyped(cache_key, "splits", result)
                    return result
            except (SourceUnavailableError, ImportError, OSError, AttributeError) as exc:
                _cb.recordFailure(source)
                log.warning("splits %s 실패 (%s): %s", source, stockCode, exc)
                continue
        return []

    def sector(self, stockCode: str, *, market: str = "KR") -> SectorInfo | None:
        """업종 분류 조회 -- KR(KIND+Naver) / US(Yahoo assetProfile).

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            SectorInfo | None -- 업종코드, 업종명, 시장구분.

        Example::

            g = getDefaultGather()
            g.sector("005930")              # 삼성전자 업종
            g.sector("AAPL", market="US")   # Apple 업종
        """
        cache_key = f"{stockCode}:{market}"
        cached = self._cache.getTyped(cache_key, "sector_info")
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = runAsync(_sector.fetch(stockCode, market=market, client=self._client))
        if result:
            self._cache.putTyped(cache_key, "sector_info", result)
        return result

    def insiderTrading(self, stockCode: str, *, market: str = "KR") -> list[InsiderTrade]:
        """내부자(임원/주요주주) 거래 내역 조회.

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[InsiderTrade] -- 내부자 거래 내역. 없으면 빈 리스트.

        Example::

            g = getDefaultGather()
            g.insiderTrading("005930")              # 삼성전자 임원 거래
            g.insiderTrading("AAPL", market="US")   # Apple 내부자 거래
        """
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)
        cache_key = f"{stockCode}:{market}:insider"
        cached = self._cache.getTyped(cache_key, "insider")
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = runAsync(_insider.fetchInsiderTrading(stockCode, market=market, client=self._client))
        if result:
            self._cache.putTyped(cache_key, "insider", result)
        return result

    def majorShareholders(self, stockCode: str, *, market: str = "KR") -> list[MajorHolder]:
        """5% 이상 대량보유 주주 변동 조회 (KR 전용).

        Args:
            stock_code: 종목코드 ("005930").
            market: "KR"만 지원.

        Returns:
            list[MajorHolder] -- 대량보유 변동 내역. 없으면 빈 리스트.

        Example::

            g = getDefaultGather()
            g.majorShareholders("005930")   # 삼성전자 대량보유
        """
        cache_key = f"{stockCode}:{market}:major_holder"
        cached = self._cache.getTyped(cache_key, "major_holder")
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = runAsync(_insider.fetchMajorShareholders(stockCode, market=market, client=self._client))
        if result:
            self._cache.putTyped(cache_key, "major_holder", result)
        return result

    def ownership(self, stockCode: str, *, market: str = "KR") -> list[InstitutionOwnership]:
        """기관/외국인 지분 보유 조회.

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[InstitutionOwnership] -- 지분 보유 목록.

        Example::

            g = getDefaultGather()
            g.ownership("005930")              # 삼성전자 외국인 보유
            g.ownership("AAPL", market="US")   # Apple 기관 보유
        """
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)
        cache_key = f"{stockCode}:{market}:ownership"
        cached = self._cache.getTyped(cache_key, "ownership")
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = runAsync(_ownership.fetch(stockCode, market=market, client=self._client))
        if result:
            self._cache.putTyped(cache_key, "ownership", result)
        return result

    def industryPeers(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """같은 업종 내 피어 종목 목록 (시총 포함).

        Args:
            stock_code: 종목코드 ("005930").
            market: "KR" 기본.

        Returns:
            list[dict] -- stockCode, stockName, marketCap 등.

        Example::

            g = getDefaultGather()
            g.industryPeers("005930")   # 삼성전자 동종업종
        """
        sectorInfo = self.sector(stockCode, market=market)
        if not sectorInfo or not sectorInfo.industryCode:
            return []
        if market == "KR":
            from ..domains.krx import fetchIndustryPeers

            return runAsync(fetchIndustryPeers(sectorInfo.industryCode, self._client))
        return []
