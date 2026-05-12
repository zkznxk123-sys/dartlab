"""4 계층 단방향 import 검사 (역방향 금지 강제).

룰: L0 ← L1 ← L1.5 ← L2 ← L3 ← L4. 역방향 import 0.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "dartlab"

LAYER_OF: dict[str, float] = {
    "core": 0.0,
    "gather": 1.0,
    "providers": 1.0,
    "scan": 1.5,
    "frame": 1.5,
    "synth": 1.5,
    "reference": 1.5,
    "analysis": 2.0,
    "macro": 2.0,
    "quant": 2.0,
    "industry": 2.0,
    "credit": 2.0,
    "story": 3.0,
    "ai": 4.0,
    "mcp": 4.0,
}
# sink 헬퍼 — CLAUDE.md "표현/전송 헬퍼: 모든 계층 결과를 다른 매체로". 호출 방향 룰 예외.
# 어디서도 import 가능 (L0~L3 → viz/cli/server/channel OK). 단 sink 끼리 cross 는 별 룰 미적용.
SINK_HELPERS = {"viz", "cli", "server", "channel"}


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
                    if target is None or target in SINK_HELPERS or target not in LAYER_OF:
                        continue
                    targetLayer = LAYER_OF[target]
                    if targetLayer > ownerLayer:
                        rel = pyFile.relative_to(ROOT.parent.parent)
                        violations.append(f"{rel}:{node.lineno}: L{ownerLayer} {ownerName} → L{targetLayer} {target}")
    # baseline 300 → 69 (-77%) — 단계 D1~D3 진행:
    #   D1: dataLoader/dataConfig/loaders → core 복귀 (-115)
    #   D2: show.py → providers, reference/providers → core/providers (-29)
    #   D3: SINK helpers (viz/cli/server/channel) 검사 제외 (-9)
    # 잔존 69 = mappers·viewer·htmlRenderer (17) + providers→{analysis,synth,industry,credit} 24 + 기타.
    # 다음 단계 D4 (providers↔reference mappers 정리) + D5 (providers→L2 의존 끊기) 후 0 목표.
    BASELINE = 69
    assert len(violations) <= BASELINE, f"역방향 import 신규 위반 ({len(violations)} > {BASELINE}):\n" + "\n".join(
        violations[:20]
    )
