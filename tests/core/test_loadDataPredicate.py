"""Phase B-2 — ``loadData`` predicate kw 회귀.

검증:
  1. ``predicate=pl.col("sj_div")=="BS"`` 가 결과를 BS row 만으로 축소.
  2. predicate 호출은 _LOAD_CACHE 우회 (다른 slice 조회 시 cache 충돌 없음).
  3. predicate 없는 호출은 기존 동작 그대로.
  4. predicate + columns 동시 작용.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _writeSampleFinanceParquet(path: Path) -> pl.DataFrame:
    """sj_div BS/IS/CF 섞인 sample finance parquet."""
    df = pl.DataFrame(
        {
            "sj_div": ["BS", "BS", "IS", "IS", "CF"],
            "fs_div": ["CFS"] * 5,
            "bsns_year": [2023, 2023, 2023, 2023, 2023],
            "reprt_nm": ["사업보고서"] * 5,
            "account_id": ["a1", "a2", "a3", "a4", "a5"],
            "thstrm_amount": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return df


def test_predicate_filters_rows(tmp_path: Path, monkeypatch) -> None:
    """predicate 가 디스크에서 row 축소."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleFinanceParquet(parquetPath)

    # _dataDir override → tmp_path 가리킴 (실제 data root 격리)
    monkeypatch.setattr(dataLoader, "_dataDir", lambda cat: tmp_path / "dart" / "finance")
    monkeypatch.setattr(dataLoader, "_ensureLocalParquet", lambda *a, **kw: None)
    monkeypatch.setattr(dataLoader, "_normalizeLoadedFrame", lambda df, cat: df)
    monkeypatch.setattr(dataLoader, "_shouldRefreshHfCategory", lambda *a, **kw: False)

    # _LOAD_CACHE 격리
    dataLoader._LOAD_CACHE.clear()

    bsOnly = dataLoader.loadData(
        "005930",
        category="finance",
        predicate=pl.col("sj_div") == "BS",
    )

    assert bsOnly.height == 2
    assert set(bsOnly.get_column("sj_div").to_list()) == {"BS"}


def test_predicate_call_yields_filtered_result(tmp_path: Path, monkeypatch) -> None:
    """Phase D — predicate 호출도 동일하게 cache 미사용 (모든 호출이 일관 동작)."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleFinanceParquet(parquetPath)

    monkeypatch.setattr(dataLoader, "_dataDir", lambda cat: tmp_path / "dart" / "finance")
    monkeypatch.setattr(dataLoader, "_ensureLocalParquet", lambda *a, **kw: None)
    monkeypatch.setattr(dataLoader, "_normalizeLoadedFrame", lambda df, cat: df)
    monkeypatch.setattr(dataLoader, "_shouldRefreshHfCategory", lambda *a, **kw: False)

    dataLoader._LOAD_CACHE.clear()

    result = dataLoader.loadData("005930", category="finance", predicate=pl.col("sj_div") == "BS")
    assert result.height == 2
    assert len(dataLoader._LOAD_CACHE) == 0


def test_no_predicate_returns_full_data(tmp_path: Path, monkeypatch) -> None:
    """Phase D — _LOAD_CACHE 폐기 후 predicate 없는 호출도 매번 disk 재로드."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleFinanceParquet(parquetPath)

    monkeypatch.setattr(dataLoader, "_dataDir", lambda cat: tmp_path / "dart" / "finance")
    monkeypatch.setattr(dataLoader, "_ensureLocalParquet", lambda *a, **kw: None)
    monkeypatch.setattr(dataLoader, "_normalizeLoadedFrame", lambda df, cat: df)
    monkeypatch.setattr(dataLoader, "_shouldRefreshHfCategory", lambda *a, **kw: False)

    dataLoader._LOAD_CACHE.clear()

    full = dataLoader.loadData("005930", category="finance")
    assert full.height == 5
    # Phase D — _LOAD_CACHE 폐기. 항상 empty.
    assert len(dataLoader._LOAD_CACHE) == 0


def test_predicate_with_columns(tmp_path: Path, monkeypatch) -> None:
    """predicate + columns 동시 작용."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleFinanceParquet(parquetPath)

    monkeypatch.setattr(dataLoader, "_dataDir", lambda cat: tmp_path / "dart" / "finance")
    monkeypatch.setattr(dataLoader, "_ensureLocalParquet", lambda *a, **kw: None)
    monkeypatch.setattr(dataLoader, "_normalizeLoadedFrame", lambda df, cat: df)
    monkeypatch.setattr(dataLoader, "_shouldRefreshHfCategory", lambda *a, **kw: False)

    dataLoader._LOAD_CACHE.clear()

    sliced = dataLoader.loadData(
        "005930",
        category="finance",
        predicate=pl.col("sj_div") == "IS",
        columns=["sj_div", "account_id"],
    )

    assert sliced.height == 2
    assert set(sliced.columns) == {"sj_div", "account_id"}
    assert set(sliced.get_column("sj_div").to_list()) == {"IS"}
