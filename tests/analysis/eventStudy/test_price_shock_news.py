"""L4 — priceShockNews 단위 테스트 (|AR|>3σ shock 자동 검출 + news context)."""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_price_shock_cache() -> None:
    """priceShockNews BoundedCache clear — 테스트 간 격리."""
    psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
    psn._CACHE._store.clear()


def _mk_ohlcv_with_shocks(n: int = 200, shock_idxs=(50, 130), shock_size=0.20) -> pl.DataFrame:
    """200 일 OHLCV — shock_idxs 일자에 큰 점프."""
    rng = np.random.default_rng(seed=7)
    rets = rng.normal(0.0005, 0.01, n)
    for idx in shock_idxs:
        if idx < n:
            rets[idx] += shock_size if idx % 2 == 0 else -shock_size
    closes = 100.0 * np.cumprod(1 + rets)
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    return pl.DataFrame({"date": dates, "close": closes.tolist()})


def _mk_bench(n: int = 200) -> pl.DataFrame:
    rng = np.random.default_rng(seed=3)
    rets = rng.normal(0.0003, 0.007, n)
    closes = 2500.0 * np.cumprod(1 + rets)
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    return pl.DataFrame({"date": dates, "close": closes.tolist()})


def test_smoke_import() -> None:
    importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")


def test_detect_shocks_no_news() -> None:
    """big shocks (2 일) 검출 + news loader 빈 결과 — graceful."""
    psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
    stock = _mk_ohlcv_with_shocks(shock_idxs=(50, 130), shock_size=0.18)
    bench = _mk_bench()

    r = psn.priceShockNews(
        "005930",
        market="KR",
        asOf=date(2024, 1, 1) + timedelta(days=199),
        periodDays=199,
        thresholdSigma=3.0,
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=lambda s, e, m: pl.DataFrame(),
        keyword="삼성전자",
    )
    assert "error" not in r
    assert r["n_shocks"] >= 2  # 최소 2 shocks 검출
    # 각 shock event 의 schema
    for ev in r["shock_events"]:
        assert "date" in ev
        assert "ar" in ev
        assert "z_score" in ev
        assert ev["direction"] in ("up", "down")


def test_detect_shocks_with_news(monkeypatch: pytest.MonkeyPatch) -> None:
    """shock 일자에 news context 첨부 — keyword 필터."""
    psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
    stock = _mk_ohlcv_with_shocks(shock_idxs=(50,), shock_size=0.25)
    bench = _mk_bench()
    shock_date = date(2024, 1, 1) + timedelta(days=50)

    def fake_news(start, end, market):
        return pl.DataFrame(
            {
                "date": [shock_date, shock_date],
                "title": ["삼성전자 깜짝 호재", "현대차 부진"],
                "url": ["http://a", "http://b"],
                "source": ["X", "Y"],
                "sentiment_score": [0.6, -0.3],
                "sentiment_label": ["pos", "neg"],
            }
        )

    r = psn.priceShockNews(
        "005930",
        market="KR",
        asOf=date(2024, 1, 1) + timedelta(days=199),
        periodDays=199,
        thresholdSigma=3.0,
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=fake_news,
        keyword="삼성전자",
        topNews=5,
    )
    assert r["n_shocks"] >= 1
    # 50 일째 shock 의 news 1건 (삼성전자 만 매칭)
    matched = [ev for ev in r["shock_events"] if ev["n_news"] >= 1]
    assert len(matched) >= 1
    assert matched[0]["news"][0]["title"] == "삼성전자 깜짝 호재"


def test_no_shocks_when_threshold_high() -> None:
    """thresholdSigma 10 (극단) → shock 0 (정상 변동성)."""
    psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
    stock = _mk_ohlcv_with_shocks(shock_idxs=(), shock_size=0.0)  # 노이즈만
    bench = _mk_bench()

    r = psn.priceShockNews(
        "005930",
        market="KR",
        asOf=date(2024, 1, 1) + timedelta(days=199),
        periodDays=199,
        thresholdSigma=10.0,
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=lambda s, e, m: pl.DataFrame(),
        keyword="삼성전자",
    )
    assert r["n_shocks"] == 0


def test_ohlcv_unavailable() -> None:
    """ohlcv None → error 키."""
    psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
    r = psn.priceShockNews(
        "005930",
        market="KR",
        ohlcvFetcher=lambda c, m: None,
        benchmarkFetcher=lambda m: None,
        newsLoader=lambda s, e, m: pl.DataFrame(),
    )
    assert "error" in r
