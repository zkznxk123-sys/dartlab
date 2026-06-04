"""pipeline.hfUpload 단위 — HfApi mock, 실 네트워크 0. 원본차단·skip·증분·토큰 검증."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class _FakeApi:
    """create_commit/upload_folder/upload_large_folder 호출을 기록하는 HfApi 대역."""

    instances: list["_FakeApi"] = []

    def __init__(self, token=None):
        self.token = token
        self.commits: list[dict] = []
        self.folderCalls = 0
        self.largeFolderCalls = 0
        _FakeApi.instances.append(self)

    def create_commit(self, *, repo_id, repo_type, operations, commit_message):  # noqa: N802
        self.commits.append({"repo": repo_id, "ops": list(operations), "msg": commit_message})

    def upload_folder(self, **kw):  # noqa: N802
        self.folderCalls += 1

    def upload_large_folder(self, **kw):  # noqa: N802
        self.largeFolderCalls += 1


@pytest.fixture(autouse=True)
def _mock_hf(monkeypatch):
    _FakeApi.instances = []
    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "HfApi", _FakeApi)
    monkeypatch.setenv("HF_TOKEN", "tok-test")
    yield


def _mkParquet(d: Path, *names: str) -> None:
    for n in names:
        p = d / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")


def test_changed_empty_skips_commit(tmp_path):
    """changedFiles=[] → 0 commit, 반환 0."""
    from dartlab.pipeline.hfUpload import uploadCategoryToHf

    monkeypatch_data(tmp_path)
    n = uploadCategoryToHf("finance", changedFiles=[], dataDir=str(tmp_path))
    assert n == 0
    assert all(not a.commits for a in _FakeApi.instances)


def test_incremental_batches_commit(tmp_path):
    """changedFiles 있으면 create_commit 호출 + path_in_repo 접두(dir) 보존."""
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.pipeline.hfUpload import uploadCategoryToHf

    cat = "finance"
    localDir = tmp_path / DATA_RELEASES[cat]["dir"]
    _mkParquet(localDir, "005930.parquet", "000660.parquet")
    n = uploadCategoryToHf(cat, changedFiles=["005930.parquet", "000660.parquet"], dataDir=str(tmp_path))
    assert n == 2
    api = _FakeApi.instances[-1]
    assert len(api.commits) == 1
    paths = {op.path_in_repo for op in api.commits[0]["ops"]}
    assert paths == {f"{DATA_RELEASES[cat]['dir']}/005930.parquet", f"{DATA_RELEASES[cat]['dir']}/000660.parquet"}


def test_token_resolution_param_over_env(tmp_path, monkeypatch):
    """토큰 우선순위 — 인자 > env > .env(부재 시 ValueError)."""
    from dartlab.pipeline.hfUpload import _resolveHfToken

    monkeypatch.setenv("HF_TOKEN", "env-tok")
    assert _resolveHfToken("arg-tok") == "arg-tok"
    assert _resolveHfToken() == "env-tok"
    # .env fallback 검증 — repo 루트 .env 회피 위해 .env 없는 tmp dir 로 cwd 이동
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(ValueError):
        _resolveHfToken()
    (tmp_path / ".env").write_text('HF_TOKEN="dotenv-tok"\n', encoding="utf-8")
    assert _resolveHfToken() == "dotenv-tok"


def monkeypatch_data(tmp_path):
    from dartlab.core.dataConfig import DATA_RELEASES

    (tmp_path / DATA_RELEASES["finance"]["dir"]).mkdir(parents=True, exist_ok=True)
    os.environ["DARTLAB_DATA_DIR"] = str(tmp_path)
