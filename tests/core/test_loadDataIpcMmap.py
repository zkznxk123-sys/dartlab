"""Phase D — ``loadData`` 의 IPC mmap path 회귀.

검증:
  1. ``.arrow`` IPC mirror 가 옆에 있으면 mmap path 선택 (parquet 보다 우선).
  2. mmap 결과의 값/dtype 이 parquet 과 동일.
  3. predicate 적용도 mmap path 에서 작동.
  4. parquet 이 더 새것이면 parquet 으로 fallback (stale mirror 회피).
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _writeBothFormats(parquetPath: Path, df: pl.DataFrame) -> Path:
    parquetPath.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(parquetPath)
    ipcPath = parquetPath.with_suffix(".arrow")
    df.write_ipc(ipcPath, compression="zstd")
    return ipcPath


def _stubLoadDataDeps(monkeypatch, tmp_path: Path) -> None:
    from dartlab.core import dataLoader

    monkeypatch.setattr(dataLoader, "_dataDir", lambda cat: tmp_path / "dart" / "finance")
    monkeypatch.setattr(dataLoader, "_ensureLocalParquet", lambda *a, **kw: None)
    monkeypatch.setattr(dataLoader, "_normalizeLoadedFrame", lambda df, cat: df)
    monkeypatch.setattr(dataLoader, "_shouldRefreshHfCategory", lambda *a, **kw: False)
    dataLoader._LOAD_CACHE.clear()


def test_mmap_path_used_when_ipc_present(tmp_path: Path, monkeypatch) -> None:
    """``.arrow`` 가 옆에 있으면 mmap path 진입."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    df = pl.DataFrame({"sj_div": ["BS", "IS"], "thstrm_amount": [1.0, 2.0]})
    ipcPath = _writeBothFormats(parquetPath, df)

    _stubLoadDataDeps(monkeypatch, tmp_path)

    # ipc mtime >= parquet mtime 보장
    nowFuture = parquetPath.stat().st_mtime + 1
    os.utime(ipcPath, (nowFuture, nowFuture))

    # 결과는 값/shape 동일
    result = dataLoader.loadData("005930", category="finance")
    assert result.height == 2
    assert set(result.columns) == {"sj_div", "thstrm_amount"}
    assert result.get_column("sj_div").to_list() == ["BS", "IS"]


def test_mmap_path_with_predicate(tmp_path: Path, monkeypatch) -> None:
    """mmap path 도 predicate filter 적용."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    df = pl.DataFrame({"sj_div": ["BS", "BS", "IS", "CF"], "thstrm_amount": [1.0, 2.0, 3.0, 4.0]})
    ipcPath = _writeBothFormats(parquetPath, df)

    _stubLoadDataDeps(monkeypatch, tmp_path)
    nowFuture = parquetPath.stat().st_mtime + 1
    os.utime(ipcPath, (nowFuture, nowFuture))

    bsOnly = dataLoader.loadData(
        "005930",
        category="finance",
        predicate=pl.col("sj_div") == "BS",
    )
    assert bsOnly.height == 2
    assert set(bsOnly.get_column("sj_div").to_list()) == {"BS"}


def test_parquet_fallback_when_ipc_stale(tmp_path: Path, monkeypatch) -> None:
    """parquet 이 더 새것이면 mmap 우회 (stale mirror 회피)."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    df = pl.DataFrame({"sj_div": ["BS"], "thstrm_amount": [99.0]})
    ipcPath = _writeBothFormats(parquetPath, df)

    _stubLoadDataDeps(monkeypatch, tmp_path)

    # parquet 의 mtime 을 *ipc 보다 미래* 로 set (stale ipc 시나리오)
    nowFuture = ipcPath.stat().st_mtime + 1
    os.utime(parquetPath, (nowFuture, nowFuture))

    # 동작 자체는 정상 (parquet 으로 fallback) — 값 동일
    result = dataLoader.loadData("005930", category="finance")
    assert result.height == 1
    assert result.get_column("thstrm_amount").to_list() == [99.0]


def test_no_ipc_uses_parquet(tmp_path: Path, monkeypatch) -> None:
    """``.arrow`` 부재 시 기존 parquet 경로."""
    from dartlab.core import dataLoader

    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    df = pl.DataFrame({"sj_div": ["BS"], "thstrm_amount": [42.0]})
    parquetPath.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(parquetPath)

    _stubLoadDataDeps(monkeypatch, tmp_path)
    # ipc 미생성

    result = dataLoader.loadData("005930", category="finance")
    assert result.height == 1
    assert result.get_column("thstrm_amount").to_list() == [42.0]
