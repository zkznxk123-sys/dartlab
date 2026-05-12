"""Default Accessor 구현 — F3 Protocol DIP 의 gather 측 구현체.

L2 (analysis/quant/industry) 가 직접 gather 모듈을 import 하지 않도록,
core.protocols 의 4 Protocol 의 default 구현을 한 곳에 모아 둔다. caller
(story/Company) 가 `getXxxAccessor()` 로 인스턴스를 받아 L2 함수에 전달.

정공법 B (Protocol DIP): L2 ↔ gather 직접 의존 차단.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from dartlab.core.protocols import CompanyProtocol


class DefaultFinanceAccessor:
    """FinanceDataAccessor 기본 구현 — gather/price + gather/macro + gather/exogenousAxes."""

    def fetchPriceSnapshot(
        self,
        stockCode: str,
        *,
        market: str = "KR",
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """OHLCV 스냅샷 fetch — gather("price") 위임.

        Args:
            stockCode: 종목코드/티커.
            market: 시장 코드 (기본 ``"KR"``).
            start: 시작일 (YYYY-MM-DD). None이면 자동.
            end: 종료일. None이면 자동.
            limit: 반환 행수 상한 (가장 위 N). None이면 전체.

        Returns:
            OHLCV DataFrame. fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultFinanceAccessor()
            >>> df = a.fetchPriceSnapshot("005930", market="KR", limit=10)
        """
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        try:
            df = g("price", stockCode, market=market, start=start, end=end)
            if df is not None and limit is not None and limit > 0 and hasattr(df, "head"):
                return df.head(limit)
            return df
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchMacroSeries(
        self,
        seriesId: str,
        *,
        source: str = "fred",
        start: str | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """단일 macro 시계열 fetch — gather("macro") 위임.

        Args:
            seriesId: macro 시리즈 ID (예: "GDP", "UNRATE").
            source: 데이터 소스 (``"fred"`` | ``"ecos"``). 기본 ``"fred"``.
            start: 시작일. None이면 자동.
            limit: 반환 행수 상한 (가장 최근 N). None이면 전체.

        Returns:
            ``(date, value)`` DataFrame. fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultFinanceAccessor()
            >>> gdp = a.fetchMacroSeries("GDP", source="fred", limit=50)
        """
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        try:
            df = g("macro", seriesId, source=source, start=start)
            if df is not None and limit is not None and limit > 0 and hasattr(df, "tail"):
                return df.tail(limit)
            return df
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchExogenousAxes(self, stockCode: str, *, limit: int | None = None) -> list[tuple[str, str]]:
        """종목별 매크로 축 매핑 — gather.mapping.exogenousAxes 위임.

        Args:
            stockCode: 종목코드.
            limit: 반환 항목 상한. None이면 전체.

        Returns:
            ``[(seriesId, source), ...]`` 리스트. 매핑 없거나 실패 시 빈 리스트.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultFinanceAccessor()
            >>> axes = a.fetchExogenousAxes("005930", limit=5)
        """
        try:
            from dartlab.gather.mapping.exogenousAxes import getExogenousAxes
        except ImportError:
            return []
        try:
            result = getExogenousAxes(stockCode) or []
            if limit is not None and limit > 0:
                return result[:limit]
            return result
        except (ValueError, RuntimeError, KeyError):
            return []

    def fetchAlignedMacro(
        self,
        stockCode: str,
        periods: list[str],
        *,
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """period 기준 정렬된 매크로 패널 — transforms.macro.loadMacroParquet 위임.

        Args:
            stockCode: 종목코드.
            periods: 정렬 대상 period 리스트.
            limit: 반환 행수 상한 (가장 최근 N). None이면 전체.

        Returns:
            패널 DataFrame. parquet 없거나 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultFinanceAccessor()
            >>> panel = a.fetchAlignedMacro("005930", ["2024Q1", "2024Q2"], limit=10)
        """
        try:
            from dartlab.gather.transforms.macro import loadMacroParquet
        except ImportError:
            return None
        try:
            df = loadMacroParquet(stockCode=stockCode, periods=periods)
            if df is not None and limit is not None and limit > 0 and hasattr(df, "tail"):
                return df.tail(limit)
            return df
        except (ValueError, RuntimeError, KeyError):
            return None

    def lookupCompany(self, stockCode: str) -> CompanyProtocol | None:
        """종목코드 → Company.

        Args:
            stockCode: 종목코드/티커.

        Returns:
            Company 인스턴스. dartlab.company import 실패 또는 생성 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultFinanceAccessor()
            >>> c = a.lookupCompany("005930")
        """
        try:
            from dartlab.company import Company
        except ImportError:
            return None
        try:
            return Company(stockCode)
        except (ValueError, RuntimeError, KeyError):
            return None


class DefaultQuantAccessor:
    """QuantDataAccessor 기본 구현."""

    def fetchOhlcv(
        self,
        stockCode: str,
        *,
        market: str = "KR",
        start: str | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """단일 종목 OHLCV — quant.screen.dataAccess.fetchOhlcv 위임.

        Args:
            stockCode: 종목코드/티커.
            market: 시장 코드 (기본 ``"KR"``).
            start: 시작일. None이면 자동.
            limit: 반환 행수 상한 (가장 최근 N일). None이면 전체.

        Returns:
            OHLCV DataFrame. fetch 실패 시 None.

        Raises:
            없음 — 위임 함수의 예외는 호출자가 처리.

        Example:
            >>> a = DefaultQuantAccessor()
            >>> df = a.fetchOhlcv("005930", market="KR", limit=20)
        """
        from dartlab.quant.screen.dataAccess import fetchOhlcv

        df = fetchOhlcv(stockCode, market=market, start=start)
        if df is not None and limit is not None and limit > 0 and hasattr(df, "tail"):
            return df.tail(limit)
        return df

    def fetchBenchmarkOhlcv(
        self,
        stockCode: str,
        *,
        market: str = "KR",
        benchmark: str | None = None,
        limit: int | None = None,
    ) -> tuple[pl.DataFrame | None, dict | None]:
        """벤치마크 OHLCV + meta — quant.benchmark.data.fetchBenchmarkOhlcv 위임.

        Args:
            stockCode: 종목코드/티커.
            market: 시장 코드 (기본 ``"KR"``).
            benchmark: 벤치마크 ID. None이면 시장별 기본.
            limit: 반환 행수 상한 (가장 최근 N일). None이면 전체.

        Returns:
            ``(ohlcv_df | None, meta | None)`` 튜플. fetch 실패 시 ``(None, None)``.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultQuantAccessor()
            >>> df, meta = a.fetchBenchmarkOhlcv("005930", limit=10)
        """
        from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

        try:
            res = fetchBenchmarkOhlcv(stockCode, market=market, benchmark=benchmark, returnMeta=True)
            if isinstance(res, tuple):
                df, meta = res[0], res[1]
            else:
                df, meta = res, None
            if df is not None and limit is not None and limit > 0 and hasattr(df, "tail"):
                df = df.tail(limit)
            return df, meta
        except (ValueError, RuntimeError, KeyError):
            return None, None

    def fetchUniverseBulk(
        self,
        stockCodes: list[str],
        *,
        columns: list[str],
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """다종목 bulk 패널 — bulkData.hfBulk.loadFiltered 위임.

        Args:
            stockCodes: 대상 종목코드 리스트.
            columns: 추출 컬럼 리스트.
            limit: 반환 행수 상한 (가장 위 N). None이면 전체.

        Returns:
            bulk 패널 DataFrame. fetch 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> a = DefaultQuantAccessor()
            >>> df = a.fetchUniverseBulk(["005930", "000660"], columns=["close"], limit=100)
        """
        try:
            from dartlab.gather.bulkData.hfBulk import loadFiltered
        except ImportError:
            return None
        try:
            df = loadFiltered(stockCodes=stockCodes, columns=columns)
            if df is not None and limit is not None and limit > 0 and hasattr(df, "head"):
                return df.head(limit)
            return df
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchTechnicalIndicators(
        self,
        stockCode: str,
        indicators: list[str],
        *,
        limit: int | None = None,
    ) -> dict[str, pl.DataFrame]:
        """지표 번들 — gather.indicators 의 함수 시리즈 호출.

        Args:
            stockCode: 종목코드/티커.
            indicators: 호출할 지표 이름 리스트 (예: ``["rsi14", "ma20"]``).
            limit: 반환 지표 개수 상한 (앞쪽 N). None이면 전체.

        Returns:
            ``{indicatorName: DataFrame}`` 딕셔너리. 위임 import 실패 시 빈 딕셔너리.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError/TypeError 는 내부에서 흡수.

        Example:
            >>> a = DefaultQuantAccessor()
            >>> out = a.fetchTechnicalIndicators("005930", ["rsi14"], limit=1)
        """
        try:
            from dartlab.core import indicators as ind
        except ImportError:
            return {}
        if limit is not None and limit > 0:
            indicators = indicators[:limit]
        out: dict[str, Any] = {}
        for name in indicators:
            fn = getattr(ind, name, None)
            if callable(fn):
                try:
                    out[name] = fn(stockCode)
                except (ValueError, RuntimeError, KeyError, TypeError):
                    pass
        return out


class DefaultIndustryAccessor:
    """IndustryDataAccessor 기본 구현."""

    def fetchListing(self, *, market: str = "KR", limit: int | None = None) -> pl.DataFrame | None:
        """전종목 listing snapshot — KRX 기준 (short_code/marketCode/marketEngName 컬럼).

        Args:
            market: 시장 코드 (현재 ``"KR"`` 만 지원).
            limit: 반환 행수 상한 (가장 위 N). None이면 전체.

        Returns:
            전종목 listing DataFrame. import 실패 또는 fetch 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError/TypeError 는 내부에서 흡수.

        Example:
            >>> a = DefaultIndustryAccessor()
            >>> df = a.fetchListing(market="KR", limit=20)
        """
        try:
            from dartlab.gather.krx.listing import getKrxList
        except ImportError:
            return None
        try:
            df = getKrxList()
            if df is not None and limit is not None and limit > 0 and hasattr(df, "head"):
                return df.head(limit)
            return df
        except (ValueError, RuntimeError, KeyError, TypeError):
            return None

    def fetchScanProfitability(self, *, limit: int | None = None) -> pl.DataFrame | None:
        """scan profitability parquet — scan.parquetLoad 위임.

        Args:
            limit: 반환 행수 상한. None이면 전체 collect.

        Returns:
            수익성 parquet 의 collect DataFrame. import/scan 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError/AttributeError 는 내부에서 흡수.

        Example:
            >>> a = DefaultIndustryAccessor()
            >>> df = a.fetchScanProfitability(limit=100)
        """
        try:
            from dartlab.scan.parquetLoad import scanFinanceParquets
        except ImportError:
            return None
        try:
            lf = scanFinanceParquets("profitability")
            if lf is None:
                return None
            if limit is not None and limit > 0:
                return lf.head(limit).collect(engine="streaming")
            return lf.collect(engine="streaming")
        except (ValueError, RuntimeError, KeyError, AttributeError):
            return None

    def fetchScanFinanceParquet(self, name: str = "finance", *, limit: int | None = None) -> pl.DataFrame | None:
        """scan finance parquet — scan.parquetLoad 위임.

        Args:
            name: parquet 카테고리 이름 (기본 ``"finance"``).
            limit: 반환 행수 상한. None이면 전체 collect.

        Returns:
            카테고리 parquet 의 collect DataFrame. import/scan 실패 시 None.

        Raises:
            없음 — ImportError/ValueError/RuntimeError/KeyError/AttributeError 는 내부에서 흡수.

        Example:
            >>> a = DefaultIndustryAccessor()
            >>> df = a.fetchScanFinanceParquet("finance", limit=100)
        """
        try:
            from dartlab.scan.parquetLoad import scanFinanceParquets
        except ImportError:
            return None
        try:
            lf = scanFinanceParquets(name)
            if lf is None:
                return None
            if limit is not None and limit > 0:
                return lf.head(limit).collect(engine="streaming")
            return lf.collect(engine="streaming")
        except (ValueError, RuntimeError, KeyError, AttributeError):
            return None
