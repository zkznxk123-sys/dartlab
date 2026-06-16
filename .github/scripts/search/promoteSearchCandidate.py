"""Promote a staged search contentIndex candidate manifest to current.

This script is intentionally small: build scripts can stage a candidate with
``DARTLAB_SEARCH_PROMOTE_CURRENT=0``; gates verify that candidate; only then
this script copies the staged pointer manifest to the current manifest path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest-path", required=True, help="Staged manifest path inside HF repo.")
    parser.add_argument("--tier", default="full", choices=["full", "lite"])
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests/offline drills.")
    parser.add_argument("--out", required=True, help="Promotion report JSON path.")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    report = promote(
        candidateManifestPath=args.candidate_manifest_path,
        tier=args.tier,
        repoId=args.repo_id,
        remoteRoot=Path(args.remote_root) if args.remote_root else None,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"promoted": report.get("promoted"), "errors": report.get("errors") or []}, ensure_ascii=False))
    if args.fail_on_error and not report.get("promoted"):
        return 1
    return 0


def promote(
    *,
    candidateManifestPath: str,
    tier: str,
    repoId: str | None = None,
    remoteRoot: Path | None = None,
) -> dict:
    from dartlab.providers.dart.search.publishIndex import promoteCandidateManifest

    try:
        return promoteCandidateManifest(
            token=os.environ.get("HF_TOKEN"),
            candidateManifestPath=candidateManifestPath,
            tier=tier,
            repoId=repoId,
            remoteRoot=remoteRoot,
        )
    except Exception as exc:  # noqa: BLE001 - operator report should preserve the failure.
        return {
            "promoted": False,
            "errors": [f"{type(exc).__name__}:{exc}"],
            "tier": tier,
            "candidateManifestPath": candidateManifestPath,
            "repoId": repoId or "",
            "remoteRoot": str(remoteRoot or ""),
        }


if __name__ == "__main__":
    raise SystemExit(main())
