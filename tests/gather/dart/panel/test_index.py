"""panel slim 인덱스 빌더 mirror — 경로 SSOT + 빈 dir 0행 (데이터 0).

``gather/dart/panel/index.py`` 의 1:1 mirror. indexPath/panelXbrlRefPath 경로 SSOT 와
artifact 없는 tmp dir 에서 buildIndex 가 rowCount 0 을 반환하는지 검증 (providers ↛ gather
경계: 본 builder 는 gather 전용).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_index_path_names() -> None:
    """경로 SSOT — _index.parquet / panelXbrlRef.parquet."""
    from dartlab.gather.dart.panel import indexPath, panelXbrlRefPath

    assert indexPath("kr").name == "_index.parquet"
    assert indexPath("kr").as_posix().endswith("dart/panel/_index.parquet")
    assert indexPath("us").as_posix().endswith("edgar/panel/_index.parquet")
    assert panelXbrlRefPath().name == "panelXbrlRef.parquet"


def test_build_index_empty_dir_zero_rows(tmp_path: Path) -> None:
    """artifact 없는 base dir → rowCount 0 (스캔 0, 부작용 0)."""
    from dartlab.gather.dart.panel import buildIndex

    out = buildIndex(panelBaseDir=tmp_path, outPath=tmp_path / "_index.parquet", verbose=False)
    assert out["rowCount"] == 0
    assert out["codeCount"] == 0
