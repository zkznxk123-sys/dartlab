"""gather/dart/document.py — DART document.xml 원본 zip 병렬 fetch 단위 (무네트워크).

옛 위치: providers/dart/openapi/bulkZipFetcher.py (수집 일원화 — fetch 는 gather 전담).
streamZipBytes/fetchZipsParallel 는 DartClient + 네트워크가 필요하므로 import + 순수
헬퍼(FetchStats·safeWriteBytes·buildTargetsFromDocsParquet)만 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """공개 fetch 표면 import smoke (실 네트워크 0)."""
    from dartlab.gather.dart.document import (  # noqa: F401
        FetchStats,
        buildTargetsFromDocsParquet,
        collectAllOriginalZips,
        fetchZipsParallel,
        safeWriteBytes,
        streamZipBytes,
    )


def test_fetch_stats_accumulate() -> None:
    """FetchStats — 스레드 안전 누적 + asDict 직렬화."""
    from dartlab.gather.dart.document import FetchStats

    stats = FetchStats()
    stats.add(saved=2, skipped=1, failed=0, bytesTotal=2048)
    stats.add(saved=1, skipped=0, failed=1, bytesTotal=512)
    d = stats.asDict()
    assert d["saved"] == 3
    assert d["skipped"] == 1
    assert d["failed"] == 1
    assert d["bytesTotal"] == 2560


def test_safe_write_bytes_atomic(tmp_path: Path) -> None:
    """safeWriteBytes — atomic write (.tmp → rename), 디렉터리 자동 생성."""
    from dartlab.gather.dart.document import safeWriteBytes

    dest = tmp_path / "nested" / "005930" / "rcept.zip"
    safeWriteBytes(dest, b"PK\x03\x04payload")
    assert dest.exists()
    assert dest.read_bytes() == b"PK\x03\x04payload"
    assert not (dest.parent / "rcept.zip.tmp").exists()


def test_build_targets_missing_dir_empty(tmp_path: Path) -> None:
    """buildTargetsFromDocsParquet — docs parquet 부재 시 빈 list (네트워크 0)."""
    from dartlab.gather.dart.document import buildTargetsFromDocsParquet

    out = buildTargetsFromDocsParquet(codes=["005930"], docsDir=tmp_path / "nope")
    assert out == []
