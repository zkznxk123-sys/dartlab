"""quant.scanBacktest top-level helper 단위 테스트.

multi_asset_backtest 호출은 mock 하지 않고 실제 합성 OHLCV 시계열로 통합 검증.
fetchOhlcv 만 monkeypatch.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


# ── helpers ──


def _trending_close(n: int = 250, drift: float = 0.0008, vol: float = 0.005, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    log_ret = drift + vol * rng.standard_normal(n - 1)
    return 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(log_ret)]))


def _make_ohlcv_df(close: np.ndarray) -> pl.DataFrame:
    n = len(close)
    base = date(2024, 1, 2)
    dates = [base + timedelta(days=i) for i in range(n)]
    return pl.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1_000_000, dtype=np.float64),
        }
    )


@pytest.fixture
def patch_ohlcv(monkeypatch):
    """종목별 OHLCV 를 합성 시계열로 대체."""

    def _patcher(seeds_per_code: dict[str, int] | None = None):
        import importlib

        _helpers = importlib.import_module("dartlab.quant._helpers")
        _backtest = importlib.import_module("dartlab.quant.strategy.backtest")
        _scan_bt = importlib.import_module("dartlab.quant.scanBacktest")

        seeds_per_code = seeds_per_code or {}

        def _fake_fetch(code, **kwargs):
            seed = seeds_per_code.get(code, hash(code) % 1000)
            close = _trending_close(n=250, seed=seed)
            return _make_ohlcv_df(close)

        # 두 위치에서 fetchOhlcv 를 사용 (multi_asset_backtest + scanBacktest)
        monkeypatch.setattr(_helpers, "fetchOhlcv", _fake_fetch)
        monkeypatch.setattr(_backtest, "fetchOhlcv", _fake_fetch, raising=False)
        monkeypatch.setattr(_scan_bt, "fetchOhlcv", _fake_fetch, raising=False)

    return _patcher


def _make_scan_result(codes: list[str], extra_cols: dict[str, list] | None = None) -> pl.DataFrame:
    data = {"stockCode": codes}
    if extra_cols:
        data.update(extra_cols)
    return pl.DataFrame(data)


# ═══════════════════════════════════════════════════════════
# universe 컬럼 자동 감지
# ═══════════════════════════════════════════════════════════


class TestUniverseDetection:
    def test_detect_stockcode(self):
        from dartlab.quant.scanBacktest import _detectStockCodeColumn

        df = pl.DataFrame({"stockCode": ["005930"], "score": [1.0]})
        assert _detectStockCodeColumn(df) == "stockCode"

    def test_detect_korean_column(self):
        from dartlab.quant.scanBacktest import _detectStockCodeColumn

        df = pl.DataFrame({"종목코드": ["005930"], "score": [1.0]})
        assert _detectStockCodeColumn(df) == "종목코드"

    def test_detect_snake_case(self):
        from dartlab.quant.scanBacktest import _detectStockCodeColumn

        df = pl.DataFrame({"stock_code": ["005930"], "score": [1.0]})
        assert _detectStockCodeColumn(df) == "stock_code"

    def test_no_match_returns_none(self):
        from dartlab.quant.scanBacktest import _detectStockCodeColumn

        df = pl.DataFrame({"foo": ["bar"]})
        assert _detectStockCodeColumn(df) is None


# ═══════════════════════════════════════════════════════════
# scan result hash
# ═══════════════════════════════════════════════════════════


class TestHash:
    def test_deterministic(self):
        from dartlab.quant.scanBacktest import _hashScanResult

        df1 = pl.DataFrame({"stockCode": ["005930", "000660"], "score": [1.0, 2.0]})
        df2 = pl.DataFrame({"stockCode": ["005930", "000660"], "score": [1.0, 2.0]})
        assert _hashScanResult(df1, 5) == _hashScanResult(df2, 5)

    def test_different_universe_different_hash(self):
        from dartlab.quant.scanBacktest import _hashScanResult

        df1 = pl.DataFrame({"stockCode": ["005930", "000660"]})
        df2 = pl.DataFrame({"stockCode": ["005930", "035420"]})
        assert _hashScanResult(df1, 5) != _hashScanResult(df2, 5)

    def test_empty(self):
        from dartlab.quant.scanBacktest import _hashScanResult

        assert _hashScanResult(pl.DataFrame(), 5) == "empty"


# ═══════════════════════════════════════════════════════════
# 메인 진입점
# ═══════════════════════════════════════════════════════════


class TestRunScanBacktest:
    def test_empty_scan_result_returns_error(self):
        from dartlab.quant.scanBacktest import runScanBacktest

        bt = runScanBacktest(pl.DataFrame(), style="trendFollow")
        assert bt.status == "error"
        assert "empty" in (bt.reason or "")

    def test_missing_signal_and_style_returns_error(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv()
        scan = _make_scan_result(["005930", "000660"])
        bt = runScanBacktest(scan)
        assert bt.status == "error"

    def test_missing_universe_column_returns_error(self):
        from dartlab.quant.scanBacktest import runScanBacktest

        bt = runScanBacktest(pl.DataFrame({"foo": [1, 2]}), style="trendFollow")
        assert bt.status == "error"
        assert "universe" in (bt.reason or "")

    def test_unknown_style_raises(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv()
        scan = _make_scan_result(["005930", "000660"])
        with pytest.raises(KeyError, match="미등록"):
            runScanBacktest(scan, style="unknownStyle")

    def test_signalfn_path(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv({"005930": 1, "000660": 2, "035420": 3})

        def momentum_signal(close):
            # 단순: SMA10 > SMA50 일 때 long
            sma10 = np.convolve(close, np.ones(10) / 10, mode="same")
            sma50 = np.convolve(close, np.ones(50) / 50, mode="same")
            return sma10 > sma50

        scan = _make_scan_result(["005930", "000660", "035420"])
        bt = runScanBacktest(scan, signalFn=momentum_signal, topN=3)
        # 합성 데이터에서는 ok 또는 데이터 부족 모두 가능. status 확인만.
        assert bt.scanContext is not None
        assert bt.scanContext["signalSource"] == "signalFn"
        assert bt.scanContext["universeSize"] == 3
        assert bt.scanContext["weighting"] == "equal"
        assert bt.scanContext["scanResultHash"] != "empty"

    def test_korean_column_universe(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv({"005930": 4, "000660": 5})
        scan = pl.DataFrame({"종목코드": ["005930", "000660"], "PER": [10.0, 12.0]})
        bt = runScanBacktest(scan, style="trendFollow", topN=2)
        assert bt.scanContext is not None
        assert bt.scanContext["universeCol"] == "종목코드"

    def test_topn_limits_universe(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv({code: i for i, code in enumerate(["005930", "000660", "035420", "207940", "068270"])})
        scan = _make_scan_result(["005930", "000660", "035420", "207940", "068270"])
        bt = runScanBacktest(scan, style="trendFollow", topN=2)
        assert bt.scanContext is not None
        assert bt.scanContext["universeSize"] == 2

    def test_hash_deterministic_across_calls(self, patch_ohlcv):
        from dartlab.quant.scanBacktest import runScanBacktest

        patch_ohlcv({"005930": 1, "000660": 2})
        scan = _make_scan_result(["005930", "000660"], {"score": [1.0, 2.0]})
        b1 = runScanBacktest(scan, style="trendFollow", topN=2)
        b2 = runScanBacktest(scan, style="trendFollow", topN=2)
        assert b1.scanContext["scanResultHash"] == b2.scanContext["scanResultHash"]


# ═══════════════════════════════════════════════════════════
# Quant attribute (top-level) 노출
# ═══════════════════════════════════════════════════════════


class TestQuantAttribute:
    def test_attribute_exists(self):
        import dartlab as dl

        assert hasattr(dl.quant, "scanBacktest")

    def test_call_via_attribute(self, patch_ohlcv):
        import dartlab as dl

        patch_ohlcv({"005930": 1, "000660": 2})
        scan = _make_scan_result(["005930", "000660"])
        bt = dl.quant.scanBacktest(scan, style="trendFollow", topN=2)
        assert bt.scanContext is not None
        assert bt.scanContext["universeSize"] == 2

    def test_axis_dispatch_blocked(self):
        """scanBacktest 는 axis 미등록 — dispatch 호출 시 KeyError."""
        import dartlab as dl

        with pytest.raises((KeyError, AttributeError, ValueError)):
            # axis dispatch 는 stockCode 가 첫 인자로 와야 하니 시그니처 어긋남
            dl.quant("scanBacktest", "005930")


# ═══════════════════════════════════════════════════════════
# BacktestResult.scanContext field
# ═══════════════════════════════════════════════════════════


class TestBacktestResultField:
    def test_default_none(self):
        from dartlab.quant.strategy.backtest import BacktestResult

        bt = BacktestResult()
        assert bt.scanContext is None

    def test_replace_field(self):
        import dataclasses

        from dartlab.quant.strategy.backtest import BacktestResult

        bt = BacktestResult()
        bt2 = dataclasses.replace(bt, scanContext={"universeSize": 5})
        assert bt2.scanContext == {"universeSize": 5}
        # frozen — 원본 변경 없음
        assert bt.scanContext is None
