"""panel 단일 패키지 자급 격리 강제 (R1) — providers/dart/panel 자족.

PRD jazzy-napping-seal: panel 도메인(schema·mapper·bridge·build·read)을 ``providers/dart/panel``
한 패키지로 통합 (core/panel·gather/dart/panel 소멸). 단일 패키지라 옛 3-서브트리 cross 방향
규칙은 사라지고, 대신 **패키지 자급 격리**를 강제한다:

- ``providers/dart/panel`` 는 ``dartlab.gather`` 를 import 0 (수집은 openapi, build 가 bytes 만 받음).
- ``providers/dart/panel`` 는 다른 분석 엔진(analysis·credit·quant·macro·industry·story·scan)을
  import 0 (panel = 자급 read/build 도메인, 상위 소비층을 모름).
- ``providers/dart/panel`` 는 ``providers.dart.company`` 를 import 0 (finance/report 주입은 facade
  층 책임 — panel 자체는 company 를 모름, cycle 0).

config(경로)·openapi(streamZipBytes, build 입력) 의존만 허용. 전역 가드
(``test_l1_no_cross_import`` module-level gather↔providers, ``dartlabGuard`` census) 위에
본 가드가 panel 자급 격리를 AST 전수(lazy 포함)로 잠근다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

# 다른 분석/상위 엔진 (panel 이 import 하면 자급 격리 위반 — 상위 소비층).
_FORBIDDEN_ENGINES = (
    "dartlab.gather",
    "dartlab.analysis",
    "dartlab.credit",
    "dartlab.quant",
    "dartlab.macro",
    "dartlab.industry",
    "dartlab.story",
    "dartlab.scan",
    "dartlab.providers.dart.company",
)

# (서브트리 상대경로, 금지 import prefix 튜플, 사유)
_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("providers/dart/panel", _FORBIDDEN_ENGINES, "panel 자급 격리 — gather·상위 엔진·company import 0 (cycle 0)"),
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
