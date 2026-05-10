"""quant.calcMarketContext 단위 테스트.

OHLCV / 거시 wide / flow DataFrame 을 fixture 로 mock — 외부 네트워크 의존 0.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


# ── helpers: 합성 시계열 + Polars 변환 ──────────────────────


def _trending_close(n: int = 250, drift: float = 0.0008, vol: float = 0.005, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    log_ret = drift + vol * rng.standard_normal(n - 1)
    return 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(log_ret)]))


def _index_close(n: int = 250, drift: float = 0.0005, vol: float = 0.004, seed: int = 12) -> np.ndarray:
    rng = np.random.default_rng(seed)
    log_ret = drift + vol * rng.standard_normal(n - 1)
    return 2500.0 * np.exp(np.concatenate([[0.0], np.cumsum(log_ret)]))


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


def _make_macro_df(n: int = 250) -> pl.DataFrame:
    rng = np.random.default_rng(33)
    base = date(2024, 1, 2)
    dates = [base + timedelta(days=i) for i in range(n)]
    return pl.DataFrame(
        {
            "date": dates,
            "USDKRW": 1300.0 + 50.0 * np.cumsum(rng.standard_normal(n) * 0.001),
            "BASE_RATE": 3.5 + 0.005 * np.cumsum(rng.standard_normal(n) * 0.05),
            "CPI": 110.0 + 0.001 * np.arange(n),
            "M2": 3000.0 * (1 + 0.0001 * np.arange(n)),
        }
    )


def _make_flow_df(n: int = 250) -> pl.DataFrame:
    rng = np.random.default_rng(77)
    base = date(2024, 1, 2)
    dates = [base + timedelta(days=i) for i in range(n)]
    foreign = rng.standard_normal(n) * 1000
    institution = rng.standard_normal(n) * 800
    return pl.DataFrame(
        {
            "date": dates,
            "foreignNet": foreign,
            "institutionNet": institution,
            "individualNet": -(foreign + institution),
            "foreignHoldingRatio": 30.0 + 0.01 * np.arange(n),
        }
    )


# ── pytest fixture ──


@pytest.fixture
def patch_market_data(monkeypatch):
    """OHLCV / benchmark / macro / flow 를 합성 데이터로 대체하는 fixture factory.

    monkeypatch 의 string-path setattr 가 dartlab.quant 의 axis dispatcher (__getattr__)
    를 함수로 해석해 모듈 attr 접근을 막는다. 따라서 import 후 객체 setattr 사용.
    """

    def _patcher(stockClose, market="KR", with_flow=True):
        import importlib

        _gather_entry = importlib.import_module("dartlab.gather.entry")
        _benchmark_mod = importlib.import_module("dartlab.quant.benchmark")
        _mc_mod = importlib.import_module("dartlab.quant.marketContext")

        stockDf = _make_ohlcv_df(stockClose)
        bm_df = _make_ohlcv_df(_index_close(n=len(stockClose)))
        macroDf = _make_macro_df(n=len(stockClose))
        flow_df = _make_flow_df(n=len(stockClose)) if with_flow else None

        def _fake_fetch_ohlcv(code, **kwargs):
            return stockDf

        def _fake_fetch_benchmark(code, **kwargs):
            return bm_df

        class _FakeGather:
            def __call__(self, axis, *args, **kwargs):
                if axis == "macro":
                    return macroDf
                if axis == "flow":
                    return flow_df if flow_df is not None else pl.DataFrame()
                raise ValueError(f"unknown axis: {axis}")

        monkeypatch.setattr(_mc_mod, "fetchOhlcv", _fake_fetch_ohlcv)
        monkeypatch.setattr(_benchmark_mod, "fetchBenchmarkOhlcv", _fake_fetch_benchmark)
        monkeypatch.setattr(_gather_entry, "GatherEntry", lambda: _FakeGather())
        return stockDf, bm_df, macroDf, flow_df

    return _patcher


# ═══════════════════════════════════════════════════════════
# OLS helper
# ═══════════════════════════════════════════════════════════


class TestOls:
    def test_perfect_fit(self):
        from dartlab.quant.regime.marketContext import _ols

        x = np.arange(50, dtype=np.float64)
        y = 2.0 + 3.0 * x  # β=3, α=2
        out = _ols(y, x)
        assert out["beta"] == pytest.approx(3.0, rel=1e-6)
        assert out["alpha"] == pytest.approx(2.0, rel=1e-6)
        assert out["r2"] == pytest.approx(1.0, abs=1e-6)

    def test_handles_short_input(self):
        from dartlab.quant.regime.marketContext import _ols

        out = _ols(np.array([1.0, 2.0]), np.array([1.0, 2.0]))
        assert not np.isfinite(out["beta"])

    def test_handles_constant_x(self):
        from dartlab.quant.regime.marketContext import _ols

        x = np.full(20, 5.0)
        y = np.arange(20, dtype=np.float64)
        out = _ols(y, x)
        # 분산 0 → β=0 fallback
        assert out["beta"] == 0.0


# ═══════════════════════════════════════════════════════════
# CAPM
# ═══════════════════════════════════════════════════════════


class TestCapm:
    def test_capm_recovers_beta(self):
        from dartlab.quant.regime.marketContext import _capmBetaAlpha

        # 종목 = 1.5 * 시장 + noise
        rng = np.random.default_rng(123)
        n = 250
        bmClose = 2000.0 * np.exp(np.cumsum(0.0005 + 0.003 * rng.standard_normal(n)))
        # 종목은 시장 일별 수익률의 1.5 배 + 작은 noise
        bm_ret = np.diff(np.log(bmClose))
        stockRet = 0.0001 + 1.5 * bm_ret + 0.001 * rng.standard_normal(len(bm_ret))
        stockClose = 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(stockRet)]))
        out = _capmBetaAlpha(stockClose, bmClose)
        assert out is not None
        beta, alpha_ann, r2, n_capm = out
        assert beta == pytest.approx(1.5, abs=0.1)
        assert r2 > 0.90  # SNR 9 시 기대 ~0.95, 임계 완화


# ═══════════════════════════════════════════════════════════
# 메인 진입점
# ═══════════════════════════════════════════════════════════


class TestCalcMarketContext:
    def test_basic_kr_call(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="KR")
        r = calcMarketContext("005930", market="KR")
        assert "error" not in r
        assert r["stockCode"] == "005930"
        assert r["market"] == "KR"
        assert "marketBeta" in r
        assert "marketR2" in r
        assert "marketAlpha" in r
        assert "lookbackDays" in r
        assert r["lookbackDays"] <= 250

    def test_macro_betas_present(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="KR")
        r = calcMarketContext("005930", market="KR")
        # KR 4 default 모두 있어야
        for k in ("usdkrwBeta", "baseRateBeta", "cpiBeta", "m2Beta"):
            assert k in r, f"매크로 β 누락: {k}"
            assert k + "_r2" in r, f"R² 누락: {k}_r2"

    def test_flow_metrics_present(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="KR", with_flow=True)
        r = calcMarketContext("005930", market="KR")
        assert r.get("flowAvailable") is True
        assert "smartMoneyNet60d" in r
        assert "flowMomentum20d" in r

    def test_flow_unavailable_for_us(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="US")
        r = calcMarketContext("AAPL", market="US")
        assert r.get("flowAvailable") is False

    def test_short_data_returns_error(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=30), market="KR")
        r = calcMarketContext("005930", market="KR")
        assert "error" in r

    def test_no_data_returns_error(self, monkeypatch):
        from dartlab.quant.regime.marketContext import calcMarketContext

        monkeypatch.setattr("dartlab.quant.marketContext.fetchOhlcv", lambda code, **kw: None)
        r = calcMarketContext("FAIL", market="KR")
        assert "error" in r

    def test_user_macro_vars_override(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="KR")
        r = calcMarketContext("005930", market="KR", macroVars=["USDKRW"])
        assert "usdkrwBeta" in r
        assert "baseRateBeta" not in r  # 명시 안 했으니 미산출

    def test_summary_format(self, patch_market_data):
        from dartlab.quant.regime.marketContext import calcMarketContext

        patch_market_data(_trending_close(n=250), market="KR")
        r = calcMarketContext("005930", market="KR")
        assert "summary" in r
        assert "β=" in r["summary"]


# ═══════════════════════════════════════════════════════════
# Axis registry 통합
# ═══════════════════════════════════════════════════════════


class TestAxisRegistry:
    def test_marketcontext_registered(self):
        from dartlab.quant import _AXIS_REGISTRY

        assert "marketContext" in _AXIS_REGISTRY
        entry = _AXIS_REGISTRY["marketContext"]
        assert entry.fn == "calcMarketContext"
        assert entry.module == "dartlab.quant.marketContext"
        assert entry.group == "risk"

    def test_korean_alias(self):
        from dartlab.quant import _ALIASES

        assert _ALIASES.get("시장맥락") == "marketContext"

    def test_dispatch_via_quant_call(self, patch_market_data):
        import dartlab

        patch_market_data(_trending_close(n=250), market="KR")
        r = dartlab.quant("marketContext", "TEST_DISPATCH", market="KR")
        assert "error" not in r
        # 한글 alias
        r2 = dartlab.quant("시장맥락", "TEST_DISPATCH", market="KR")
        assert r2["lookbackDays"] == r["lookbackDays"]
