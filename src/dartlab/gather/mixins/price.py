"""Gather price/flow/history/revenueConsensus mixin — 가격·수급·시계열·컨센서스 6 메서드."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from dartlab.core.polarsUtil import isEmptyDf

from ..infra.http import runAsync
from ..sources import flow as _flow
from ..sources import history as _history
from ..sources import price as _price
from ..types import FlowData, PriceSnapshot, RevenueConsensus, SourceUnavailableError
from .context import GatherMixinContext

log = logging.getLogger(__name__)


class _GatherPriceMixin(GatherMixinContext):
    """가격·수급·히스토리·컨센서스 메서드 모음 — Gather 클래스 6 메서드."""

    def price(
        self,
        stockCode: str,
        *,
        market: str = "KR",
        start: str | None = None,
        end: str | None = None,
        snapshot: bool = False,
    ) -> "pl.DataFrame | PriceSnapshot | None":
        """OHLCV 주가 시계열 조회.

        Capabilities:
            - KR: Naver 금융 (기본 1년)
            - US: Yahoo Finance (기본 1년)
            - OHLCV + 거래량 DataFrame
            - snapshot=True 시 현재가 PriceSnapshot 반환
            - 자동 fallback 체인 (Naver -> Yahoo -> FMP)
            - TTL 캐시 (5분)

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".
            start: 시작일 (YYYY-MM-DD). None이면 1년 전.
            end: 종료일. None이면 오늘.
            snapshot: True면 PriceSnapshot (현재가) 반환.

        Returns:
            pl.DataFrame — date, open, high, low, close, volume 컬럼.
            snapshot=True 시 PriceSnapshot | None.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.price("005930")                    # 삼성전자 1년
            g.price("AAPL", market="US")         # Apple 1년
            g.price("005930", snapshot=True)     # 현재가 스냅샷
        """
        # market 자동 감지 (core SSOT)
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)

        if snapshot:
            return self._priceSnapshot(stockCode, market=market)
        from datetime import date, timedelta

        if start is None:
            end = end or date.today().isoformat()
            start = (date.today() - timedelta(days=365)).isoformat()
        elif end is None:
            end = date.today().isoformat()
        return self.history(stockCode, start=start, end=end, market=market)

    def _priceSnapshot(self, stockCode: str, *, market: str = "KR") -> PriceSnapshot | None:
        """현재가 스냅샷 — naver → naver_global fallback.

        Parameters
        ----------
        stock_code : str
            종목코드 ("005930") 또는 티커 ("AAPL").
        market : str
            "KR" 또는 "US". 기본 "KR".

        Returns
        -------
        PriceSnapshot | None
            price : float — 현재가 (원 또는 USD).
            change : float — 전일 대비 변동 (원 또는 USD).
            changePercent : float — 전일 대비 변동률 (%).
            volume : int — 거래량 (주).
            None — 데이터 수집 실패 시.
        """
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)
        cached = self._cache.getTyped(stockCode, "price")
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = runAsync(_price.fetch(stockCode, market=market, client=self._client))
        if result:
            self._cache.putTyped(stockCode, "price", result)
        return result

    def flow(self, stockCode: str, *, market: str = "KR") -> "pl.DataFrame | None":
        """투자자별 수급 시계열 조회 (KR 전용).

        Capabilities:
            - KR 전용 (Naver 금융)
            - 외국인/기관/개인 순매수 + 외국인 보유비율
            - 일별 시계열 DataFrame
            - TTL 캐시

        Args:
            stock_code: 종목코드 ("005930").
            market: "KR"만 지원. "US"이면 None 반환.

        Returns:
            pl.DataFrame | None — date, foreignNet, institutionNet,
            individualNet, foreignHoldingRatio 컬럼. KR 외 None.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.flow("005930")   # 삼성전자 수급 시계열
        """
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)
        import polars as pl

        if market != "KR":
            return None
        cache_key = f"{stockCode}:flow_series"
        cached = self._cache.getTyped(cache_key, "flow")
        if cached is not None:
            return cached  # type: ignore[return-value]
        raw = runAsync(_flow.fetch(stockCode, market=market, client=self._client))
        if not raw:
            return None
        df = pl.DataFrame(raw)
        if "date" in df.columns and df["date"].dtype == pl.Utf8:
            df = df.with_columns(pl.col("date").str.to_date("%Y%m%d").alias("date"))
        self._cache.putTyped(cache_key, "flow", df)
        return df

    def _flowSnapshot(self, stockCode: str, *, market: str = "KR") -> FlowData | None:
        """수급 스냅샷 — flow() 시계열의 최신 행을 FlowData로 변환 (GatherSnapshot 내부용).

        Parameters
        ----------
        stock_code : str
            종목코드 ("005930").
        market : str
            "KR"만 지원. "US"이면 None 반환.

        Returns
        -------
        FlowData | None
            foreign_net : float — 외국인 순매수 (주).
            institution_net : float — 기관 순매수 (주).
            foreign_holding_ratio : float — 외국인 보유비율 (%).
            source : str — 데이터 출처 ("naver").
            None — KR 외 시장이거나 데이터 없을 때.
        """
        df = self.flow(stockCode, market=market)
        if isEmptyDf(df):
            return None
        row = df.row(0, named=True)
        return FlowData(
            foreign_net=row.get("foreignNet") or 0.0,
            institution_net=row.get("institutionNet") or 0.0,
            foreign_holding_ratio=row.get("foreignHoldingRatio") or 0.0,
            source="naver",
        )

    def revenueConsensus(
        self,
        stockCode: str,
        *,
        market: str = "KR",
    ) -> list[RevenueConsensus]:
        """매출/이익 컨센서스 (연간 추정치) 조회.

        Capabilities:
            - KR: 네이버 금융 (연간 매출/영업이익/순이익 추정)
            - US: Yahoo Finance quoteSummary
            - 연도별 RevenueConsensus 리스트
            - TTL 캐시

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            list[RevenueConsensus] — 연도별 매출/이익 추정치. 실패 시 빈 리스트.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.revenue_consensus("005930")              # 삼성전자
            g.revenue_consensus("AAPL", market="US")   # Apple
        """
        from ..domains import loadDomain

        cache_key = f"{stockCode}_{market}"
        cached = self._cache.getTyped(cache_key, "revenue_consensus")
        if cached is not None:
            return cached  # type: ignore[return-value]
        try:
            if market == "KR":
                module = loadDomain("naver")
                result = runAsync(module.fetchRevenueConsensus(stockCode, self._client))
            else:
                # US/글로벌: revenue consensus 소스 없음 (네이버 KR 전용)
                result = []
        except (SourceUnavailableError, ImportError, OSError, AttributeError) as exc:
            log.warning("revenue_consensus 실패 (%s, %s): %s", stockCode, market, exc)
            result = []
        if result:
            self._cache.putTyped(cache_key, "revenue_consensus", result)
        return result

    def history(
        self,
        stockCode: str,
        *,
        start: str,
        end: str,
        market: str = "KR",
    ) -> "pl.DataFrame":
        """OHLCV 히스토리 DataFrame 조회 (기간 지정).

        Capabilities:
            - fallback 체인: Naver(KR) -> naver_global -> FMP -> Yahoo
            - date, open, high, low, close, volume 컬럼
            - 자동 날짜 파싱 (문자열 -> pl.Date)
            - TTL 캐시 (TTL_HISTORY)

        Args:
            stock_code: 종목코드 ("005930") 또는 티커 ("AAPL").
            start: 시작일 (YYYY-MM-DD). 필수.
            end: 종료일 (YYYY-MM-DD). 필수.
            market: "KR" 또는 "US". 기본 "KR".

        Returns:
            pl.DataFrame — date, open, high, low, close, volume 컬럼.
            데이터 없으면 빈 DataFrame.

        Requires:
            없음 (공개 API).

        Raises:
            없음 — fallback 체인 내부 예외는 흡수.

        Example::

            g = getDefaultGather()
            g.history("005930", start="2025-01-01", end="2025-12-31")
            g.history("AAPL", start="2025-06-01", end="2025-12-31", market="US")
        """
        # market 자동 감지 (core SSOT)
        from dartlab.core.market import resolveMarket

        market = resolveMarket(stockCode, market)

        import polars as pl

        cache_key = f"{stockCode}:history:{start}:{end}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        raw = runAsync(
            _history.fetch(
                stockCode,
                start=start,
                end=end,
                market=market,
                client=self._client,
            )
        )
        if not raw:
            return pl.DataFrame()
        df = pl.DataFrame(raw)
        if "date" in df.columns and df["date"].dtype == pl.Utf8:
            df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d").alias("date"))
        from ..infra.cache import TTL_HISTORY

        self._cache.put(cache_key, df, TTL_HISTORY)
        return df
