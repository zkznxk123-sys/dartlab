"""Run a local end-to-end search pipeline drill.

The drill uses synthetic rows, not production data. It proves the operational
contract that a full source catalog can become a loadable contentIndex artifact,
publish through staging upload/current manifest pointer order, activate locally, and
roll back without contacting HuggingFace.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class LocalHfApi:
    """Tiny HfApi-compatible copier used by the local drill."""

    def __init__(self, remoteRoot: Path) -> None:
        self.remoteRoot = remoteRoot
        self.uploads: list[str] = []
        self.deletes: list[str] = []

    def upload_file(self, *, path_or_fileobj: str, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        src = Path(path_or_fileobj)
        dst = self.remoteRoot / path_in_repo
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        self.uploads.append(path_in_repo)

    def delete_file(self, *, path_in_repo: str, repo_id: str, repo_type: str) -> None:
        path = self.remoteRoot / path_in_repo
        if path.exists():
            path.unlink()
        self.deletes.append(path_in_repo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", help="Optional drill workspace. Defaults to a temporary directory.")
    parser.add_argument("--out", required=True, help="JSON report path.")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    if args.work_dir:
        workDir = Path(args.work_dir)
        workDir.mkdir(parents=True, exist_ok=True)
        report = _runDrill(workDir)
    else:
        with tempfile.TemporaryDirectory(prefix="dartlab-search-drill-") as tmp:
            report = _runDrill(Path(tmp))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"valid": report["valid"], "errors": report["errors"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    return 0


def _runDrill(workDir: Path) -> dict[str, Any]:
    import polars as pl

    from dartlab.providers.dart.search.fieldIndex import buildContentSegment, saveSegment
    from dartlab.providers.dart.search.fieldIndexRebuild import writeIndexManifest
    from dartlab.providers.dart.search.localUpdate import (
        activateStagedIndex,
        downloadAndActivateContentIndex,
        resolveActiveIndexDir,
        rollbackActiveIndex,
    )
    from dartlab.providers.dart.search.pipeline import (
        exportCatalogRowsForContentIndex,
        runCatalogDeltaDryRun,
    )
    from dartlab.providers.dart.search.publishIndex import (
        preflightContentIndexPublish,
        publishContentIndexFiles,
    )
    from dartlab.providers.dart.search.sourceCatalog import writeSourceCatalogArtifacts

    previousPath = workDir / "previous.catalog_snapshot.parquet"
    sourceRoot = workDir / "searchCatalog"
    sourceRawRoot = workDir / "sourceRaw"
    indexDir = workDir / "artifact"
    remoteRoot = workDir / "remote"
    activeBase = workDir / "localContentIndex"

    sourceFiles = _writeSourceInputParquets(sourceRawRoot)
    for source, files in sourceFiles.items():
        writeSourceCatalogArtifacts(
            source,
            files,
            outDir=sourceRoot / source,
            producer="runSearchPipelineDrill.source",
            producerRun={
                "system": "localDrill",
                "workflow": "runSearchPipelineDrill",
                "job": f"{source}-bootstrap",
                "runId": "local-drill",
                "sha": "local",
                "artifactName": f"search-catalog-{source}-local-drill",
            },
        )
    prepared = _prepareCanonicalCatalogInputs(sourceRoot, workDir)
    currentPath = Path(prepared["DARTLAB_SEARCH_CURRENT_CATALOG"])
    manifestSetPath = Path(prepared["DARTLAB_SEARCH_SOURCE_MANIFEST_SET"])
    manifestPaths = [Path(path) for path in prepared["DARTLAB_SEARCH_SOURCE_MANIFESTS"].split(os.pathsep) if path]
    currentCatalog = pl.read_parquet(currentPath)
    currentCatalog.head(1).write_parquet(previousPath)

    deltaReport = runCatalogDeltaDryRun(
        previousCatalogPath=previousPath,
        currentCatalogPath=currentPath,
        sourceManifestPaths=manifestPaths,
        expectedSources=["allFilings", "dartPanel", "edgarPanel", "newsPublic"],
    )
    rows = exportCatalogRowsForContentIndex(currentCatalog)
    idx, meta = buildContentSegment(rows.to_dicts(), showProgress=False)
    saveSegment(idx, meta, "main", outDir=indexDir)
    shutil.copyfile(currentPath, indexDir / "catalog_snapshot.parquet")
    shutil.copyfile(manifestSetPath, indexDir / "source_manifest_set.json")
    manifest = writeIndexManifest(indexDir, tier="full", buildCommand="runSearchPipelineDrill")
    _patchManifest(
        indexDir,
        {
            "builtAt": "2026-06-15T00:00:00",
            "canaryQueries": ["유상증자", "환율 리스크"],
            "sourceCanaryPack": [
                {
                    "query": "환율 리스크",
                    "target": "news",
                    "expectedSource": "news",
                },
                {
                    "query": "미등재특수어휘",
                    "target": "noAnswer",
                    "expectedAnswerable": False,
                },
            ],
        },
    )

    preflight = preflightContentIndexPublish(indexDir)
    api = LocalHfApi(remoteRoot)
    publish = publishContentIndexFiles(
        token=None,
        indexDir=indexDir,
        files=[*manifest["requiredFiles"], "manifest.json"],
        tier="full",
        runId="local-drill",
        api=api,
        repoId="local-repo",
    )

    oldActive = activeBase / "_staging" / "old"
    oldActive.mkdir(parents=True, exist_ok=True)
    oldIdx, oldMeta = buildContentSegment([_oldActiveRow()], showProgress=False)
    saveSegment(oldIdx, oldMeta, "main", outDir=oldActive)
    writeIndexManifest(oldActive, tier="full", buildCommand="runSearchPipelineDrill.old")
    _patchManifest(oldActive, {"builtAt": "2026-06-14T00:00:00", "canaryQueries": ["기존 공시"]})
    oldActivation = activateStagedIndex(oldActive, baseDir=activeBase)

    def fakeDownload(repoPath: str, downloadRoot: Path) -> Path:
        src = remoteRoot / repoPath
        if not src.exists():
            raise FileNotFoundError(repoPath)
        return src

    activation = downloadAndActivateContentIndex(
        tier="full",
        baseDir=activeBase,
        downloadFile=fakeDownload,
    )
    rollback = rollbackActiveIndex(baseDir=activeBase)
    activeAfterRollback = resolveActiveIndexDir(activeBase)

    errors = []
    if not deltaReport.get("valid"):
        errors.append("deltaReport")
    if not preflight.get("valid"):
        errors.append("preflight")
    if not manifest.get("sourceManifestSetId"):
        errors.append("sourceManifestSet")
    if not oldActivation.get("activated"):
        errors.append("oldActivation")
    if not activation.get("activated"):
        errors.append("activation")
    if not rollback.get("rolledBack"):
        errors.append("rollback")
    if activeAfterRollback != oldActive:
        errors.append("rollbackTarget")

    return {
        "valid": not errors,
        "errors": errors,
        "delta": deltaReport,
        "preflight": preflight,
        "sourceManifestSet": {
            "path": str(manifestSetPath),
            "id": manifest.get("sourceManifestSetId", ""),
            "sources": [item.get("source") for item in manifest.get("sourceManifestSet", {}).get("sources", [])],
        },
        "publish": {
            "stagingPrefix": publish["stagingPrefix"],
            "currentPrefix": publish["currentPrefix"],
            "publishMode": publish["publishMode"],
            "uploaded": publish["uploaded"],
        },
        "activation": activation,
        "rollback": rollback,
        "activeAfterRollback": str(activeAfterRollback or ""),
    }


def _writeSourceInputParquets(root: Path) -> dict[str, list[Path]]:
    import polars as pl

    allFilings = root / "allFilings" / "20260615.parquet"
    dartPanel = root / "dartPanel" / "005930.parquet"
    edgarPanel = root / "edgarPanel" / "AAPL.parquet"
    newsPublic = root / "newsPublic" / "20260615.parquet"
    for path in (allFilings, dartPanel, edgarPanel, newsPublic):
        path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "rcept_no": "20260615000001",
                "rcept_dt": "20260615",
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "report_nm": "주요사항보고서",
                "content_raw": "삼성전자는 유상증자 자금조달 계획을 공시했다.",
                "fetch_status": "ok",
            }
        ]
    ).write_parquet(allFilings)
    pl.DataFrame(
        [
            {
                "rceptNo": "20260615000002",
                "period": "2026Q2",
                "corp": "삼성전자",
                "sectionLeaf": "사업의 내용",
                "contentRaw": "HBM 반도체 투자는 생산능력 확대와 연결된다.",
            }
        ]
    ).write_parquet(dartPanel)
    pl.DataFrame(
        [
            {
                "rceptNo": "0000320193-26-000001",
                "ticker": "AAPL",
                "corp": "Apple Inc.",
                "filing_date": "2026-06-15",
                "period": "2026Q2",
                "sectionLeaf": "Risk Factors",
                "contentRaw": "Foreign exchange risk may affect revenue and margin.",
            }
        ]
    ).write_parquet(edgarPanel)
    pl.DataFrame(
        [
            {
                "url": "https://example.com/news/fx-risk",
                "date": "20260615",
                "title": "환율 리스크 뉴스",
                "content": "환율 리스크가 수출기업 실적에 부담이 된다는 뉴스 원문이다.",
            }
        ]
    ).write_parquet(newsPublic)
    return {
        "allFilings": [allFilings],
        "dartPanel": [dartPanel],
        "edgarPanel": [edgarPanel],
        "newsPublic": [newsPublic],
    }


def _prepareCanonicalCatalogInputs(sourceRoot: Path, workDir: Path) -> dict[str, str]:
    envFile = workDir / "canonical.env"
    current = workDir / "current.catalog_snapshot.parquet"
    manifestSet = workDir / "source_manifest_set.json"
    module = _loadSearchScript("prepareSearchDeltaInputs.py")
    rc = module.main(
        [
            "--source-dir",
            str(sourceRoot),
            "--previous",
            "",
            "--out-current",
            str(current),
            "--out-manifest-set",
            str(manifestSet),
            "--env-file",
            str(envFile),
            "--expected-sources",
            "allFilings,dartPanel,edgarPanel,newsPublic",
        ]
    )
    if rc != 0:
        raise RuntimeError(f"prepareSearchDeltaInputs failed: {rc}")
    env = _readEnvFile(envFile)
    required = {
        "DARTLAB_SEARCH_MAIN_MODE",
        "DARTLAB_SEARCH_CURRENT_CATALOG",
        "DARTLAB_SEARCH_SOURCE_MANIFESTS",
        "DARTLAB_SEARCH_SOURCE_MANIFEST_SET",
    }
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError(f"prepareSearchDeltaInputs did not set {missing}")
    if env["DARTLAB_SEARCH_MAIN_MODE"] != "catalog":
        raise RuntimeError("prepareSearchDeltaInputs did not enter catalog main mode")
    return env


def _loadSearchScript(name: str):
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"dartlabSearchScript_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load search script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _readEnvFile(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    return out


def _oldActiveRow() -> dict[str, Any]:
    return {
        "section_content": "기존 공시 검색 인덱스",
        "rcept_no": "20260614000001",
        "section_order": 0,
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "rcept_dt": "20260614",
        "report_nm": "기존공시",
        "section_title": "",
        "source": "allFilings",
        "sourceRef": "dart:allFilings:20260614000001#section=0",
        "sourceDataAsOf": "20260614",
    }


def _patchManifest(indexDir: Path, patch: dict[str, Any]) -> None:
    path = indexDir / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(patch)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
