"""pipeline W0 foundation — types·changed·hashing 단위 (실 네트워크 0)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_stage_report_merge() -> None:
    """StageReport.merge — per-item 집계 누적."""
    from dartlab.pipeline import StageReport

    a = StageReport(ok=1, fail=1, failures=["x"])
    a.merge(StageReport(ok=2, skip=3, failures=["y"]))
    assert (a.ok, a.skip, a.fail) == (3, 3, 1)
    assert a.failures == ["x", "y"]


def test_stage_spec_describe() -> None:
    """StageSpec.describe — sync --list 표시 메타."""
    from dartlab.pipeline import StageSpec

    spec = StageSpec("finance", online=True, uploadCategories=("finance",), label="DART 재무")
    d = spec.describe()
    assert d["category"] == "finance" and d["online"] is True
    assert d["uploadCategories"] == ["finance"]


def test_changed_roundtrip(tmp_path: Path) -> None:
    """writeChanged → readChanged 라운드트립 + dedup·정렬, 빈 목록 = []."""
    from dartlab.pipeline import readChanged, writeChanged

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        writeChanged("panel", ["b/2.parquet", "a/1.parquet", "a/1.parquet"])
        assert readChanged("panel") == ["a/1.parquet", "b/2.parquet"]
        writeChanged("panel", [])
        assert readChanged("panel") == []
        assert readChanged("__missing__") == []
    finally:
        os.chdir(cwd)


def test_hashing_diff(tmp_path: Path) -> None:
    """snapshotHashes + diffChanged — 신규·변경만 검출(삭제 제외)."""
    from dartlab.pipeline import diffChanged, fileHash, snapshotHashes

    (tmp_path / "a.parquet").write_bytes(b"one")
    before = snapshotHashes(tmp_path)
    (tmp_path / "a.parquet").write_bytes(b"two")  # modified
    (tmp_path / "b.parquet").write_bytes(b"new")  # added
    after = snapshotHashes(tmp_path)
    assert diffChanged(before, after) == ["a.parquet", "b.parquet"]
    assert isinstance(fileHash(tmp_path / "a.parquet"), str)
    assert snapshotHashes(tmp_path / "nope") == {}


def test_hf_retry_promoted() -> None:
    """core.hfRetry — LFS-RuntimeError-429 unwrap retry & non-transient 즉시 raise."""
    from dartlab.core.hfRetry import parseRetryWait, retryHfCall

    assert parseRetryWait(RuntimeError("retry this action in 2 minutes"), 0) == 150

    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("Error while uploading 'x' to the Hub.")  # transient msg
        return "ok"

    # transient(메시지 매칭) → 1회 재시도 후 성공. parseRetryWait fallback 60s 회피 위해 monkeypatch.
    import dartlab.core.hfRetry as hr

    orig = hr.time.sleep
    hr.time.sleep = lambda *_: None
    try:
        assert retryHfCall(flaky) == "ok"
        assert calls["n"] == 2
        with pytest.raises(ValueError):
            retryHfCall(lambda: (_ for _ in ()).throw(ValueError("400 bad")))
    finally:
        hr.time.sleep = orig
