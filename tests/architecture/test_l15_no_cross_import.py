"""L1.5 4 형제 (scan/frame/synth/reference) cross import 0 강제 — P-CORE 가드.

룰 (operation.architecture SSOT):
- L1.5 = scan · frame · synth · reference (가공 4 형제)
- 4 형제끼리 cross import 금지 (core 잡동사니화 재발 방지)
- 4 형제 모두 core (L0) 와 gather/providers (L1) 만 import 가능
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"
_BASELINE_DIR = Path(__file__).resolve().parents[2] / "tests" / "audit" / "_baselines"
L15_PEERS = ("scan", "frame", "synth", "reference")


def _dynamicCrossViolations(peers: tuple[str, ...]) -> list[str]:
    """``importlib.import_module("dartlab.{peer}...")`` 동적 cross — 정적 가드 사각 보강.

    정적 L1.5 가드는 ``ast.Import``/``ast.ImportFrom`` 만 봐서 importlib 문자열 import 를
    못 본다 (W-G2). 본 함수가 그 사각을 메운다 (debt-honesty P1-7). 키는 line 무관.
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


def test_l15_no_cross_import() -> None:
    """L1.5 4 형제 상호 import 0 건 강제."""
    _assertRealSourceRoot()
    violations: list[str] = []
    for peer in L15_PEERS:
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
                    for other in L15_PEERS:
                        if other == peer:
                            continue
                        if n == f"dartlab.{other}" or n.startswith(f"dartlab.{other}."):
                            rel = pyFile.relative_to(ROOT.parent.parent)
                            violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "L1.5 cross import 위반:\n" + "\n".join(violations)


def test_l15_no_new_dynamic_cross_import() -> None:
    """L1.5 importlib 동적 cross — 신규 0.

    baseline(``l15DynamicImport.json``) = synth→frame/scan (bottomUpBeta·impliedERP).
    이들은 **sanctioned 아님** — pattern-4(§181)는 L2 전용이고 L1.5 형제 cross 엔 sanction 이
    없다. 정적 가드가 importlib 로 우회당해 못 보던 *진짜 미허가 위반*이라, 추적 부채로 baseline
    동결(해소 = 호출자 inversion: L2 호출 측이 sector params·scan 데이터를 주입). 신규는 차단.
    """
    _assertRealSourceRoot()
    current = set(_dynamicCrossViolations(L15_PEERS))
    baseline = _loadDynamicBaseline("l15DynamicImport.json")
    new = sorted(current - baseline)
    assert not new, (
        "L1.5 신규 importlib 동적 cross (정적 가드 사각):\n"
        + "\n".join(new)
        + "\n→ L1.5 형제 cross 는 미허가. 호출자 inversion 으로 해소 (synth 는 데이터 주입받기)."
    )
