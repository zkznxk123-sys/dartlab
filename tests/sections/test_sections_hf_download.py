"""sectionsStorage._ensureFromHf lazy 다운로드 회귀 가드.

plan snazzy-wibbling-origami PR-4b-ii. 사용자 측 artifact 부재 시 huggingface_hub
snapshot_download 으로 한 종목 디렉터리만 lazy 다운로드. 실패 시 silent fallback.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dartlab.providers.dart.docs.sections.sectionsStorage import (
    _HF_DOWNLOAD_ATTEMPTED,
    _ensureFromHf,
    hasSectionsArtifact,
)

pytestmark = [pytest.mark.unit]


def test_ensure_returns_true_when_artifact_present(monkeypatch, tmp_path):
    """artifact 이미 있으면 HF 호출 0 + True."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    _HF_DOWNLOAD_ATTEMPTED.clear()
    code = "HFEXIST"

    # 픽스처 artifact 생성
    import polars as pl

    from dartlab.providers.dart.docs.sections.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {"topic": ["A"], "blockType": ["text"], "blockOrder": [0], "segmentKey": ["x"], "2025": ["v"]}
    )
    saveSectionsByPeriod(code, fixture)

    with patch("huggingface_hub.snapshot_download") as mockDownload:
        assert _ensureFromHf(code) is True
        mockDownload.assert_not_called()


def test_ensure_skipped_by_env(monkeypatch, tmp_path):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    _HF_DOWNLOAD_ATTEMPTED.clear()
    code = "HFENVSKIP"

    with patch("huggingface_hub.snapshot_download") as mockDownload:
        result = _ensureFromHf(code)
        assert result is False
        mockDownload.assert_not_called()


def test_ensure_attempts_once_per_code(monkeypatch, tmp_path):
    """한 종목 당 다운로드 시도 1 회 — 실패 시 반복 HF 호출 회피."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    monkeypatch.delenv("DARTLAB_NO_HF_DOWNLOAD", raising=False)
    _HF_DOWNLOAD_ATTEMPTED.clear()
    code = "HFONCE"

    callCount = {"n": 0}

    def fakeDownload(**kwargs):
        callCount["n"] += 1
        # 다운로드 시뮬레이션 실패 (artifact 미생성)

    with patch("huggingface_hub.snapshot_download", side_effect=fakeDownload):
        _ensureFromHf(code)
        _ensureFromHf(code)
        _ensureFromHf(code)
    assert callCount["n"] == 1, "한 종목 1 회만 시도 기대, 실제 {}".format(callCount["n"])


def test_ensure_silent_on_hf_error(monkeypatch, tmp_path):
    """huggingface_hub import 실패 또는 네트워크 에러 silent + False."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    monkeypatch.delenv("DARTLAB_NO_HF_DOWNLOAD", raising=False)
    _HF_DOWNLOAD_ATTEMPTED.clear()
    code = "HFERR"

    def raiseNetwork(**kwargs):
        raise ConnectionError("simulated network failure")

    with patch("huggingface_hub.snapshot_download", side_effect=raiseNetwork):
        result = _ensureFromHf(code)
        assert result is False
    assert not hasSectionsArtifact(code)


def test_ensure_returns_true_after_successful_download(monkeypatch, tmp_path):
    """다운로드 성공 시 hasSectionsArtifact True → return True."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    monkeypatch.delenv("DARTLAB_NO_HF_DOWNLOAD", raising=False)
    _HF_DOWNLOAD_ATTEMPTED.clear()
    code = "HFOK"

    def fakeDownload(**kwargs):
        # 다운로드 시뮬레이션 — sectionsDir 안 dummy parquet 생성
        import polars as pl

        from dartlab.providers.dart.docs.sections.sectionsStorage import sectionsDir

        d = sectionsDir(code)
        d.mkdir(parents=True, exist_ok=True)
        pl.DataFrame({"x": [1]}).write_parquet(d / "2025.parquet")

    with patch("huggingface_hub.snapshot_download", side_effect=fakeDownload):
        result = _ensureFromHf(code)
        assert result is True
        assert hasSectionsArtifact(code)
