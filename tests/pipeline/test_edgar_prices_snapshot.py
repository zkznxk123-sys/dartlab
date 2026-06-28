"""edgarPrices deep 스냅샷 파생 — buildSnapshotFromCompanyDir 가 company parquet(전체이력)에서
실수익률·52주·현재가를 정확히 뽑는지(daily recent 패치와 분리된 정본). Polars Company 미사용 → OOM 무관.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _writeDeep(d, ticker: str, n: int) -> None:
    """ticker.parquet 합성 — n 거래일, close=100+i 상승(date Utf8 'YYYYMMDD')."""
    from datetime import date, timedelta

    base = date(2020, 1, 2)
    dates = [(base + timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]
    pl.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.0 + i for i in range(n)],
            "volume": [1000 + i for i in range(n)],
        }
    ).write_parquet(d / f"{ticker}.parquet")


def test_build_snapshot_deep_returns(tmp_path):
    """>252 거래일 ticker 는 return1y/52w/volatility 실값, currentPrice=마지막 종가."""
    from dartlab.pipeline.stages.edgarPrices import buildSnapshotFromCompanyDir

    _writeDeep(tmp_path, "AAPL", 400)  # 전체이력 충분 → 1y 계산 가능
    snap = buildSnapshotFromCompanyDir(tmp_path)

    assert "AAPL" in snap
    row = snap["AAPL"]
    assert row["currentPrice"] == 100.0 + 399  # 마지막 종가
    assert row["return1y"] is not None  # 252일 전 대비 — 상승이므로 양수
    assert row["return1y"] > 0
    assert row["week52High"] == max(101.0 + i for i in range(400 - 252, 400))
    assert row["volatility1y"] is not None


def test_build_snapshot_short_history_nullable(tmp_path):
    """짧은 이력(<252) ticker 는 return1y null 이지만 currentPrice·존재는 유지(게이트 통과)."""
    from dartlab.pipeline.stages.edgarPrices import buildSnapshotFromCompanyDir

    _writeDeep(tmp_path, "NEWCO", 30)  # 30거래일 — 1y 불가
    snap = buildSnapshotFromCompanyDir(tmp_path)

    assert "NEWCO" in snap
    assert snap["NEWCO"]["return1y"] is None
    assert snap["NEWCO"]["currentPrice"] == 100.0 + 29


def test_build_snapshot_skips_corrupt(tmp_path):
    """빈/손상 parquet 은 격리(나머지 진행) — 디렉터리 전체가 죽지 않는다."""
    from dartlab.pipeline.stages.edgarPrices import buildSnapshotFromCompanyDir

    _writeDeep(tmp_path, "GOOD", 300)
    (tmp_path / "BAD.parquet").write_bytes(b"not a parquet")
    snap = buildSnapshotFromCompanyDir(tmp_path)

    assert "GOOD" in snap
    assert "BAD" not in snap
