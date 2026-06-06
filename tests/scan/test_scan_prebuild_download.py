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


def test_prepareRealdataScanCache_builds_from_fixture_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import importlib.util

    import dartlab.scan.builders.kr.common as common
    import dartlab.scan.builders.kr.core as core
    import dartlab.scan.builders.kr.shares as shares
    import dartlab.scan.io.parquet as parquet

    script_path = Path(".github/scripts/ops/prepareRealdataScanCache.py").resolve()
    spec = importlib.util.spec_from_file_location("prepare_realdata_scan_cache", script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    calls: list[str] = []
    scan_dir = tmp_path / "dart" / "scan"

    def write_required_outputs() -> None:
        for name in parquet._REQUIRED_SCAN_ROOT_FILES:
            (scan_dir / name).parent.mkdir(parents=True, exist_ok=True)
            (scan_dir / name).write_bytes(b"parquet")
        for name in parquet._REQUIRED_REPORT_FILES:
            path = scan_dir / "report" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"parquet")

    monkeypatch.setattr(common, "scanDir", lambda: scan_dir)
    monkeypatch.setattr(core, "buildChanges", lambda **_kwargs: calls.append("changes") or scan_dir / "changes.parquet")
    monkeypatch.setattr(core, "buildFinance", lambda **_kwargs: calls.append("finance") or scan_dir / "finance.parquet")
    monkeypatch.setattr(
        core, "buildFinanceLite", lambda **_kwargs: calls.append("finance-lite") or scan_dir / "finance-lite.parquet"
    )
    monkeypatch.setattr(core, "buildReport", lambda **_kwargs: calls.append("report") or [])
    monkeypatch.setattr(
        shares,
        "buildSharesOutstandingSafe",
        lambda **_kwargs: calls.append("shares") or scan_dir / "sharesOutstanding.parquet",
    )
    monkeypatch.setattr(parquet, "_ensureScanData", lambda **_kwargs: pytest.fail("_ensureScanData must not be called"))
    monkeypatch.setattr(parquet, "_missingScanFiles", lambda *_args, **_kwargs: write_required_outputs() or [])

    assert mod.main() == 0
    assert calls == ["changes", "finance", "finance-lite", "report", "shares"]
