"""AI workbench 아티팩트 저장.

LLM 에 넣는 요약 문자열과 별도로, 웹/CLI 가 내려받을 수 있는 표 원본과
질의별 journal/result 원본을 dataDir 내부에 남긴다.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def csvArtifactsForToolResult(result: Any, *, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    """tool_result 원본에서 CSV 로 저장 가능한 표를 찾아 아티팩트 메타를 반환한다."""
    frames = _extractFrames(result)
    if not frames:
        return []

    out: list[dict[str, Any]] = []
    day = datetime.now().strftime("%Y-%m-%d")
    outDir = _artifactRoot() / day
    outDir.mkdir(parents=True, exist_ok=True)

    for label, frame in frames:
        rows, cols = _shape(frame)
        if rows <= 0 or cols <= 0:
            continue
        filename = _filename(name, label)
        path = outDir / filename
        _writeCsv(frame, path)
        out.append(
            {
                "id": path.stem,
                "kind": "table",
                "format": "csv",
                "primary": _isPrimaryArtifact(name=name, label=label, rows=rows, columns=cols),
                "mimeType": "text/csv; charset=utf-8",
                "name": name,
                "label": label,
                "fileName": filename,
                "day": day,
                "url": f"/api/ask/artifacts/{day}/{filename}",
                "rows": rows,
                "columns": cols,
                "target": arguments.get("stockCode") or arguments.get("target") or arguments.get("axis"),
            }
        )
    return out


class WorkbenchJournal:
    """Append-only JSONL journal for one Ask Workbench request."""

    def __init__(self, *, question: str) -> None:
        day = datetime.now().strftime("%Y-%m-%d")
        filename = _filename("journal", "events").replace(".csv", ".jsonl")
        self.day = day
        self.path = _artifactRoot() / day / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact = _artifactMeta(
            path=self.path,
            day=day,
            filename=filename,
            kind="journal",
            format="jsonl",
            name="workbench_journal",
            label="events",
            primary=False,
            mime_type="application/x-ndjson; charset=utf-8",
            extra={"questionHash": uuid.uuid5(uuid.NAMESPACE_URL, question).hex[:12]},
        )

    def append(self, event: Any) -> None:
        """Append one event; journal failures must never break analysis."""
        try:
            payload = event.to_dict() if hasattr(event, "to_dict") else event
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str))
                handle.write("\n")
        except OSError:
            return


def jsonArtifactForPayload(
    payload: Any,
    *,
    name: str,
    label: str,
    primary: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store arbitrary JSON payload and return artifact metadata."""
    day = datetime.now().strftime("%Y-%m-%d")
    outDir = _artifactRoot() / day
    outDir.mkdir(parents=True, exist_ok=True)
    filename = _filename(name, label).replace(".csv", ".json")
    path = outDir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return _artifactMeta(
        path=path,
        day=day,
        filename=filename,
        kind="result",
        format="json",
        name=name,
        label=label,
        primary=primary,
        mime_type="application/json; charset=utf-8",
        extra=extra or {},
    )


def _isPrimaryArtifact(*, name: str, label: str, rows: int, columns: int) -> bool:
    if name in {"pythonExec", "run_python"} and label in {"stdout", "result"}:
        return True
    return 0 < rows <= 100 and columns >= 2


