"""Plan search productization bootstrap actions from current remote evidence.

This script does not mutate GitHub or HuggingFace. It converts the remote
evidence report into an operator plan: source-owner bootstrap workflow
dispatches when source catalogs are missing, then the catalog-mode Search Main
run and evidence checks needed before S2 opsReady can become true.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_SOURCES = "allFilings,dartPanel,edgarPanel,newsPublic"
DEFAULT_TIERS = "full,lite"


SOURCE_BOOTSTRAP: dict[str, dict[str, Any]] = {
    "allFilings": {
        "workflow": "originalSync.yml",
        "inputs": {
            "jobs": "allfilings",
            "lookback_days": "30",
            "search_catalog_bootstrap": "true",
        },
        "reason": "Build initial allFilings search catalog from source-owner allFilings/recent parquet.",
        "minContract": "minFiles>=300, minRows>=150000, minCatalogRows>=150000",
    },
    "dartPanel": {
        "workflow": "originalSync.yml",
        "inputs": {
            "jobs": "dart-zip",
            "dart_full_rebuild": "true",
            "search_catalog_bootstrap": "true",
        },
        "reason": "Build initial DART panel search catalog from source-owner full panel rebuild.",
        "minContract": "minFiles>=2400, minRows>=90000, minCatalogRows>=90000",
    },
    "edgarPanel": {
        "workflow": "originalSync.yml",
        "inputs": {
            "jobs": "edgar",
            "edgar_full_rebuild": "true",
            "search_catalog_bootstrap": "true",
        },
        "reason": "Build initial EDGAR panel search catalog from source-owner full EDGAR panel rebuild.",
        "minContract": "minFiles>=2000, minRows>=50000, minCatalogRows>=50000",
    },
    "newsPublic": {
        "workflow": "newsArchiveSync.yml",
        "inputs": {
            "max_queries": "150",
            "search_catalog_bootstrap": "true",
        },
        "reason": "Build initial public-news search catalog from enriched public RSS artifacts.",
        "minContract": "minFiles>=1, minRows>=100, minCatalogRows>=100",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-evidence", help="Existing searchRemoteEvidence JSON. If omitted, audit now.")
    parser.add_argument(
        "--productization-status", help="Optional searchProductizationStatus JSON for semantic blockers."
    )
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests/offline planning.")
    parser.add_argument("--expected-sources", default=DEFAULT_SOURCES)
    parser.add_argument("--content-tiers", default=DEFAULT_TIERS)
    parser.add_argument("--out", help="Optional JSON output path.")
    args = parser.parse_args(argv)

    expectedSources = _splitCsv(args.expected_sources)
    contentTiers = _splitCsv(args.content_tiers)
    evidence = (
        _loadJson(Path(args.remote_evidence))
        if args.remote_evidence
        else _auditRemoteEvidence(args.repo_id, args.remote_root, expectedSources, contentTiers)
    )
    status = _loadJson(Path(args.productization_status)) if args.productization_status else {}
    plan = buildPlan(evidence, status=status, expectedSources=expectedSources, contentTiers=contentTiers)
    text = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        outPath = Path(args.out)
        outPath.parent.mkdir(parents=True, exist_ok=True)
        outPath.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def buildPlan(
    evidence: dict[str, Any],
    *,
    expectedSources: list[str],
    contentTiers: list[str],
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _statusBlockers(status or {})
    missingSources = _dedupe([*_missingSourceCatalogs(evidence, expectedSources), *_sourceBlockerSources(blockers)])
    missingContentTiers = _dedupe([*_missingContentTiers(evidence, contentTiers), *_contentBlockerTiers(blockers)])
    actions: list[dict[str, Any]] = []
    for source in missingSources:
        actions.append(_sourceBootstrapAction(source))
    if missingSources or missingContentTiers:
        actions.append(_searchMainAction(expectedSources))
    actions.extend(_verificationActions(expectedSources, contentTiers))
    return {
        "valid": not missingSources and not missingContentTiers,
        "missingSources": missingSources,
        "missingContentTiers": missingContentTiers,
        "actions": actions,
        "preconditions": [
            "Run these commands only after this checkout is committed and available to GitHub Actions.",
            "Do not use source_catalog_bootstrap=true for scheduled steady-state runs.",
            "After each source-owner run, inspect the search-catalog-* artifact and source_manifest producerRun.",
        ],
    }


def _sourceBootstrapAction(source: str) -> dict[str, Any]:
    spec = SOURCE_BOOTSTRAP.get(source)
    if not spec:
        return {
            "id": f"bootstrapSource:{source}",
            "source": source,
            "kind": "manualReview",
            "reason": "No known source-owner bootstrap workflow for this source.",
            "command": "",
            "argv": [],
        }
    argv = _workflowRunArgv(spec["workflow"], spec["inputs"])
    return {
        "id": f"bootstrapSource:{source}",
        "source": source,
        "kind": "githubWorkflowDispatch",
        "workflow": spec["workflow"],
        "inputs": spec["inputs"],
        "reason": spec["reason"],
        "minContract": spec["minContract"],
        "command": shlex.join(argv),
        "argv": argv,
    }


def _searchMainAction(expectedSources: list[str]) -> dict[str, Any]:
    inputs = {
        "build_mode": "catalog",
        "expected_sources": ",".join(expectedSources),
        "productization_gate": "ops",
    }
    argv = _workflowRunArgv("searchIndexBuild.yml", inputs)
    return {
        "id": "buildContentIndex:mainCatalog",
        "kind": "githubWorkflowDispatch",
        "workflow": "searchIndexBuild.yml",
        "inputs": inputs,
        "reason": "Publish full/lite contentIndex from source catalogs and produce ops evidence artifacts.",
        "command": shlex.join(argv),
        "argv": argv,
    }


def _verificationActions(expectedSources: list[str], contentTiers: list[str]) -> list[dict[str, Any]]:
    sources = ",".join(expectedSources)
    tiers = ",".join(contentTiers)
    remoteArgv = [
        "uv",
        "run",
        "python",
        "-X",
        "utf8",
        ".github/scripts/search/checkSearchRemoteEvidence.py",
        "--expected-sources",
        sources,
        "--content-tiers",
        tiers,
        "--out",
        "data/search/searchRemoteEvidence.bootstrap.json",
        "--fail-on-missing",
    ]
    proofArgv = [
        "uv",
        "run",
        "python",
        "-X",
        "utf8",
        ".github/scripts/search/buildSearchProofBundle.py",
        "--out-dir",
        "data/search/searchProofBundle.bootstrap",
        "--expected-sources",
        sources,
        "--content-tiers",
        tiers,
        "--run-hf-round-trip",
        "--fail-on-ops-not-ready",
    ]
    return [
        {
            "id": "verifyRemoteEvidence",
            "kind": "localCommand",
            "reason": "Confirm source catalogs, content manifests, fileSources, and source manifest set lineage exist remotely.",
            "command": shlex.join(remoteArgv),
            "argv": remoteArgv,
        },
        {
            "id": "verifyOpsProofBundle",
            "kind": "localCommand",
            "reason": "Confirm design/ops readiness from remote evidence, local indexInfo, result contract, canary, and HF round-trip.",
            "command": shlex.join(proofArgv),
            "argv": proofArgv,
        },
    ]


def _workflowRunArgv(workflow: str, inputs: dict[str, str]) -> list[str]:
    argv = ["gh", "workflow", "run", workflow]
    for key, value in inputs.items():
        argv.extend(["-f", f"{key}={value}"])
    return argv


def _missingSourceCatalogs(evidence: dict[str, Any], expectedSources: list[str]) -> list[str]:
    catalog = evidence.get("sourceCatalog") if isinstance(evidence.get("sourceCatalog"), dict) else {}
    missing = catalog.get("missingSources")
    if isinstance(missing, list):
        return [source for source in expectedSources if source in {str(item) for item in missing}]
    sources = catalog.get("sources") if isinstance(catalog.get("sources"), dict) else {}
    out: list[str] = []
    for source in expectedSources:
        item = sources.get(source) if isinstance(sources, dict) else None
        if not isinstance(item, dict) or not item.get("manifestExists") or not item.get("catalogExists"):
            out.append(source)
    return out


def _missingContentTiers(evidence: dict[str, Any], contentTiers: list[str]) -> list[str]:
    content = evidence.get("contentIndex") if isinstance(evidence.get("contentIndex"), dict) else {}
    manifests = content.get("manifests") if isinstance(content.get("manifests"), dict) else {}
    out: list[str] = []
    for tier in contentTiers:
        item = manifests.get(tier) if isinstance(manifests, dict) else None
        if not isinstance(item, dict) or not item.get("exists"):
            out.append(tier)
    return out


def _statusBlockers(status: dict[str, Any]) -> list[str]:
    raw = status.get("blockers")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item)]


def _sourceBlockerSources(blockers: list[str]) -> list[str]:
    prefixes = (
        "sourceCatalogManifestMissing:",
        "sourceCatalogNotFull:",
        "sourceCatalogMissingDataAsOf:",
        "sourceCatalogEmptyRows:",
        "sourceCatalogEmptyFiles:",
        "sourceCatalogMissingProducerRun:",
        "sourceCatalogMissingProducerRunField:",
        "remoteContentManifestSetMissingProducerRun:",
    )
    sources: list[str] = []
    for blocker in blockers:
        if not blocker.startswith(prefixes):
            continue
        parts = blocker.split(":")
        if blocker.startswith("remoteContentManifestSetMissingProducerRun:") and len(parts) >= 3:
            sources.append(parts[2])
        elif len(parts) >= 2:
            sources.append(parts[1])
    return _dedupe([source for source in sources if source in SOURCE_BOOTSTRAP])


def _contentBlockerTiers(blockers: list[str]) -> list[str]:
    prefixes = (
        "remoteContent",
        "contentIndexManifestMissing",
        "contentIndexFileSourceMissing",
    )
    tiers: list[str] = []
    for blocker in blockers:
        if not blocker.startswith(prefixes):
            continue
        parts = blocker.split(":")
        if len(parts) >= 2 and parts[1] in {"full", "lite"}:
            tiers.append(parts[1])
        else:
            tiers.extend(["full", "lite"])
    return _dedupe(tiers)


def _auditRemoteEvidence(
    repoId: str | None,
    remoteRoot: str | None,
    expectedSources: list[str],
    contentTiers: list[str],
) -> dict[str, Any]:
    module = _loadScriptModule("checkSearchRemoteEvidence.py")
    return module.auditRemoteEvidence(
        repoId=repoId or module._defaultRepoId(),  # noqa: SLF001 - script-local default.
        remoteRoot=Path(remoteRoot) if remoteRoot else None,
        expectedSources=expectedSources,
        contentTiers=contentTiers,
    )


def _loadScriptModule(name: str) -> Any:
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _loadJson(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def _splitCsv(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


if __name__ == "__main__":
    sys.exit(main())
