"""panel batch mirror — multiprocessing fan-out 공개표면 (데이터 0).

``providers/dart/panel/build/batch.py`` 의 1:1 mirror. buildPanelAll/_main 공개표면 존재와
_buildOne 의 실패 흡수(빈 ref·없는 종목 → (code, 0, 0, elapsed)) 순수 경로 검증. 실 전종목
빌드(multiprocessing heavy)는 운영자/CI sync 담당.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_batch_callables_public() -> None:
    """buildPanelAll/_main 공개표면 존재 (build __init__ re-export 포함)."""
    from dartlab.providers.dart.panel.build import buildPanelAll
    from dartlab.providers.dart.panel.build.batch import _main
    from dartlab.providers.dart.panel.build.batch import buildPanelAll as ba

    assert callable(buildPanelAll)
    assert buildPanelAll is ba
    assert callable(_main)


def test_build_one_absorbs_missing_code() -> None:
    """_buildOne: 없는 종목/없는 ref → 실패 흡수, (code, 0, 0, elapsed) 반환 (예외 전파 0)."""
    from dartlab.providers.dart.panel.build.batch import _buildOne

    code, pcount, rows, elapsed = _buildOne(("000000nonexistent", "data/__no_such_ref__.parquet", "/tmp/__no_out__"))
    assert code == "000000nonexistent"
    assert pcount == 0
    assert rows == 0
    assert elapsed >= 0.0


def test_cells_batch_callables_public() -> None:
    """buildPanelCellsAll/_buildOneCells 공개표면 (panelCell 전종목 빌더)."""
    from dartlab.providers.dart.panel.build import buildPanelCellsAll
    from dartlab.providers.dart.panel.build.batch import _buildOneCells

    assert callable(buildPanelCellsAll)
    assert callable(_buildOneCells)


def test_build_one_cells_absorbs_missing_code(tmp_path) -> None:
    """_buildOneCells: 없는 종목(panel.parquet 부재) → 실패 흡수, (code, 0, 0, elapsed)."""
    from dartlab.providers.dart.panel.build.batch import _buildOneCells

    code, pcount, rows, elapsed = _buildOneCells(("000000nonexistent", str(tmp_path)))
    assert code == "000000nonexistent"
    assert pcount == 0 and rows == 0 and elapsed >= 0.0


def test_cells_all_codes_autoextract(monkeypatch, tmp_path) -> None:
    """codes=None → panelBaseDir 종목 자동추출(spine 제외), 빈 base 면 빈 결과."""
    import dartlab.config as _cfg
    from dartlab.providers.dart.panel.build.batch import buildPanelCellsAll

    monkeypatch.setattr(_cfg, "dataDir", str(tmp_path))
    (tmp_path / "dart" / "panel" / "005930").mkdir(parents=True)
    (tmp_path / "dart" / "panel" / "spine").mkdir(parents=True)  # spine 제외 확인
    out = buildPanelCellsAll(numWorkers=1, verbose=False)
    assert "spine" not in out  # spine 디렉터리는 종목 아님
    assert "005930" in out  # panel.parquet 0개라 (0,0)이지만 종목으로 잡힘
