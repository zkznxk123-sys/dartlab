"""Controlled write tool for artifacts and scratchpad-adjacent files."""

from __future__ import annotations

from pathlib import Path

from dartlab.ai.contracts import Ref

from .types import ToolResult


def write(name: str, content: str, *, kind: str = "artifact") -> ToolResult:
    safe_name = Path(str(name or "artifact.txt")).name
    root = Path.home() / ".dartlab" / "ask_artifacts"
    root.mkdir(parents=True, exist_ok=True)
    path = root / safe_name
    path.write_text(str(content or ""), encoding="utf-8")
    ref = Ref(
        id=f"artifact:{path.name}",
        kind="artifactRef",
        title=path.name,
        source=str(path),
        payload={"path": str(path), "kind": kind, "bytes": path.stat().st_size},
    )
    return ToolResult(True, f"artifact를 저장했습니다: {path.name}", refs=[ref], data={"path": str(path)})
