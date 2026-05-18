"""core/dataLoader LRU 캐시 폐기 회귀 (Phase D).

이전 buyer 의 LRU memoization 은 Phase D 에서 폐기됨. 본 모듈은 *폐기 후 동작*
검증 — 매 호출 disk 재로드 (BoundedCache + IPC mmap 이 cache 역할 담당).
"""

from __future__ import annotations

from unittest.mock import patch

import polars as pl
import pytest

from dartlab.core.dataLoader import _LOAD_CACHE, _LOAD_CACHE_MAX, _clearLoadCache, loadData
from dartlab.frame import dataLoader

pytestmark = pytest.mark.unit


def _fakeLoadedDataFrame(category: str) -> pl.DataFrame:
    return pl.DataFrame({"year": [2023, 2024], "category": [category, category]})


class TestLoadDataCachePhaseD:
    """Phase D — _LOAD_CACHE 폐기 후 회귀."""

    def test_load_cache_always_empty(self):
        """_LOAD_CACHE 가 store 안 함 — 항상 empty 유지."""
        with (
            patch("dartlab.core.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch("dartlab.core.dataLoader.pl.read_parquet", return_value=_fakeLoadedDataFrame("finance")),
            patch("dartlab.core.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            loadData("005930", "finance")
            loadData("005930", "finance")
            loadData("068270", "docs")
        assert len(_LOAD_CACHE) == 0

    def test_each_call_reloads_from_disk(self):
        """캐시 폐기 → 매 호출 read_parquet 호출."""
        with (
            patch("dartlab.core.dataLoader._ensureLocalParquet", lambda *a, **k: None),
            patch(
                "dartlab.core.dataLoader.pl.read_parquet", return_value=_fakeLoadedDataFrame("finance")
            ) as readParquet,
            patch("dartlab.core.dataLoader._normalizeLoadedFrame", side_effect=lambda df, c: df),
        ):
            loadData("005930", "finance")
            loadData("005930", "finance")
            loadData("005930", "finance")
        assert readParquet.call_count == 3

    def test_clear_load_cache_is_noop(self):
        """_clearLoadCache 는 backward-compat no-op."""
        _clearLoadCache()
        assert len(_LOAD_CACHE) == 0

    def test_module_level_symbols_preserved(self):
        """_LOAD_CACHE / _clearLoadCache / _LOAD_CACHE_MAX backward-compat alias 유지."""
        assert hasattr(dataLoader, "_LOAD_CACHE")
        assert hasattr(dataLoader, "_clearLoadCache")
        assert hasattr(dataLoader, "_LOAD_CACHE_MAX")
        assert dataLoader._LOAD_CACHE_MAX == 0  # 폐기 신호


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
