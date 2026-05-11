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
        self, stockCode: str, *, market: str = "KR", start: str | None = None, end: str | None = None
    ) -> pl.DataFrame | None:
        """OHLCV 스냅샷 fetch."""
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        try:
            return g("price", stockCode, market=market, start=start, end=end)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchMacroSeries(self, seriesId: str, *, source: str = "fred", start: str | None = None) -> pl.DataFrame | None:
        """단일 macro 시계열 fetch."""
        from dartlab.gather.entry import GatherEntry

        g = GatherEntry()
        try:
            return g("macro", seriesId, source=source, start=start)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchExogenousAxes(self, stockCode: str) -> list[tuple[str, str]]:
        """종목별 매크로 축 매핑."""
        try:
            from dartlab.gather.exogenousAxes import getExogenousAxes
        except ImportError:
            return []
        try:
            return getExogenousAxes(stockCode) or []
        except (ValueError, RuntimeError, KeyError):
            return []

    def fetchAlignedMacro(self, stockCode: str, periods: list[str]) -> pl.DataFrame | None:
        """period 기준 정렬된 매크로 패널."""
        try:
            from dartlab.gather.macro import loadMacroParquet
        except ImportError:
            return None
        try:
            return loadMacroParquet(stockCode=stockCode, periods=periods)
        except (ValueError, RuntimeError, KeyError):
            return None

    def lookupCompany(self, stockCode: str) -> CompanyProtocol | None:
        """종목코드 → Company. 실패 시 None."""
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

    def fetchOhlcv(self, stockCode: str, *, market: str = "KR", start: str | None = None) -> pl.DataFrame | None:
        """단일 종목 OHLCV."""
        from dartlab.quant.screen.dataAccess import fetchOhlcv

        return fetchOhlcv(stockCode, market=market, start=start)

    def fetchBenchmarkOhlcv(
        self, stockCode: str, *, market: str = "KR", benchmark: str | None = None
    ) -> tuple[pl.DataFrame | None, dict | None]:
        """벤치마크 OHLCV + meta."""
        from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

        try:
            res = fetchBenchmarkOhlcv(stockCode, market=market, benchmark=benchmark, returnMeta=True)
            if isinstance(res, tuple):
                return res[0], res[1]
            return res, None
        except (ValueError, RuntimeError, KeyError):
            return None, None

    def fetchUniverseBulk(self, stockCodes: list[str], *, columns: list[str]) -> pl.DataFrame | None:
        """다종목 bulk 패널."""
        try:
            from dartlab.gather.bulkData.hfBulk import loadFiltered
        except ImportError:
            return None
        try:
            return loadFiltered(stockCodes=stockCodes, columns=columns)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchTechnicalIndicators(self, stockCode: str, indicators: list[str]) -> dict[str, pl.DataFrame]:
        """지표 번들 — gather.indicators 의 함수 시리즈 호출."""
        try:
            from dartlab.core import indicators as ind
        except ImportError:
            return {}
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

    def fetchListing(self, *, market: str = "KR") -> pl.DataFrame | None:
        """전종목 listing snapshot — KRX 기준 (short_code/marketCode/marketEngName 컬럼)."""
        try:
            from dartlab.gather.listing import getKrxList
        except ImportError:
            return None
        try:
            return getKrxList()
        except (ValueError, RuntimeError, KeyError, TypeError):
            return None

    def fetchScanProfitability(self) -> pl.DataFrame | None:
        """scan profitability parquet."""
        try:
            from dartlab.scan.parquetLoad import scanFinanceParquets
        except ImportError:
            return None
        try:
            lf = scanFinanceParquets("profitability")
            if lf is None:
                return None
            return lf.collect()
        except (ValueError, RuntimeError, KeyError, AttributeError):
            return None

    def fetchScanFinanceParquet(self, name: str = "finance") -> pl.DataFrame | None:
        """scan finance parquet."""
        try:
            from dartlab.scan.parquetLoad import scanFinanceParquets
        except ImportError:
            return None
        try:
            lf = scanFinanceParquets(name)
            if lf is None:
                return None
            return lf.collect()
        except (ValueError, RuntimeError, KeyError, AttributeError):
            return None
