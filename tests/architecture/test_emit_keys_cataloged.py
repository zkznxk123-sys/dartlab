"""모든 emit("key") 리터럴은 messagingCatalog 에 등록돼야 한다 — 수집 크래시 가드.

`emit(key, **kwargs)` → `formatMessage(key)` → `_SIMPLE[key].format(**kwargs)`.
catalog 에 없는 key 면 런타임 `KeyError` 로 *수집 파이프라인이 마지막 단계에서 크래시*
한다 (테스트는 emit 경로를 mock 해 잠복; 실수집에서만 터짐 — `edgar:sections_save`
선례). 본 가드는 gather/providers 의 모든 emit literal key 가 catalog 에 있음을 강제해
그 잠복 버그를 census 단계에서 차단한다.

스코프: ``gather`` + ``providers`` 의 module/function 본문 emit literal. 동적 key(f-string·
변수)는 본 정적 가드 밖 — 그건 호출부 책임.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[2] / "src" / "dartlab"
_SCOPES = ("gather", "providers")


def _emitLiteralKeys(root: Path) -> dict[str, str]:
    """root 하위 .py 의 emit("리터럴") key → 첫 발견 파일경로."""
    keys: dict[str, str] = {}
    for pyFile in root.rglob("*.py"):
        if "__pycache__" in pyFile.parts:
            continue
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            isEmit = (isinstance(func, ast.Name) and func.id == "emit") or (
                isinstance(func, ast.Attribute) and func.attr == "emit"
            )
            if not isEmit or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.setdefault(first.value, pyFile.relative_to(_SRC.parent.parent).as_posix())
    return keys


def test_all_emit_keys_cataloged() -> None:
    """gather/providers 의 모든 emit literal key 가 messagingCatalog 에 등록돼 있다."""
    from dartlab.core.messagingCatalog import SIMPLE, STRUCTURED

    cataloged = set(SIMPLE) | set(STRUCTURED)
    missing: list[str] = []
    for scope in _SCOPES:
        for key, where in _emitLiteralKeys(_SRC / scope).items():
            if key not in cataloged:
                missing.append(f"{where}: emit({key!r}) — catalog 미등록 (수집 시 KeyError)")
    assert not missing, "emit key catalog 누락 (런타임 크래시 유발):\n" + "\n".join(sorted(missing))
