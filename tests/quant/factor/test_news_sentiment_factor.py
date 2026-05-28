"""L2 — newsSentimentFactor 단위 테스트 (Tetlock 2007 sentiment alpha).

calcNewsSentimentScore + buildNewsSentimentUniverse + newsSentimentIC 검증.
모두 monkeypatch 로 외부 의존 (archive/listing/ohlcv) 격리.
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _mk_archive(items: list[tuple[str, str, float]]) -> pl.DataFrame:
    """(title, sentiment_label, sentiment_score) tuples → archive-like DataFrame."""
    return pl.DataFrame(
        {
            "date": [date(2026, 5, 15) for _ in items],
            "title": [t for t, _, _ in items],
            "url": [f"http://x/{i}" for i in range(len(items))],
            "market": ["KR"] * len(items),
            "captured_at": [date(2026, 5, 15) for _ in items],
        }
    )


def test_smoke_import() -> None:
    """모듈 import 가능 — 구조 회귀 차단."""
    importlib.import_module("dartlab.quant.factor.newsSentimentFactor")


def test_calc_news_sentiment_score_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """archive 빈 → score NaN, n_headlines 0."""
    nf = importlib.import_module("dartlab.quant.factor.newsSentimentFactor")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")
    monkeypatch.setattr(news_mod, "loadNewsArchive", lambda s, e, m, *, asof=None: pl.DataFrame())
    monkeypatch.setattr(nf, "_resolveStockName", lambda c: "삼성전자")

    r = nf.calcNewsSentimentScore("005930", asOf="2026-05-28", lookbackDays=30)
    assert r["n_headlines"] == 0
    assert r["sentiment_label"] == "neutral"


def test_calc_news_sentiment_score_filtered(monkeypatch: pytest.MonkeyPatch) -> None:
    """corpName 필터 + scoreNewsBatch 통합 → mean score."""
    nf = importlib.import_module("dartlab.quant.factor.newsSentimentFactor")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")
    sent_mod = importlib.import_module("dartlab.quant.text.newsSentiment")

    archive = _mk_archive(
        [("삼성전자 호실적", "pos", 0.4), ("삼성전자 부도 위기", "neg", -0.6), ("LG화학 배터리", "neutral", 0.0)]
    )
    monkeypatch.setattr(news_mod, "loadNewsArchive", lambda s, e, m, *, asof=None: archive)
    monkeypatch.setattr(nf, "_resolveStockName", lambda c: "삼성전자")

    def fake_score(df, *, market="KR", model="lm_dict", batchSize=32):
        return df.with_columns(
            pl.Series("sentiment_score", [0.4, -0.6][: df.height]),
            pl.Series("sentiment_label", ["pos", "neg"][: df.height]),
            pl.Series("model_version", ["test"] * df.height),
        )

    monkeypatch.setattr(sent_mod, "scoreNewsBatch", fake_score)

    r = nf.calcNewsSentimentScore("005930", asOf="2026-05-28", lookbackDays=30)
    assert r["n_headlines"] == 2  # 삼성전자 2건만
    assert r["score"] == pytest.approx(-0.1, abs=0.01)


def test_build_news_sentiment_universe(monkeypatch: pytest.MonkeyPatch) -> None:
    """listing × archive cross-section dict."""
    nf = importlib.import_module("dartlab.quant.factor.newsSentimentFactor")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")
    listing_mod = importlib.import_module("dartlab.gather.krx.listing.registry")
    sent_mod = importlib.import_module("dartlab.quant.text.newsSentiment")

    archive = _mk_archive(
        [
            ("삼성전자 호실적 발표", "pos", 0.5),
            ("삼성전자 신제품 출시", "pos", 0.3),
            ("LG화학 배터리 사고", "neg", -0.4),
            ("현대차 SUV 출시", "neutral", 0.1),
        ]
    )
    monkeypatch.setattr(news_mod, "loadNewsArchive", lambda s, e, m, *, asof=None: archive)
    monkeypatch.setattr(
        listing_mod,
        "getKindList",
        lambda *, forceRefresh=False: pl.DataFrame(
            {"종목코드": ["005930", "051910", "005380"], "회사명": ["삼성전자", "LG화학", "현대차"]}
        ),
    )

    def fake_score(df, *, market="KR", model="lm_dict", batchSize=32):
        return df.with_columns(pl.Series("sentiment_score", [0.5, 0.3, -0.4, 0.1]))

    monkeypatch.setattr(sent_mod, "scoreNewsBatch", fake_score)

    # 캐시 무효화 — same key 충돌 차단 위해 asOf 변경
    asof = date.today() - timedelta(days=1)
    u = nf.buildNewsSentimentUniverse(market="KR", asOf=asof, lookbackDays=30)
    assert set(u.keys()) == {"005930", "051910", "005380"}
    assert u["005930"] == pytest.approx(0.4, abs=0.01)  # (0.5 + 0.3) / 2
    assert u["051910"] == pytest.approx(-0.4, abs=0.01)
    assert u["005380"] == pytest.approx(0.1, abs=0.01)


def test_news_sentiment_ic_with_injected_universe() -> None:
    """ohlcv mock + injected universe → IC + quintile_spread 계산."""
    nf = importlib.import_module("dartlab.quant.factor.newsSentimentFactor")

    # 12 stock universe — score 와 forward return monotonic (강한 양의 IC 기대)
    universe = {f"{i:06d}": (i - 5) * 0.1 for i in range(12)}

    def fake_ohlcv(code):
        i = int(code)
        # forward return 도 monotonic + 약간의 noise
        ret = (i - 5) * 0.02 + (0.001 if i % 2 == 0 else -0.001)
        return pl.DataFrame(
            {
                "date": [date(2026, 5, 28), date(2026, 6, 5)],
                "close": [100.0, 100.0 * (1 + ret)],
            }
        )

    r = nf.newsSentimentIC(
        market="KR",
        asOf="2026-05-28",
        lookbackDays=30,
        forwardDays=5,
        ohlcvFetcher=fake_ohlcv,
        universe=universe,
    )
    assert r["n_stocks"] == 12
    assert r["ic_pearson"] > 0.9  # 강한 양의 상관
    assert r["quintile_spread"] > 0  # top - bottom > 0


def test_news_sentiment_ic_empty_universe() -> None:
    """빈 universe → graceful NaN."""
    nf = importlib.import_module("dartlab.quant.factor.newsSentimentFactor")
    r = nf.newsSentimentIC(market="KR", asOf="2026-05-28", universe={})
    assert r["n_stocks"] == 0
    assert r["t_stat"] is None
