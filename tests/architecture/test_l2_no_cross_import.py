"""L2 5 엔진 (analysis · credit · macro · quant · industry) cross import 0 강제.

룰 (CLAUDE.md "4 계층 단방향 import"):
- L2 = analysis · credit · macro · quant · industry (분석 엔진 5)
- 5 엔진끼리 cross import 금지 — 공통 계산은 L1.5 synth SSOT 또는
  inject 패턴으로 처리.
- 5 엔진 모두 core (L0) · gather/providers (L1) · scan/frame/synth/reference
  (L1.5) 만 import 가능.

baseline 0 — 본 가드는 신규 위반 발생을 100 % 차단한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"
L2_PEERS = ("analysis", "credit", "macro", "quant", "industry")


def _assertRealSourceRoot() -> None:
    assert ROOT.exists(), f"dartlab source root not found: {ROOT}"
    assert any(ROOT.rglob("*.py")), f"dartlab source root has no Python files: {ROOT}"


def test_l2_no_cross_import() -> None:
    """L2 5 엔진 상호 import 0 건 강제."""
    _assertRealSourceRoot()
    violations: list[str] = []
    for peer in L2_PEERS:
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
                    for other in L2_PEERS:
                        if other == peer:
                            continue
                        if n == f"dartlab.{other}" or n.startswith(f"dartlab.{other}."):
                            rel = pyFile.relative_to(ROOT.parent.parent)
                            violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "L2 cross import 위반:\n" + "\n".join(violations)
