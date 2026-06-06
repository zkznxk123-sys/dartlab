"""scan prebuild auto-download contract."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _patchScanRoot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    import dartlab.core.dataLoader as dataLoader
    import dartlab.scan.io.parquet as parquet

    scanDir = tmp_path / "scan"
    monkeypatch.setattr(dataLoader, "_dataDir", lambda category="scan": scanDir)
    monkeypatch.setattr(dataLoader, "_IS_PYODIDE", False, raising=False)
    monkeypatch.setattr(parquet, "_scanDownloaded", False, raising=False)
    return scanDir


def test_ensureScanData_downloads_missing_root_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import dartlab.scan.io.parquet as parquet

    scanDir = _patchScanRoot(monkeypatch, tmp_path)
    downloaded: list[str] = []

    def fakeDownload(targetDir: Path, relativePath: str) -> None:
        downloaded.append(relativePath)
        path = targetDir / relativePath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"parquet")

    monkeypatch.setattr(parquet, "_downloadScanFile", fakeDownload)

    assert parquet._ensureScanData() == scanDir
    assert set(downloaded) == set(parquet._REQUIRED_SCAN_ROOT_FILES)
    assert parquet._isScanRootComplete(scanDir)


def test_ensureScanData_downloads_report_files_when_required(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import dartlab.scan.io.parquet as parquet

    scanDir = _patchScanRoot(monkeypatch, tmp_path)
    downloaded: list[str] = []

    def fakeDownload(targetDir: Path, relativePath: str) -> None:
        downloaded.append(relativePath)
        path = targetDir / relativePath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"parquet")

    monkeypatch.setattr(parquet, "_downloadScanFile", fakeDownload)

    assert parquet._ensureScanData(requireReports=True) == scanDir
    assert set(downloaded) == {
        *parquet._REQUIRED_SCAN_ROOT_FILES,
        *(f"report/{name}" for name in parquet._REQUIRED_REPORT_FILES),
    }
    assert parquet._isScanComplete(scanDir)
