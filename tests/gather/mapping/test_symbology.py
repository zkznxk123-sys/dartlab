"""dartlab.gather.mapping.symbology 단위 테스트.

OpenFIGI 라이브 호출 없음 (monkeypatch). cache load/save 라운드트립 + 4 lookup.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

from dartlab.gather.mapping import symbology
from dartlab.gather.mapping.symbology import (
    figiToTicker,
    isinToTicker,
    loadCache,
    saveCache,
    tickerToFigi,
)

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.mapping.symbology")


def test_loadCache_missing_returns_empty(tmp_path, monkeypatch) -> None:
    """cache 파일 없으면 빈 DataFrame + schema 보존."""
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "no.parquet")
    df = loadCache()
    assert df.is_empty()
    assert "id_type" in df.schema
    assert "figi" in df.schema


def test_saveCache_loadCache_roundtrip(tmp_path, monkeypatch) -> None:
    """save → load 직렬화 일치."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    df = pl.DataFrame(
        {
            "id_type": ["TICKER"],
            "id_value": ["AAPL"],
            "exch_code": ["US"],
            "figi": ["BBG000B9XRY4"],
            "ticker": ["AAPL"],
            "name": ["APPLE INC"],
        }
    )
    saveCache(df)
    out = loadCache()
    assert out.height == 1
    assert out["figi"][0] == "BBG000B9XRY4"


def test_tickerToFigi_cache_hit(tmp_path, monkeypatch) -> None:
    """cache 에 있으면 OpenFIGI 안 호출."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    saveCache(
        pl.DataFrame(
            {
                "id_type": ["TICKER"],
                "id_value": ["AAPL"],
                "exch_code": ["US"],
                "figi": ["BBG000B9XRY4"],
                "ticker": ["AAPL"],
                "name": ["APPLE INC"],
            }
        )
    )

    def _fail_lookup(*args, **kwargs):
        raise AssertionError("cache hit 인데 lookupBulk 호출됨")

    monkeypatch.setattr(symbology, "lookupBulk", _fail_lookup)
    assert tickerToFigi("AAPL", exchCode="US") == "BBG000B9XRY4"


def test_tickerToFigi_cache_miss_calls_live(tmp_path, monkeypatch) -> None:
    """cache miss → lookupBulk 호출 + 결과 cache 추가."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    monkeypatch.setattr(
        symbology,
        "lookupBulk",
        lambda items, **kwargs: [{"figi": "BBG000B9XRY4", "ticker": "AAPL", "name": "APPLE INC", "exchCode": "US"}],
    )
    figi = tickerToFigi("AAPL", exchCode="US")
    assert figi == "BBG000B9XRY4"
    # cache 에 추가됐는지
    cache = loadCache()
    assert cache.height == 1
    assert cache["figi"][0] == "BBG000B9XRY4"


def test_isinToTicker_live(tmp_path, monkeypatch) -> None:
    """ISIN → (ticker, exchCode)."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    monkeypatch.setattr(
        symbology,
        "lookupBulk",
        lambda items, **kwargs: [{"ticker": "AAPL", "exchCode": "US", "figi": "BBG000B9XRY4", "name": "APPLE INC"}],
    )
    result = isinToTicker("US0378331005")
    assert result == ("AAPL", "US")


def test_figiToTicker_live(tmp_path, monkeypatch) -> None:
    """FIGI → (ticker, exchCode)."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    monkeypatch.setattr(
        symbology,
        "lookupBulk",
        lambda items, **kwargs: [{"ticker": "MSFT", "exchCode": "US", "figi": "BBG000BPH459", "name": "MICROSOFT"}],
    )
    result = figiToTicker("BBG000BPH459")
    assert result == ("MSFT", "US")


def test_lookup_no_match_returns_none(tmp_path, monkeypatch) -> None:
    """OpenFIGI no_match → None."""
    monkeypatch.setattr(symbology, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(symbology, "_CACHE_FILE", tmp_path / "figi.parquet")
    monkeypatch.setattr(symbology, "lookupBulk", lambda items, **kwargs: [{"error": "no_match"}])
    assert tickerToFigi("UNKNOWN_TICKER", exchCode="US") is None
    assert isinToTicker("INVALID_ISIN") is None
    assert figiToTicker("INVALID_FIGI") is None


def test_lookupBulk_empty_returns_empty() -> None:
    """빈 items → 빈 list (네트워크 호출 0)."""
    assert symbology.lookupBulk([]) == []
