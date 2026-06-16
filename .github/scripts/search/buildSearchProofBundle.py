"""Build one search productization proof bundle.

The bundle is intentionally evidence-first. It does not publish or mutate
remote data. It gathers the reports that decide design/ops/release readiness,
then writes a final productization status report next to the raw evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_QUERIES = (
    "유상증자",
    "공시 말고 뉴스로 환율 기사",
    "HBM 투자 계획",
)
DEFAULT_SOURCES = "allFilings,dartPanel,edgarPanel,newsPublic"
DEFAULT_TIERS = "full,lite"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, help="Directory for proof bundle JSON artifacts.")
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests/offline drills.")
    parser.add_argument("--expected-sources", default=DEFAULT_SOURCES)
    parser.add_argument("--content-tiers", default=DEFAULT_TIERS)
    parser.add_argument("--query", action="append", default=[], help="Result-contract smoke query.")
    parser.add_argument("--queries-json", help="JSON/JSONL query list for result-contract smoke.")
    parser.add_argument("--local-index-info", help="Existing dartlab.search.indexInfo() JSON report.")
    parser.add_argument("--result-contract-report", help="Existing result contract report.")
    parser.add_argument("--result-contract-results-json", help="Precomputed result rows for result contract.")
    parser.add_argument("--canary-report", help="Existing canary report.")
    parser.add_argument("--canary", help="Canary JSON/JSONL pack path.")
    parser.add_argument("--canary-manifest", help="Manifest JSON containing sourceCanaryPack.")
    parser.add_argument("--canary-results-json", help="Precomputed canary results by query.")
    parser.add_argument("--quality-report", help="Existing query-log quality report.")
    parser.add_argument("--quality-gold", help="Reviewed real query-log gold JSON/JSONL.")
    parser.add_argument("--quality-results-json", help="Precomputed search results by quality-gold query.")
    parser.add_argument(
        "--miss-ledger", help="Miss ledger output path. Defaults inside out-dir when quality-gold is set."
    )
    parser.add_argument("--hf-round-trip", action="append", default=[], help="Existing HF round-trip report.")
    parser.add_argument("--run-hf-round-trip", action="store_true", help="Run full/lite HF round-trip checks now.")
    parser.add_argument("--skip-result-contract", action="store_true")
    parser.add_argument("--skip-canary", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--min-result-rows", type=int, default=3)
    parser.add_argument("--min-quality-rows", type=int, default=100)
    parser.add_argument("--required-targets", default="filing,news,noAnswer,edgar")
    parser.add_argument("--allow-proxy-query-log", action="store_true")
    parser.add_argument("--fail-on-ops-not-ready", action="store_true")
    parser.add_argument("--fail-on-release-not-ready", action="store_true")
    args = parser.parse_args(argv)
    queries = list(args.query)
    if args.queries_json:
        queries.extend(_loadQueries(args.queries_json))

    report = buildProofBundle(
        outDir=Path(args.out_dir),
        repoId=args.repo_id or _defaultRepoId(),
        remoteRoot=Path(args.remote_root) if args.remote_root else None,
        expectedSources=_splitCsv(args.expected_sources),
        contentTiers=_splitCsv(args.content_tiers),
        queries=queries,
        localIndexInfoPath=Path(args.local_index_info) if args.local_index_info else None,
        resultContractReportPath=Path(args.result_contract_report) if args.result_contract_report else None,
        resultContractResultsPath=Path(args.result_contract_results_json)
        if args.result_contract_results_json
        else None,
        canaryReportPath=Path(args.canary_report) if args.canary_report else None,
        canaryPath=Path(args.canary) if args.canary else None,
        canaryManifestPath=Path(args.canary_manifest) if args.canary_manifest else None,
        canaryResultsPath=Path(args.canary_results_json) if args.canary_results_json else None,
        qualityReportPath=Path(args.quality_report) if args.quality_report else None,
        qualityGoldPath=Path(args.quality_gold) if args.quality_gold else None,
        qualityResultsPath=Path(args.quality_results_json) if args.quality_results_json else None,
        missLedgerPath=Path(args.miss_ledger) if args.miss_ledger else None,
        hfRoundTripPaths=[Path(path) for path in args.hf_round_trip],
        runHfRoundTrip=args.run_hf_round_trip,
        skipResultContract=args.skip_result_contract,
        skipCanary=args.skip_canary,
        skipQuality=args.skip_quality,
        limit=args.limit,
        scope=args.scope,
        minResultRows=args.min_result_rows,
        minQualityRows=args.min_quality_rows,
        requiredTargets=_splitCsv(args.required_targets),
        allowProxyQueryLog=args.allow_proxy_query_log,
    )

    print(
        json.dumps(
            {
                "opsReady": report["status"]["opsReady"],
                "releaseReady": report["status"]["releaseReady"],
                "blockers": report["status"]["blockers"],
                "bundle": report["bundlePath"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.fail_on_release_not_ready and not report["status"]["releaseReady"]:
        return 1
    if args.fail_on_ops_not_ready and not report["status"]["opsReady"]:
        return 1
    return 0


def buildProofBundle(
    *,
    outDir: Path,
    repoId: str,
    remoteRoot: Path | None,
    expectedSources: list[str],
    contentTiers: list[str],
    queries: list[str],
    localIndexInfoPath: Path | None = None,
    resultContractReportPath: Path | None = None,
    resultContractResultsPath: Path | None = None,
    canaryReportPath: Path | None = None,
    canaryPath: Path | None = None,
    canaryManifestPath: Path | None = None,
    canaryResultsPath: Path | None = None,
    qualityReportPath: Path | None = None,
    qualityGoldPath: Path | None = None,
    qualityResultsPath: Path | None = None,
    missLedgerPath: Path | None = None,
    hfRoundTripPaths: list[Path] | None = None,
    runHfRoundTrip: bool = False,
    skipResultContract: bool = False,
    skipCanary: bool = False,
    skipQuality: bool = False,
    limit: int = 10,
    scope: str = "auto",
    minResultRows: int = 3,
    minQualityRows: int = 100,
    requiredTargets: list[str] | None = None,
    allowProxyQueryLog: bool = False,
) -> dict[str, Any]:
    outDir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, str] = {}
    missing: list[str] = []

    remoteEvidence = outDir / "searchRemoteEvidence.json"
    _writeRemoteEvidence(
        remoteEvidence, repoId=repoId, expectedSources=expectedSources, contentTiers=contentTiers, remoteRoot=remoteRoot
    )
    reports["remoteEvidence"] = str(remoteEvidence)

    localInfo = outDir / "localIndexInfo.json"
    if localIndexInfoPath:
        _copyJson(localIndexInfoPath, localInfo)
    else:
        _writeLocalIndexInfo(localInfo)
    reports["localIndexInfo"] = str(localInfo)

    resultContract = outDir / "searchResultContract.json"
    if resultContractReportPath and resultContractReportPath.exists():
        _copyJson(resultContractReportPath, resultContract)
        reports["resultContract"] = str(resultContract)
    elif resultContractReportPath:
        missing.append("resultContract")
    elif not skipResultContract:
        _writeResultContract(
            resultContract,
            queries=queries or list(DEFAULT_QUERIES),
            resultsPath=resultContractResultsPath,
            limit=limit,
            scope=scope,
            minRows=minResultRows,
        )
        reports["resultContract"] = str(resultContract)
    else:
        missing.append("resultContract")

    canaryReport = outDir / "searchCanary.json"
    if canaryReportPath and canaryReportPath.exists():
        _copyJson(canaryReportPath, canaryReport)
        reports["canary"] = str(canaryReport)
    elif canaryReportPath:
        missing.append("canary")
    elif not skipCanary:
        manifest = canaryManifestPath or _defaultActiveManifest()
        if canaryPath or manifest:
            _writeCanaryReport(
                canaryReport,
                canaryPath=canaryPath,
                manifestPath=manifest,
                resultsPath=canaryResultsPath,
                limit=limit,
                scope=scope,
            )
            reports["canary"] = str(canaryReport)
        else:
            missing.append("canary")
    else:
        missing.append("canary")

    qualityReport = outDir / "searchQuality.json"
    if qualityReportPath and qualityReportPath.exists():
        _copyJson(qualityReportPath, qualityReport)
        reports["quality"] = str(qualityReport)
    elif qualityReportPath:
        missing.append("quality")
    elif qualityGoldPath and not skipQuality:
        ledger = missLedgerPath or (outDir / "searchMissLedger.jsonl")
        _writeQualityReport(
            qualityReport,
            missLedgerPath=ledger,
            goldPath=qualityGoldPath,
            resultsPath=qualityResultsPath,
            limit=limit,
            scope=scope,
            minRows=minQualityRows,
            requiredTargets=requiredTargets or ["filing", "news", "noAnswer", "edgar"],
            requireRealReviewed=not allowProxyQueryLog,
        )
        reports["quality"] = str(qualityReport)
        reports["missLedger"] = str(ledger)
    else:
        missing.append("quality")

    roundTripReports = [
        _copyRoundTrip(path, outDir, index=i) for i, path in enumerate(hfRoundTripPaths or []) if path.exists()
    ]
    if runHfRoundTrip:
        roundTripReports.extend(
            _writeRoundTripReports(outDir, tiers=contentTiers, repoId=repoId, remoteRoot=remoteRoot)
        )
    for i, path in enumerate(roundTripReports):
        reports[f"hfRoundTrip:{i}"] = str(path)
    if not roundTripReports:
        missing.append("hfRoundTrip")

    statusPath = outDir / "searchProductizationStatus.json"
    status = _writeProductizationStatus(
        statusPath,
        repoId=repoId,
        expectedSources=expectedSources,
        contentTiers=contentTiers,
        remoteRoot=remoteRoot,
        remoteEvidencePath=remoteEvidence,
        localIndexInfoPath=localInfo,
        resultContractPath=Path(reports["resultContract"]) if "resultContract" in reports else None,
        canaryReportPath=Path(reports["canary"]) if "canary" in reports else None,
        qualityReportPath=Path(reports["quality"]) if "quality" in reports else None,
        hfRoundTripPaths=roundTripReports,
    )
    reports["productizationStatus"] = str(statusPath)
    nextActions: dict[str, Any] = {}
    if _needsBootstrapPlan(status.get("blockers") or []):
        bootstrapPlan = outDir / "searchBootstrapPlan.json"
        plan = _writeBootstrapPlan(
            bootstrapPlan,
            remoteEvidencePath=remoteEvidence,
            status=status,
            expectedSources=expectedSources,
            contentTiers=contentTiers,
        )
        reports["bootstrapPlan"] = str(bootstrapPlan)
        nextActions["bootstrapPlan"] = {
            "path": str(bootstrapPlan),
            "missingSources": plan.get("missingSources") or [],
            "missingContentTiers": plan.get("missingContentTiers") or [],
            "actionIds": [str(action.get("id") or "") for action in plan.get("actions", []) if action.get("id")],
        }

    bundlePath = outDir / "searchProofBundle.json"
    bundle = {
        "valid": bool(status.get("opsReady")),
        "releaseReady": bool(status.get("releaseReady")),
        "opsReady": bool(status.get("opsReady")),
        "blockers": status.get("blockers") or [],
        "missingEvidence": sorted(set(missing)),
        "reports": reports,
        "expectedSources": expectedSources,
        "contentTiers": contentTiers,
        "nextActions": nextActions,
    }
    bundlePath.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"bundlePath": str(bundlePath), "bundle": bundle, "status": status}


def _needsBootstrapPlan(blockers: list[Any]) -> bool:
    remotePrefixes = (
        "missingRemoteEvidence",
        "sourceCatalog",
        "remoteContent",
        "contentIndexManifestMissing",
    )
    return any(str(blocker).startswith(remotePrefixes) for blocker in blockers)


def _writeBootstrapPlan(
    out: Path,
    *,
    remoteEvidencePath: Path,
    status: dict[str, Any],
    expectedSources: list[str],
    contentTiers: list[str],
) -> dict[str, Any]:
    mod = _loadScriptModule("planSearchBootstrap.py")
    remoteEvidence = json.loads(remoteEvidencePath.read_text(encoding="utf-8"))
    if not isinstance(remoteEvidence, dict):
        remoteEvidence = {"valid": False, "loadError": "notObject"}
    plan = mod.buildPlan(remoteEvidence, status=status, expectedSources=expectedSources, contentTiers=contentTiers)
    _writeJson(out, plan)
    return plan


def _writeRemoteEvidence(
    out: Path,
    *,
    repoId: str,
    expectedSources: list[str],
    contentTiers: list[str],
    remoteRoot: Path | None,
) -> None:
    mod = _loadScriptModule("checkSearchRemoteEvidence.py")
    report = mod.auditRemoteEvidence(
        repoId=repoId,
        expectedSources=expectedSources,
        contentTiers=contentTiers,
        remoteRoot=remoteRoot,
    )
    _writeJson(out, report)


def _writeLocalIndexInfo(out: Path) -> None:
    try:
        import dartlab

        info = dartlab.search.indexInfo()
        payload = dict(info) if isinstance(info, dict) else {"available": False, "loadError": "notObject"}
    except Exception as exc:  # noqa: BLE001 - proof bundle must preserve the failure as evidence.
        payload = {"available": False, "compatible": False, "loadError": f"{type(exc).__name__}:{exc}"}
    _writeJson(out, payload)


def _writeResultContract(
    out: Path,
    *,
    queries: list[str],
    resultsPath: Path | None,
    limit: int,
    scope: str,
    minRows: int,
) -> None:
    from dartlab.providers.dart.search.resultContract import (
        auditSearchResultRows,
        flattenResultRows,
        loadResultRows,
        writeResultContractReport,
    )

    if resultsPath:
        rows = loadResultRows(resultsPath)
    else:
        rows = flattenResultRows(_runSearchQueries(queries, limit=limit, scope=scope))
    report = auditSearchResultRows(rows, minRows=minRows)
    writeResultContractReport(out, report)


def _writeCanaryReport(
    out: Path,
    *,
    canaryPath: Path | None,
    manifestPath: Path | None,
    resultsPath: Path | None,
    limit: int,
    scope: str,
) -> None:
    from dartlab.providers.dart.search.canaryPack import (
        evaluateCanaryPack,
        evaluateCanaryPackRows,
        loadCanaryPack,
        writeCanaryReport,
    )

    if canaryPath:
        canaries = loadCanaryPack(canaryPath)
    elif manifestPath:
        manifest = json.loads(manifestPath.read_text(encoding="utf-8"))
        rows = manifest.get("sourceCanaryPack") if isinstance(manifest, dict) else None
        if not isinstance(rows, list):
            raise ValueError(f"manifest does not contain sourceCanaryPack: {manifestPath}")
        canaries = [dict(row) for row in rows]
    else:
        raise ValueError("--canary or --canary-manifest is required")
    resultsByQuery = _loadResultsByQuery(resultsPath)
    if resultsByQuery is None:
        from dartlab.providers.dart.search.api import search

        report = evaluateCanaryPack(canaries, search, limit=limit, scope=scope)
    else:
        report = evaluateCanaryPackRows(canaries, resultsByQuery, defaultTopK=limit)
    writeCanaryReport(out, report)


def _writeQualityReport(
    out: Path,
    *,
    missLedgerPath: Path,
    goldPath: Path,
    resultsPath: Path | None,
    limit: int,
    scope: str,
    minRows: int,
    requiredTargets: list[str],
    requireRealReviewed: bool,
) -> None:
    from dartlab.providers.dart.search.qualityGate import (
        buildMissLedgerRows,
        evaluateQueryGoldRows,
        loadQueryGold,
        writeMissLedger,
    )

    goldRows = loadQueryGold(goldPath)
    resultsByQuery = _loadResultsByQuery(resultsPath)
    if resultsByQuery is None:
        resultsByQuery = _runSearchGold(goldRows, limit=limit, scope=scope)
    report = evaluateQueryGoldRows(
        goldRows,
        resultsByQuery,
        minRows=minRows,
        requiredTargets=requiredTargets,
        requireRealReviewed=requireRealReviewed,
    )
    _writeJson(out, report)
    writeMissLedger(missLedgerPath, buildMissLedgerRows(goldRows, resultsByQuery))


def _writeRoundTripReports(
    outDir: Path,
    *,
    tiers: list[str],
    repoId: str,
    remoteRoot: Path | None,
) -> list[Path]:
    mod = _loadScriptModule("verifySearchHfRoundTrip.py")
    out: list[Path] = []
    for tier in tiers:
        with tempfile.TemporaryDirectory(prefix=f"dartlab-search-proof-{tier}-") as tmp:
            report = mod.runRoundTrip(
                tier=tier,
                baseDir=Path(tmp) / "contentIndex",
                repoId=repoId,
                remoteRoot=remoteRoot,
                rollback=True,
            )
        path = outDir / f"searchHfRoundTrip.{tier}.json"
        _writeJson(path, report)
        out.append(path)
    return out


def _writeProductizationStatus(
    out: Path,
    *,
    repoId: str,
    expectedSources: list[str],
    contentTiers: list[str],
    remoteRoot: Path | None,
    remoteEvidencePath: Path,
    localIndexInfoPath: Path,
    resultContractPath: Path | None,
    canaryReportPath: Path | None,
    qualityReportPath: Path | None,
    hfRoundTripPaths: list[Path],
) -> dict[str, Any]:
    mod = _loadScriptModule("evaluateSearchProductizationStatus.py")
    report = mod.evaluateProductizationStatus(
        repoId=repoId,
        expectedSources=expectedSources,
        contentTiers=contentTiers,
        remoteRoot=remoteRoot,
        remoteEvidencePath=remoteEvidencePath,
        resultContractPath=resultContractPath,
        qualityReportPath=qualityReportPath,
        canaryReportPath=canaryReportPath,
        hfRoundTripPaths=hfRoundTripPaths,
        localIndexInfoPath=localIndexInfoPath,
    )
    _writeJson(out, report)
    return report


def _copyRoundTrip(path: Path, outDir: Path, *, index: int) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    tier = str(data.get("tier") or index).replace("/", "-")
    dst = outDir / f"searchHfRoundTrip.{tier}.json"
    _writeJson(dst, data)
    return dst


def _copyJson(src: Path, dst: Path) -> None:
    data = json.loads(src.read_text(encoding="utf-8"))
    _writeJson(dst, data)


def _writeJson(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _runSearchQueries(queries: Iterable[str], *, limit: int, scope: str) -> list[dict[str, Any]]:
    from dartlab.providers.dart.search.api import search

    out: list[dict[str, Any]] = []
    for query in queries:
        df = search(str(query), limit=limit, scope=scope)
        out.append({"query": str(query), "results": df.to_dicts()})
    return out


def _runSearchGold(goldRows: list[dict[str, Any]], *, limit: int, scope: str) -> dict[str, list[dict[str, Any]]]:
    from dartlab.providers.dart.search.api import search

    out: dict[str, list[dict[str, Any]]] = {}
    for row in goldRows:
        query = str(row.get("query") or "")
        if query and query not in out:
            out[query] = search(query, limit=limit, scope=scope).to_dicts()
    return out


def _loadResultsByQuery(path: Path | None) -> dict[str, list[dict[str, Any]]] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(query): [dict(row) for row in rows] for query, rows in data.items()}
    if isinstance(data, list):
        out: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            if isinstance(item, dict):
                rows = [dict(row) for row in item.get("results", [])]
                for key in _resultKeys(item):
                    out[key] = rows
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _resultKeys(item: Mapping[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("query", "queryId", "id"):
        key = str(item.get(field) or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _loadQueries(path: str) -> list[str]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".jsonl":
        return [
            str(json.loads(line).get("query") if line.strip().startswith("{") else line).strip()
            for line in text.splitlines()
            if line.strip()
        ]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [
            str(item.get("query") if isinstance(item, dict) else item).strip() for item in data if str(item).strip()
        ]
    if isinstance(data, dict):
        rows = data.get("queries") or data.get("rows")
        if isinstance(rows, list):
            return [
                str(item.get("query") if isinstance(item, dict) else item).strip() for item in rows if str(item).strip()
            ]
    raise ValueError(f"unsupported queries-json shape: {path}")


def _defaultActiveManifest() -> Path | None:
    try:
        from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
        from dartlab.providers.dart.search.localUpdate import resolveActiveIndexDir

        base = _contentIndexDir()
        active = resolveActiveIndexDir(base)
        candidates = [active / "manifest.json"] if active is not None else []
        candidates.extend([base / "manifest.json", base / "lite" / "manifest.json"])
        return next((path for path in candidates if path.exists()), None)
    except Exception:  # noqa: BLE001 - missing runtime index should become missing evidence.
        return None


def _loadScriptModule(name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(f"_dartlab_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _splitCsv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _defaultRepoId() -> str:
    from dartlab.core.dataConfig import repoFor

    return repoFor("contentIndex")


if __name__ == "__main__":
    raise SystemExit(main())
