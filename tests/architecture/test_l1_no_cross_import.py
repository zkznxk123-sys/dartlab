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
            # module-level imports 만 검사 — function body lazy 는 cycle 회피 패턴.
            # test_import_direction.py 와 동일 정책.
            for node in tree.body:
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
    # baseline 100 → 0 도달. gather/dart/viewer 의 viewerPageExtractor 의존을 함수 본문
    # lazy 로 처리 (providers/dart 가 raw owner, gather/dart 는 단건 fetch 시만 사용).
    BASELINE = 0
    assert len(violations) <= BASELINE, f"L1 cross import 위반 ({len(violations)} > {BASELINE}):\n" + "\n".join(
        violations[:20]
    )
