"""Verify HF current manifest download, local activation, and rollback.

This is the operator-facing smoke for real contentIndex artifacts. By default
it uses a temporary local contentIndex base, so it can validate a real HF
current manifest without mutating the user's normal cache. Tests can pass
``--remote-root`` to exercise the same path against a local fake HF tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default="full", choices=["full", "lite"], help="contentIndex tier to verify.")
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests and offline drills.")
    parser.add_argument("--manifest-repo-path", help="Explicit staged candidate manifest path to verify.")
    parser.add_argument("--base-dir", help="Local contentIndex base. Defaults to a temporary directory.")
    parser.add_argument("--out", required=True, help="JSON report path.")
    parser.add_argument("--skip-rollback", action="store_true", help="Leave the downloaded artifact active.")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    if args.base_dir:
        baseDir = Path(args.base_dir)
        baseDir.mkdir(parents=True, exist_ok=True)
        report = runRoundTrip(
            tier=args.tier,
            baseDir=baseDir,
            repoId=args.repo_id,
            remoteRoot=Path(args.remote_root) if args.remote_root else None,
            manifestRepoPath=args.manifest_repo_path,
            rollback=not args.skip_rollback,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="dartlab-search-hf-roundtrip-") as tmp:
            report = runRoundTrip(
                tier=args.tier,
                baseDir=Path(tmp) / "contentIndex",
                repoId=args.repo_id,
                remoteRoot=Path(args.remote_root) if args.remote_root else None,
                manifestRepoPath=args.manifest_repo_path,
                rollback=not args.skip_rollback,
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"valid": report["valid"], "errors": report["errors"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    return 0


def runRoundTrip(
    *,
    tier: str,
    baseDir: Path,
    repoId: str | None = None,
    remoteRoot: Path | None = None,
    manifestRepoPath: str | None = None,
    rollback: bool = True,
) -> dict[str, Any]:
    from dartlab.providers.dart.search.localUpdate import (
        activateStagedIndex,
        downloadAndActivateContentIndex,
        loadActiveSearchManifest,
        resolveActiveIndexDir,
        rollbackActiveIndex,
    )

    baseDir.mkdir(parents=True, exist_ok=True)
    oldDir = _ensurePreviousActive(baseDir)
    oldActivation = activateStagedIndex(oldDir, baseDir=baseDir)

    activation = downloadAndActivateContentIndex(
        tier=tier,
        baseDir=baseDir,
        downloadFile=_downloadHook(repoId=repoId, remoteRoot=remoteRoot),
        manifestRepoPath=manifestRepoPath,
    )
    activeManifest = loadActiveSearchManifest(baseDir)
    activeDir = resolveActiveIndexDir(baseDir)

    rollbackResult: dict[str, Any] | None = None
    if rollback and activation.get("activated"):
        rollbackResult = rollbackActiveIndex(baseDir=baseDir)

    restoredManifest = loadActiveSearchManifest(baseDir)
    restoredDir = resolveActiveIndexDir(baseDir)

    errors: list[str] = []
    if not oldActivation.get("activated"):
        errors.append("oldActivation")
    if not activation.get("activated"):
        errors.extend(str(err) for err in activation.get("errors") or ["activation"])
        if activation.get("skipped"):
            errors.append(f"activationSkipped:{activation['skipped']}")
    if rollback and activation.get("activated"):
        if not rollbackResult or not rollbackResult.get("rolledBack"):
            errors.extend(str(err) for err in (rollbackResult or {}).get("errors") or ["rollback"])
        if restoredDir != oldDir:
            errors.append("rollbackTarget")

    return {
        "valid": not errors,
        "errors": errors,
        "tier": tier,
        "baseDir": str(baseDir),
        "repoId": repoId or _defaultRepoId(),
        "remoteRoot": str(remoteRoot or ""),
        "manifestRepoPath": manifestRepoPath or "",
        "previousActivation": oldActivation,
        "activation": activation,
        "activatedDir": str(activeDir or ""),
        "activatedManifest": _manifestSummary(activeManifest),
        "rollback": rollbackResult,
        "restoredDir": str(restoredDir or ""),
        "restoredManifest": _manifestSummary(restoredManifest),
    }


def _downloadHook(*, repoId: str | None, remoteRoot: Path | None):
    if remoteRoot is not None:

        def _downloadLocal(repoPath: str, downloadRoot: Path) -> Path:
            src = remoteRoot / repoPath
            if not src.exists():
                raise FileNotFoundError(repoPath)
            return src

        return _downloadLocal

    from dartlab.core.hfRetry import retryHfCall

    repo = repoId or _defaultRepoId()

    def _downloadHf(repoPath: str, downloadRoot: Path) -> Path:
        from huggingface_hub import hf_hub_download

        return Path(
            retryHfCall(
                hf_hub_download,
                repo_id=repo,
                repo_type="dataset",
                filename=repoPath,
                local_dir=str(downloadRoot),
            )
        )

    return _downloadHf


def _defaultRepoId() -> str:
    from dartlab.core.dataConfig import repoFor

    return repoFor("contentIndex")


def _ensurePreviousActive(baseDir: Path) -> Path:
    from dartlab.providers.dart.search.fieldIndex import buildContentSegment, saveSegment
    from dartlab.providers.dart.search.fieldIndexRebuild import writeIndexManifest

    oldDir = baseDir / "_staging" / "roundtrip-previous"
    if oldDir.exists():
        shutil.rmtree(oldDir)
    oldDir.mkdir(parents=True)
    rows = [
        {
            "section_content": "roundtrip previous active artifact",
            "rcept_no": "roundtrip-previous",
            "section_order": 0,
            "corp_code": "",
            "corp_name": "RoundTrip",
            "stock_code": "",
            "rcept_dt": "19000101",
            "report_nm": "Previous Active",
            "section_title": "",
            "source": "allFilings",
        }
    ]
    idx, meta = buildContentSegment(rows, showProgress=False)
    saveSegment(idx, meta, "main", outDir=oldDir)
    writeIndexManifest(oldDir, tier="full", buildCommand="verifySearchHfRoundTrip.previous")
    manifestPath = oldDir / "manifest.json"
    manifest = json.loads(manifestPath.read_text(encoding="utf-8"))
    manifest["builtAt"] = "1900-01-01T00:00:00"
    manifestPath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return oldDir


def _manifestSummary(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not manifest:
        return {}
    fileSources = manifest.get("fileSources") if isinstance(manifest.get("fileSources"), dict) else {}
    return {
        "artifactVersion": manifest.get("artifactVersion"),
        "schemaVersion": manifest.get("schemaVersion"),
        "builtAt": manifest.get("builtAt"),
        "publishMode": manifest.get("publishMode"),
        "sourceDataAsOf": manifest.get("sourceDataAsOf") or {},
        "nDocsBySource": manifest.get("nDocsBySource") or {},
        "requiredFiles": manifest.get("requiredFiles") or [],
        "fileSourcesCount": len(fileSources),
        "stagingPrefix": manifest.get("stagingPrefix") or "",
    }


if __name__ == "__main__":
    raise SystemExit(main())
