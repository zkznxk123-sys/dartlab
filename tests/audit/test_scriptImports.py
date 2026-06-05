"""``.github/scripts/`` 의 dartlab import 정합 가드 — 파이프라인 스크립트가 참조하는
모듈·심볼이 현재 패키지에 실제 존재하는지 ci-fast 에서 선제 검증.

배경(이슈 #58): ``.github/scripts/`` 는 패키지(``src/dartlab``) 밖이라 architecture import
테스트·lint·camelCase 가 스캔하지 않는다. 패키지가 모듈을 옮기면
(``providers.dart.openapi.client`` → ``core.dartClient``, ``core.cross.corporateAggregate`` →
``macro.corporate.corporateAggregate`` 등) 스크립트가 *조용히* 깨지고, 예약 sync 워크플로
실패(Data Sync·Update KindList)로만 뒤늦게 드러난다. 본 테스트가 모듈 해소 + ``from M import N``
의 심볼/서브모듈 해소까지 검증해 그 클래스를 선제 차단한다.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / ".github" / "scripts"


def _collectDartlabImports() -> list[tuple[str, str, str, tuple[str, ...]]]:
    """``.github/scripts`` 전수에서 dartlab 대상 import 수집 → (scriptRel, stmt, module, names)."""
    out: list[tuple[str, str, str, tuple[str, ...]]] = []
    for py in sorted(_SCRIPTS.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            continue
        rel = py.relative_to(_REPO).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if not mod.startswith("dartlab"):
                    continue
                names = tuple(a.name for a in node.names if a.name != "*")
                out.append((rel, f"from {mod} import {', '.join(names) or '*'}", mod, names))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("dartlab"):
                        out.append((rel, f"import {a.name}", a.name, ()))
    return out


def _resolves(module: str, names: tuple[str, ...]) -> str | None:
    """모듈 + (있으면) 심볼/서브모듈 해소 시도. 실패 사유 문자열 또는 None(성공)."""
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 — import 실패 사유를 그대로 보고
        return f"{type(exc).__name__}: {exc}"
    for name in names:
        if hasattr(mod, name):
            continue
        try:
            importlib.import_module(f"{module}.{name}")  # name 이 서브모듈일 수 있음
        except Exception:  # noqa: BLE001
            return f"심볼/서브모듈 '{name}' 부재"
    return None


def test_github_scripts_dartlab_imports_resolve() -> None:
    """.github/scripts 의 모든 dartlab import 가 현재 패키지에서 해소된다(모듈 + 심볼)."""
    imports = _collectDartlabImports()
    assert imports, ".github/scripts dartlab import 0건 — 수집 로직 회귀 의심"
    failures: list[str] = []
    seen: dict[tuple[str, tuple[str, ...]], str | None] = {}
    for rel, stmt, module, names in imports:
        key = (module, names)
        if key not in seen:
            seen[key] = _resolves(module, names)
        if seen[key]:
            failures.append(f"{rel}: `{stmt}` → {seen[key]}")
    assert not failures, (
        "파이프라인 스크립트의 dartlab import 깨짐(모듈/심볼 이동 후 미갱신 — 이슈 #58 클래스):\n  "
        + "\n  ".join(failures)
    )
