"""pipeline.seed 단위 — HfApi/_download mock, 실 네트워크 0. idempotent size-skip 검증."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


class _FakeApi:
    def __init__(self, token=None):
        self.token = token

    def repo_info(self, *, repo_id, repo_type, files_metadata):  # noqa: N802
        from dartlab.core.dataConfig import DATA_RELEASES

        d = DATA_RELEASES["finance"]["dir"]
        return SimpleNamespace(
            siblings=[
                SimpleNamespace(rfilename=f"{d}/a.parquet", size=3),
                SimpleNamespace(rfilename=f"{d}/b.parquet", size=5),
                SimpleNamespace(rfilename=f"{d}/", size=0),  # dir entry — 무시돼야
            ]
        )


def test_seed_downloads_missing_only(tmp_path, monkeypatch):
    """로컬 size 일치는 skip, 누락/불일치만 _download."""
    import huggingface_hub

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


def test_is_fresh(tmp_path):
    """_isFresh — 존재 + size 일치만 True."""
    from dartlab.pipeline.seed import _isFresh

    f = tmp_path / "x"
    assert not _isFresh(f, 3)
    f.write_bytes(b"abc")
    assert _isFresh(f, 3)
    assert not _isFresh(f, 9)