def artifactPath(day: str, filename: str) -> Path | None:
    """다운로드 요청의 day/filename 을 dataDir 내부 artifact 경로로 해석한다."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return None
    if "/" in filename or "\\" in filename or not filename.endswith((".csv", ".json", ".jsonl")):
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(csv|json|jsonl)", filename):
        return None
    path = (_artifactRoot() / day / filename).resolve()
    root = _artifactRoot().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def _artifactMeta(
    *,
    path: Path,
    day: str,
    filename: str,
    kind: str,
    format: str,
    name: str,
    label: str,
    primary: bool,
    mime_type: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = {
        "id": path.stem,
        "kind": kind,
        "format": format,
        "primary": primary,
        "mimeType": mime_type,
        "name": name,
        "label": label,
        "fileName": filename,
        "day": day,
        "url": f"/api/ask/artifacts/{day}/{filename}",
    }
    if extra:
        meta.update(extra)
    return meta


def _artifactRoot() -> Path:
    from dartlab import config

    return Path(config.dataDir) / "ai-artifacts"


def _extractFrames(result: Any) -> list[tuple[str, Any]]:
    try:
        import polars as pl

        if isinstance(result, pl.DataFrame):
            return [("result", result)]
    except ImportError:
        pass

    if _isTabularList(result):
        return [("result", result)]

    if isinstance(result, str):
        parsed = _parseDelimitedText(result)
        return [("stdout", parsed)] if parsed else []

    if isinstance(result, dict):
        frames: list[tuple[str, Any]] = []
        for key, value in result.items():
            if _isDataFrame(value) or _isTabularList(value):
                frames.append((str(key), value))
        return frames
    return []


def _isDataFrame(value: Any) -> bool:
    try:
        import polars as pl

        return isinstance(value, pl.DataFrame)
    except ImportError:
        return False


def _isTabularList(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    if not all(isinstance(row, dict) for row in value):
        return False
    first = tuple(value[0].keys())
    return len(first) > 0 and all(tuple(row.keys()) == first for row in value)


def _parseDelimitedText(text: str) -> list[dict[str, str]] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for delimiter in ("\t", ","):
        for idx, line in enumerate(lines):
            if delimiter not in line:
                continue
            headers = [cell.strip() for cell in line.split(delimiter)]
            if len(headers) < 2 or len(set(headers)) != len(headers):
                continue
            rows: list[dict[str, str]] = []
            for body in lines[idx + 1 :]:
                if delimiter not in body:
                    if rows:
                        break
                    continue
                cells = [cell.strip() for cell in body.split(delimiter)]
                if len(cells) != len(headers):
                    if rows:
                        break
                    continue
                rows.append(dict(zip(headers, cells, strict=True)))
            if rows:
                return rows
    return None


def _shape(frame: Any) -> tuple[int, int]:
    if _isDataFrame(frame):
        return int(frame.height), int(frame.width)
    if _isTabularList(frame):
        return len(frame), len(frame[0])
    return 0, 0


def _writeCsv(frame: Any, path: Path) -> None:
    try:
        import polars as pl

        df = frame if isinstance(frame, pl.DataFrame) else pl.DataFrame(_flattenNestedValues(frame), strict=False)
        df = _flattenNestedDataFrame(df)
        df.write_csv(path)
        return
    except ImportError:
        pass

    import csv

    rows = frame if isinstance(frame, list) else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _flattenNestedValues(frame: Any) -> Any:
    if not isinstance(frame, list):
        return frame
    rows: list[dict[str, Any]] = []
    for row in frame:
        if not isinstance(row, dict):
            return frame
        rows.append({str(key): _csvScalar(value) for key, value in row.items()})
    return rows


def _flattenNestedDataFrame(df: Any) -> Any:
    try:
        import polars as pl

        casts = []
        for name, dtype in zip(df.columns, df.dtypes, strict=True):
            if dtype in (pl.List, pl.Struct, pl.Object) or str(dtype).startswith(("List", "Struct", "Object")):
                casts.append(pl.col(name).map_elements(_csvScalar, return_dtype=pl.Utf8).alias(name))
        return df.with_columns(casts) if casts else df
    except Exception:  # noqa: BLE001
        return df


def _csvScalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _filename(toolName: str, label: str) -> str:
    safeTool = _slug(toolName) or "tool"
    safeLabel = _slug(label) or "result"
    token = uuid.uuid4().hex[:12]
    return f"{safeTool}_{safeLabel}_{token}.csv"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("._-")[:40]
