"""Local search-index activation and rollback-safe pointer helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ACTIVE_POINTER_NAME = "active.json"
STAGING_DIR_NAME = "_staging"
CORE_INDEX_FILES: tuple[str, ...] = ("main.npz", "main_stems.json", "main_meta.parquet", "main_info.json")


def resolveActiveIndexDir(baseDir: str | Path) -> Path | None:
    """Resolve `contentIndex/active.json` to an active artifact directory.

    Args:
        baseDir: Flat `data/dart/contentIndex` directory.

    Returns:
        Path | None: Active artifact directory when the pointer is valid and has
        `main.npz`; otherwise None.

    Raises:
        None.

    Example:
        >>> resolveActiveIndexDir("missing") is None
        True
    """
    base = Path(baseDir)
    pointer = base / ACTIVE_POINTER_NAME
    data = _readPointer(pointer)
    if not data:
        return None
    activeDir = data.get("activeDir") or data.get("path")
    if not isinstance(activeDir, str) or not activeDir:
        return None
    target = _resolveInsideBase(base, activeDir)
    if target is None:
        return None
    for name in CORE_INDEX_FILES:
        if not (target / name).exists():
            return None
    if not (target / "manifest.json").exists():
        return None
    return target


def loadActiveSearchManifest(baseDir: str | Path) -> dict[str, Any] | None:
    """Load the current active search manifest.

    Args:
        baseDir: Flat `data/dart/contentIndex` directory containing active.json.

    Returns:
        dict[str, Any] | None: Active manifest payload when present and valid.

    Raises:
        None.

    Example:
        >>> loadActiveSearchManifest("missing") is None
        True
    """
    activeDir = resolveActiveIndexDir(baseDir)
    if activeDir is None:
        return None
    from dartlab.providers.dart.search.manifest import loadSearchManifest

    return loadSearchManifest(activeDir)


def shouldActivateRemoteManifest(remote: dict[str, Any], local: dict[str, Any] | None) -> bool:
    """Return whether a remote manifest should replace the local active index.

    Args:
        remote: Remote manifest downloaded from HF current.
        local: Current active local manifest, or None.

    Returns:
        bool: True when remote differs from or is newer than local.

    Raises:
        None.

    Example:
        >>> shouldActivateRemoteManifest({"builtAt": "2026"}, {"builtAt": "2025"})
        True
    """
    if local is None:
        return True
    if _manifestIdentity(remote) == _manifestIdentity(local):
        return False
    remoteBuiltAt = str(remote.get("builtAt") or "")
    localBuiltAt = str(local.get("builtAt") or "")
    if remoteBuiltAt and localBuiltAt and remoteBuiltAt <= localBuiltAt:
        return False
    return True


def selfcheckLocalIndex(
    indexDir: str | Path,
    *,
    requireManifest: bool = True,
    requireLoadable: bool = True,
) -> dict[str, Any]:
    """Validate a local index directory before making it active.

    Args:
        indexDir: Candidate content index directory.
        requireManifest: True rejects legacy directories without `manifest.json`.
        requireLoadable: True runs a lightweight `loadSegment("main")` smoke.

    Returns:
        dict: {"valid": bool, "errors": list[str], "manifestValid": bool}.

    Raises:
        None.

    Example:
        >>> selfcheckLocalIndex("missing")["valid"]
        False
    """
    base = Path(indexDir)
    errors: list[str] = []
    manifestValid = False

    from dartlab.providers.dart.search.manifest import loadSearchManifest, validateSearchManifest

    manifest = loadSearchManifest(base)
    if manifest is None:
        if requireManifest:
            errors.append("missing:manifest")
        if not (base / "main.npz").exists():
            errors.append("missingFile:main.npz")
    else:
        from dartlab.providers.dart.search.fieldIndex import INDEX_SCHEMA_VERSION

        validation = validateSearchManifest(manifest, base, codeSchemaVersion=INDEX_SCHEMA_VERSION)
        manifestValid = bool(validation["valid"])
        errors.extend(validation["errors"])
        errors.extend(_canaryErrors(base, manifest.get("canaryQueries") or []))
        errors.extend(_sourceCanaryPackErrors(base, manifest.get("sourceCanaryPack") or []))

    if requireLoadable and (base / "main.npz").exists():
        try:
            from dartlab.providers.dart.search.fieldIndex import loadSegment

            if loadSegment("main", base) is None:
                errors.append("loadSmoke:main")
        except Exception:  # noqa: BLE001 — corrupt local artifact must not activate.
            errors.append("loadSmoke:main")

    return {"valid": not errors, "errors": errors, "manifestValid": manifestValid}


def activateStagedIndex(
    stagedDir: str | Path,
    *,
    baseDir: str | Path,
    requireLoadable: bool = True,
) -> dict[str, Any]:
    """Atomically point the active index pointer at a staged artifact directory.

    Args:
        stagedDir: Candidate artifact directory under `baseDir`.
        baseDir: Flat `data/dart/contentIndex` directory containing `active.json`.
        requireLoadable: True runs `loadSegment("main")` before activation.

    Returns:
        dict: Activation result with `activated`, `errors`, and `activeDir`.

    Raises:
        None. Pointer replacement failures are returned as errors.

    Example:
        >>> callable(activateStagedIndex)
        True
    """
    base = Path(baseDir)
    staged = Path(stagedDir)
    check = selfcheckLocalIndex(staged, requireManifest=True, requireLoadable=requireLoadable)
    if not check["valid"]:
        return {"activated": False, "errors": check["errors"], "activeDir": None}
    try:
        rel = staged.resolve().relative_to(base.resolve())
    except ValueError:
        return {"activated": False, "errors": ["outsideBase:activeDir"], "activeDir": None}
    try:
        writeActivePointer(base, str(rel).replace("\\", "/"))
    except OSError as exc:
        return {"activated": False, "errors": [f"writePointer:{exc.__class__.__name__}"], "activeDir": None}
    return {
        "activated": True,
        "errors": [],
        "activeDir": str(staged),
        "previousActiveDir": _previousActiveDir(base),
    }


def rollbackActiveIndex(
    *,
    baseDir: str | Path,
    requireLoadable: bool = True,
) -> dict[str, Any]:
    """Rollback `active.json` to the previously active index directory.

    Args:
        baseDir: Flat `data/dart/contentIndex` directory containing `active.json`.
        requireLoadable: True runs `loadSegment("main")` on the rollback target.

    Returns:
        dict: Rollback result with `rolledBack`, `errors`, and `activeDir`.

    Raises:
        None. Invalid rollback targets preserve the current active pointer.

    Example:
        >>> rollbackActiveIndex(baseDir="missing")["rolledBack"]
        False
    """
    base = Path(baseDir)
    pointer = base / ACTIVE_POINTER_NAME
    data = _readPointer(pointer)
    previous = data.get("previousActiveDir") if isinstance(data, dict) else None
    if not isinstance(previous, str) or not previous:
        return {
            "rolledBack": False,
            "errors": ["missing:previousActiveDir"],
            "activeDir": str(resolveActiveIndexDir(base) or ""),
        }
    target = _resolveInsideBase(base, previous)
    if target is None:
        return {
            "rolledBack": False,
            "errors": ["outsideBase:previousActiveDir"],
            "activeDir": str(resolveActiveIndexDir(base) or ""),
        }
    check = selfcheckLocalIndex(target, requireManifest=True, requireLoadable=requireLoadable)
    if not check["valid"]:
        return {"rolledBack": False, "errors": check["errors"], "activeDir": str(resolveActiveIndexDir(base) or "")}
    try:
        writeActivePointer(base, previous)
    except OSError as exc:
        return {
            "rolledBack": False,
            "errors": [f"writePointer:{exc.__class__.__name__}"],
            "activeDir": str(resolveActiveIndexDir(base) or ""),
        }
    return {"rolledBack": True, "errors": [], "activeDir": str(target)}


def downloadAndActivateContentIndex(
    *,
    tier: str | None = None,
    baseDir: str | Path | None = None,
    requireLoadable: bool = True,
    downloadFile: Any | None = None,
    manifestRepoPath: str | None = None,
) -> dict[str, Any]:
    """Download a manifest-described HF content index into staging and activate it.

    Args:
        tier: ``"lite"`` or ``"full"``. None resolves to ``"lite"``.
        baseDir: Flat ``data/dart/contentIndex`` directory. None uses the runtime data root.
        requireLoadable: True runs ``loadSegment("main")`` before activation.
        downloadFile: Test hook. Callable ``(repo_path, download_root) -> local_path``.
        manifestRepoPath: Optional explicit manifest path inside the HF repo.
            Use this to validate a staged candidate manifest before it is
            promoted to the current pointer.

    Returns:
        dict: ``{"activated": bool, "errors": list[str], "activeDir": str | None}``.

    Raises:
        None. Download and validation failures are returned as errors.

    Example:
        >>> callable(downloadAndActivateContentIndex)
        True
    """
    tier = (tier or "lite").strip()
    base: Path | None = None
    try:
        from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

        base = Path(baseDir) if baseDir is not None else _contentIndexDir()
        runId = f"{tier}-{time.strftime('%Y%m%dT%H%M%S')}-{int(time.time() * 1000) % 1000:03d}"
        staged = base / STAGING_DIR_NAME / runId
        downloadRoot = staged / "_download"
        staged.mkdir(parents=True, exist_ok=True)
        downloadRoot.mkdir(parents=True, exist_ok=True)

        from dartlab.core.dataConfig import DATA_RELEASES, repoFor
        from dartlab.core.hfRetry import retryHfCall

        ciDir = DATA_RELEASES["contentIndex"]["dir"]
        repoPrefix = ciDir if tier == "full" else f"{ciDir}/{tier}"
        repo = repoFor("contentIndex")

        def _fetchRel(rel: str) -> Path:
            repoPath = rel if rel.startswith(f"{repoPrefix}/") else f"{repoPrefix}/{rel}"
            if downloadFile is not None:
                return Path(downloadFile(repoPath, downloadRoot))
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

        manifestPath = _fetchRel(manifestRepoPath or "manifest.json")
        manifestTarget = staged / "manifest.json"
        _copyFile(manifestPath, manifestTarget)

        from dartlab.providers.dart.search.manifest import loadSearchManifest

        manifest = loadSearchManifest(staged)
        if manifest is None:
            return {"activated": False, "errors": ["download:invalidManifest"], "activeDir": _currentActiveDir(base)}
        localManifest = loadActiveSearchManifest(base)
        if not shouldActivateRemoteManifest(manifest, localManifest):
            return {
                "activated": False,
                "errors": [],
                "activeDir": str(resolveActiveIndexDir(base) or ""),
                "skipped": "notNewer",
            }
        required = _requiredFiles(manifest)
        fileSources = _fileSources(manifest)
        for rel in required:
            if rel == "manifest.json":
                continue
            src = _fetchRel(fileSources.get(rel) or rel)
            _copyFile(src, staged / rel)
        return activateStagedIndex(staged, baseDir=base, requireLoadable=requireLoadable)
    except Exception as exc:  # noqa: BLE001 — bad downloads must preserve the active index.
        return {
            "activated": False,
            "errors": [f"download:{exc.__class__.__name__}"],
            "activeDir": _currentActiveDir(base),
        }


def writeActivePointer(baseDir: str | Path, activeDir: str) -> Path:
    """Write `active.json` through a replace-style atomic pointer update.

    Args:
        baseDir: Flat `data/dart/contentIndex` directory.
        activeDir: Directory path relative to `baseDir`.

    Returns:
        Path: Written active pointer path.

    Raises:
        OSError: When the pointer cannot be written.

    Example:
        >>> writeActivePointer
        <function writeActivePointer at ...>
    """
    base = Path(baseDir)
    base.mkdir(parents=True, exist_ok=True)
    pointer = base / ACTIVE_POINTER_NAME
    tmp = base / f"{ACTIVE_POINTER_NAME}.tmp"
    current = _readPointer(pointer)
    previous = current.get("activeDir") if isinstance(current.get("activeDir"), str) else ""
    if previous == activeDir:
        previous = current.get("previousActiveDir") if isinstance(current.get("previousActiveDir"), str) else ""
    payload = {"activeDir": activeDir, "activatedAt": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if previous:
        payload["previousActiveDir"] = previous
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(pointer)
    return pointer


def _readPointer(pointer: Path) -> dict[str, Any]:
    if not pointer.exists():
        return {}
    try:
        data = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _currentActiveDir(base: Path | None) -> str | None:
    if base is None:
        return None
    active = resolveActiveIndexDir(base)
    return str(active) if active is not None else None


def _resolveInsideBase(base: Path, raw: str) -> Path | None:
    target = Path(raw)
    if not target.is_absolute():
        target = base / target
    try:
        target.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return target


def _previousActiveDir(base: Path) -> str:
    data = _readPointer(base / ACTIVE_POINTER_NAME)
    value = data.get("previousActiveDir")
    return value if isinstance(value, str) else ""


def _requiredFiles(manifest: dict[str, Any]) -> list[str]:
    raw = manifest.get("requiredFiles") or []
    out: list[str] = ["manifest.json"]
    if isinstance(raw, list):
        for rel in raw:
            if isinstance(rel, str) and rel and rel not in out:
                out.append(rel)
    return out


def _fileSources(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("fileSources")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for rel, repoPath in raw.items():
        if isinstance(rel, str) and isinstance(repoPath, str) and rel and repoPath:
            out[rel] = repoPath
    return out


def _copyFile(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def _canaryErrors(indexDir: Path, rawQueries: Any) -> list[str]:
    if not rawQueries:
        return []
    if not isinstance(rawQueries, list):
        return ["invalid:canaryQueries"]
    try:
        from dartlab.providers.dart.search.fieldIndex import _scoreBM25, loadSegment, tokenizeContent

        loaded = loadSegment("main", indexDir)
        if loaded is None:
            return ["canary:mainLoad"]
        idx, _meta = loaded
    except Exception:  # noqa: BLE001 — corrupt artifacts must not activate.
        return ["canary:mainLoad"]
    errors: list[str] = []
    for item in rawQueries:
        query = item.get("query") if isinstance(item, dict) else item
        if not isinstance(query, str) or not query.strip():
            errors.append("invalid:canaryQuery")
            continue
        tokens = tokenizeContent(query)
        if not tokens:
            errors.append(f"canaryNoTokens:{query}")
            continue
        scores = _scoreBM25(idx, tokens)
        if scores.size == 0 or float(scores.max()) <= 0:
            errors.append(f"canaryMiss:{query}")
    return errors


def _sourceCanaryPackErrors(indexDir: Path, rawRows: Any) -> list[str]:
    if not rawRows:
        return []
    if not isinstance(rawRows, list):
        return ["invalid:sourceCanaryPack"]
    try:
        from dartlab.providers.dart.search.canaryPack import evaluateCanaryPackRows
        from dartlab.providers.dart.search.fieldIndex import _scoreBM25, loadSegment, tokenizeContent

        loaded = loadSegment("main", indexDir)
        if loaded is None:
            return ["sourceCanary:mainLoad"]
        idx, meta = loaded
    except Exception:  # noqa: BLE001 — corrupt artifacts must not activate.
        return ["sourceCanary:mainLoad"]
    resultsByQuery: dict[str, list[dict[str, Any]]] = {}
    for row in rawRows:
        if not isinstance(row, dict):
            return ["invalid:sourceCanaryPackRow"]
        query = str(row.get("query") or row.get("q") or "")
        tokens = tokenizeContent(query)
        scores = _scoreBM25(idx, tokens) if tokens else []
        ranked: list[dict[str, Any]] = []
        if len(scores):
            order = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
            for docId in order[: int(row.get("topK") or 10)]:
                score = float(scores[docId])
                if score <= 0:
                    continue
                metaRow = dict(meta.row(docId, named=True))
                ranked.append(
                    {
                        "source": metaRow.get("source") or "",
                        "sourceRef": metaRow.get("sourceRef") or metaRow.get("rcept_no") or "",
                        "answerable": True,
                    }
                )
        resultsByQuery[query] = ranked
    report = evaluateCanaryPackRows(rawRows, resultsByQuery)
    return [f"sourceCanary:{failure['query']}:{failure['failureType']}" for failure in report["failures"]]


def _manifestIdentity(manifest: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        manifest.get("artifactVersion"),
        manifest.get("builtAt"),
        manifest.get("sourceDataAsOf"),
        manifest.get("fileHashes"),
    )
