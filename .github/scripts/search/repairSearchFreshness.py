"""Repair search artifact freshness metadata without rebuilding BM25 files."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import polars as pl

from dartlab.providers.dart.search.freshness import normalizeSearchDate

CATALOG_TO_INDEX_SOURCE = {
    "allFilings": "allFilings",
    "dartPanel": "panel",
    "edgarPanel": "edgar-panel",
    "newsPublic": "news",
    "newsGdelt": "news",
}
INDEX_TO_CATALOG_SOURCE = {value: key for key, value in CATALOG_TO_INDEX_SOURCE.items()}
SOURCE_ALIASES = {
    "allfilings": "allFilings",
    "allFilings": "allFilings",
    "dartpanel": "dartPanel",
    "dartPanel": "dartPanel",
    "panel": "dartPanel",
    "edgarpanel": "edgarPanel",
    "edgarPanel": "edgarPanel",
    "edgar-panel": "edgarPanel",
    "newspublic": "newsPublic",
    "newsPublic": "newsPublic",
    "news": "newsPublic",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-catalog-dir", default="data/dart/searchCatalog")
    parser.add_argument(
        "--content-index-dir",
        action="append",
        default=[],
        help="Content index directory to repair. Repeatable. Defaults to full and lite if present.",
    )
    parser.add_argument(
        "--source-fallback",
        action="append",
        default=[],
        help="SOURCE=YYYYMMDD freshness fallback, e.g. edgarPanel=20260616.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default="", help="Optional JSON summary path.")
    args = parser.parse_args(argv)

    catalogDir = Path(args.search_catalog_dir)
    contentDirs = [Path(raw) for raw in args.content_index_dir] or _defaultContentDirs(catalogDir)
    summary = repairFreshnessArtifacts(
        catalogDir,
        contentDirs,
        sourceFallbacks=parseSourceFallbacks(args.source_fallback),
        dryRun=args.dry_run,
    )
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def parseSourceFallbacks(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"invalid --source-fallback: {raw}")
        source, date = raw.split("=", 1)
        catalogSource = _catalogSource(source)
        dataAsOf = normalizeSearchDate(date)
        if not dataAsOf:
            raise ValueError(f"invalid fallback date for {source}: {date}")
        out[catalogSource] = dataAsOf
    return out


def repairFreshnessArtifacts(
    searchCatalogDir: Path,
    contentIndexDirs: list[Path],
    *,
    sourceFallbacks: dict[str, str],
    dryRun: bool = False,
) -> dict[str, Any]:
    repairedAt = time.strftime("%Y-%m-%dT%H:%M:%S")
    catalogReport = _repairSourceCatalogs(
        searchCatalogDir,
        sourceFallbacks=sourceFallbacks,
        repairedAt=repairedAt,
        dryRun=dryRun,
    )
    manifestSet = _buildSourceManifestSet(searchCatalogDir, dryRun=dryRun)
    contentReports = [
        _repairContentIndex(
            path,
            manifestSet=manifestSet,
            sourceFallbacks=sourceFallbacks,
            repairedAt=repairedAt,
            dryRun=dryRun,
        )
        for path in contentIndexDirs
        if path.exists()
    ]
    return {
        "valid": all(report.get("valid", False) for report in [catalogReport, *contentReports]),
        "dryRun": dryRun,
        "repairedAt": repairedAt,
        "catalog": catalogReport,
        "contentIndexes": contentReports,
    }


def _repairSourceCatalogs(
    searchCatalogDir: Path,
    *,
    sourceFallbacks: dict[str, str],
    repairedAt: str,
    dryRun: bool,
) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for manifestPath in sorted(searchCatalogDir.glob("*/*.source_manifest.json")):
        source = _catalogSource(manifestPath.parent.name)
        catalogPath = manifestPath.with_name(f"{source}.catalog_snapshot.parquet")
        if not catalogPath.exists():
            continue
        if source in sourceFallbacks:
            _replaceSourceDataAsOf(
                catalogPath,
                source=source,
                dataAsOf=sourceFallbacks[source],
                dryRun=dryRun,
            )
        dataAsOf = (
            sourceFallbacks.get(source) if dryRun and source in sourceFallbacks else _catalogDataAsOf(catalogPath)
        )
        manifest = _loadJson(manifestPath)
        before = str(manifest.get("dataAsOf") or "")
        manifest["dataAsOf"] = dataAsOf
        manifest["freshnessRepair"] = {
            "method": "metadataOnlySourceDataAsOf",
            "repairedAt": repairedAt,
            "sourceFallbacks": sourceFallbacks,
        }
        if not dryRun:
            _writeJson(manifestPath, manifest)
        reports.append(
            {
                "source": source,
                "manifest": manifestPath.as_posix(),
                "catalog": catalogPath.as_posix(),
                "beforeDataAsOf": before,
                "afterDataAsOf": dataAsOf,
                "fallbackApplied": source in sourceFallbacks,
            }
        )
    combinedPath = searchCatalogDir / "main.current.catalog_snapshot.parquet"
    if combinedPath.exists():
        for source, dataAsOf in sourceFallbacks.items():
            _replaceSourceDataAsOf(combinedPath, source=source, dataAsOf=dataAsOf, dryRun=dryRun)
    return {
        "valid": True,
        "sources": reports,
        "combinedCatalog": combinedPath.as_posix() if combinedPath.exists() else "",
    }


def _buildSourceManifestSet(searchCatalogDir: Path, *, dryRun: bool) -> dict[str, Any]:
    setPath = searchCatalogDir / "source_manifest_set.json"
    combinedPath = searchCatalogDir / "main.current.catalog_snapshot.parquet"
    previous = _loadJson(setPath) if setPath.exists() else {}
    expectedSources = previous.get("expectedSources") if isinstance(previous.get("expectedSources"), list) else []
    sources: list[dict[str, Any]] = []
    for manifestPath in sorted(searchCatalogDir.glob("*/*.source_manifest.json")):
        source = _catalogSource(manifestPath.parent.name)
        catalogPath = manifestPath.with_name(f"{source}.catalog_snapshot.parquet")
        if not catalogPath.exists():
            continue
        manifest = _loadJson(manifestPath)
        files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
        sources.append(
            {
                "source": source,
                "manifestPath": manifestPath.as_posix(),
                "catalogPath": catalogPath.as_posix(),
                "manifestSha256": _sha256File(manifestPath),
                "catalogSha256": _sha256File(catalogPath),
                "snapshotScope": manifest.get("snapshotScope"),
                "dataAsOf": manifest.get("dataAsOf"),
                "builtAt": manifest.get("builtAt"),
                "totalRows": manifest.get("totalRows"),
                "changedRows": manifest.get("changedRows"),
                "deletedRows": manifest.get("deletedRows"),
                "fileCount": len(files),
                "catalogRows": _parquetRows(catalogPath),
                "producer": manifest.get("producer"),
                "producerRun": manifest.get("producerRun") if isinstance(manifest.get("producerRun"), dict) else {},
            }
        )
    payload = {
        "schemaVersion": "searchSourceManifestSet.v1",
        "expectedSources": expectedSources or [row["source"] for row in sources],
        "combinedCatalogPath": combinedPath.as_posix() if combinedPath.exists() else "",
        "combinedCatalogSha256": _sha256File(combinedPath) if combinedPath.exists() else "",
        "combinedCatalogRows": _parquetRows(combinedPath) if combinedPath.exists() else 0,
        "sources": sources,
    }
    payload["sourceManifestSetId"] = _stableId(_stableManifestSetPayload(payload))
    if not dryRun and setPath.parent.exists():
        _writeJson(setPath, payload)
    return payload


def _repairContentIndex(
    indexDir: Path,
    *,
    manifestSet: dict[str, Any],
    sourceFallbacks: dict[str, str],
    repairedAt: str,
    dryRun: bool,
) -> dict[str, Any]:
    metaPath = indexDir / "main_meta.parquet"
    manifestPath = indexDir / "manifest.json"
    manifestSetPath = indexDir / "source_manifest_set.json"
    if not manifestPath.exists():
        return {"valid": False, "indexDir": indexDir.as_posix(), "errors": ["missingManifest"]}
    for catalogSource, dataAsOf in sourceFallbacks.items():
        indexSource = CATALOG_TO_INDEX_SOURCE.get(catalogSource, catalogSource)
        if metaPath.exists():
            _replaceSourceDataAsOf(metaPath, source=indexSource, dataAsOf=dataAsOf, dryRun=dryRun)
    if not dryRun:
        _writeJson(manifestSetPath, manifestSet)
    manifest = _loadJson(manifestPath)
    sourceDataAsOf = _metaSourceDataAsOf(metaPath)
    if sourceDataAsOf:
        manifest["sourceDataAsOf"] = sourceDataAsOf
        manifest["mainDataAsOf"] = max(sourceDataAsOf.values(), default=manifest.get("mainDataAsOf") or "")
    manifest["sourceManifestSetId"] = manifestSet.get("sourceManifestSetId", "")
    manifest["sourceManifestSet"] = _sourceManifestSetSummary(manifestSet)
    manifest["freshnessRepair"] = {
        "method": "metadataOnlySourceDataAsOf",
        "repairedAt": repairedAt,
        "sourceFallbacks": sourceFallbacks,
    }
    requiredFiles = manifest.get("requiredFiles") if isinstance(manifest.get("requiredFiles"), list) else []
    manifest["fileHashes"] = {
        name: _sha256File(indexDir / name)
        for name in requiredFiles
        if isinstance(name, str) and (indexDir / name).exists()
    }
    if not dryRun:
        _writeJson(manifestPath, manifest)
    return {
        "valid": True,
        "indexDir": indexDir.as_posix(),
        "sourceDataAsOf": manifest.get("sourceDataAsOf") or {},
        "sourceManifestSetId": manifest.get("sourceManifestSetId") or "",
    }


def _replaceSourceDataAsOf(path: Path, *, source: str, dataAsOf: str, dryRun: bool) -> bool:
    if not path.exists():
        return False
    try:
        schema = set(pl.scan_parquet(path).collect_schema().names())
    except (pl.exceptions.PolarsError, OSError):
        return False
    if "source" not in schema or "sourceDataAsOf" not in schema:
        return False
    df = pl.read_parquet(path)
    if source not in set(df.get_column("source").cast(pl.Utf8).unique().to_list()):
        return False
    patched = df.with_columns(
        pl.when(pl.col("source").cast(pl.Utf8) == source)
        .then(pl.lit(dataAsOf))
        .otherwise(pl.col("sourceDataAsOf").cast(pl.Utf8, strict=False))
        .alias("sourceDataAsOf")
    )
    if not dryRun:
        tmp = path.with_name(f"{path.name}.tmp")
        patched.write_parquet(tmp)
        tmp.replace(path)
    return True


def _catalogDataAsOf(catalogPath: Path) -> str:
    try:
        schema = set(pl.scan_parquet(catalogPath).collect_schema().names())
        dateCol = "sourceDataAsOf" if "sourceDataAsOf" in schema else "date" if "date" in schema else ""
        if not dateCol:
            return ""
        row = (
            pl.scan_parquet(catalogPath)
            .select(pl.col(dateCol).cast(pl.Utf8, strict=False).max().alias("dataAsOf"))
            .collect()
            .row(0, named=True)
        )
    except (pl.exceptions.PolarsError, OSError):
        return ""
    return normalizeSearchDate(row.get("dataAsOf"))


def _metaSourceDataAsOf(metaPath: Path) -> dict[str, str]:
    if not metaPath.exists():
        return {}
    try:
        rows = (
            pl.scan_parquet(metaPath)
            .select(
                pl.col("source").cast(pl.Utf8, strict=False).alias("source"),
                pl.col("sourceDataAsOf").cast(pl.Utf8, strict=False).alias("sourceDataAsOf"),
            )
            .group_by("source")
            .agg(pl.col("sourceDataAsOf").max().alias("dataAsOf"))
            .collect()
        )
    except (pl.exceptions.PolarsError, OSError):
        return {}
    out: dict[str, str] = {}
    for row in rows.iter_rows(named=True):
        source = str(row.get("source") or "")
        dataAsOf = normalizeSearchDate(row.get("dataAsOf"))
        if source and dataAsOf:
            out[source] = dataAsOf
    return out


def _sourceManifestSetSummary(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    return {
        "schemaVersion": payload.get("schemaVersion", ""),
        "sourceManifestSetId": payload.get("sourceManifestSetId", ""),
        "expectedSources": payload.get("expectedSources") if isinstance(payload.get("expectedSources"), list) else [],
        "combinedCatalogRows": payload.get("combinedCatalogRows"),
        "combinedCatalogSha256": payload.get("combinedCatalogSha256", ""),
        "sources": [
            {
                "source": item.get("source", ""),
                "dataAsOf": item.get("dataAsOf", ""),
                "snapshotScope": item.get("snapshotScope", ""),
                "totalRows": item.get("totalRows"),
                "catalogRows": item.get("catalogRows"),
                "manifestSha256": item.get("manifestSha256", ""),
                "catalogSha256": item.get("catalogSha256", ""),
                "producer": item.get("producer", ""),
            }
            for item in sources
            if isinstance(item, dict)
        ],
    }


def _stableManifestSetPayload(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    return {
        "schemaVersion": payload.get("schemaVersion"),
        "expectedSources": payload.get("expectedSources"),
        "combinedCatalogSha256": payload.get("combinedCatalogSha256"),
        "combinedCatalogRows": payload.get("combinedCatalogRows"),
        "sources": [
            {key: value for key, value in item.items() if key not in {"manifestPath", "catalogPath"}}
            for item in sources
            if isinstance(item, dict)
        ],
    }


def _stableId(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _catalogSource(source: str) -> str:
    key = source.strip()
    return SOURCE_ALIASES.get(key, SOURCE_ALIASES.get(key.lower(), key))


def _defaultContentDirs(catalogDir: Path) -> list[Path]:
    root = catalogDir.parent / "contentIndex"
    candidates = [root, root / "lite"]
    return [path for path in candidates if path.exists()]


def _loadJson(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _writeJson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _sha256File(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parquetRows(path: Path) -> int:
    import pyarrow.parquet as pq

    return int(pq.ParquetFile(path).metadata.num_rows)


if __name__ == "__main__":
    sys.exit(main())
