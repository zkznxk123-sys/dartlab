"""HF metadata read 병목 회귀 가드."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _loadScript(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_new_stocks_uses_prefix_tree_listing(monkeypatch):
    """신규종목 remote code discovery 는 dataset 전체 repo_info 를 열거하지 않는다."""
    import huggingface_hub

    from dartlab.core.dataConfig import DATA_RELEASES

    calls: list[tuple[str, str, bool, bool]] = []

    class FakeApi:
        def __init__(self, token=None):
            self.token = token

        def repo_info(self, **_kwargs):  # noqa: N802
            raise AssertionError("syncNewStocks must not use broad repo_info listing")

        def list_repo_tree(self, *, repo_id, path_in_repo, repo_type, recursive, expand, token=None):  # noqa: N802
            calls.append((repo_id, path_in_repo, recursive, expand))
            return [
                SimpleNamespace(path=f"{path_in_repo}/005930.parquet"),
                SimpleNamespace(path=f"{path_in_repo}/README.md"),
            ]

    monkeypatch.setattr(huggingface_hub, "HfApi", FakeApi)
    mod = _loadScript(".github/scripts/sync/syncNewStocks.py")

    result = mod._remoteParquetCodes(["finance", "report"])

    assert result == {"finance": {"005930"}, "report": {"005930"}}
    assert calls == [
        ("eddmpython/dartlab-data", DATA_RELEASES["finance"]["dir"], True, False),
        ("eddmpython/dartlab-data", DATA_RELEASES["report"]["dir"], True, False),
    ]


def test_prebuild_requires_panel_input():
    """full 모드: prebuild 는 panel 없이 부분 scan 을 만들면 안 된다."""
    mod = _loadScript(".github/scripts/prebuild/prebuildData.py")

    with pytest.raises(SystemExit):
        mod._validateInputCoverage({"finance": 0, "report": 0, "panel": 0}, incremental=False)
    with pytest.raises(SystemExit):
        mod._validateInputCoverage({"finance": 1000, "report": 1000, "panel": 0}, incremental=False)
    with pytest.raises(SystemExit):
        mod._validateInputCoverage({"finance": 1000, "report": 1000, "panel": 100}, incremental=False)

    mod._validateInputCoverage({"finance": 1000, "report": 1000, "panel": 600}, incremental=False)


def test_prebuild_incremental_allows_zero_panel():
    """증분 모드: panel 로컬 수 = 변경 종목 수라 0 도 정상(전량 보존). 단 전부 0 은 실패."""
    mod = _loadScript(".github/scripts/prebuild/prebuildData.py")

    # finance/report 존재하면 panel 변경 0 은 통과 (no-op 사이클)
    mod._validateInputCoverage({"finance": 1000, "report": 1000, "panel": 0}, incremental=True)
    # base seed 실패로 전부 0 이면 증분이어도 실패
    with pytest.raises(SystemExit):
        mod._validateInputCoverage({"finance": 0, "report": 0, "panel": 0}, incremental=True)
