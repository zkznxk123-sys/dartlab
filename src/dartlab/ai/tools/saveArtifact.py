"""save_artifact — 산출물 저장 + artifactRef 발급.

read.py + write.py 의 통합 후속. ai/ 가 사용자 홈 안전 경로에 결과를 저장한다.
"""

from __future__ import annotations

import re
from pathlib import Path

from dartlab.ai.contracts import Ref

from .types import ToolResult

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _resolveArtifactRoot() -> Path:
    root = Path.home() / ".dartlab" / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def saveArtifact(name: str, content: str, *, kind: str = "text") -> ToolResult:
    """saveArtifact — TODO 한국어 동작 설명."""
    safe = _SAFE_NAME_RE.sub("_", str(name or "").strip()) or "artifact"
    target = _resolveArtifactRoot() / safe
    try:
        target.write_text(str(content or ""), encoding="utf-8")
    except OSError as exc:
        return ToolResult(False, f"save_artifact 실패: {exc}", error="save_failed")
    refs = [
        Ref(
            id=f"artifact:{safe}",
            kind="artifactRef",
            title=safe,
            source=str(target),
            payload={"kind": kind, "size": len(content or ""), "path": str(target)},
        )
    ]
    return ToolResult(True, f"artifact 저장: {safe}", refs=refs, data={"path": str(target), "kind": kind})
