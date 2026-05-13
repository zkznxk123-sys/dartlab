"""L1.5 4 형제 (scan/frame/synth/reference) cross import 0 강제 — P-CORE 가드.

룰 (operation.architecture SSOT):
- L1.5 = scan · frame · synth · reference (가공 4 형제)
- 4 형제끼리 cross import 금지 (core 잡동사니화 재발 방지)
- 4 형제 모두 core (L0) 와 gather/providers (L1) 만 import 가능
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"
L15_PEERS = ("scan", "frame", "synth", "reference")


def _assertRealSourceRoot() -> None:
    assert ROOT.exists(), f"dartlab source root not found: {ROOT}"
    assert any(ROOT.rglob("*.py")), f"dartlab source root has no Python files: {ROOT}"


def test_l15_no_cross_import() -> None:
    """L1.5 4 형제 상호 import 0 건 강제."""
    _assertRealSourceRoot()
    violations: list[str] = []
    for peer in L15_PEERS:
        peerDir = ROOT / peer
        if not peerDir.exists():
            continue
        for pyFile in peerDir.rglob("*.py"):
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
                    for other in L15_PEERS:
                        if other == peer:
                            continue
                        if n == f"dartlab.{other}" or n.startswith(f"dartlab.{other}."):
                            rel = pyFile.relative_to(ROOT.parent.parent)
                            violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "L1.5 cross import 위반:\n" + "\n".join(violations)
