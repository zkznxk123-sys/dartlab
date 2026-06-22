"""L2 5 엔진 (analysis · credit · macro · quant · industry) cross import 0 강제.

룰 (CLAUDE.md "4 계층 단방향 import"):
- L2 = analysis · credit · macro · quant · industry (분석 엔진 5)
- 5 엔진끼리 cross import 금지 — 공통 계산은 L1.5 synth SSOT 또는
  inject 패턴으로 처리.
- 5 엔진 모두 core (L0) · gather/providers (L1) · scan/frame/synth/reference
  (L1.5) 만 import 가능.

baseline 0 — 본 가드는 신규 위반 발생을 100 % 차단한다.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"
_BASELINE_DIR = Path(__file__).resolve().parents[2] / "tests" / "audit" / "_baselines"
L2_PEERS = ("analysis", "credit", "macro", "quant", "industry")


def _dynamicCrossViolations(peers: tuple[str, ...]) -> list[str]:
    """``importlib.import_module("dartlab.{peer}...")`` 동적 cross — 정적 가드 사각 보강.

    ``test_*_no_cross_import`` 은 ``ast.Import``/``ast.ImportFrom`` 만 봐서 importlib
    문자열 import 를 못 본다 (W-G1/W-G2). 본 함수가 그 사각을 메운다 (debt-honesty P1-7).
    키는 line 무관 ``relpath: src->dst import_module(mod)`` (line 이동 견고).
    """
    violations: list[str] = []
    for peer in peers:
        peerDir = ROOT / peer
        if not peerDir.exists():
            continue
        for pyFile in peerDir.rglob("*.py"):
            if "__pycache__" in pyFile.parts:
                continue
            try:
                tree = ast.parse(pyFile.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            rel = pyFile.relative_to(ROOT.parent.parent).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                func = node.func
                isImportModule = (isinstance(func, ast.Attribute) and func.attr == "import_module") or (
                    isinstance(func, ast.Name) and func.id == "import_module"
                )
                if not isImportModule:
                    continue
                arg0 = node.args[0]
                if not (isinstance(arg0, ast.Constant) and isinstance(arg0.value, str)):
                    continue
                mod = arg0.value
                for other in peers:
                    if other == peer:
                        continue
                    if mod == f"dartlab.{other}" or mod.startswith(f"dartlab.{other}."):
                        violations.append(f"{rel}: {peer}->{other} import_module({mod})")
    return sorted(set(violations))


def _loadDynamicBaseline(name: str) -> set[str]:
    path = _BASELINE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"dynamic-import baseline 부재: {path}")
    return set(json.loads(path.read_text(encoding="utf-8-sig")).get("violations", []))


def _assertRealSourceRoot() -> None:
    assert ROOT.exists(), f"dartlab source root not found: {ROOT}"
    assert any(ROOT.rglob("*.py")), f"dartlab source root has no Python files: {ROOT}"


def test_l2_no_cross_import() -> None:
    """L2 5 엔진 상호 import 0 건 강제."""
    _assertRealSourceRoot()
    violations: list[str] = []
    for peer in L2_PEERS:
        peerDir = ROOT / peer
        if not peerDir.exists():
            continue
        for pyFile in peerDir.rglob("*.py"):
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
                    for other in L2_PEERS:
                        if other == peer:
                            continue
                        if n == f"dartlab.{other}" or n.startswith(f"dartlab.{other}."):
                            rel = pyFile.relative_to(ROOT.parent.parent)
                            violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "L2 cross import 위반:\n" + "\n".join(violations)


def test_l2_no_new_dynamic_cross_import() -> None:
    """L2 importlib 동적 cross — 신규 0 (sanctioned §172/pattern-4 는 baseline 동결).

    baseline(``l2DynamicImport.json``) = analysis→macro(§172 허용방향) +
    credit→macro·credit→analysis(§181 pattern-4 cycle-break). 전부 sanctioned cycle-break라
    유지하되, *새* 동적 cross 는 차단 — 정적 가드가 못 보던 사각을 ratchet 으로 메운다.
    """
    _assertRealSourceRoot()
    current = set(_dynamicCrossViolations(L2_PEERS))
    baseline = _loadDynamicBaseline("l2DynamicImport.json")
    new = sorted(current - baseline)
    assert not new, (
        "L2 신규 importlib 동적 cross (정적 가드 사각):\n"
        + "\n".join(new)
        + "\n→ §172 허용방향/pattern-4 cycle-break 면 architecture.md 등재 후 baseline 갱신, 아니면 해소."
    )
