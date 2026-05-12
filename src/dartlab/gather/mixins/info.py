"""Gather info mixin — 회사 정보 (배당/분할/업종/내부자/지분/피어) 7 메서드."""

from __future__ import annotations

import logging
import time

from ..infra.http import runAsync
from ..infra.telemetry import emitGatherFetch
from ..sources import insider as _insider
from ..sources import ownership as _ownership
from ..sources import sector as _sector
from ..types import InsiderTrade, InstitutionOwnership, MajorHolder, SectorInfo, SourceUnavailableError
from .context import GatherMixinContext

log = logging.getLogger(__name__)


class _GatherInfoMixin(GatherMixinContext):
    """회사 정보 조회 메서드 모음 — Gather 클래스 7 메서드."""

    def dividends(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """배당 이력 조회.

        Capabilities:
            - fallback 체인: naver_global -> FMP
            - 배당일, 배당금, 배당수익률 등
            - circuit breaker 적용
            - TTL 캐시 (DARTLAB_TTL_DIVIDENDS override)

        AIContext:
            - 배당 수익률 + 정책 (안정/감액) 분석

        Guide:
            naver_global → FMP fallback. circuit breaker 가 source 안정성 추적.

        When:
            배당 이력/안정성 분석 필요 시.

        How:
            stockCode + market → fallback chain → list[dict].

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[dict] — 배당 이력 (date, dividend 등). 없으면 빈 리스트.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.dividends("005930")              # 삼성전자 배당 이력
            g.dividends("AAPL", market="US")   # Apple 배당 이력

        See Also:
            ``splits`` — 액면분할/병합 이력 (같은 fallback 패턴).
        """
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}:dividends"
            cached = self._cache.getTyped(cache_key, "dividends")
            if cached is not None:
                cacheHit = True
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
        finally:
            emitGatherFetch("dividends", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def splits(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """액면분할/병합 이력 조회.

        Capabilities:
            - fallback 체인: naver_global -> FMP
            - 분할일, 분할비율 등
            - circuit breaker 적용
            - TTL 캐시 (DARTLAB_TTL_SPLITS override)

        AIContext:
            - 주가 시계열의 split 보정 (price.fetch 가 이미 자동 보정하지만 raw 기록 필요 시)

        Guide:
            naver_global → FMP fallback. dividends 와 같은 체인 패턴.

        When:
            split 이력 확인 / split 보정 검증 필요 시.

        How:
            stockCode + market → fallback chain → list[dict].

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[dict] — 분할 이력 (date, ratio 등). 없으면 빈 리스트.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.splits("005930")              # 삼성전자 분할 이력
            g.splits("AAPL", market="US")   # Apple 분할 이력

        See Also:
            ``dividends`` — 같은 fallback 체인.
            ``dartlab.gather.transforms.adjustPrice`` — split 보정 변환.
        """
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}:splits"
            cached = self._cache.getTyped(cache_key, "splits")
            if cached is not None:
                cacheHit = True
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
        finally:
            emitGatherFetch("splits", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def sector(self, stockCode: str, *, market: str = "KR") -> SectorInfo | None:
        """업종 분류 조회 -- KR(KIND+Naver) / US(Yahoo assetProfile).

        Capabilities:
            - KR: KIND 등록부 + Naver 업종 자동 매핑
            - US: Yahoo assetProfile sectorCode
            - 단일 SectorInfo 객체 (industry/sector 1:1)
            - TTL 캐시 (DARTLAB_TTL_SECTOR override)

        AIContext:
            - 업종 분류 — peer 매칭 / industry 분석의 baseline

        Guide:
            가장 자주 사용 — KIND 캐시 hit 가 보통. 첫 호출만 fetch.

        When:
            "이 종목 업종이 뭐야" / peer scan / industry rotation 분석 시.

        How:
            stockCode + market → fetch → SectorInfo or None.

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            SectorInfo | None -- 업종코드, 업종명, 시장구분.

        Requires:
            네트워크 (KIND/Naver/Yahoo). KIND 캐시 우선.

        Raises:
            없음 — provider 내부 예외는 None 반환으로 흡수.

        Example::

            g = getDefaultGather()
            g.sector("005930")              # 삼성전자 업종
            g.sector("AAPL", market="US")   # Apple 업종

        See Also:
            ``industryPeers`` — 같은 업종 종목 리스트.
            ``dartlab.gather.krx.listing.getKindList`` — KR KIND 등록부.
        """
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}"
            cached = self._cache.getTyped(cache_key, "sector_info")
            if cached is not None:
                cacheHit = True
                return cached  # type: ignore[return-value]
            result = runAsync(_sector.fetch(stockCode, market=market, client=self._client))
            if result:
                self._cache.putTyped(cache_key, "sector_info", result)
            return result
        finally:
            emitGatherFetch("sector", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def insiderTrading(self, stockCode: str, *, market: str = "KR") -> list[InsiderTrade]:
        """내부자(임원/주요주주) 거래 내역 조회.

        Capabilities:
            - KR: DART 임원거래 공시 (DART_API_KEY 필요)
            - US: SEC Form 4 (EDGAR)
            - InsiderTrade dataclass 리스트
            - TTL 캐시 (DARTLAB_TTL_INSIDER)

        AIContext:
            - 내부자 매수/매도 신호 — informed trading 분석

        Guide:
            KR 의 경우 DART_API_KEY 필수. 미설정 시 빈 리스트.

        When:
            informed trading / 경영진 신뢰도 / 매수 시그널 분석 시.

        How:
            stockCode + market → fetchInsiderTrading → InsiderTrade 리스트.

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[InsiderTrade] -- 내부자 거래 내역. 없으면 빈 리스트.

        Requires:
            KR: DART_API_KEY env. US: 없음.

        Raises:
            없음 — provider 내부 예외는 빈 리스트로 흡수.

        Example::

            g = getDefaultGather()
            g.insiderTrading("005930")              # 삼성전자 임원 거래
            g.insiderTrading("AAPL", market="US")   # Apple 내부자 거래

        See Also:
            ``majorShareholders`` — 5% 이상 대량보유 (KR 전용).
        """
        from dartlab.frame.market import resolveMarket

        market = resolveMarket(stockCode, market)
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}:insider"
            cached = self._cache.getTyped(cache_key, "insider")
            if cached is not None:
                cacheHit = True
                return cached  # type: ignore[return-value]
            result = runAsync(_insider.fetchInsiderTrading(stockCode, market=market, client=self._client))
            if result:
                self._cache.putTyped(cache_key, "insider", result)
            return result
        finally:
            emitGatherFetch("insider", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def majorShareholders(self, stockCode: str, *, market: str = "KR") -> list[MajorHolder]:
        """5% 이상 대량보유 주주 변동 조회 (KR 전용).

        Capabilities:
            - DART 5% 보유공시 — 변동 시점 + 보유자 + 비율
            - MajorHolder dataclass 리스트
            - TTL 캐시 (DARTLAB_TTL_MAJOR_HOLDER)

        AIContext:
            - 행동주의 / 적대적 인수 / 지배구조 변동 신호 분석

        Guide:
            KR 만. DART_API_KEY 필수.

        When:
            지배구조 / activist 분석 / 5% 룰 모니터링.

        How:
            stockCode → fetchMajorShareholders → list[MajorHolder].

        Args:
            stock_code: 종목코드 ("005930").
            market: "KR"만 지원.

        Returns:
            list[MajorHolder] -- 대량보유 변동 내역. 없으면 빈 리스트.

        Requires:
            DART_API_KEY env.

        Raises:
            없음 — provider 내부 예외는 빈 리스트로 흡수.

        Example::

            g = getDefaultGather()
            g.majorShareholders("005930")   # 삼성전자 대량보유

        See Also:
            ``ownership`` — 기관/외국인 비율 (시점 스냅샷).
        """
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}:major_holder"
            cached = self._cache.getTyped(cache_key, "major_holder")
            if cached is not None:
                cacheHit = True
                return cached  # type: ignore[return-value]
            result = runAsync(_insider.fetchMajorShareholders(stockCode, market=market, client=self._client))
            if result:
                self._cache.putTyped(cache_key, "major_holder", result)
            return result
        finally:
            emitGatherFetch("majorHolder", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def ownership(self, stockCode: str, *, market: str = "KR") -> list[InstitutionOwnership]:
        """기관/외국인 지분 보유 조회.

        Capabilities:
            - KR: Naver 외국인 비율 + 기관 보유
            - US: Yahoo institutionOwners
            - InstitutionOwnership 리스트
            - TTL 캐시 (DARTLAB_TTL_OWNERSHIP)

        AIContext:
            - 외국인/기관 매수/매도 추적 — sentiment/flow 분석의 누적 형태

        Guide:
            flow() 는 일별 변동, ownership 은 시점 스냅샷 (누적).

        When:
            기관 영향력 평가 / passive vs active 보유 분포 분석 시.

        How:
            stockCode + market → fetch → list[InstitutionOwnership].

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[InstitutionOwnership] -- 지분 보유 목록.

        Requires:
            네트워크 (Naver/Yahoo).

        Raises:
            없음 — provider 내부 예외는 빈 리스트로 흡수.

        Example::

            g = getDefaultGather()
            g.ownership("005930")              # 삼성전자 외국인 보유
            g.ownership("AAPL", market="US")   # Apple 기관 보유

        See Also:
            ``flow`` — 일별 매매 동향.
            ``majorShareholders`` — 5% 이상 변동 (KR DART).
        """
        from dartlab.frame.market import resolveMarket

        market = resolveMarket(stockCode, market)
        t0 = time.monotonic()
        cacheHit = False
        try:
            cache_key = f"{stockCode}:{market}:ownership"
            cached = self._cache.getTyped(cache_key, "ownership")
            if cached is not None:
                cacheHit = True
                return cached  # type: ignore[return-value]
            result = runAsync(_ownership.fetch(stockCode, market=market, client=self._client))
            if result:
                self._cache.putTyped(cache_key, "ownership", result)
            return result
        finally:
            emitGatherFetch("ownership", (time.monotonic() - t0) * 1000, cacheHit=cacheHit, market=market)

    def industryPeers(self, stockCode: str, *, market: str = "KR") -> list[dict]:
        """같은 업종 내 피어 종목 목록 (시총 포함).

        Capabilities:
            - 자기 종목의 sector → 같은 industryCode 종목 리스트
            - 시총 정보 포함 (dict 의 marketCap)
            - KR 만 지원 (KRX 카테고리)

        AIContext:
            - peer-relative 분석 / 동종업종 valuation 비교 baseline

        Guide:
            sector() 가 먼저 실행돼야 함 (의존). industryCode 없으면 빈 리스트.

        When:
            peer 분석 / valuation 비교 / industry rotation 분석 시.

        How:
            sector(stockCode) → industryCode → fetchIndustryPeers → list[dict].

        Args:
            stock_code: 종목코드 ("005930").
            market: "KR" 기본.

        Returns:
            list[dict] -- stockCode, stockName, marketCap 등.

        Requires:
            sector() 가 먼저 정상 결과. KRX 카테고리 데이터.

        Raises:
            없음 — sector 부재 또는 KR 외 시장은 빈 리스트.

        Example::

            g = getDefaultGather()
            g.industryPeers("005930")   # 삼성전자 동종업종

        See Also:
            ``sector`` — peer 의 industryCode 원천.
        """
        t0 = time.monotonic()
        try:
            sectorInfo = self.sector(stockCode, market=market)
            if not sectorInfo or not sectorInfo.industryCode:
                return []
            if market == "KR":
                from ..domains.krx import fetchIndustryPeers

                return runAsync(fetchIndustryPeers(sectorInfo.industryCode, self._client))
            return []
        finally:
            emitGatherFetch("peers", (time.monotonic() - t0) * 1000, cacheHit=False, market=market)
