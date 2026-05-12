"""core/dataLoader LRU 캐시 단위 테스트.

Part 5 commit 1 — loadData 함수 레벨 memoization 회귀 보호.
"""

from __future__ import annotations

from unittest.mock import patch

import polars as pl
import pytest

from dartlab.frame import dataLoader
from dartlab.frame.dataLoader import _LOAD_CACHE, _LOAD_CACHE_MAX, _clearLoadCache, loadData

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _resetCache():
    """각 테스트 전후 LRU 초기화."""
    _LOAD_CACHE.clear()
    yield
    _LOAD_CACHE.clear()


def _fakeLoadedDataFrame(category: str) -> pl.DataFrame:
    return pl.DataFrame({"year": [2023, 2024], "category": [category, category]})


class TestLoadDataCache:
    def test_second_call_returns_cached_dataframe(self):
        """같은 (stockCode, category) 재호출 시 pl.read_parquet 1회만 실행."""
        with (
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch(
                "dartlab.frame.dataLoader.pl.read_parquet", return_value=_fakeLoadedDataFrame("finance")
            ) as readParquet,
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            a = loadData("005930", "finance")
            b = loadData("005930", "finance")
        assert readParquet.call_count == 1
        assert a is b

    def test_different_keys_cache_separately(self):
        """stockCode 또는 category 가 다르면 별도 캐시 엔트리."""
        with (
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch("dartlab.frame.dataLoader.pl.read_parquet", side_effect=lambda p: _fakeLoadedDataFrame(str(p))),
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            loadData("005930", "finance")
            loadData("005930", "docs")
            loadData("068270", "finance")
        assert len(_LOAD_CACHE) == 3

    def test_refresh_force_bypasses_cache(self):
        """refresh="force" 는 LRU 를 우회하고 재로드."""
        with (
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch(
                "dartlab.frame.dataLoader.pl.read_parquet", return_value=_fakeLoadedDataFrame("finance")
            ) as readParquet,
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            loadData("005930", "finance")
            loadData("005930", "finance", refresh="force")
        assert readParquet.call_count == 2

    def test_krx_auto_bypasses_memory_cache_when_freshness_expired(self):
        """KRX daily 데이터는 TTL 만료 시 프로세스 LRU보다 HF freshness를 우선한다."""
        with (
            patch("dartlab.frame.dataLoader._shouldRefreshHfCategory", side_effect=[False, True]) as shouldRefresh,
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch(
                "dartlab.frame.dataLoader.pl.read_parquet", side_effect=lambda p: _fakeLoadedDataFrame(str(p))
            ) as readParquet,
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            first = loadData("raw-2026", "krxPrices")
            second = loadData("raw-2026", "krxPrices")

        assert shouldRefresh.call_count == 2
        assert readParquet.call_count == 2
        assert first is not second

    def test_clear_cache_empties_store(self):
        """_clearLoadCache 가 LRU 를 완전히 비운다."""
        with (
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch("dartlab.frame.dataLoader.pl.read_parquet", return_value=_fakeLoadedDataFrame("finance")),
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            loadData("005930", "finance")
            loadData("068270", "finance")
        assert len(_LOAD_CACHE) == 2
        _clearLoadCache()
        assert len(_LOAD_CACHE) == 0

    def test_lru_evicts_oldest_when_over_max(self):
        """_LOAD_CACHE_MAX 초과 시 가장 오래된 엔트리 evict."""
        # MAX 보다 2 많은 엔트리 삽입
        with (
            patch("dartlab.frame.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch("dartlab.frame.dataLoader.pl.read_parquet", side_effect=lambda p: _fakeLoadedDataFrame(str(p))),
            patch("dartlab.frame.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            for i in range(_LOAD_CACHE_MAX + 2):
                loadData(f"{i:06d}", "finance")
        assert len(_LOAD_CACHE) == _LOAD_CACHE_MAX

    def test_module_level_symbols_exported(self):
        """_LOAD_CACHE / _clearLoadCache / _LOAD_CACHE_MAX public 참조 가능."""
        assert hasattr(dataLoader, "_LOAD_CACHE")
        assert hasattr(dataLoader, "_clearLoadCache")
        assert hasattr(dataLoader, "_LOAD_CACHE_MAX")


class TestWarmupFinanceAccessors:
    def test_warmup_populates_cache_keys(self):
        """_warmupFinanceAccessors 가 _financeStmt_*_Q_consolidated key 를 미리 채운다."""
        from unittest.mock import MagicMock

        from dartlab.analysis.financial import _warmupFinanceAccessors

        company = MagicMock()
        cache = {}
        company._cache = cache

        def fakeStmt(sjDiv: str, *, freq: str = "Q", scope: str = "consolidated"):
            cache[f"_financeStmt_{sjDiv}_{freq}_{scope}"] = f"df_{sjDiv}"
            return cache[f"_financeStmt_{sjDiv}_{freq}_{scope}"]

        company._financeStmt = fakeStmt
        _warmupFinanceAccessors(company)
        assert set(cache.keys()) == {
            "_financeStmt_IS_Q_consolidated",
            "_financeStmt_BS_Q_consolidated",
            "_financeStmt_CF_Q_consolidated",
        }

    def test_warmup_tolerates_missing_attribute(self):
        """_financeStmt 없는 company 에 대해 조용히 통과 (EDGAR/비정상 객체)."""
        from dartlab.analysis.financial import _warmupFinanceAccessors

        class _Bare:
            pass

        _warmupFinanceAccessors(_Bare())  # 예외 없이 반환

    def test_warmup_tolerates_calc_exceptions(self):
        """_financeStmt 가 KeyError/ValueError 던져도 warm-up 은 통과 (금융업 CF 부재 등)."""
        from unittest.mock import MagicMock

        from dartlab.analysis.financial import _warmupFinanceAccessors

        company = MagicMock()
        company._cache = {}

        def raising(*a, **k):
            raise KeyError("CF missing")

        company._financeStmt = raising
        _warmupFinanceAccessors(company)  # 예외 없이 반환
