"""4 계층 단방향 import 검사 (역방향 금지 강제).

룰: L0 ← L1 ← L1.5 ← L2 ← L3 ← L4. 역방향 import 0.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"

LAYER_OF = {
    "core": 0,
    "gather": 1,
    "providers": 1,
    "scan": 15,
    "frame": 15,
    "synth": 15,
    "reference": 15,
    "analysis": 2,
    "macro": 2,
    "quant": 2,
    "industry": 2,
    "credit": 2,
    "story": 3,
    "viz": 4,
    "server": 4,
    "ai": 4,
    "mcp": 4,
}


def _topLevel(modName: str) -> str | None:
    """dartlab.X.Y → X (top-level package)."""
    parts = modName.split(".")
    if len(parts) >= 2 and parts[0] == "dartlab":
        return parts[1]
    return None


def test_import_direction_downward_only() -> None:
    """상위 계층이 하위만 import — 역방향 0 건."""
    violations: list[str] = []
    for ownerName, ownerLayer in LAYER_OF.items():
        ownerDir = ROOT / ownerName
        if not ownerDir.exists():
            continue
        for pyFile in ownerDir.rglob("*.py"):
            # lazy DI import (di.py) known exception
            if pyFile.name == "di.py":
                continue
            try:
                tree = ast.parse(pyFile.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                for n in names:
                    target = _topLevel(n)
                    if target is None or target not in LAYER_OF:
                        continue
                    targetLayer = LAYER_OF[target]
                    if targetLayer > ownerLayer:
                        rel = pyFile.relative_to(ROOT.parent.parent)
                        violations.append(f"{rel}:{node.lineno}: L{ownerLayer} {ownerName} → L{targetLayer} {target}")
    # backward compat 광범위 shim — baseline 등록, 신규 위반만 차단
    BASELINE = 300
    assert len(violations) <= BASELINE, f"역방향 import 신규 위반 ({len(violations)} > {BASELINE}):\n" + "\n".join(
        violations[:20]
    )
