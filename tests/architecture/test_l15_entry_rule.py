"""L1.5 진입 룰 — ≥ 2 분석엔진이 같은 모듈을 import 해야 함 (정적 grep 기반).

1 개 분석엔진만 쓰면 그 분석엔진이 owner. 본 테스트는 baseline 카운트만 추적.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"
L15_PEERS = ("frame", "synth", "reference")
L2_PEERS = ("analysis", "macro", "quant", "industry", "credit")


def test_l15_entry_rule_baseline() -> None:
    """L1.5 모듈이 ≥ 2 분석엔진에서 쓰이는지 정적 추적 (baseline only)."""
    usage: dict[str, set[str]] = {}
    for l2 in L2_PEERS:
        l2Dir = ROOT / l2
        if not l2Dir.exists():
            continue
        for pyFile in l2Dir.rglob("*.py"):
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
                    for peer in L15_PEERS:
                        if n.startswith(f"dartlab.{peer}.") and n.count(".") >= 2:
                            modPath = ".".join(n.split(".")[:3])
                            usage.setdefault(modPath, set()).add(l2)

    soloOwner = {mod: list(l2s)[0] for mod, l2s in usage.items() if len(l2s) == 1}
    BASELINE_SOLO = 50  # 1 엔진만 쓰는 모듈 baseline. 단계 D 정리 후 0 으로.
    assert len(soloOwner) <= BASELINE_SOLO, (
        f"L1.5 진입 룰 — 1 엔진만 쓰는 모듈 {len(soloOwner)} > {BASELINE_SOLO}:\n"
        + "\n".join(f"  {m} ← {owner}" for m, owner in list(soloOwner.items())[:20])
    )
