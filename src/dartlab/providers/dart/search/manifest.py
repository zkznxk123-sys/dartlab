"""Search index manifest contract.

The content index can exist in older legacy form (`main_info.json`) or in the
product form (`manifest.json`). This module keeps the new manifest parsing and
self-check rules separate from BM25 segment loading.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEARCH_MANIFEST_NAMES: tuple[str, ...] = ("manifest.json", "search_manifest.json", "index_manifest.json")

REQUIRED_SEARCH_MANIFEST_FIELDS: tuple[str, ...] = (
    "artifactVersion",
    "schemaVersion",
    "builtAt",
    "sourceDataAsOf",
    "nDocsBySource",
    "requiredFiles",
)


def loadSearchManifest(indexDir: str | Path) -> dict[str, Any] | None:
    """Load the first supported search index manifest in a contentIndex directory.

    Args:
        indexDir: Content index directory.

    Returns:
        dict | None: Parsed manifest, or None when no valid manifest JSON exists.

    Raises:
        None. Invalid JSON is treated as no manifest so legacy indexes keep working.

    Example:
        >>> loadSearchManifest("missing") is None
        True
    """
    base = Path(indexDir)
    for name in SEARCH_MANIFEST_NAMES:
        path = base / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None
    return None


def validateSearchManifest(
    manifest: dict[str, Any],
    indexDir: str | Path | None = None,
    *,
    codeSchemaVersion: int | None = None,
) -> dict[str, Any]:
    """Validate required manifest fields, files, and optional sha256 hashes.

    Args:
        manifest: Parsed search manifest.
        indexDir: Optional directory used to verify required files.
        codeSchemaVersion: Optional search index schema version supported by the
            running library. When provided, incompatible manifests are invalid.

    Returns:
        dict: {"valid": bool, "errors": list[str], "checkedFiles": int}.

    Raises:
        None.

    Example:
        >>> validateSearchManifest({})["valid"]
        False
    """
    errors: list[str] = []
    for field in REQUIRED_SEARCH_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing:{field}")

    requiredFiles = manifest.get("requiredFiles") or []
    if requiredFiles is not None and not isinstance(requiredFiles, list):
        errors.append("invalid:requiredFiles")
        requiredFiles = []

    fileHashes = manifest.get("fileHashes") or {}
    if fileHashes is not None and not isinstance(fileHashes, dict):
        errors.append("invalid:fileHashes")
        fileHashes = {}

    if codeSchemaVersion is not None:
        schemaVersion = _intOrDefault(manifest.get("schemaVersion"), -1)
        compatibleMax = _intOrDefault(manifest.get("compatibleMaxSchemaVersion"), codeSchemaVersion)
        if schemaVersion > codeSchemaVersion or codeSchemaVersion > compatibleMax:
            errors.append(f"schemaIncompatible:{schemaVersion}:{codeSchemaVersion}:{compatibleMax}")

    checkedFiles = 0
    if indexDir is not None:
        base = Path(indexDir)
        for rel in requiredFiles:
            if not isinstance(rel, str) or not rel:
                errors.append("invalid:requiredFile")
                continue
            path = base / rel
            if not path.exists():
                errors.append(f"missingFile:{rel}")
                continue
            checkedFiles += 1
            expectedHash = fileHashes.get(rel)
            if expectedHash:
                gotHash = _sha256(path)
                if gotHash != expectedHash:
                    errors.append(f"hashMismatch:{rel}")

    return {"valid": not errors, "errors": errors, "checkedFiles": checkedFiles}


def indexInfoFromManifest(
    manifest: dict[str, Any],
    *,
    codeSchemaVersion: int,
    indexDir: str | Path | None = None,
) -> dict[str, Any]:
    """Convert a product search manifest into the public indexInfo shape.

    Args:
        manifest: Parsed search manifest.
        codeSchemaVersion: Search index schema version supported by this library.
        indexDir: Optional directory for self-checking required files.

    Returns:
        dict: Backward-compatible indexInfo fields plus manifest freshness fields.

    Raises:
        None.

    Example:
        >>> indexInfoFromManifest({"schemaVersion": 1, "nDocsBySource": {"x": 2}}, codeSchemaVersion=1)["nDocs"]
        2
    """
    validation = validateSearchManifest(manifest, indexDir=indexDir, codeSchemaVersion=codeSchemaVersion)
    schemaVersion = _intOrDefault(manifest.get("schemaVersion"), 0)
    nDocsBySource = _dictInt(manifest.get("nDocsBySource"))
    nDocsByTier = _dictInt(manifest.get("nDocsByTier"))
    nDocs = sum(nDocsBySource.values()) or sum(nDocsByTier.values())
    dataAsOf = manifest.get("deltaDataAsOf") or manifest.get("mainDataAsOf") or manifest.get("builtAt")
    compatibleMax = _intOrDefault(manifest.get("compatibleMaxSchemaVersion"), codeSchemaVersion)
    return {
        "available": validation["valid"],
        "dataAsOf": dataAsOf,
        "nDocs": nDocs,
        "hasDelta": bool(manifest.get("hasDelta")),
        "schemaVersion": schemaVersion,
        "compatible": schemaVersion <= codeSchemaVersion <= compatibleMax,
        "sourceDataAsOf": manifest.get("sourceDataAsOf") or {},
        "nDocsBySource": nDocsBySource,
        "nDocsByTier": nDocsByTier,
        "manifestValid": validation["valid"],
        "manifestErrors": validation["errors"],
        "artifactVersion": manifest.get("artifactVersion"),
        "builtAt": manifest.get("builtAt"),
    }


def writeSearchManifest(indexDir: str | Path, manifest: dict[str, Any], *, name: str = "manifest.json") -> Path:
    """Write a product search manifest.

    Args:
        indexDir: Content index directory.
        manifest: Manifest payload.
        name: Manifest filename. Defaults to `manifest.json`.

    Returns:
        Path: Written manifest path.

    Raises:
        OSError: When the directory or file cannot be written.

    Example:
        >>> writeSearchManifest
        <function writeSearchManifest at ...>
    """
    base = Path(indexDir)
    base.mkdir(parents=True, exist_ok=True)
    path = base / name
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _intOrDefault(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dictInt(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        try:
            out[str(key)] = int(raw)
        except (TypeError, ValueError):
            continue
    return out
