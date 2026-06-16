"""Pull the current manifest-pointer contentIndex into a flat build directory.

Daily delta builds need the previous full ``main.*`` files locally before they
write a new manifest. This script follows the current HF ``manifest.json``
``fileSources`` map instead of assuming legacy flat files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default="full", choices=["full", "lite"])
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests and offline drills.")
    parser.add_argument("--out-dir", help="Flat local contentIndex directory. Defaults to runtime data root.")
    parser.add_argument(
        "--previous-manifest",
        help="Where to preserve the remote current manifest. Defaults to OUT/previous_manifest.json.",
    )
    parser.add_argument(
        "--optional-file",
        action="append",
        default=["catalog_snapshot.parquet"],
        help="Optional file to pull when present in fileSources or at the tier prefix.",
    )
    args = parser.parse_args(argv)

    report = pullCurrentIndex(
        tier=args.tier,
        repoId=args.repo_id,
        remoteRoot=Path(args.remote_root) if args.remote_root else None,
        outDir=Path(args.out_dir) if args.out_dir else None,
        previousManifestPath=Path(args.previous_manifest) if args.previous_manifest else None,
        optionalFiles=args.optional_file,
    )
    print(json.dumps({"valid": report["valid"], "errors": report["errors"], "pulled": report["pulled"]}))
    return 0 if report["valid"] else 1


def pullCurrentIndex(
    *,
    tier: str = "full",
    repoId: str | None = None,
    remoteRoot: Path | None = None,
    outDir: Path | None = None,
    previousManifestPath: Path | None = None,
    optionalFiles: list[str] | None = None,
) -> dict[str, Any]:
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.publishIndex import contentIndexRepoPrefix

    tier = (tier or "full").strip()
    target = outDir or (_contentIndexDir() if tier == "full" else _contentIndexDir(tier))
    target.mkdir(parents=True, exist_ok=True)
    previousManifestPath = previousManifestPath or (target / "previous_manifest.json")
    repoPrefix = contentIndexRepoPrefix(tier=tier)
    download = _downloadHook(repoId=repoId, remoteRoot=remoteRoot)
    errors: list[str] = []
    pulled: list[str] = []

    try:
        manifestSrc = download(f"{repoPrefix}/manifest.json")
        manifest = json.loads(manifestSrc.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "valid": False,
            "errors": [f"manifest:{type(exc).__name__}"],
            "pulled": [],
            "outDir": str(target),
            "tier": tier,
        }

    manifestTarget = target / "manifest.json"
    _copyFile(manifestSrc, manifestTarget)
    _copyFile(manifestSrc, previousManifestPath)
    pulled.extend(["manifest.json", previousManifestPath.name])

    requiredFiles = _requiredFiles(manifest)
    fileSources = _fileSources(manifest)
    for rel in requiredFiles:
        if rel == "manifest.json":
            continue
        repoPath = _repoPathFor(rel, repoPrefix=repoPrefix, fileSources=fileSources)
        try:
            src = download(repoPath)
            _copyFile(src, target / rel)
            pulled.append(rel)
        except Exception as exc:
            errors.append(f"required:{rel}:{type(exc).__name__}")

    for rel in optionalFiles or []:
        if not rel or rel in requiredFiles:
            continue
        repoPath = _repoPathFor(rel, repoPrefix=repoPrefix, fileSources=fileSources)
        try:
            src = download(repoPath)
            _copyFile(src, target / rel)
            pulled.append(rel)
        except Exception:
            continue

    return {
        "valid": not errors,
        "errors": errors,
        "pulled": pulled,
        "outDir": str(target),
        "tier": tier,
        "repoPrefix": repoPrefix,
        "fileSourcesCount": len(fileSources),
        "requiredFiles": requiredFiles,
    }


def _downloadHook(*, repoId: str | None, remoteRoot: Path | None) -> Callable[[str], Path]:
    if remoteRoot is not None:

        def _downloadLocal(repoPath: str) -> Path:
            src = remoteRoot / repoPath
            if not src.exists():
                raise FileNotFoundError(repoPath)
            return src

        return _downloadLocal

    from dartlab.core.hfRetry import retryHfCall

    repo = repoId or _defaultRepoId()

    def _downloadHf(repoPath: str) -> Path:
        from huggingface_hub import hf_hub_download

        return Path(
            retryHfCall(
                hf_hub_download,
                repo_id=repo,
                repo_type="dataset",
                filename=repoPath,
                local_dir="data",
                token=os.environ.get("HF_TOKEN") or None,
            )
        )

    return _downloadHf


def _repoPathFor(rel: str, *, repoPrefix: str, fileSources: dict[str, str]) -> str:
    raw = fileSources.get(rel) or rel
    return raw if raw.startswith(f"{repoPrefix}/") else f"{repoPrefix}/{raw.lstrip('/')}"


def _requiredFiles(manifest: dict[str, Any]) -> list[str]:
    raw = manifest.get("requiredFiles") or []
    out = ["manifest.json"]
    if isinstance(raw, list):
        for rel in raw:
            if isinstance(rel, str) and rel and rel not in out:
                out.append(rel)
    return out


def _fileSources(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("fileSources")
    if not isinstance(raw, dict):
        return {}
    return {
        rel: repoPath
        for rel, repoPath in raw.items()
        if isinstance(rel, str) and isinstance(repoPath, str) and rel and repoPath
    }


def _copyFile(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.resolve() == dst.resolve():
            return
    except OSError:
        pass
    shutil.copyfile(src, dst)


def _defaultRepoId() -> str:
    from dartlab.core.dataConfig import repoFor

    return repoFor("contentIndex")


if __name__ == "__main__":
    raise SystemExit(main())
