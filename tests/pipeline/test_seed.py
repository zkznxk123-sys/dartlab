"""pipeline.seed 단위 — HfApi/_download mock, 실 네트워크 0. idempotent size-skip 검증."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


class _FakeApi:
    calls: list[tuple[str, str, str]] = []

    def __init__(self, token=None):
        self.token = token

    def repo_info(self, **_kwargs):  # noqa: N802
        raise AssertionError("seed must not use broad repo_info metadata listing")

    def list_repo_tree(self, *, repo_id, path_in_repo, repo_type, recursive, expand, token=None):  # noqa: N802
        from dartlab.core.dataConfig import DATA_RELEASES

        d = DATA_RELEASES["finance"]["dir"]
        self.calls.append((repo_id, path_in_repo, repo_type))
        assert path_in_repo == d
        assert recursive is True
        assert expand is True
        return [
            SimpleNamespace(path=f"{d}/a.parquet", size=3),
            SimpleNamespace(path=f"{d}/b.parquet", size=5),
            SimpleNamespace(path=f"{d}/", size=0),  # dir entry — 무시돼야
        ]


def test_seed_downloads_missing_only(tmp_path, monkeypatch):
    """로컬 size 일치는 skip, 누락/불일치만 _download."""
    import huggingface_hub

    _FakeApi.calls = []
    monkeypatch.setattr(huggingface_hub, "HfApi", _FakeApi)

    from dartlab.core.dataConfig import DATA_RELEASES

    d = tmp_path / DATA_RELEASES["finance"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.parquet").write_bytes(b"xyz")  # size 3 = 일치 → skip

    downloaded: list[str] = []

    def fakeDownload(url, dest, token, timeout=60):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"00000")
        downloaded.append(Path(dest).name)
        return 5

    import dartlab.pipeline.seed as seedmod

    monkeypatch.setattr(seedmod, "_download", fakeDownload)

    result = seedmod.seedCategoriesFromHf(["finance"], dataDir=str(tmp_path))
    total, newCount, _mb = result["finance"]
    assert downloaded == ["b.parquet"]  # a 는 size 일치 skip, dir entry 무시
    assert newCount == 1
    assert total >= 2
    assert _FakeApi.calls == [("eddmpython/dartlab-data", "dart/finance", "dataset")]


def test_seed_skips_hf_tree_resolve_404(tmp_path, monkeypatch):
    """HF list-tree 와 resolve 사이 stale 404는 seed 전체를 죽이지 않고 skip."""
    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "HfApi", _FakeApi)

    import dartlab.pipeline.seed as seedmod

    def fakeDownload(url, dest, token, timeout=60):
        if url.endswith("/a.parquet"):
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            Path(dest).write_bytes(b"000")
            return 3
        return None

    monkeypatch.setattr(seedmod, "_download", fakeDownload)

    result = seedmod.seedCategoriesFromHf(["finance"], dataDir=str(tmp_path))
    total, newCount, _mb = result["finance"]
    assert newCount == 1
    assert total == 1


def test_is_fresh(tmp_path):
    """_isFresh — 존재 + size 일치만 True."""
    from dartlab.pipeline.seed import _isFresh

    f = tmp_path / "x"
    assert not _isFresh(f, 3)
    f.write_bytes(b"abc")
    assert _isFresh(f, 3)
    assert not _isFresh(f, 9)
