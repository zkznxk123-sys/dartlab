"""L3 — newsImpact event study 단위 테스트.

CAR 계산 + news context 결합 검증. 모두 mock 으로 외부 의존 격리.
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _mk_ohlcv(n: int = 200, ev_shock: float = 0.0, ev_idx: int = 130) -> pl.DataFrame:
    """200 거래일 OHLCV. ev_idx 에 ev_shock 만큼 점프 (CAR 검출용)."""
    rng = np.random.default_rng(seed=42)
    rets = rng.normal(0.0005, 0.012, n)
    if ev_idx < n:
        rets[ev_idx] += ev_shock
    closes = 100.0 * np.cumprod(1 + rets)
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    return pl.DataFrame({"date": dates, "close": closes.tolist()})


def _mk_benchmark(n: int = 200) -> pl.DataFrame:
    """benchmark OHLCV — 같은 dates 의 약한 양의 drift."""
    rng = np.random.default_rng(seed=1)
    rets = rng.normal(0.0003, 0.008, n)
    closes = 2000.0 * np.cumprod(1 + rets)
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    return pl.DataFrame({"date": dates, "close": closes.tolist()})


def test_smoke_import() -> None:
    """모듈 import 가능."""
    importlib.import_module("dartlab.analysis.eventStudy.newsImpact")


def test_news_impact_no_event() -> None:
    """평범한 이벤트 (shock=0) → CAR 작음, isSignificant False 가능."""
    ni = importlib.import_module("dartlab.analysis.eventStudy.newsImpact")
    stock = _mk_ohlcv(ev_shock=0.0)
    bench = _mk_benchmark()
    ev = stock["date"][130]

    r = ni.newsImpact(
        "005930",
        ev,
        market="KR",
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=lambda s, e, m: pl.DataFrame(),
        keyword="삼성전자",
    )
    assert "error" not in r
    assert r["stockCode"] == "005930"
    assert isinstance(r["car"], (int, float))
    assert "tStat" in r


def test_news_impact_large_shock_significant() -> None:
    """큰 shock (+15%) 이벤트 → CAR > 5%, isSignificant True 기대."""
    ni = importlib.import_module("dartlab.analysis.eventStudy.newsImpact")
    stock = _mk_ohlcv(ev_shock=0.15, ev_idx=130)
    bench = _mk_benchmark()
    ev = stock["date"][130]

    r = ni.newsImpact(
        "005930",
        ev,
        market="KR",
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=lambda s, e, m: pl.DataFrame(),
        keyword="삼성전자",
    )
    assert "error" not in r
    assert r["carPct"] > 5.0
    assert r["isSignificant"] is True


def test_news_impact_news_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """news context — keyword 필터로 동기간 news items 첨부."""
    ni = importlib.import_module("dartlab.analysis.eventStudy.newsImpact")
    stock = _mk_ohlcv(ev_shock=0.0)
    bench = _mk_benchmark()
    ev = stock["date"][130]

    def fake_news(start, end, market):
        return pl.DataFrame(
            {
                "date": [ev, ev],
                "title": ["삼성전자 깜짝 실적", "현대차 신차 발표"],
                "url": ["http://a", "http://b"],
                "source": ["A", "B"],
                "sentiment_score": [0.6, 0.1],
                "sentiment_label": ["pos", "neutral"],
            }
        )

    r = ni.newsImpact(
        "005930",
        ev,
        market="KR",
        ohlcvFetcher=lambda c, m: stock,
        benchmarkFetcher=lambda m: bench,
        newsLoader=fake_news,
        keyword="삼성전자",
    )
    assert r["n_news"] == 1  # 삼성전자 헤드라인 1건만
    assert r["news"][0]["title"] == "삼성전자 깜짝 실적"


def test_news_impact_ohlcv_unavailable() -> None:
    """ohlcv None → error 키."""
    ni = importlib.import_module("dartlab.analysis.eventStudy.newsImpact")
    r = ni.newsImpact(
        "005930",
        "2024-05-15",
        market="KR",
        ohlcvFetcher=lambda c, m: None,
        benchmarkFetcher=lambda m: None,
        newsLoader=lambda s, e, m: pl.DataFrame(),
    )
    assert "error" in r
    assert "ohlcv" in r["error"]
