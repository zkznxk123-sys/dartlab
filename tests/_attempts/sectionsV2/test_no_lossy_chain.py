"""sections 빌더 path 에서 옛 lossy chain 호출 0 — AST 가드.

plan snazzy-wibbling-origami v4 회귀 차단:
    xmlChunkToMixed (P → plain text, USERMARK B → markdown) 같은 옛 lossy chain
    이 sections 빌더 path 에 다시 들어오면 6 cycle 회귀 (태그 보존 약속 위배).

검사 대상 파일:
    - sectionsBuilder.py — 빌더 entry.
    - zipToTopicRows.py — section → row.
    - sectionsStorage.py — read API (mmap path).

금지 import / 호출:
    - xmlChunkToMixed (옛 P/SPAN 변환)
    - _reportRowsToTopicRows (옛 mixed 양식 입력 가정)
    - _splitContentBlocks (markdown line split)
    - _expandStructuredRows (옛 dict expansion)
    - _accumulatePeriodRows (옛 period 누적)
    - _mergeFragmentTables (옛 fragment merge)

본 가드는 ast.parse 로 import 문 + 함수 호출 검사. 새 functions 명시 import 0 +
함수명 직접 참조 0.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SECTIONS_DIR = _REPO_ROOT / "src" / "dartlab" / "providers" / "dart" / "docs" / "sections"

_GUARDED_FILES = (
    _SECTIONS_DIR / "sectionsBuilder.py",
    _SECTIONS_DIR / "zipToTopicRows.py",
    _SECTIONS_DIR / "sectionsStorage.py",
)

_FORBIDDEN_NAMES = frozenset(
    {
        "xmlChunkToMixed",
        "_reportRowsToTopicRows",
        "_splitContentBlocks",
        "_expandStructuredRows",
        "_accumulatePeriodRows",
        "_mergeFragmentTables",
    }
)


def _findForbiddenReferences(path: Path) -> list[tuple[int, str]]:
    """파일 AST 검사 — import / 함수 호출 / 이름 참조에서 금지 식별자 검출."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _FORBIDDEN_NAMES:
                    violations.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.Name):
            if node.id in _FORBIDDEN_NAMES:
                violations.append((node.lineno, f"name {node.id}"))
        elif isinstance(node, ast.Attribute):
            if node.attr in _FORBIDDEN_NAMES:
                violations.append((node.lineno, f"attribute .{node.attr}"))
    return violations


@pytest.mark.architecture
@pytest.mark.parametrize("path", _GUARDED_FILES, ids=lambda p: p.name)
def testNoLossyChainImport(path: Path) -> None:
    """sections 빌더 / read path 에서 옛 lossy chain 호출 0."""
    if not path.exists():
        pytest.skip(f"파일 부재: {path}")
    violations = _findForbiddenReferences(path)
    if violations:
        msg = f"{path.name} 옛 lossy chain 참조:\n"
        for line, ref in violations:
            msg += f"  L{line}: {ref}\n"
        msg += "→ xmlChunkToMixed 등 옛 chain 은 P → plain text 변환 (사용자 비전 위배)."
        pytest.fail(msg)
