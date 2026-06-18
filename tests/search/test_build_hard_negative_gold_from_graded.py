"""buildHardNegativeGoldFromGraded — non-circular hard-negative gold derivation tests.

사람-검수 graded refs 에서 cross-query-sibling forbidden 을 유도해 죽은 하드네거티브 게이트를 살리는 builder.
순환(self-scored) buildSearchHardNegativeGold 와 달리 랭커 EVENT_RULES 를 참조하지 않는다(비순환 불변식).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(".github/scripts/search/buildHardNegativeGoldFromGraded.py")


def _load():
    spec = importlib.util.spec_from_file_location("buildHardNegativeGoldFromGraded", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_exists_and_is_non_circular() -> None:
    import ast

    text = _SCRIPT.read_text(encoding="utf-8")
    assert "deriveHardNegativeRows" in text
    assert "forbiddenSourceRefs" in text
    assert "primaryRef" in text
    # 비순환 불변식: 랭커의 event-rule 추론을 *호출/임포트* 하지 않는다(docstring 언급은 허용 — AST 로 검사).
    tree = ast.parse(text)
    called = {
        node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "inferEventRole" not in called
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert not any("buildSearchHardNegativeGold" in m for m in imported)  # 순환 builder 미임포트


def test_derive_cross_query_sibling_forbidden() -> None:
    mod = _load()
    rows = [
        {
            "query": "유상증자 공시 원문",
            "targetKind": "filing",
            "expectedSourceRef": "ref:A1",
            "expectedSourceRefs": ["ref:A1", "ref:A2"],
        },
        {
            "query": "무상증자 결정 공시",
            "targetKind": "filing",
            "expectedSourceRef": "ref:B1",
            "expectedSourceRefs": ["ref:B1"],
        },
        {
            "query": "전환사채 발행 결정",
            "targetKind": "filing",
            "expectedSourceRef": "ref:C1",
            "expectedSourceRefs": ["ref:C1"],
        },
        {
            "query": "현금배당 결정",
            "targetKind": "filing",
            "expectedSourceRef": "ref:D1",
            "expectedSourceRefs": ["ref:D1"],
        },
        {
            "query": "주식배당 결정",
            "targetKind": "filing",
            "expectedSourceRef": "ref:E1",
            "expectedSourceRefs": ["ref:E1"],
        },
        {"query": "환율 뉴스", "targetKind": "news", "expectedSourceRef": "ref:N1", "expectedSourceRefs": ["ref:N1"]},
    ]
    derived, stats = mod.deriveHardNegativeRows(rows)
    byq = {r["query"]: r for r in derived}
    # capital-raise 패밀리: 유상/무상/전환사채 가 서로의 PRIMARY 를 forbidden 으로 갖는다.
    assert set(byq["유상증자 공시 원문"]["forbiddenSourceRefs"]) == {"ref:B1", "ref:C1"}
    assert set(byq["무상증자 결정 공시"]["forbiddenSourceRefs"]) == {"ref:A1", "ref:C1"}
    # dividend 패밀리: 현금/주식배당 상호.
    assert byq["현금배당 결정"]["forbiddenSourceRefs"] == ["ref:E1"]
    # 자기 expectedSourceRefs 는 forbidden 에서 제외(ref:A2 가 유상증자 forbidden 에 없음).
    assert "ref:A2" not in byq["유상증자 공시 원문"]["forbiddenSourceRefs"]
    # news 행은 derived 에 포함되지 않는다(filing 만).
    assert "환율 뉴스" not in byq
    assert stats["hardNegativeRows"] == 5  # 5 filing 행 모두 같은-패밀리 sibling 보유
    assert stats["degenerate"] is False
    assert "primaryRef" in byq["유상증자 공시 원문"]


def test_real_gold_revives_dead_gate(tmp_path) -> None:
    """실제 reviewed gold 에서 hardNegativeRows 0 -> >=40 (비퇴화) + 출력이 evaluateSearchGold 포맷."""
    goldPath = Path("tests/fixtures/search/queryLogGold.real.jsonl")
    if not goldPath.exists():
        pytest.skip("real gold fixture absent")
    out = tmp_path / "derived.jsonl"
    summary = tmp_path / "summary.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(_SCRIPT),
            "--gold",
            str(goldPath),
            "--out",
            str(out),
            "--summary-out",
            str(summary),
        ],
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    st = json.loads(summary.read_text(encoding="utf-8"))
    assert st["hardNegativeRows"] >= 40  # 죽은 게이트를 살릴 만큼(>=40)
    assert st["degenerate"] is False
    derived = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    nForbidden = sum(1 for r in derived if r.get("forbiddenSourceRefs"))
    assert nForbidden >= 40
    # 모든 forbidden ref 는 그 행의 expectedSourceRefs 와 겹치지 않는다(자기 정답을 금지하지 않음).
    for r in derived:
        own = set(r.get("expectedSourceRefs") or [])
        assert own.isdisjoint(set(r.get("forbiddenSourceRefs") or []))
