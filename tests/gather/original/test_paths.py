"""gather.original.paths — data/original/ 경로 헬퍼 unit 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_paths_layout(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """4 경로 헬퍼가 data/original/{dart,edgar}/... 레이아웃을 정확히 만든다."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))

    assert paths.originalRoot() == tmp_path / "original"
    assert paths.dartDocsDir("005930") == tmp_path / "original" / "dart" / "docs" / "005930"
    assert paths.dartFilingsDir("005930") == tmp_path / "original" / "dart" / "allFilings" / "005930"


def test_edgar_cik_zero_padded(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """edgarDir 은 CIK 를 10자리 zero-pad 한다(ticker/짧은 CIK 무관 단일 식별)."""
    import dartlab.config as cfg
    from dartlab.gather.original import paths

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))

    assert paths.edgarDir("320193").name == "0000320193"
    assert paths.edgarDir("0000320193").name == "0000320193"
