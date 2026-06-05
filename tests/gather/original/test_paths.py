"""gather.original.paths — data/original/ 경로 헬퍼 unit 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_paths_layout(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """DART 원본 zip 경로 헬퍼가 data/original/dart/... 레이아웃을 정확히 만든다."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))

    assert paths.originalRoot() == tmp_path / "original"
    assert paths.dartDocsDir("005930") == tmp_path / "original" / "dart" / "docs" / "005930"
    assert paths.dartFilingsDir("005930") == tmp_path / "original" / "dart" / "allFilings" / "005930"
