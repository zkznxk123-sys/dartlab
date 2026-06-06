"""core ↛ providers 강제 — 정적 import + importlib 리터럴 dispatch 0.

`test_core_l0_only` 가 core 의 상위계층 module-level import 를 막지만, core/dataLoader
가 과거 문자열 리터럴로 providers 를 런타임 더듬던 스멜(AST module-level 검사 우회)을
별도로 lock 한다. provider별 loader 등록은 LoaderProvider DIP 경계에서만 허용한다.

허용: `core/loaders.py`·`gatherProvider.py` 등 DIP discovery 의 ``import_module(modPath)``
— modPath 가 ``_KNOWN_*_MODULES`` 변수(문자열 리터럴 아님)라 본 검사에 안 걸린다.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "core"


def _isProvidersLiteral(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("dartlab.providers")


def test_core_no_static_providers_import() -> None:
    """core 의 어떤 파일도 ``dartlab.providers`` 를 정적 import 하지 않는다 (module/function 본문 모두)."""
    assert CORE.exists(), f"core source root not found: {CORE}"
    violations: list[str] = []
    for pyFile in CORE.rglob("*.py"):
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = pyFile.relative_to(CORE.parent.parent.parent)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dartlab.providers"):
                violations.append(f"{rel}:{node.lineno}: from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("dartlab.providers"):
                        violations.append(f"{rel}:{node.lineno}: import {alias.name}")
    assert not violations, "core → providers 정적 import 위반:\n" + "\n".join(violations)


def test_core_no_providers_importlib_literal() -> None:
    """core 에 ``import_module("dartlab.providers...")`` 리터럴 dispatch 0 (DIP discovery 변수는 허용)."""
    assert CORE.exists(), f"core source root not found: {CORE}"
    violations: list[str] = []
    for pyFile in CORE.rglob("*.py"):
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = pyFile.relative_to(CORE.parent.parent.parent)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            isImportModule = (isinstance(func, ast.Attribute) and func.attr == "import_module") or (
                isinstance(func, ast.Name) and func.id == "import_module"
            )
            if isImportModule and node.args and _isProvidersLiteral(node.args[0]):
                violations.append(f"{rel}:{node.lineno}: import_module({node.args[0].value!r})")
    assert not violations, "core → providers importlib 리터럴 dispatch 위반:\n" + "\n".join(violations)
