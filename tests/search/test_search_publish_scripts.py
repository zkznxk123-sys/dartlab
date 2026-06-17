"""Search publish script contract tests."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _assignedStringList(path: Path, functionName: str, variableName: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != functionName:
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == variableName for target in stmt.targets):
                continue
            if not isinstance(stmt.value, ast.List):
                continue
            return [
                elt.value for elt in stmt.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    return []


def test_search_main_publish_includes_manifest() -> None:
    text = Path(".github/scripts/search/buildSearchMain.py").read_text(encoding="utf-8")
    assert "writeIndexManifest(outDir" in text
    assert '"manifest.json"' in text
    assert '"source_manifest_set.json"' in text
    assert '"entityGraphCatalog.parquet"' in text
    assert "DARTLAB_SEARCH_SOURCE_MANIFEST_SET" in text
    assert "publishContentIndexFiles" in text
    assert "obsoleteCurrentFiles" in text
    assert "DARTLAB_SEARCH_MAIN_MODE" in text
    assert "DARTLAB_SEARCH_MAIN_ONLY" in text
    assert 'mainOnly == "lite"' in text
    assert "prepareEntityGraphCatalogArtifact" in text
    assert "rebuildMainFromCatalog" in text
    assert "[lite] HF_TOKEN 없음" in text


def test_search_main_publish_file_list_includes_catalog_snapshot() -> None:
    files = _assignedStringList(Path(".github/scripts/search/buildSearchMain.py"), "main", "files")

    assert "catalog_snapshot.parquet" in files


def test_push_content_index_file_list_includes_catalog_snapshot() -> None:
    files = _assignedStringList(
        Path("src/dartlab/providers/dart/search/fieldIndexRebuild.py"), "pushContentIndex", "names"
    )

    assert "catalog_snapshot.parquet" in files


def test_search_main_lite_catalog_filter_uses_date() -> None:
    import polars as pl

    path = Path(".github/scripts/search/buildSearchMain.py")
    spec = importlib.util.spec_from_file_location("buildSearchMainForTest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    catalog = pl.DataFrame(
        [
            {"docKey": "old", "date": "20240101"},
            {"docKey": "recent", "date": "20250101"},
            {"docKey": "dash", "date": "2025-03-01"},
        ]
    )
    filtered = module._filterLiteCatalogRows(catalog, "20250101")

    assert filtered["docKey"].to_list() == ["recent", "dash"]


def test_search_delta_publish_includes_manifest() -> None:
    text = Path(".github/scripts/search/buildSearchDelta.py").read_text(encoding="utf-8")
    assert '"manifest.json"' in text
    assert '"catalog_snapshot.parquet"' in text
    assert '"source_manifest_set.json"' in text
    assert '"entityGraphCatalog.parquet"' in text
    assert "DARTLAB_SEARCH_SOURCE_MANIFEST_SET" in text
    assert "publishContentIndexFiles" in text
    assert "previous_manifest.json" in text
    assert "prepareEntityGraphCatalogArtifact" in text


def test_search_publish_helper_uses_staging_and_manifest_pointer() -> None:
    text = Path("src/dartlab/providers/dart/search/publishIndex.py").read_text(encoding="utf-8")
    assert "_staging" in text
    assert "MANIFEST_NAME" in text
    assert "orderedPublishFiles" in text
    assert "currentPrefix" in text
    assert "manifestPointer" in text
    assert "fileSources" in text
    assert "preflightContentIndexPublish" in text
    assert "contentIndex publish selfcheck failed" in text
    assert "create_commit" in text
    assert "CommitOperationAdd" in text


def test_search_delta_script_exposes_catalog_dry_run() -> None:
    text = Path(".github/scripts/search/buildSearchDelta.py").read_text(encoding="utf-8")
    assert "DARTLAB_SEARCH_DELTA_DRY_RUN" in text
    assert "runCatalogDeltaDryRun" in text
    assert "DARTLAB_SEARCH_DELTA_MODE" in text
    assert "_previousManifestHasDelta" in text
    assert "_compactCatalogMain" in text
    assert "buildSearchDelta.catalogCompaction" in text
    assert "previous current has delta" in text


def test_pull_search_current_index_script_exists() -> None:
    text = Path(".github/scripts/search/pullSearchCurrentIndex.py").read_text(encoding="utf-8")
    assert "fileSources" in text
    assert "previous_manifest.json" in text
    assert "requiredFiles" in text


def test_promote_search_candidate_script_exists() -> None:
    text = Path(".github/scripts/search/promoteSearchCandidate.py").read_text(encoding="utf-8")
    assert "promoteCandidateManifest" in text
    assert "--candidate-manifest-path" in text
    assert "--fail-on-error" in text


def test_search_proof_bundle_script_exists() -> None:
    text = Path(".github/scripts/search/buildSearchProofBundle.py").read_text(encoding="utf-8")
    assert "searchProofBundle.json" in text
    assert "evaluateSearchProductizationStatus.py" in text
    assert "missingEvidence" in text


def test_search_replacement_evidence_script_exists() -> None:
    text = Path(".github/scripts/search/buildSearchReplacementEvidence.py").read_text(encoding="utf-8")
    assert "buildReplacementEvidence" in text
    assert "defaultBuildMode" in text
    assert "scheduledBuildMode" in text
    assert "legacyFallbackOperatorOnly" in text
    assert "failClosedPublish" in text
    assert "activeManifestId" in text
    assert "previousManifestId" in text


def test_search_delta_script_dry_run_subprocess(tmp_path) -> None:
    import polars as pl

    prev = tmp_path / "prev.parquet"
    curr = tmp_path / "curr.parquet"
    manifest = tmp_path / "source.json"
    report = tmp_path / "report.json"
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "old"}]).write_parquet(prev)
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "new"}]).write_parquet(curr)
    manifest.write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [{"path": "x.parquet", "rowCount": 1}],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "DARTLAB_SEARCH_DELTA_DRY_RUN": "1",
        "DARTLAB_SEARCH_PREVIOUS_CATALOG": str(prev),
        "DARTLAB_SEARCH_CURRENT_CATALOG": str(curr),
        "DARTLAB_SEARCH_SOURCE_MANIFESTS": str(manifest),
        "DARTLAB_SEARCH_DELTA_REPORT": str(report),
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", ".github/scripts/search/buildSearchDelta.py"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["delta"]["changedDocs"] == 1


def test_search_delta_script_catalog_build_subprocess(tmp_path) -> None:
    import polars as pl

    prev = tmp_path / "prev.parquet"
    curr = tmp_path / "curr.parquet"
    manifest = tmp_path / "source.json"
    dataDir = tmp_path / "data"
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "old"}]).write_parquet(prev)
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "new 유상증자"}]).write_parquet(curr)
    manifest.write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [{"path": "x.parquet", "rowCount": 1}],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "HF_TOKEN": "",
        "DARTLAB_DATA_DIR": str(dataDir),
        "DARTLAB_SEARCH_DELTA_FROM_CATALOG": "1",
        "DARTLAB_SEARCH_PREVIOUS_CATALOG": str(prev),
        "DARTLAB_SEARCH_CURRENT_CATALOG": str(curr),
        "DARTLAB_SEARCH_SOURCE_MANIFESTS": str(manifest),
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", ".github/scripts/search/buildSearchDelta.py"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    outDir = dataDir / "dart" / "contentIndex"
    assert (outDir / "delta.npz").exists()
    assert (outDir / "manifest.json").exists()


def test_search_main_script_catalog_build_subprocess(tmp_path) -> None:
    import polars as pl

    curr = tmp_path / "curr.parquet"
    manifest = tmp_path / "source.json"
    dataDir = tmp_path / "data"
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "main 유상증자"}]).write_parquet(curr)
    manifest.write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [{"path": "x.parquet", "rowCount": 1}],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "HF_TOKEN": "",
        "DARTLAB_DATA_DIR": str(dataDir),
        "DARTLAB_SEARCH_MAIN_MODE": "catalog",
        "DARTLAB_SEARCH_CURRENT_CATALOG": str(curr),
        "DARTLAB_SEARCH_SOURCE_MANIFESTS": str(manifest),
        "DARTLAB_SEARCH_EXPECTED_SOURCES": "allFilings",
        "DARTLAB_SEARCH_MIN_DOCS": "1",
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", ".github/scripts/search/buildSearchMain.py"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    outDir = dataDir / "dart" / "contentIndex"
    assert (outDir / "main.npz").exists()
    assert (outDir / "manifest.json").exists()
    assert (outDir / "catalog_snapshot.parquet").exists()
    manifestData = json.loads((outDir / "manifest.json").read_text(encoding="utf-8"))
    assert "catalog_snapshot.parquet" in manifestData["requiredFiles"]
    assert "catalog_snapshot.parquet" in manifestData["fileHashes"]


def test_search_delta_script_catalog_mode_requires_current_catalog(tmp_path) -> None:
    env = {
        **os.environ,
        "DARTLAB_SEARCH_DELTA_MODE": "catalog",
        "DARTLAB_SEARCH_CURRENT_CATALOG": "",
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", ".github/scripts/search/buildSearchDelta.py"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "requires DARTLAB_SEARCH_CURRENT_CATALOG" in proc.stdout


def test_search_delta_script_catalog_mode_requires_previous_catalog(tmp_path) -> None:
    import polars as pl

    curr = tmp_path / "curr.parquet"
    pl.DataFrame([{"source": "allFilings", "rcept_no": "A", "text": "new"}]).write_parquet(curr)
    env = {
        **os.environ,
        "DARTLAB_SEARCH_DELTA_MODE": "catalog",
        "DARTLAB_SEARCH_PREVIOUS_CATALOG": "",
        "DARTLAB_SEARCH_CURRENT_CATALOG": str(curr),
    }
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", ".github/scripts/search/buildSearchDelta.py"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "requires DARTLAB_SEARCH_PREVIOUS_CATALOG" in proc.stdout


def test_search_index_delta_workflow_exposes_catalog_mode_inputs() -> None:
    text = Path(".github/workflows/searchIndexDelta.yml").read_text(encoding="utf-8")
    assert "workflow_run" in text
    assert "Original SSOT Sync" in text
    assert "AllFilings Backfill" in text
    assert "News Archive Sync" in text
    assert "EDGAR Data Sync (Bulk)" in text
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "delta_mode" in text
    assert "default: 'catalog'" in text
    assert "expected_sources" in text
    assert "productization_gate" in text
    assert "default: 'release'" in text
    assert (
        "github.event_name != 'workflow_run' && (github.event.inputs.productization_gate || 'release') == 'release'"
        in text
    )
    assert (
        "github.event_name == 'workflow_run' || (github.event.inputs.productization_gate || 'release') != 'release'"
        in text
    )
    assert (
        "github.event_name == 'workflow_run' && 'ops' || (github.event.inputs.productization_gate || 'release')" in text
    )
    assert "DARTLAB_HF_RETRY_ATTEMPTS: '3'" in text
    assert "DARTLAB_HF_RETRY_MAX_SINGLE_WAIT_SECONDS: '120'" in text
    assert "DARTLAB_HF_RETRY_ATTEMPTS: '5'" in text
    assert "DARTLAB_HF_RETRY_MAX_SINGLE_WAIT_SECONDS: '300'" in text
    assert "quality_gold" in text
    assert "tests/fixtures/search/queryLogGold.real.jsonl" in text
    assert "DARTLAB_SEARCH_EXPECTED_SOURCES" in text
    assert "DARTLAB_SEARCH_DELTA_MODE" in text
    assert "DARTLAB_SEARCH_CURRENT_CATALOG" in text
    assert "DARTLAB_SEARCH_SOURCE_MANIFEST_SET" in text
    assert "runSearchPipelineDrill.py" in text
    assert "verifySearchHfRoundTrip.py" in text
    assert 'DARTLAB_SEARCH_PROMOTE_CURRENT: "0"' in text
    assert '--manifest-repo-path "$DARTLAB_SEARCH_FULL_CANDIDATE_MANIFEST"' in text
    assert "Build content lite + stage candidate" in text
    assert 'DARTLAB_SEARCH_MAIN_ONLY: "lite"' in text
    assert '--manifest-repo-path "$DARTLAB_SEARCH_LITE_CANDIDATE_MANIFEST"' in text
    assert "promoteSearchCandidate.py" in text
    assert "searchPromote.delta.full.json" in text
    assert "searchPromote.delta.lite.json" in text
    assert "evaluateSearchResultContract.py" in text
    assert "evaluateSearchCanary.py" in text
    assert "runSearchQualityDrill.py" in text
    assert "checkSearchRemoteEvidence.py" in text
    assert "--fail-on-missing" in text
    assert "pullSearchCurrentIndex.py" in text
    assert "evaluateSearchGold.py" in text
    assert "evaluateSearchProductizationStatus.py" in text
    assert "buildSearchProofBundle.py" in text
    assert "buildSearchReplacementEvidence.py" in text
    assert "evaluateSearchCutover.py" in text
    assert "--replacement-evidence" in text
    assert "PRODUCTIZATION_GATE" in text
    assert "github.event.inputs.productization_gate || 'release'" in text
    assert "--fail-on-incomplete" in text
    assert "--fail-on-default-not-ready" in text
    assert "--fail-on-ops-not-ready" in text
    assert "--fail-on-release-not-ready" in text
    assert 'blockers":["missingProofBundle"]' in text
    assert "searchHfRoundTrip.delta.full.json" in text
    assert "searchHfRoundTrip.delta.lite.json" in text
    assert "searchResultContract.delta.json" in text
    assert "searchCanary.delta.json" in text
    assert "searchQualityDrill.delta.json" in text
    assert "searchRemoteEvidence.delta.json" in text
    assert "searchQuality.delta.json" in text
    assert "searchMissLedger.delta.jsonl" in text
    assert "searchProductizationStatus.delta.json" in text
    assert "searchReplacementEvidence.delta.json" in text
    assert "searchCutover.delta.json" in text
    assert "searchProofBundle.delta" in text
    assert "actions/upload-artifact" in text
    assert "Apply manual catalog delta inputs" in text
    assert "DARTLAB_SEARCH_PREVIOUS_CATALOG: ${{ github.event.inputs.previous_catalog || '' }}" not in text
    assert "--require-previous-catalog" in text


def test_search_index_main_workflow_prefers_source_catalog_compaction() -> None:
    text = Path(".github/workflows/searchIndexMain.yml").read_text(encoding="utf-8")
    assert "build_mode" in text
    assert "default: catalog" in text
    assert "productization_gate" in text
    assert "default: release" in text
    assert "quality_gold" in text
    assert "tests/fixtures/search/queryLogGold.real.jsonl" in text
    assert "dart/searchCatalog/**" in text
    assert "prepareSearchDeltaInputs.py" in text
    assert "DARTLAB_SEARCH_MAIN_MODE" in text
    assert "main.current.catalog_snapshot.parquet" in text
    assert "runSearchPipelineDrill.py" in text
    assert "verifySearchHfRoundTrip.py" in text
    assert 'DARTLAB_SEARCH_PROMOTE_CURRENT: "0"' in text
    assert '--manifest-repo-path "$DARTLAB_SEARCH_FULL_CANDIDATE_MANIFEST"' in text
    assert '--manifest-repo-path "$DARTLAB_SEARCH_LITE_CANDIDATE_MANIFEST"' in text
    assert "promoteSearchCandidate.py" in text
    assert "searchPromote.main.full.json" in text
    assert "searchPromote.main.lite.json" in text
    assert "evaluateSearchResultContract.py" in text
    assert "evaluateSearchCanary.py" in text
    assert "runSearchQualityDrill.py" in text
    assert "checkSearchRemoteEvidence.py" in text
    assert "--fail-on-missing" in text
    assert "evaluateSearchGold.py" in text
    assert "evaluateSearchProductizationStatus.py" in text
    assert "buildSearchProofBundle.py" in text
    assert "buildSearchReplacementEvidence.py" in text
    assert "evaluateSearchCutover.py" in text
    assert "--replacement-evidence" in text
    assert "PRODUCTIZATION_GATE" in text
    assert "inputs.productization_gate || 'release'" in text
    assert "--fail-on-incomplete" in text
    assert "--fail-on-default-not-ready" in text
    assert "--fail-on-ops-not-ready" in text
    assert "--fail-on-release-not-ready" in text
    assert 'blockers":["missingProofBundle"]' in text
    assert "searchHfRoundTrip.main.full.json" in text
    assert "searchHfRoundTrip.main.lite.json" in text
    assert "searchResultContract.main.json" in text
    assert "searchCanary.main.json" in text
    assert "searchQualityDrill.main.json" in text
    assert "searchRemoteEvidence.main.json" in text
    assert "searchQuality.main.json" in text
    assert "searchMissLedger.main.jsonl" in text
    assert "searchProductizationStatus.main.json" in text
    assert "searchReplacementEvidence.main.json" in text
    assert "searchCutover.main.json" in text
    assert "searchProofBundle.main" in text
    assert "actions/upload-artifact" in text
    assert "for attempt in $(seq 1 12)" in text
    assert "sleep 310" in text
    assert "bootstrap from full HF pull" in text
    assert 'source catalog inputs were not prepared"\n            exit 1' not in text
    assert "dart/allFilings/*" in text
    assert "dart/panel/**" in text
    assert "edgar/panel/**" in text
    assert "news/public/rss/**" in text
    assert "news/public/rss_enriched/**" in text
    assert "news/headlines" not in text


def test_search_catalog_script_exists() -> None:
    text = Path(".github/scripts/search/buildSearchCatalog.py").read_text(encoding="utf-8")
    assert "writeSourceCatalogArtifacts" in text
    assert "--snapshot-scope" in text
    assert "--min-files" in text
    assert "--min-rows" in text
    assert "--min-catalog-rows" in text
    assert "--compare-remote-manifest" in text
    assert "--require-previous-manifest" in text
    assert "create_commit" in text
    assert "CommitOperationAdd" in text


def test_source_workflows_build_search_catalog_artifacts() -> None:
    original = Path(".github/workflows/originalSync.yml").read_text(encoding="utf-8")
    backfill = Path(".github/workflows/allFilingsBackfill.yml").read_text(encoding="utf-8")
    news = Path(".github/workflows/newsArchiveSync.yml").read_text(encoding="utf-8")
    edgar = Path(".github/workflows/edgarSync.yml").read_text(encoding="utf-8")
    combined = "\n".join([original, backfill, news, edgar])
    for source in ("dartPanel", "allFilings", "edgarPanel", "newsPublic"):
        assert f"--source {source}" in combined
        assert f"search-catalog-{source}" in combined
        assert f"data/dart/searchCatalog/{source}/**" in combined
    assert "--upload" in combined
    assert "--compare-remote-manifest" in combined
    assert "--require-previous-manifest" in combined
    assert "search_catalog_bootstrap" in combined
    assert "SEARCH_CATALOG_BOOTSTRAP" in combined
    assert "extra+=(--require-previous-manifest)" in combined
    assert "--min-files 300" in combined
    assert "--min-rows 150000" in combined
    assert "--min-catalog-rows 150000" in combined
    assert "--min-files 2400" in combined
    assert "--min-rows 90000" in combined
    assert "--min-catalog-rows 90000" in combined
    assert "--min-files 2000" in combined
    assert "--min-rows 50000" in combined
    assert "--min-catalog-rows 50000" in combined
    assert "--min-rows 100" in combined
    assert "actions/upload-artifact" in combined
    assert "if-no-files-found: ignore" in combined


def test_allfilings_backfill_is_decoupled_from_daily_original_sync() -> None:
    original = Path(".github/workflows/originalSync.yml").read_text(encoding="utf-8")
    backfill = Path(".github/workflows/allFilingsBackfill.yml").read_text(encoding="utf-8")
    assert "name: AllFilings Backfill" in backfill
    assert "cron: '30 5 * * *'" in backfill
    assert "timeout-minutes: 75" in backfill
    assert "timeout-minutes: 50" in backfill
    assert "DARTLAB_HF_RETRY_ATTEMPTS: '3'" in original
    assert "DARTLAB_HF_RETRY_ATTEMPTS: '3'" in backfill
    assert "DARTLAB_HF_RETRY_MAX_SINGLE_WAIT_SECONDS: '120'" in original
    assert "DARTLAB_HF_RETRY_MAX_SINGLE_WAIT_SECONDS: '120'" in backfill
    assert "--producer allFilingsBackfill.allfilings-backfill" in backfill
    assert "name: search-catalog-allFilings-backfill-${{ github.run_id }}" in backfill
    assert "github.event.inputs.jobs == 'allfilings-backfill'" in original
    assert (
        "github.event_name == 'schedule' || github.event.inputs.jobs == 'all' || github.event.inputs.jobs == 'allfilings-backfill'"
        not in original
    )


def test_search_main_workflow_bootstraps_canonical_source_catalogs() -> None:
    text = Path(".github/workflows/searchIndexMain.yml").read_text(encoding="utf-8")
    assert "Build canonical source search catalogs from full HF pull" in text
    assert "Prepare canonical catalog main inputs after bootstrap" in text
    assert "news/public/rss_enriched/**" in text
    assert "searchIndexMain.full-pull" in text
    for source in ("allFilings", "dartPanel", "edgarPanel", "newsPublic"):
        assert f"--source {source}" in text
        assert f"data/dart/searchCatalog/{source}" in text
    assert text.count("prepareSearchDeltaInputs.py") >= 2
    assert "legacy mode requested; skip canonical source catalog bootstrap" in text
    assert "--compare-remote-manifest" in text


def test_search_delta_workflow_prepares_catalog_inputs() -> None:
    text = Path(".github/workflows/searchIndexDelta.yml").read_text(encoding="utf-8")
    assert "prepareSearchDeltaInputs.py" in text
    assert "dart/searchCatalog/**" in text
    assert "catalog_snapshot.parquet" in text
