"""Runtime dataset catalog and dataset inspection.

The package intentionally uses `datasets`, not `data`, to avoid confusing the
AI engine implementation with a local or external runtime data root.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .contracts import Ref, new_id

_DATASET_PATTERNS = ("*.parquet", "*.csv")


@dataclass(frozen=True)
class DatasetLocation:
    dataset_id: str
    root: str
    path: str
    exists: bool
    files: list[str] = field(default_factory=list)
    latest_as_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatasetInspection:
    ok: bool
    dataset_id: str | None
    path: str | None
    format: str | None
    rows: int | None
    columns: list[str]
    dtypes: dict[str, str]
    latest: dict[str, Any] | None
    semantic_profile: dict[str, Any]
    head: list[dict[str, Any]]
    tail: list[dict[str, Any]]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeDatasetCatalog:
    """Discovers usable runtime datasets without assuming they are git-tracked."""

    def __init__(self, roots: list[str | os.PathLike[str]] | None = None) -> None:
        self.roots = _unique_paths([Path(p) for p in roots] if roots else _default_roots())

    def list(self) -> list[DatasetLocation]:
        """런타임 데이터셋 목록 — 접근 가능한 parquet/csv 묶음 discovery.

        Description
        -----------
        `DARTLAB_DATA_DIR`, 로컬 `data/`, 패키지 번들, 사용자 캐시에서
        parquet/csv 파일이 있는 디렉터리를 데이터셋으로 발견한다. 데이터셋 id는
        경로에서 자동 생성하며 수동 registry 를 사용하지 않는다.

        Parameters
        ----------
        없음
            생성자에 전달된 roots 또는 기본 런타임 roots 를 사용한다.

        Returns
        -------
        list[DatasetLocation]
            dataset_id : str — 경로 기반 dataset id
            root : str — 탐색 root 경로
            path : str — 데이터셋 디렉터리 경로
            exists : bool — 파일 존재 여부
            files : list[str] — 샘플 파일 경로
            latest_as_of : str | None — 실제 파일에서 계산한 최신 관측일

        Raises
        ------
        없음
            읽을 수 없는 파일은 건너뛴다.

        Examples
        --------
        >>> RuntimeDatasetCatalog().list()
        [DatasetLocation(...)]

        Notes
        -----
        git 추적 여부는 품질 조건이 아니다.

        Guide
        -----
        LLM 에게 사용 가능한 런타임 데이터셋 후보를 짧게 보여줄 때 쓴다.

        See Also
        --------
        inspect_dataset : 특정 dataset id/path 의 schema/latest 검사.
        """

        locations: list[DatasetLocation] = []
        seen: set[str] = set()
        for root in self.roots:
            if not root.exists():
                continue
            for directory, files in _dataset_directories(root):
                dataset_id = _dataset_id(root, directory)
                if dataset_id in seen:
                    continue
                seen.add(dataset_id)
                locations.append(
                    DatasetLocation(
                        dataset_id=dataset_id,
                        root=str(root),
                        path=str(directory),
                        exists=bool(files),
                        files=[str(p) for p in files[:50]],
                        latest_as_of=_latest_as_of(files),
                    )
                )
        return sorted(locations, key=lambda item: item.dataset_id)

    def resolve(self, dataset_id: str) -> DatasetLocation:
        normalized = dataset_id.replace("\\", ".").replace("/", ".")
        for location in self.list():
            if location.dataset_id == normalized:
                return location
        for root in self.roots:
            path = root.joinpath(*normalized.split("."))
            files = _dataset_files(path)
            if files:
                return DatasetLocation(
                    dataset_id=normalized,
                    root=str(root),
                    path=str(path),
                    exists=True,
                    files=[str(p) for p in files[:50]],
                    latest_as_of=_latest_as_of(files),
                )
        fallback = self.roots[0].joinpath(*normalized.split(".")) if self.roots else Path(*normalized.split("."))
        return DatasetLocation(dataset_id=normalized, root=str(self.roots[0]) if self.roots else "", path=str(fallback), exists=False)

    def inspect(self, target: str, *, sample: int = 5, columns: list[str] | None = None) -> DatasetInspection:
        target = _normalize_dataset_target(target)
        location: DatasetLocation | None = None
        path: Path
        path_candidate = _resolve_path_target(target, self.roots)
        if path_candidate is not None and path_candidate.exists():
            path = path_candidate
            if path.is_dir():
                files = _dataset_files(path)
                if not files:
                    return _inspection_error(str(path), "dataset directory has no parquet/csv files")
                location = _location_for_path(self.roots, path, files)
                path = _best_file([str(p) for p in files])
            else:
                location = _location_for_path(self.roots, path.parent, [path])
        else:
            resolved = self.resolve(target)
            if resolved.exists:
                location = resolved
                path = _best_file(location.files)
            else:
                raw_target = target if _looks_like_path(target) else target.replace(".", os.sep)
                path = Path(raw_target).expanduser()
                if not path.is_absolute():
                    for root in self.roots:
                        for candidate in (root / target, root / raw_target):
                            if candidate.exists():
                                path = candidate
                                break
                        if path.exists():
                            break
                if path.is_dir():
                    files = _dataset_files(path)
                    if not files:
                        return _inspection_error(str(path), "dataset directory has no parquet/csv files")
                    location = _location_for_path(self.roots, path, files)
                    path = _best_file([str(p) for p in files])
                if not path.exists():
                    return _inspection_error(str(path), "dataset path not found")
                if path.is_file():
                    location = _location_for_path(self.roots, path.parent, [path])

        return _inspect_file(path, dataset_id=location.dataset_id if location else None, sample=sample, requested_columns=columns)


def inspect_dataset(target: str, *, sample: int = 5, columns: list[str] | None = None) -> DatasetInspection:
    """런타임 데이터셋 검사 — schema/latest/entity/metric 요약.

    Description
    -----------
    dataset id 또는 parquet/csv 경로를 받아 실제 런타임 데이터 파일을 검사한다.
    git 추적 여부와 무관하게 접근 가능한 데이터 루트를 기준으로 동작한다.

    Parameters
    ----------
    target : str
        dataset id 또는 파일/디렉터리 경로. 예: `"krx.indices"`, `"data/krx/indices"`.
    sample : int, optional
        head/tail 샘플 행 수.
    columns : list[str], optional
        확인할 컬럼 목록. None 이면 전체 schema 를 사용한다.

    Returns
    -------
    DatasetInspection
        ok : bool — 검사 성공 여부
        dataset_id : str | None — 경로에서 추론한 dataset id
        path : str | None — 검사한 parquet/csv 파일 경로
        rows : int | None — 전체 행 수 (행)
        columns : list[str] — 컬럼명
        latest : dict | None — 최신 관측일 컬럼과 값
        semantic_profile : dict — date/entity/metric 후보
        head : list[dict] — 앞쪽 샘플 행
        tail : list[dict] — 뒤쪽 샘플 행
        error : str | None — 실패 사유

    Raises
    ------
    없음
        실패는 `ok=False` 와 `error` 로 반환한다.

    Examples
    --------
    >>> inspect_dataset("krx.indices").latest
    {'column': 'BAS_DD', 'value': '20260428'}

    Notes
    -----
    최신일을 모르면 None 으로 둔다. 날짜를 추정하거나 만들지 않는다.

    Guide
    -----
    LLM 은 데이터 날짜나 schema 를 말하기 전에 이 함수를 호출해야 한다.

    See Also
    --------
    RuntimeDatasetCatalog : 런타임 데이터셋 discovery.
    """

    return RuntimeDatasetCatalog().inspect(target, sample=sample, columns=columns)


def inspection_to_refs(inspection: DatasetInspection) -> list[Ref]:
    refs: list[Ref] = []
    if not inspection.ok:
        return refs
    refs.append(
        Ref(
            id=new_id("dataset"),
            kind="dataset",
            source="inspect_dataset",
            payload=inspection.to_dict(),
        )
    )
    if inspection.latest:
        refs.append(
            Ref(
                id=new_id("date"),
                kind="date",
                source="inspect_dataset",
                payload={
                    "datasetId": inspection.dataset_id,
                    "path": inspection.path,
                    "observedDate": inspection.latest.get("value"),
                    "basis": f"max {inspection.latest.get('column')} in runtime dataset",
                },
            )
        )
    return refs


inspectDataset = inspect_dataset


def _default_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.environ.get("DARTLAB_DATA_DIR")
    if env:
        roots.append(Path(env))
    cwd = Path.cwd()
    for base in [cwd, *cwd.parents]:
        roots.append(base / "data")
        if (base / "pyproject.toml").exists() and (base / "src" / "dartlab").exists():
            break
    package_root = Path(__file__).resolve().parents[2]
    roots.append(package_root / "data")
    roots.append(Path.home() / ".dartlab" / "data")
    return roots


def _unique_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = str(path.expanduser().resolve()) if path.exists() else str(path.expanduser())
        key = resolved.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(Path(resolved))
    return out


def _looks_like_path(target: str) -> bool:
    lowered = target.lower()
    return (
        "/" in target
        or "\\" in target
        or lowered.endswith((".parquet", ".csv"))
        or ":" in target
    )


def _normalize_dataset_target(target: str) -> str:
    prefix = "dartlab://datasets/"
    if target.startswith(prefix):
        return target[len(prefix) :]
    if target == "dartlab://datasets":
        return ""
    return target


def _resolve_path_target(target: str, roots: list[Path]) -> Path | None:
    if not target or target.startswith("dartlab://"):
        return None
    if not _looks_like_path(target):
        return None
    path = Path(target).expanduser()
    if path.exists():
        return path
    if path.is_absolute():
        return path
    for root in roots:
        candidate = root.parent / target if root.name == "data" and target.replace("\\", "/").startswith("data/") else root / target
        if candidate.exists():
            return candidate
    return path


def _dataset_directories(root: Path) -> list[tuple[Path, list[Path]]]:
    grouped: dict[Path, list[Path]] = {}
    for pattern in _DATASET_PATTERNS:
        for file in root.rglob(pattern):
            if not file.is_file():
                continue
            parts = file.relative_to(root).parts
            if any(part.startswith(".") for part in parts) or _is_non_analysis_dataset(parts):
                continue
            grouped.setdefault(file.parent, []).append(file)
    return [(directory, sorted(files, key=lambda p: p.name, reverse=True)) for directory, files in grouped.items()]


def _is_non_analysis_dataset(parts: tuple[str, ...]) -> bool:
    blocked = {"ai-artifacts", "audit", "logs", "tmp", "temp", "__pycache__"}
    return any(part in blocked for part in parts)


def _dataset_id(root: Path, directory: Path) -> str:
    try:
        rel = directory.relative_to(root)
    except ValueError:
        rel = directory
    parts = [part for part in rel.parts if part not in {"", "."}]
    return ".".join(parts) if parts else directory.name


def _location_for_path(roots: list[Path], directory: Path, files: list[Path]) -> DatasetLocation:
    root = _nearest_root(roots, directory)
    dataset_id = _dataset_id(root, directory)
    return DatasetLocation(
        dataset_id=dataset_id,
        root=str(root),
        path=str(directory),
        exists=bool(files),
        files=[str(p) for p in files[:50]],
        latest_as_of=_latest_as_of(files),
    )


def _nearest_root(roots: list[Path], path: Path) -> Path:
    for root in roots:
        try:
            path.relative_to(root)
            return root
        except ValueError:
            continue
    return path.parent


def _dataset_files(path: Path) -> list[Path]:
    files: list[Path] = []
    if not path.exists():
        return files
    for pattern in _DATASET_PATTERNS:
        files.extend(p for p in path.glob(pattern) if p.is_file())
    return sorted(files, key=lambda p: p.name, reverse=True)


def _latest_as_of(files: list[Path]) -> str | None:
    latest: str | None = None
    for file in files[:20]:
        candidate = _file_latest(file)
        if candidate and (latest is None or candidate > latest):
            latest = candidate
    return latest


def _best_file(files: list[str]) -> Path:
    best_path = Path(files[0])
    best_latest = _file_latest(best_path)
    for file in files[1:20]:
        path = Path(file)
        latest = _file_latest(path)
        if latest and (best_latest is None or latest > best_latest):
            best_path = path
            best_latest = latest
    return best_path


def _file_latest(path: Path) -> str | None:
    try:
        import polars as pl

        if path.suffix.lower() == ".parquet":
            schema = pl.scan_parquet(str(path)).collect_schema()
            for col in _infer_date_columns(schema.names()):
                if col in schema.names():
                    value = pl.scan_parquet(str(path)).select(pl.col(col).max()).collect().item()
                    return str(value) if value is not None else None
        if path.suffix.lower() == ".csv":
            lazy = pl.scan_csv(str(path), infer_schema_length=100)
            schema = lazy.collect_schema()
            for col in _infer_date_columns(schema.names()):
                if col in schema.names():
                    value = lazy.select(pl.col(col).max()).collect().item()
                    return str(value) if value is not None else None
    except Exception:
        return None
    return None


def _inspect_file(path: Path, *, dataset_id: str | None, sample: int, requested_columns: list[str] | None) -> DatasetInspection:
    try:
        import polars as pl

        suffix = path.suffix.lower().lstrip(".")
        if suffix == "parquet":
            lazy = pl.scan_parquet(str(path))
        elif suffix == "csv":
            lazy = pl.scan_csv(str(path), infer_schema_length=200)
        else:
            return _inspection_error(str(path), f"unsupported dataset format: {path.suffix}")

        schema = lazy.collect_schema()
        available_columns = schema.names()
        selected_columns = [c for c in (requested_columns or available_columns) if c in available_columns]
        if not selected_columns:
            selected_columns = available_columns
        projected = lazy.select(selected_columns)
        rows = int(lazy.select(pl.len()).collect().item())
        dtypes = {name: str(dtype) for name, dtype in schema.items()}
        profile = _semantic_profile(str(path), dataset_id, available_columns, dtypes, lazy)
        latest = profile.get("latest")
        head = projected.head(max(1, sample)).collect().to_dicts()
        tail = projected.tail(max(1, sample)).collect().to_dicts()
        return DatasetInspection(
            ok=True,
            dataset_id=dataset_id,
            path=str(path),
            format=suffix,
            rows=rows,
            columns=available_columns,
            dtypes=dtypes,
            latest=latest,
            semantic_profile=profile,
            head=head,
            tail=tail,
        )
    except Exception as exc:  # noqa: BLE001
        return _inspection_error(str(path), str(exc))


def _semantic_profile(path: str, dataset_id: str | None, columns: list[str], dtypes: dict[str, str], lazy: Any) -> dict[str, Any]:
    date_cols = _infer_date_columns(columns, dtypes)
    target_cols = _infer_entity_columns(columns)
    metric_cols = _infer_metric_columns(columns, dtypes)
    latest = None
    if date_cols:
        col = date_cols[0]
        try:
            value = lazy.select(__import__("polars").col(col).max()).collect().item()
            latest = {"column": col, "value": str(value) if value is not None else None}
        except Exception:
            latest = {"column": col, "value": None}
    universe = None
    if target_cols:
        try:
            pl = __import__("polars")
            universe = {"column": target_cols[0], "uniqueCount": int(lazy.select(pl.col(target_cols[0]).n_unique()).collect().item())}
        except Exception:
            universe = {"column": target_cols[0], "uniqueCount": None}
    return {
        "datasetId": dataset_id,
        "path": path,
        "columnRoles": {c: _role_for(c, dtypes.get(c, "")) for c in columns},
        "dateColumns": date_cols,
        "entityColumns": target_cols,
        "metricCandidates": metric_cols,
        "latest": latest,
        "universe": universe,
    }


def _infer_date_columns(columns: list[str], dtypes: dict[str, str] | None = None) -> list[str]:
    priority = ["BAS_DD", "rcept_dt", "date", "DATE", "observedDate"]
    dtypes = dtypes or {}
    out = [c for c in priority if c in columns]
    for column in columns:
        if column in priority:
            continue
        lowered = column.lower()
        dtype = dtypes.get(column, "")
        numeric = any(marker in dtype for marker in ("Int", "Float", "Decimal", "UInt"))
        if "date" in lowered or lowered.endswith("_dt") or lowered.endswith("_date"):
            out.append(column)
            continue
        if numeric:
            continue
        if lowered in {"dt", "ymd"} or lowered.endswith("_ymd"):
            out.append(column)
    return out


def _infer_entity_columns(columns: list[str]) -> list[str]:
    candidates = ["IDX_NM", "IDX_CD", "ISU_CD", "ISU_NM", "ISU_SRT_CD", "ISU_ABBRV", "corp_name", "corp_code", "stock_code", "symbol", "series"]
    return [c for c in candidates if c in columns]


def _infer_metric_columns(columns: list[str], dtypes: dict[str, str]) -> list[str]:
    numeric_markers = ("Int", "Float", "Decimal", "UInt")
    date_columns = set(_infer_date_columns(columns, dtypes))
    return [c for c in columns if any(marker in dtypes.get(c, "") for marker in numeric_markers) and c not in date_columns]


def _role_for(column: str, dtype: str) -> str:
    if column in _infer_date_columns([column], {column: dtype}):
        return "date"
    if column in _infer_entity_columns([column]):
        return "entity"
    if any(marker in dtype for marker in ("Int", "Float", "Decimal", "UInt")):
        return "metric"
    return "attribute"


def _inspection_error(path: str, error: str) -> DatasetInspection:
    return DatasetInspection(
        ok=False,
        dataset_id=None,
        path=path,
        format=None,
        rows=None,
        columns=[],
        dtypes={},
        latest=None,
        semantic_profile={},
        head=[],
        tail=[],
        error=error,
    )
