"""gather/edgar/universe.py mirror smoke — SEC listed universe Extract.

수집 일원화: SEC company_tickers_exchange.json fetch+build → gather 전담.
core 는 갱신 delegate + 캐시 read(loadEdgarListedUniverse).
"""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.universe  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_update_listed_universe_callable() -> None:
    """updateListedUniverse() callable smoke."""
    from dartlab.gather.edgar.universe import updateListedUniverse

    assert callable(updateListedUniverse)


def test_core_delegate_routes_to_gather() -> None:
    """core.edgarClient.updateListedUniverse → gather/edgar/universe (DIP seam)."""
    from dartlab.core.edgarClient import updateListedUniverse

    assert callable(updateListedUniverse)


def test_update_builds_records_from_fetch(monkeypatch, tmp_path) -> None:
    """fetch payload → cik·ticker·exchange·상장여부 정규화 parquet (network 0, monkeypatched)."""
    import polars as pl

    from dartlab import config
    from dartlab.gather.edgar import universe

    payload = {
        "data": [
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [123456, "OTC Example", "OTCX", "OTC"],
        ]
    }
    monkeypatch.setattr(config, "dataDir", str(tmp_path / "data"))
    monkeypatch.setattr(universe, "_fetchJson", lambda url: payload)

    path = universe.updateListedUniverse(force=True)
    df = pl.read_parquet(path)

    assert df.height == 2
    assert df.filter(pl.col("ticker") == "AAPL")["is_exchange_listed"][0] is True
    assert df.filter(pl.col("ticker") == "OTCX")["is_otc"][0] is True


def test_universe_stale_serve_on_fetch_failure(monkeypatch, tmp_path) -> None:
    """TTL 만료 + SEC fetch 실패 + stale 캐시 존재 → crash 대신 stale path 반환."""
    import polars as pl

    from dartlab.gather.edgar import universe as U

    path = tmp_path / "edgar" / "listedUniverse.parquet"
    path.parent.mkdir(parents=True)
    pl.DataFrame({"cik": ["0000000001"], "ticker": ["X"]}).write_parquet(path)

    monkeypatch.setattr("dartlab.core.dataLoader._getDataRoot", lambda: tmp_path)
    monkeypatch.setattr("dartlab.core.dataLoader._isLocalCacheExpired", lambda p, t: True)  # 만료 강제

    def boom(url):
        raise OSError("SEC down")

    monkeypatch.setattr(U, "_fetchJson", boom)
    assert U.updateListedUniverse() == path  # stale 서빙(crash 0)
