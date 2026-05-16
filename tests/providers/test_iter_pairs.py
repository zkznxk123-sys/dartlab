"""iter*/fetch* pair 검증 — P-트랙 룰 10 게이트.

collection 반환 메서드 (fetch*/list*/search*) 는 iterator 쌍 (iter*) 동행 의무.
사용자가 streaming (메모리 bound) vs limited 둘 다 고를 수 있게.

heuristic: 같은 도메인 module 안에 `fetchFilings` 가 있으면 `iterFilings` 도 있어야 함.

baseline (`_baselines/iterPairs.json`) 외 위반만 fail.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_PROVIDERS = _REPO / "src" / "dartlab" / "providers"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "iterPairs.json"

_PAIRING_PREFIXES = ("fetch", "list", "search")


def _providerScope() -> tuple[str, ...]:
    raw = os.environ.get("DARTLAB_PROVIDER_SCOPE", "dart,edgar")
    providers = tuple(p.strip() for p in raw.split(",") if p.strip())
    return providers or ("dart", "edgar")


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


def _publicFunctions(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
    return names


def _expectedIterName(fetchName: str) -> str | None:
    for prefix in _PAIRING_PREFIXES:
        if fetchName.startswith(prefix) and len(fetchName) > len(prefix):
            rest = fetchName[len(prefix) :]
            if rest and rest[0].isupper():
                return "iter" + rest
    return None


def _scanFile(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    names = _publicFunctions(tree)
    violations: list[str] = []
    rel = str(path.relative_to(_REPO).as_posix())
    for name in sorted(names):
        expectedIter = _expectedIterName(name)
        if expectedIter and expectedIter not in names:
            violations.append(f"{rel}::{name} (iter pair {expectedIter} 부재)")
    return violations


def _scanAll() -> list[str]:
    all_violations: list[str] = []
    for provider in _providerScope():
        providerRoot = _PROVIDERS / provider
        if not providerRoot.exists():
            continue
        for p in providerRoot.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            all_violations.extend(_scanFile(p))
    return sorted(all_violations)


def test_provider_iter_pairs() -> None:
    """fetch*/list*/search* 함수는 iter* 쌍 보유 필수.

    P-phase 끝까지 baseline 축소. P1.5 Protocol 신설 시 iter* 메서드 의무화.
    """
    violations = _scanAll()
    baseline = _loadBaseline()
    allowed = set(baseline.get("violations", []))
    new_violations = set(violations) - allowed
    assert not new_violations, f"iter pair 누락 회귀 {len(new_violations)} 건: {sorted(new_violations)[:10]}."
