"""흡수 완료 stage 가 ``runScript`` 서브프로세스 위임을 쓰지 않는지 AST 가드.

edgar/allFilings/macro 처럼 흡수 완료된 stage 는 gather/L2 공개함수를 in-library 직접
호출한다 — ``runScript`` 재등장 = 흡수 회귀(서브프로세스 위임 부활). 본 가드는 macro 흡수
완료를 봉인한다(``stages/macro.py`` 에 runScript import/call 0). dart/news 는 아직 흡수
전이라 allowlist — 각 도메인 흡수 시 allowlist 에서 제거(가드 자동 확장).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_STAGES_DIR = _ROOT / "src" / "dartlab" / "pipeline" / "stages"

# 아직 흡수 전이라 runScript 위임이 합법인 stage(흡수 시 제거 → 가드 자동 확장).
_RUNSCRIPT_ALLOWLIST: frozenset[str] = frozenset({"dart.py", "news.py", "krx.py"})

# 흡수 완료 — runScript import/call 0 을 강제하는 stage.
_ABSORBED_STAGES: tuple[str, ...] = ("macro.py",)


def _importsRunScript(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and "runScript" in {a.name for a in node.names}:
            return True
        if isinstance(node, ast.Import) and any(a.name.endswith("runScript") for a in node.names):
            return True
    return False


def _callsRunScript(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "runScript":
                return True
            if isinstance(fn, ast.Attribute) and fn.attr == "runScript":
                return True
    return False


@pytest.mark.parametrize("stageFile", _ABSORBED_STAGES)
def test_absorbed_stage_no_runscript(stageFile: str) -> None:
    """흡수 완료 stage 는 runScript 를 import 도 호출도 하지 않는다."""
    path = _STAGES_DIR / stageFile
    assert path.exists(), f"{stageFile} 부재"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not _importsRunScript(tree), (
        f"{stageFile}: runScript import 발견 — 흡수 회귀(서브프로세스 위임 부활). "
        "gather/L2 공개함수 in-library 직접 호출로 전환하시오."
    )
    assert not _callsRunScript(tree), f"{stageFile}: runScript() 호출 발견 — 흡수 회귀."


def test_allowlist_stages_acknowledge_runscript() -> None:
    """allowlist 는 아직 흡수 전 stage 만 — 흡수되면 제거(가드 자동 확장) 잊지 않게 메타 단언."""
    # 흡수 완료 + allowlist 동시 등록 = 모순(흡수했는데 allowlist 에 남김).
    overlap = set(_ABSORBED_STAGES) & set(_RUNSCRIPT_ALLOWLIST)
    assert not overlap, f"흡수 완료인데 allowlist 에 잔존: {overlap} — allowlist 에서 제거하시오."
