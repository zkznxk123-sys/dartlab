"""core/ 잔존 모듈이 L0 primitive 만 (상위 계층 import 금지) 강제."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"
UPPER_LAYERS = (
    "gather",
    "providers",
    "scan",
    "frame",
    "synth",
    "reference",
    "analysis",
    "macro",
    "quant",
    "industry",
    "credit",
    "story",
    "viz",
    "server",
    "ai",
    "mcp",
)


def test_core_l0_only_no_upper_import() -> None:
    """core/ 의 모듈이 상위 계층 import 시 위반."""
    violations: list[str] = []
    coreDir = ROOT / "core"
    for pyFile in coreDir.rglob("*.py"):
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
                for upper in UPPER_LAYERS:
                    if n == f"dartlab.{upper}" or n.startswith(f"dartlab.{upper}."):
                        # lazy DI import (di.py) 는 known exception
                        if pyFile.name == "di.py":
                            continue
                        rel = pyFile.relative_to(ROOT.parent.parent)
                        violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "core L0 only 위반 (상위 계층 import):\n" + "\n".join(violations)
