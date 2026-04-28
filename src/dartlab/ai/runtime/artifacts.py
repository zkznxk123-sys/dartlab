"""AI tool 결과 아티팩트 저장.

LLM 에 넣는 요약 문자열과 별도로, 웹/CLI 가 내려받을 수 있는 표 원본을 CSV 로 남긴다.
"""

from __future__ import annotations

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


def artifactPath(day: str, filename: str) -> Path | None:
    """다운로드 요청의 day/filename 을 dataDir 내부 CSV 경로로 해석한다."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return None
    if "/" in filename or "\\" in filename or not filename.endswith(".csv"):
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.csv", filename):
        return None
    path = (_artifactRoot() / day / filename).resolve()
    root = _artifactRoot().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


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

        df = frame if isinstance(frame, pl.DataFrame) else pl.DataFrame(frame)
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


def _filename(toolName: str, label: str) -> str:
    safeTool = _slug(toolName) or "tool"
    safeLabel = _slug(label) or "result"
    token = uuid.uuid4().hex[:12]
    return f"{safeTool}_{safeLabel}_{token}.csv"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("._-")[:40]
