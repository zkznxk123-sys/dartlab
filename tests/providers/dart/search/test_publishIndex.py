"""publishIndex mirror tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class FakeHfApi:
    def __init__(self) -> None:
        self.uploads: list[str] = []
        self.deletes: list[str] = []

    def upload_file(self, *, path_or_fileobj: str, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        assert Path(path_or_fileobj).exists()
        assert repo_id == "repo"
        assert repo_type == "dataset"
        self.uploads.append(path_in_repo)

    def delete_file(self, *, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        assert repo_id == "repo"
        assert repo_type == "dataset"
        self.deletes.append(path_in_repo)


class BatchFakeHfApi:
    def __init__(self) -> None:
        self.commits: list[dict] = []

    def create_commit(
        self,
        *,
        repo_id: str,
        repo_type: str,
        operations: list,
        commit_message: str,
    ) -> None:
        assert repo_id == "repo"
        assert repo_type == "dataset"
        self.commits.append(
            {
                "message": commit_message,
                "paths": [operation.path_in_repo for operation in operations],
            }
        )


def test_ordered_publish_files_manifest_last() -> None:
    from dartlab.providers.dart.search.publishIndex import orderedPublishFiles

    assert orderedPublishFiles(["manifest.json", "main.npz", "main.npz"]) == ["main.npz", "manifest.json"]


def test_publish_content_index_files_uses_staging_and_manifest_pointer(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    api = FakeHfApi()

    summary = publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["manifest.json", "main.npz"],
        tier="full",
        runId="run1",
        api=api,
        repoId="repo",
        requireSelfcheck=False,
    )

    assert summary["stagingPrefix"] == "dart/contentIndex/_staging/full-run1"
    assert summary["publishMode"] == "manifestPointer"
    assert api.uploads == [
        "dart/contentIndex/_staging/full-run1/main.npz",
        "dart/contentIndex/_staging/full-run1/manifest.json",
        "dart/contentIndex/manifest.json",
    ]


def test_publish_content_index_files_preserves_current_files_in_manifest_pointer_mode(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    api = FakeHfApi()

    publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["main.npz", "manifest.json"],
        tier="lite",
        runId="run2",
        api=api,
        repoId="repo",
        obsoleteCurrentFiles=["delta.npz"],
        requireSelfcheck=False,
    )

    assert api.deletes == []
    assert api.uploads[-1] == "dart/contentIndex/lite/manifest.json"


def test_publish_content_index_files_batches_manifest_pointer_commit(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")
    (tmp_path / "main_info.json").write_bytes(b"info")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    api = BatchFakeHfApi()

    summary = publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["main.npz", "main_info.json", "manifest.json"],
        tier="full",
        runId="run-batch",
        api=api,
        repoId="repo",
        requireSelfcheck=False,
    )

    assert len(api.commits) == 1
    assert api.commits[0]["paths"] == [
        "dart/contentIndex/_staging/full-run-batch/main.npz",
        "dart/contentIndex/_staging/full-run-batch/main_info.json",
        "dart/contentIndex/_staging/full-run-batch/manifest.json",
        "dart/contentIndex/manifest.json",
    ]
    assert summary["uploaded"] == api.commits[0]["paths"]
    assert summary["candidateManifestPath"] == "dart/contentIndex/_staging/full-run-batch/manifest.json"
    assert summary["currentManifestPath"] == "dart/contentIndex/manifest.json"
    assert summary["promoted"] is True


def test_publish_content_index_files_can_stage_without_current_promotion(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")
    (tmp_path / "manifest.json").write_text('{"requiredFiles":["main.npz"]}', encoding="utf-8")
    api = BatchFakeHfApi()

    summary = publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["main.npz", "manifest.json"],
        tier="full",
        runId="run-stage",
        api=api,
        repoId="repo",
        requireSelfcheck=False,
        promoteCurrent=False,
    )

    assert len(api.commits) == 1
    assert api.commits[0]["paths"] == [
        "dart/contentIndex/_staging/full-run-stage/main.npz",
        "dart/contentIndex/_staging/full-run-stage/manifest.json",
    ]
    assert "dart/contentIndex/manifest.json" not in api.commits[0]["paths"]
    assert summary["candidateManifestPath"] == "dart/contentIndex/_staging/full-run-stage/manifest.json"
    assert summary["promoted"] is False


def test_promote_candidate_manifest_copies_staged_manifest_to_current(tmp_path) -> None:
    import json

    from dartlab.providers.dart.search.publishIndex import promoteCandidateManifest

    remote = tmp_path / "remote"
    candidate = remote / "dart/contentIndex/_staging/full-run-stage/manifest.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_text(
        json.dumps({"publishMode": "manifestPointer", "fileSources": {"main.npz": "staged/main.npz"}}),
        encoding="utf-8",
    )

    summary = promoteCandidateManifest(
        token=None,
        candidateManifestPath="dart/contentIndex/_staging/full-run-stage/manifest.json",
        tier="full",
        repoId="repo",
        remoteRoot=remote,
    )

    current = remote / "dart/contentIndex/manifest.json"
    assert summary["promoted"] is True
    assert summary["currentManifestPath"] == "dart/contentIndex/manifest.json"
    assert current.exists()
    assert json.loads(current.read_text(encoding="utf-8"))["fileSources"]["main.npz"] == "staged/main.npz"


def test_publish_content_index_files_writes_manifest_file_sources(tmp_path) -> None:
    import json

    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")
    (tmp_path / "entityGraphCatalog.parquet").write_bytes(b"graph")
    (tmp_path / "manifest.json").write_text(
        '{"requiredFiles":["main.npz","entityGraphCatalog.parquet"]}',
        encoding="utf-8",
    )
    remote = tmp_path / "remote"
    api = FakeHfApi()

    def upload_file(*, path_or_fileobj: str, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        dst = remote / path_in_repo
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(Path(path_or_fileobj).read_bytes())
        api.uploads.append(path_in_repo)

    api.upload_file = upload_file  # type: ignore[method-assign]
    publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["main.npz", "entityGraphCatalog.parquet", "manifest.json"],
        tier="full",
        runId="run3",
        api=api,
        repoId="repo",
        requireSelfcheck=False,
    )

    manifest = json.loads((remote / "dart/contentIndex/manifest.json").read_text(encoding="utf-8"))
    assert manifest["fileSources"]["main.npz"] == "dart/contentIndex/_staging/full-run3/main.npz"
    assert (
        manifest["fileSources"]["entityGraphCatalog.parquet"]
        == "dart/contentIndex/_staging/full-run3/entityGraphCatalog.parquet"
    )
    assert manifest["publishMode"] == "manifestPointer"


def test_publish_content_index_files_preserves_previous_file_sources_for_delta(tmp_path) -> None:
    import json

    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "delta.npz").write_bytes(b"delta")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"requiredFiles": ["main.npz", "delta.npz"]}),
        encoding="utf-8",
    )
    previous = tmp_path / "previous_manifest.json"
    previous.write_text(
        json.dumps({"fileSources": {"main.npz": "dart/contentIndex/_staging/full-old/main.npz"}}),
        encoding="utf-8",
    )
    remote = tmp_path / "remote"
    api = FakeHfApi()

    def upload_file(*, path_or_fileobj: str, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        dst = remote / path_in_repo
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(Path(path_or_fileobj).read_bytes())
        api.uploads.append(path_in_repo)

    api.upload_file = upload_file  # type: ignore[method-assign]
    publishContentIndexFiles(
        token=None,
        indexDir=tmp_path,
        files=["delta.npz", "manifest.json"],
        tier="full",
        runId="run-delta",
        api=api,
        repoId="repo",
        requireSelfcheck=False,
        previousManifestPath=previous,
    )

    manifest = json.loads((remote / "dart/contentIndex/manifest.json").read_text(encoding="utf-8"))
    assert manifest["fileSources"]["main.npz"] == "dart/contentIndex/_staging/full-old/main.npz"
    assert manifest["fileSources"]["delta.npz"] == "dart/contentIndex/_staging/full-run-delta/delta.npz"


def test_publish_content_index_files_requires_manifest_when_requested(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main.npz").write_bytes(b"main")

    with pytest.raises(FileNotFoundError):
        publishContentIndexFiles(
            token=None,
            indexDir=tmp_path,
            files=["main.npz", "manifest.json"],
            api=FakeHfApi(),
            repoId="repo",
        )


def test_publish_content_index_files_selfcheck_rejects_bad_hash(tmp_path) -> None:
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    (tmp_path / "main_info.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        '{"artifactVersion":1,"schemaVersion":1,"builtAt":"2026","sourceDataAsOf":{},'
        '"nDocsBySource":{},"requiredFiles":["main_info.json"],"fileHashes":{"main_info.json":"bad"}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hashMismatch:main_info.json"):
        publishContentIndexFiles(
            token=None,
            indexDir=tmp_path,
            files=["main_info.json", "manifest.json"],
            api=FakeHfApi(),
            repoId="repo",
        )


def test_preflight_content_index_publish_accepts_manifest_only_artifact(tmp_path) -> None:
    import hashlib

    from dartlab.providers.dart.search.publishIndex import preflightContentIndexPublish

    payload = b"{}"
    (tmp_path / "main_info.json").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    (tmp_path / "manifest.json").write_text(
        '{"artifactVersion":1,"schemaVersion":1,"builtAt":"2026","sourceDataAsOf":{},'
        f'"nDocsBySource":{{}},"requiredFiles":["main_info.json"],"fileHashes":{{"main_info.json":"{digest}"}}}}',
        encoding="utf-8",
    )

    assert preflightContentIndexPublish(tmp_path)["valid"] is True
