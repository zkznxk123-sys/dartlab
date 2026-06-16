"""Source manifest contract for search catalog delta builds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SOURCE_MANIFEST_SOURCES: tuple[str, ...] = ("allFilings", "dartPanel", "edgarPanel", "newsPublic", "newsGdelt")
SOURCE_MANIFEST_SNAPSHOT_SCOPES: tuple[str, ...] = ("full", "partial")

REQUIRED_SOURCE_MANIFEST_FIELDS: tuple[str, ...] = (
    "source",
    "sourceVersion",
    "schemaVersion",
    "snapshotScope",
    "dataAsOf",
    "builtAt",
    "files",
    "totalRows",
    "changedRows",
    "deletedRows",
    "producer",
)


def loadSourceManifest(path: str | Path) -> dict[str, Any] | None:
    """Load a source manifest JSON file.

    Args:
        path: Manifest file path.

    Returns:
        dict | None: Parsed manifest, or None when absent/invalid.

    Raises:
        None.

    Example:
        >>> loadSourceManifest("missing") is None
        True
    """
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def validateSourceManifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate a search source manifest.

    Args:
        manifest: Parsed source manifest payload.

    Returns:
        dict: {"valid": bool, "errors": list[str], "source": str | None}.

    Raises:
        None.

    Example:
        >>> validateSourceManifest({})["valid"]
        False
    """
    errors: list[str] = []
    for field in REQUIRED_SOURCE_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing:{field}")
    source = manifest.get("source")
    if source not in SOURCE_MANIFEST_SOURCES:
        errors.append("invalid:source")
    snapshotScope = manifest.get("snapshotScope")
    if snapshotScope not in SOURCE_MANIFEST_SNAPSHOT_SCOPES:
        errors.append("invalid:snapshotScope")
    files = manifest.get("files")
    if files is not None and not isinstance(files, list):
        errors.append("invalid:files")
    for field in ("totalRows", "changedRows", "deletedRows"):
        if field in manifest and _intOrNone(manifest.get(field)) is None:
            errors.append(f"invalid:{field}")
    return {"valid": not errors, "errors": errors, "source": source if isinstance(source, str) else None}


def sourceFreshness(manifests: list[dict[str, Any]]) -> dict[str, str]:
    """Return source -> dataAsOf for valid manifests only.

    Args:
        manifests: Parsed source manifest payloads.

    Returns:
        dict[str, str]: Source name to dataAsOf map for valid manifests.

    Raises:
        None.

    Example:
        >>> sourceFreshness([])
        {}
    """
    out: dict[str, str] = {}
    for manifest in manifests:
        check = validateSourceManifest(manifest)
        if check["valid"] and manifest.get("snapshotScope") == "full":
            out[str(manifest["source"])] = str(manifest.get("dataAsOf") or "")
    return out


def _intOrNone(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
