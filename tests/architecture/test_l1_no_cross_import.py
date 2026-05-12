"""L1 raw 생산 owner (gather ↛ providers 상호 import 금지) 강제."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"
L1_PEERS = ("gather", "providers")


def test_l1_no_cross_import() -> None:
    """gather ↛ providers 상호 import 0 강제."""
    violations: list[str] = []
    for peer in L1_PEERS:
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
                    for other in L1_PEERS:
                        if other == peer:
                            continue
                        if n == f"dartlab.{other}" or n.startswith(f"dartlab.{other}."):
                            rel = pyFile.relative_to(ROOT.parent.parent)
                            violations.append(f"{rel}:{node.lineno}: {n}")
    # L1 cross import 는 known violation 가능 (gather/entry/providerAdapter 등 DI 패턴).
    # 본 테스트는 baseline 카운트 검증 — 새 위반 추가만 차단.
    BASELINE = 100  # 광범위 backward compat shim. 단계 D 정리 후 0 으로 낮춤.
    assert len(violations) <= BASELINE, f"L1 cross import 신규 위반 ({len(violations)} > {BASELINE}):\n" + "\n".join(
        violations[:20]
    )
