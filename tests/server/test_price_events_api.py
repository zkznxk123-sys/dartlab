"""L6 Backend — /api/dartlab/price-events 단위 테스트.

buildPriceEventsPayload (pure function) + FastAPI TestClient route.
모든 외부 의존 (ohlcv/disclosure/news/shocks/regime) monkeypatch 격리.
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import polars as pl
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """priceEvents + priceShockNews BoundedCache clear."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    pe._CACHE._store.clear()
    try:
        psn = importlib.import_module("dartlab.analysis.eventStudy.priceShockNews")
        psn._CACHE._store.clear()
    except Exception:
        pass


def _mk_ohlcv() -> pl.DataFrame:
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(30)]
    return pl.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i for i in range(30)],
            "high": [101.0 + i for i in range(30)],
            "low": [99.0 + i for i in range(30)],
            "close": [100.5 + i for i in range(30)],
            "volume": [1000] * 30,
        }
    )


def test_smoke_import() -> None:
    importlib.import_module("dartlab.server.api.priceEvents")


def test_build_payload_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """OHLCV + 빈 events → 정상 schema."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    ohlcv_mod = importlib.import_module("dartlab.quant.screen._dataAccessOhlcv")
    listing_mod = importlib.import_module("dartlab.gather.krx.listing.registry")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    monkeypatch.setattr(ohlcv_mod, "fetchOhlcv", lambda c, **kw: _mk_ohlcv())
    monkeypatch.setattr(listing_mod, "codeToName", lambda c: "삼성전자" if c == "005930" else None)
    monkeypatch.setattr(news_mod, "loadNewsArchive", lambda s, e, m, *, asof=None: pl.DataFrame())

    payload = pe.buildPriceEventsPayload(
        "005930",
        "2024-01-01",
        "2024-01-30",
        market="KR",
        includeShocks=False,
        includeRegime=False,
    )
    assert payload["stockCode"] == "005930"
    assert payload["corpName"] == "삼성전자"
    assert payload["market"] == "KR"
    assert len(payload["ohlc"]) == 30
    # LWC row schema [ts, o, h, l, c, v]
    assert len(payload["ohlc"][0]) == 6
    assert payload["events"] == {}
    assert payload["shocks"] == []


def test_build_payload_with_news(monkeypatch: pytest.MonkeyPatch) -> None:
    """news archive + keyword filter → events 일자별 dict."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    ohlcv_mod = importlib.import_module("dartlab.quant.screen._dataAccessOhlcv")
    listing_mod = importlib.import_module("dartlab.gather.krx.listing.registry")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    monkeypatch.setattr(ohlcv_mod, "fetchOhlcv", lambda c, **kw: _mk_ohlcv())
    monkeypatch.setattr(listing_mod, "codeToName", lambda c: "삼성전자")
    monkeypatch.setattr(
        news_mod,
        "loadNewsArchive",
        lambda s, e, m, *, asof=None: pl.DataFrame(
            {
                "date": [date(2024, 1, 5), date(2024, 1, 5)],
                "title": ["삼성전자 호재", "현대차 부진"],
                "url": ["http://a", "http://b"],
                "source": ["NewsA", "NewsB"],
                "sentiment_score": [0.4, -0.2],
                "sentiment_label": ["pos", "neg"],
            }
        ),
    )

    payload = pe.buildPriceEventsPayload(
        "005930",
        "2024-01-01",
        "2024-01-10",
        market="KR",
        sources="news_rss",
        includeShocks=False,
        includeRegime=False,
    )
    assert "2024-01-05" in payload["events"]
    rss = payload["events"]["2024-01-05"].get("news_rss", [])
    assert len(rss) == 1  # 삼성전자 매칭 1건만
    assert rss[0]["title"] == "삼성전자 호재"


def test_build_payload_invalid_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """sources 미지원 → ValueError."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    with pytest.raises(ValueError):
        pe.buildPriceEventsPayload("005930", "2024-01-01", "2024-01-30", sources="invalid")


def test_route_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """FastAPI TestClient — /api/dartlab/price-events 응답 schema."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    ohlcv_mod = importlib.import_module("dartlab.quant.screen._dataAccessOhlcv")
    listing_mod = importlib.import_module("dartlab.gather.krx.listing.registry")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    monkeypatch.setattr(ohlcv_mod, "fetchOhlcv", lambda c, **kw: _mk_ohlcv())
    monkeypatch.setattr(listing_mod, "codeToName", lambda c: "삼성전자")
    monkeypatch.setattr(news_mod, "loadNewsArchive", lambda s, e, m, *, asof=None: pl.DataFrame())

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(pe.router)
    client = TestClient(app)

    resp = client.get(
        "/api/dartlab/price-events",
        params={
            "stockCode": "005930",
            "start": "2024-01-01",
            "end": "2024-01-30",
            "market": "KR",
            "includeShocks": "false",
            "includeRegime": "false",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stockCode"] == "005930"
    assert "ohlc" in body
    assert "events" in body
    assert "shocks" in body
    assert "regime_band" in body


def test_route_validation_stockCode_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """stockCode 5 자리 → 422."""
    pe = importlib.import_module("dartlab.server.api.priceEvents")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(pe.router)
    client = TestClient(app)

    resp = client.get("/api/dartlab/price-events", params={"stockCode": "00593"})
    assert resp.status_code == 422
