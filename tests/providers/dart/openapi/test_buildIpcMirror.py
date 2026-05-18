"""Phase A — ``buildIpcMirror`` 회귀 테스트.

검증:
  1. parquet → .arrow IPC 생성.
  2. dtype/row count/값 일치.
  3. ``ipcMirror=False`` 카테고리 skip.
  4. parquet 갱신 시 .arrow 재빌드 (mtime 기반).
  5. ``dist/changed_{cat}.txt`` 있으면 그 parquet 만 변환.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _loadBuildIpcMirror():
    """.github/scripts/sync/buildIpcMirror.py 모듈 로드 (path 명시)."""
    repoRoot = Path(__file__).resolve().parents[4]
    scriptPath = repoRoot / ".github" / "scripts" / "sync" / "buildIpcMirror.py"
    spec = importlib.util.spec_from_file_location("buildIpcMirror", scriptPath)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["buildIpcMirror"] = mod
    spec.loader.exec_module(mod)
    return mod


def _writeSampleParquet(dest: Path) -> pl.DataFrame:
    df = pl.DataFrame(
        {
            "sj_div": ["BS", "BS", "CF", "IS"],
            "bsns_year": [2023] * 4,
            "account_id": ["a1", "a2", "a3", "a4"],
            "thstrm_amount": [100.0, 200.0, 300.0, 400.0],
        }
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(dest)
    return df


def test_creates_ipc_mirror(tmp_path: Path, monkeypatch) -> None:
    bim = _loadBuildIpcMirror()
    monkeypatch.chdir(tmp_path)  # 프로젝트 루트의 dist/changed_*.txt 와 격리
    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    df = _writeSampleParquet(parquetPath)

    converted = bim.buildMirror("finance", tmp_path)

    arrowPath = parquetPath.with_suffix(".arrow")
    assert converted == 1
    assert arrowPath.exists()

    # dtype + row count + 값 동일성
    fromIpc = pl.read_ipc(arrowPath)
    assert fromIpc.schema == df.schema
    assert fromIpc.height == df.height
    assert fromIpc.equals(df)


def test_skip_when_ipcMirror_false(tmp_path: Path, monkeypatch) -> None:
    bim = _loadBuildIpcMirror()
    monkeypatch.chdir(tmp_path)

    # ipcMirror=False 인 가짜 카테고리 — 실제 DATA_RELEASES 에서 stemIndex 가 False.
    parquetPath = tmp_path / "dart" / "stemIndex" / "test.parquet"
    _writeSampleParquet(parquetPath)

    converted = bim.buildMirror("stemIndex", tmp_path)
    assert converted == 0
    assert not parquetPath.with_suffix(".arrow").exists()


def test_idempotent_mtime_skip(tmp_path: Path, monkeypatch) -> None:
    """동일 parquet 재실행 시 .arrow 재변환 안 함."""
    bim = _loadBuildIpcMirror()
    monkeypatch.chdir(tmp_path)
    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleParquet(parquetPath)

    bim.buildMirror("finance", tmp_path)
    arrowPath = parquetPath.with_suffix(".arrow")
    firstMtime = arrowPath.stat().st_mtime

    time.sleep(0.05)
    bim.buildMirror("finance", tmp_path)
    assert arrowPath.stat().st_mtime == firstMtime, "두번째 호출이 재변환 했음"


def test_rebuild_on_parquet_update(tmp_path: Path, monkeypatch) -> None:
    """parquet 이 새것이면 .arrow 재변환."""
    bim = _loadBuildIpcMirror()
    monkeypatch.chdir(tmp_path)
    parquetPath = tmp_path / "dart" / "finance" / "005930.parquet"
    _writeSampleParquet(parquetPath)

    bim.buildMirror("finance", tmp_path)
    arrowPath = parquetPath.with_suffix(".arrow")
    firstArrowMtime = arrowPath.stat().st_mtime

    # parquet 의 mtime 을 명시적으로 미래 시점으로 set (polars write_parquet 가 mtime
    # 갱신 안 하는 경우 + Windows FS 정밀도 race 둘 다 회피).
    futureTime = firstArrowMtime + 10
    os.utime(parquetPath, (futureTime, futureTime))

    bim.buildMirror("finance", tmp_path)
    assert arrowPath.stat().st_mtime > firstArrowMtime


def test_changed_txt_filters_targets(tmp_path: Path, monkeypatch) -> None:
    """``dist/changed_{cat}.txt`` 가 있으면 그 parquet 만 변환."""
    bim = _loadBuildIpcMirror()

    # 두 parquet 작성
    parquetA = tmp_path / "dart" / "finance" / "005930.parquet"
    parquetB = tmp_path / "dart" / "finance" / "000660.parquet"
    _writeSampleParquet(parquetA)
    _writeSampleParquet(parquetB)

    # changed.txt 에 005930 만 적음 — 작업 디렉토리 격리.
    monkeypatch.chdir(tmp_path)
    distDir = tmp_path / "dist"
    distDir.mkdir()
    (distDir / "changed_finance.txt").write_text("005930.parquet\n", encoding="utf-8")

    converted = bim.buildMirror("finance", tmp_path)

    assert converted == 1
    assert parquetA.with_suffix(".arrow").exists()
    assert not parquetB.with_suffix(".arrow").exists()

    # 변환된 .arrow 가 changed.txt 에 추가됨
    after = (distDir / "changed_finance.txt").read_text(encoding="utf-8")
    assert "005930.arrow" in after
