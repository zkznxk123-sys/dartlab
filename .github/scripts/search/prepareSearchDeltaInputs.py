"""Prepare catalog-mode inputs for the daily search delta workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default="data/dart/searchCatalog")
    parser.add_argument("--previous", default="data/dart/contentIndex/catalog_snapshot.parquet")
    parser.add_argument("--out-current", default="data/dart/searchCatalog/current.catalog_snapshot.parquet")
    parser.add_argument("--out-manifest-set", default="data/dart/searchCatalog/current.source_manifest_set.json")
    parser.add_argument("--env-file", default=os.environ.get("GITHUB_ENV", ""))
    parser.add_argument(
        "--require-previous-catalog",
        action="store_true",
        help="Fail when catalog delta mode cannot prove the previous catalog snapshot.",
    )
    parser.add_argument(
        "--expected-sources",
        default=os.environ.get("DARTLAB_SEARCH_EXPECTED_SOURCES", "allFilings,dartPanel,edgarPanel,newsPublic"),
        help="Comma-separated source set required for catalog mode. Empty disables expected-source enforcement.",
    )
    args = parser.parse_args(argv)

    sourceDir = Path(args.source_dir)
    manifests = sorted(sourceDir.glob("*/*.source_manifest.json"))
    catalogs = sorted(sourceDir.glob("*/*.catalog_snapshot.parquet"))
    if not manifests or not catalogs:
        if args.require_previous_catalog:
            print("[search-catalog] source manifests/catalogs missing; catalog delta cannot run")
            return 2
        print("[search-catalog] source manifests/catalogs missing; keep legacy delta mode")
        return 0
    expectedSources = _parseSources(args.expected_sources)
    eligible = _eligibleArtifacts(manifests, catalogs, expectedSources)
    if not eligible["valid"]:
        if args.require_previous_catalog:
            print(f"[search-catalog] {eligible['reason']}; catalog delta cannot run")
            return 2
        print(f"[search-catalog] {eligible['reason']}; keep legacy delta mode")
        return 0

    previous = Path(args.previous) if args.previous else None
    previousExists = bool(previous and previous.exists())
    if args.require_previous_catalog and not previousExists:
        print(f"[search-catalog] previous catalog missing: {previous}; catalog delta cannot run")
        return 2

    outCurrent = Path(args.out_current)
    outCurrent.parent.mkdir(parents=True, exist_ok=True)
    catalogRows = _writeCombinedCatalogs(eligible["catalogs"], outCurrent)
    if catalogRows <= 0:
        if args.require_previous_catalog:
            print("[search-catalog] combined catalog empty; catalog delta cannot run")
            return 2
        print("[search-catalog] combined catalog empty; keep legacy delta mode")
        return 0
    outManifestSet = Path(args.out_manifest_set) if args.out_manifest_set else None
    if outManifestSet is not None:
        _writeManifestSet(
            manifests=eligible["manifests"],
            catalogs=eligible["catalogs"],
            expectedSources=expectedSources,
            out=outManifestSet,
            combinedCatalog=outCurrent,
            combinedCatalogRows=catalogRows,
        )

    env = {
        "DARTLAB_SEARCH_DELTA_MODE": "catalog",
        "DARTLAB_SEARCH_MAIN_MODE": "catalog",
        "DARTLAB_SEARCH_PREVIOUS_CATALOG": str(previous) if previousExists else "",
        "DARTLAB_SEARCH_CURRENT_CATALOG": str(outCurrent),
        "DARTLAB_SEARCH_SOURCE_MANIFESTS": os.pathsep.join(str(path) for path in eligible["manifests"]),
        "DARTLAB_SEARCH_SOURCE_MANIFEST_SET": str(outManifestSet) if outManifestSet is not None else "",
    }
    if args.env_file:
        _appendEnv(Path(args.env_file), env)
    for key, value in env.items():
        print(f"{key}={value}")
    return 0


def _parseSources(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _eligibleArtifacts(manifests: list[Path], catalogs: list[Path], expectedSources: list[str]) -> dict[str, object]:
    manifestBySource: dict[str, Path] = {}
    catalogBySource: dict[str, Path] = {}
    invalid: list[str] = []
    partial: list[str] = []
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append(path.as_posix())
            continue
        source = data.get("source")
        if not isinstance(source, str) or not source:
            invalid.append(path.as_posix())
            continue
        if data.get("snapshotScope", "partial") != "full":
            partial.append(source)
            continue
        manifestBySource[source] = path
    for path in catalogs:
        source = path.name.removesuffix(".catalog_snapshot.parquet")
        if source:
            catalogBySource[source] = path
    if invalid:
        return {
            "valid": False,
            "reason": f"invalid source manifests: {','.join(invalid)}",
            "manifests": [],
            "catalogs": [],
        }
    if partial:
        return {
            "valid": False,
            "reason": f"partial source snapshots: {','.join(sorted(partial))}",
            "manifests": [],
            "catalogs": [],
        }
    required = expectedSources or sorted(manifestBySource)
    missing = [source for source in required if source not in manifestBySource or source not in catalogBySource]
    if missing:
        return {
            "valid": False,
            "reason": f"expected source catalogs missing: {','.join(missing)}",
            "manifests": [],
            "catalogs": [],
        }
    return {
        "valid": True,
        "reason": "",
        "manifests": [manifestBySource[source] for source in required],
        "catalogs": [catalogBySource[source] for source in required],
    }


def _writeCombinedCatalogs(paths: list[Path], out: Path, *, batchSize: int = 2048) -> int:
    import pyarrow as pa
    import pyarrow.parquet as pq

    writer: pq.ParquetWriter | None = None
    totalRows = 0
    tmp = out.with_name(f"{out.name}.tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        for path in paths:
            if not path.exists():
                continue
            parquet = pq.ParquetFile(path)
            for batch in parquet.iter_batches(batch_size=batchSize):
                if batch.num_rows == 0:
                    continue
                table = pa.Table.from_batches([batch])
                if writer is None:
                    writer = pq.ParquetWriter(str(tmp), table.schema, compression="zstd")
                writer.write_table(table)
                totalRows += int(batch.num_rows)
    except Exception:
        if writer is not None:
            writer.close()
        if tmp.exists():
            tmp.unlink()
        raise
    if writer is not None:
        writer.close()
        tmp.replace(out)
    elif out.exists():
        out.unlink()
    return totalRows


def _appendEnv(path: Path, env: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for key, value in env.items():
            f.write(f"{key}={value}\n")


def _writeManifestSet(
    *,
    manifests: list[Path],
    catalogs: list[Path],
    expectedSources: list[str],
    out: Path,
    combinedCatalog: Path,
    combinedCatalogRows: int,
) -> None:
    manifestBySource: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = str(data.get("source") or path.parent.name)
        manifestBySource[source] = (path, data)
    catalogBySource = {path.name.removesuffix(".catalog_snapshot.parquet"): path for path in catalogs}
    sources: list[dict[str, Any]] = []
    for source in expectedSources or sorted(manifestBySource):
        manifestPath, data = manifestBySource[source]
        catalogPath = catalogBySource[source]
        sources.append(
            {
                "source": source,
                "manifestPath": manifestPath.as_posix(),
                "catalogPath": catalogPath.as_posix(),
                "manifestSha256": _sha256File(manifestPath),
                "catalogSha256": _sha256File(catalogPath),
                "snapshotScope": data.get("snapshotScope"),
                "dataAsOf": data.get("dataAsOf"),
                "builtAt": data.get("builtAt"),
                "totalRows": data.get("totalRows"),
                "changedRows": data.get("changedRows"),
                "deletedRows": data.get("deletedRows"),
                "fileCount": len(data.get("files") if isinstance(data.get("files"), list) else []),
                "catalogRows": _parquetRows(catalogPath),
                "producer": data.get("producer"),
                "producerRun": data.get("producerRun") if isinstance(data.get("producerRun"), dict) else {},
            }
        )
    payload = {
        "schemaVersion": "searchSourceManifestSet.v1",
        "expectedSources": expectedSources,
        "combinedCatalogPath": combinedCatalog.as_posix(),
        "combinedCatalogSha256": _sha256File(combinedCatalog),
        "combinedCatalogRows": combinedCatalogRows,
        "sources": sources,
    }
    payload["sourceManifestSetId"] = _stableId(_stableManifestSetPayload(payload))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


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


def _sha256File(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parquetRows(path: Path) -> int:
    import pyarrow.parquet as pq

    return int(pq.ParquetFile(path).metadata.num_rows)


if __name__ == "__main__":
    sys.exit(main())
