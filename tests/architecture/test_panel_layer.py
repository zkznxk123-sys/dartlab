"""panel 4계층 단방향 import 강제 (R1) — core ← gather(write) · providers(read).

plan snazzy-wibbling-origami R1. panel 3 서브트리의 import 방향을 고정:

- ``core/panel`` (L0): dartlab.gather·dartlab.providers 0 (하위 계약은 상위를 모름).
- ``gather/dart/panel`` (L1 write): dartlab.providers 0 (gather ↛ providers, core_boundary).
- ``providers/dart/panel`` (L1 read): dartlab.gather 0 (read 는 gather 를 모름 — 경로는 config).

전역 가드(``test_l1_no_cross_import`` module-level gather↔providers, ``dartlabGuard``
census)를 panel 특이 케이스로 보강: 본 가드는 **module+function body 전수**(lazy 포함)라
core/panel 의 하위 순수성까지 잠근다(broad ``test_import_direction_layers`` 가 core→gather
prefix 를 known-violation 으로 허용해 새는 구멍을 메움). cross 의 index 접근은 gather import
가 아니라 ``dartlab.config`` 경로 직접 read 여야 한다(providers ↛ gather).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

# (서브트리 상대경로, 금지 import prefix 튜플, 사유)
_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("core/panel", ("dartlab.gather", "dartlab.providers"), "L0 계약 — 상위 계층 import 0"),
    ("gather/dart/panel", ("dartlab.providers",), "gather ↛ providers (core_boundary)"),
    ("providers/dart/panel", ("dartlab.gather",), "providers ↛ gather (경로는 config 직접 read)"),
)


def _dartlabImports(pyFile: Path) -> list[tuple[int, str]]:
    """파일의 dartlab.* import 대상을 (lineno, module) 로 — module+function body 전수."""
    try:
        tree = ast.parse(pyFile.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((node.lineno, a.name) for a in node.names if a.name.startswith("dartlab"))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and node.module.startswith("dartlab"):
                out.append((node.lineno, node.module))
    return out


def _isForbidden(module: str, forbidden: tuple[str, ...]) -> bool:
    return any(module == f or module.startswith(f + ".") for f in forbidden)


def test_panel_layer_import_direction() -> None:
    """panel 서브트리별 역방향·형제 cross import 0 강제 (R1)."""
    violations: list[str] = []
    for subtree, forbidden, reason in _RULES:
        base = ROOT / subtree
        if not base.exists():
            continue
        for pyFile in base.rglob("*.py"):
            if "__pycache__" in pyFile.parts:
                continue
            for lineno, module in _dartlabImports(pyFile):
                if _isForbidden(module, forbidden):
                    rel = pyFile.relative_to(ROOT.parent.parent).as_posix()
                    violations.append(f"{rel}:{lineno}: import '{module}' 금지 — {subtree}: {reason}")
    assert not violations, "panel 계층 import 방향(R1) 위반:\n" + "\n".join(violations)
