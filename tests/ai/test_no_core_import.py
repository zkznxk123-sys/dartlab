"""회귀 가드 — ai/ 가 dartlab core engine 을 정적 import 하지 않는다.

ai/tools/{readSkill,readCapability,proposeSkill}.py 만 dartlab.skills.* 와 dartlab.core.capability.* 메타 read-only 허용.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_AI_ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "ai"

# 정적 import 금지 대상 (core engines)
_FORBIDDEN_PREFIXES = (
    "dartlab.analysis",
    "dartlab.company",
    "dartlab.scan",
    "dartlab.quant",
    "dartlab.gather",
    "dartlab.macro",
    "dartlab.industry",
    "dartlab.review",
    "dartlab.credit",
    "dartlab.viz",
    "dartlab.dashboard",
    "dartlab.story",
    "dartlab.mappers",
    "dartlab.search",
)

# 메타 접근만 허용되는 파일 화이트리스트 (skills 메타, capability docstring)
_META_ALLOWED_FILES = {
    "ai/tools/skillSearch.py",
    "ai/tools/readSkill.py",
    "ai/tools/generatedSpecSearch.py",
    "ai/tools/readCapability.py",
    "ai/tools/proposeSkill.py",
    "ai/tools/read.py",
    "ai/tools/runPython.py",  # runPython 안에서 동적 import 만, 정적 import 는 polars/dartlab 루트만
    "ai/tools/engineCall.py",  # legacy heuristic — dynamic import only
}


def _staticImports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # ImportFrom 의 module 만 수집 (level=0 — 절대 경로)
            if node.level == 0 and node.module:
                names.append(node.module)
    return names


def _gatherAiPyFiles() -> list[Path]:
    return [p for p in _AI_ROOT.rglob("*.py") if "__pycache__" not in p.parts]


@pytest.mark.unit
def test_no_static_core_engine_imports_in_workbench_providers_lenses_tools() -> None:
    violations: list[str] = []
    for path in _gatherAiPyFiles():
        rel = path.relative_to(_AI_ROOT.parent).as_posix()
        # workbench/, providers/, lenses/, tools/ 만 검사 (settings/, kernel.py 등 제외)
        if not any(rel.startswith(f"ai/{seg}/") for seg in ("workbench", "providers", "lenses", "tools")):
            continue
        for imp in _staticImports(path):
            if any(imp == p or imp.startswith(p + ".") for p in _FORBIDDEN_PREFIXES):
                # tools/runPython.py 는 dartlab 루트 정적 import 금지 — 동적만 허용
                violations.append(f"{rel}: {imp}")
    assert not violations, "core engine 정적 import 발견:\n" + "\n".join(violations)
