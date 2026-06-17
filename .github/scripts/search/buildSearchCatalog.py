"""Build search source manifests and catalog snapshots from local parquet files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="allFilings|dartPanel|edgarPanel|newsPublic|newsGdelt")
    parser.add_argument("--input", action="append", required=True, help="Parquet path or glob. Repeatable.")
    parser.add_argument("--out-dir", required=True, help="Output directory for manifest/catalog artifacts.")
    parser.add_argument("--producer", default="buildSearchCatalog")
    parser.add_argument("--source-version", default="v1")
    parser.add_argument("--schema-version", default="2026-06")
    parser.add_argument("--snapshot-scope", default="full", choices=("full", "partial"))
    parser.add_argument("--min-files", type=int, default=1, help="minimum source parquet files for publishable catalog")
    parser.add_argument("--min-rows", type=int, default=1, help="minimum source parquet rows for publishable catalog")
    parser.add_argument("--min-catalog-rows", type=int, default=1, help="minimum normalized catalog rows")
    parser.add_argument("--allow-empty-full-snapshot", action="store_true")
    parser.add_argument("--previous-manifest", default="", help="Prior source manifest JSON for drop protection.")
    parser.add_argument("--previous-catalog", default="", help="Prior full source catalog parquet for delta merge.")
    parser.add_argument(
        "--merge-previous-catalog",
        action="store_true",
        help="Merge current changed files into the previous full source catalog before publishing.",
    )
    parser.add_argument(
        "--compare-remote-manifest",
        action="store_true",
        help="Download the current HF source manifest and reject unexpected full-snapshot drops.",
    )
    parser.add_argument(
        "--require-previous-manifest",
        action="store_true",
        help="Fail when no previous manifest is available. Use for source-owner incremental jobs.",
    )
    parser.add_argument("--max-file-drop-ratio", type=float, default=0.05)
    parser.add_argument("--max-row-drop-ratio", type=float, default=0.05)
    parser.add_argument("--max-catalog-row-drop-ratio", type=float, default=0.05)
    parser.add_argument("--upload", action="store_true", help="Upload artifacts to HF dataset.")
    parser.add_argument("--hf-prefix", default="dart/searchCatalog", help="HF path prefix for uploaded artifacts.")
    args = parser.parse_args(argv)

    from dartlab.providers.dart.search.sourceCatalog import discoverSourceFiles, writeSourceCatalogArtifacts
    from dartlab.providers.dart.search.sourceCatalogMerge import writeMergedSourceCatalogArtifacts

    files = discoverSourceFiles(args.input)
    previousManifest = _loadPreviousManifest(args.previous_manifest)
    previousCatalog = _existingPath(args.previous_catalog)
    if args.compare_remote_manifest and previousManifest is None:
        previousManifest = _downloadRemotePreviousManifest(args.source, args.hf_prefix)
    if args.merge_previous_catalog and previousCatalog is None:
        previousCatalog = _downloadRemotePreviousCatalog(args.source, args.hf_prefix)
    if args.require_previous_manifest and previousManifest is None:
        raise RuntimeError(
            f"previous source manifest required for {args.source}; run a canonical full catalog bootstrap first"
        )
    if args.merge_previous_catalog:
        if previousManifest is None or previousCatalog is None:
            raise RuntimeError(
                f"previous source manifest and catalog required for {args.source} catalog merge; "
                "run a canonical full catalog bootstrap first"
            )
        result = writeMergedSourceCatalogArtifacts(
            args.source,
            files,
            previousCatalog=previousCatalog,
            previousManifest=previousManifest,
            outDir=args.out_dir,
            producer=args.producer,
            sourceVersion=args.source_version,
            schemaVersion=args.schema_version,
            minFiles=args.min_files,
            minRows=args.min_rows,
            minCatalogRows=args.min_catalog_rows,
            producerRun=_githubProducerRun(args.source),
            maxFileDropRatio=args.max_file_drop_ratio,
            maxRowDropRatio=args.max_row_drop_ratio,
            maxCatalogRowDropRatio=args.max_catalog_row_drop_ratio,
        )
    else:
        result = writeSourceCatalogArtifacts(
            args.source,
            files,
            outDir=args.out_dir,
            producer=args.producer,
            sourceVersion=args.source_version,
            schemaVersion=args.schema_version,
            snapshotScope=args.snapshot_scope,
            minFiles=args.min_files,
            minRows=args.min_rows,
            minCatalogRows=args.min_catalog_rows,
            allowEmptyFullSnapshot=args.allow_empty_full_snapshot,
            producerRun=_githubProducerRun(args.source),
            previousManifest=previousManifest,
            maxFileDropRatio=args.max_file_drop_ratio,
            maxRowDropRatio=args.max_row_drop_ratio,
            maxCatalogRowDropRatio=args.max_catalog_row_drop_ratio,
        )
    if args.upload:
        _upload(args.source, result, args.hf_prefix)
    print(json.dumps({key: str(path) for key, path in result.items()}, ensure_ascii=False, sort_keys=True))
    return 0


def _upload(source: str, result: dict[str, Path], prefix: str) -> None:
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise RuntimeError("--upload requires HF_TOKEN")
    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import repoFor

    api = HfApi(token=token)
    repo = repoFor("contentIndex")
    items = [(path, f"{prefix.strip('/')}/{source}/{path.name}") for path in result.values()]
    _uploadFiles(
        api,
        repo,
        items,
        commitMessage=f"Publish search source catalog {source}",
    )


def _loadPreviousManifest(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _existingPath(path: str) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    return candidate if candidate.exists() else None


def _downloadRemotePreviousManifest(source: str, prefix: str) -> dict[str, Any] | None:
    token = os.environ.get("HF_TOKEN", "")
    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError
    except Exception as exc:  # noqa: BLE001 - optional at local test time.
        raise RuntimeError("--compare-remote-manifest requires huggingface_hub") from exc

    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall

    filename = f"{prefix.strip('/')}/{source}/{source}.source_manifest.json"
    try:
        path = retryHfCall(
            hf_hub_download,
            repo_id=repoFor("contentIndex"),
            repo_type="dataset",
            filename=filename,
            token=token or None,
        )
    except (EntryNotFoundError, RepositoryNotFoundError):
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _downloadRemotePreviousCatalog(source: str, prefix: str) -> Path | None:
    token = os.environ.get("HF_TOKEN", "")
    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError
    except Exception as exc:  # noqa: BLE001 - optional at local test time.
        raise RuntimeError("--merge-previous-catalog requires huggingface_hub") from exc

    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall

    filename = f"{prefix.strip('/')}/{source}/{source}.catalog_snapshot.parquet"
    try:
        path = retryHfCall(
            hf_hub_download,
            repo_id=repoFor("contentIndex"),
            repo_type="dataset",
            filename=filename,
            token=token or None,
        )
    except (EntryNotFoundError, RepositoryNotFoundError):
        return None
    return Path(path)


def _uploadFiles(api: Any, repo: str, items: list[tuple[Path, str]], *, commitMessage: str) -> list[str]:
    from dartlab.core.hfRetry import retryHfCall

    if not items:
        return []
    if not hasattr(api, "create_commit"):
        uploaded = []
        for src, dstPath in items:
            retryHfCall(
                api.upload_file,
                path_or_fileobj=str(src),
                path_in_repo=dstPath,
                repo_id=repo,
                repo_type="dataset",
            )
            uploaded.append(dstPath)
        return uploaded

    try:
        from huggingface_hub import CommitOperationAdd
    except Exception:  # noqa: BLE001 - old environments can fall back to upload_file.
        uploaded = []
        for src, dstPath in items:
            retryHfCall(
                api.upload_file,
                path_or_fileobj=str(src),
                path_in_repo=dstPath,
                repo_id=repo,
                repo_type="dataset",
            )
            uploaded.append(dstPath)
        return uploaded

    operations = [CommitOperationAdd(path_in_repo=dstPath, path_or_fileobj=str(src)) for src, dstPath in items]
    retryHfCall(
        api.create_commit,
        repo_id=repo,
        repo_type="dataset",
        operations=operations,
        commit_message=commitMessage,
    )
    return [dstPath for _, dstPath in items]


def _githubProducerRun(source: str) -> dict[str, str]:
    runId = os.environ.get("GITHUB_RUN_ID", "")
    job = os.environ.get("GITHUB_JOB", "")
    if not runId and not job:
        return {}
    return {
        "system": "githubActions",
        "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "job": job,
        "runId": runId,
        "runAttempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "sha": os.environ.get("GITHUB_SHA", ""),
        "ref": os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF", ""),
        "artifactName": f"search-catalog-{source}-{job}-{runId}" if runId and job else "",
    }


if __name__ == "__main__":
    sys.exit(main())
