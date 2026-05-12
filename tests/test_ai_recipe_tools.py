"""ListEngineGaps · ProposeRecipe · ValidateRecipe unit (chat-native, graph node X).

각 도구가 stateless 인지, recipe-전용 frontmatter 강제가 작동하는지 검증.
ValidateRecipe 의 실제 dartlab 데이터 실행은 tests/test_recipe_validate.py (heavy + requires_data)
가 담당 — 본 unit 은 mock recipe spec + mock runPython.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from dartlab.ai.contracts import Ref
from dartlab.ai.tools.listEngineGaps import listEngineGaps
from dartlab.ai.tools.proposeRecipe import proposeRecipe
from dartlab.ai.tools.types import ToolResult
from dartlab.ai.tools.validateRecipe import validateRecipe

pytestmark = pytest.mark.unit


# ── ListEngineGaps ────────────────────────────────────────────────────────


def test_list_engine_gaps_returns_underbridged_pairs():
    result = listEngineGaps(minBridges=0, limit=50)
    assert result.ok
    gaps = result.data["gaps"]
    # 모든 페어 — bridgeCount 0 인 페어 ≥ 1 (alphabetic 정렬).
    assert isinstance(gaps, list)
    for entry in gaps:
        assert "pair" in entry
        assert len(entry["pair"]) == 2
        assert entry["bridgeCount"] <= 0


def test_list_engine_gaps_filters_by_engines_arg():
    result = listEngineGaps(engines=["credit", "macro"], minBridges=99)
    assert result.ok
    pairs = [tuple(g["pair"]) for g in result.data["gaps"]]
    assert ("credit", "macro") in pairs


def test_list_engine_gaps_excludes_facade_engines():
    result = listEngineGaps(engines=["credit", "company"], minBridges=99)
    # company 는 facade — gap 후보에서 제외돼야 함.
    assert not result.ok or all("company" not in g["pair"] for g in result.data.get("gaps", []))


# ── ProposeRecipe ─────────────────────────────────────────────────────────


def test_propose_recipe_requires_recipes_prefix():
    result = proposeRecipe(
        id="engines.foo.bar",
        title="잘못된 prefix",
        gap={"primary": ["a", "b"]},
        falsifier={"description": "x"},
    )
    assert not result.ok
    assert result.error == "invalid_id_prefix"


def test_propose_recipe_requires_gap_with_two_engines():
    result = proposeRecipe(
        id="recipes.testCase",
        title="gap primary 1 개",
        gap={"primary": ["analysis"]},
        falsifier={"description": "x"},
    )
    assert not result.ok
    assert result.error == "invalid_gap"


def test_propose_recipe_requires_falsifier_description():
    result = proposeRecipe(
        id="recipes.testCase",
        title="falsifier 빈 description",
        gap={"primary": ["a", "b"]},
        falsifier={"pythonCheck": "assert True"},
    )
    assert not result.ok
    assert result.error == "invalid_falsifier"


def test_propose_recipe_writes_drafted_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.proposeRecipe._RECIPE_DIR",
        tmp_path,
    )
    result = proposeRecipe(
        id="recipes.unitProbe",
        title="단위 테스트 probe",
        purpose="unit 검증",
        gap={"primary": ["analysis", "credit"]},
        falsifier={"description": "z drift > 2σ", "pythonCheck": "pass"},
        expectedNovelty=["consensus"],
        linkedSkills=["engines.analysis.governance"],
        requiredEvidence=["skillRef", "tableRef"],
    )
    assert result.ok, result.summary
    written = tmp_path / "unitProbe.md"
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert "status: drafted" in text
    assert "recipes.unitProbe" in text
    assert "## 공개 호출 방식" in text  # placeholder body 자동 작성.


def test_propose_recipe_rejects_duplicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "dartlab.ai.tools.proposeRecipe._RECIPE_DIR",
        tmp_path,
    )
    args = dict(
        id="recipes.dupCheck",
        title="중복 검사",
        gap={"primary": ["a", "b"]},
        falsifier={"description": "x"},
    )
    first = proposeRecipe(**args)
    assert first.ok
    second = proposeRecipe(**args)
    assert not second.ok
    assert second.error == "recipe_already_exists"


# ── ValidateRecipe ────────────────────────────────────────────────────────


def _stub_get_skill_body(skill_id: str):
    """getSkillBody mock — recipe 본문 + frontmatter 반환."""
    body = """## 공개 호출 방식

```python
target = "005930"
emit_result(table=[{"metric": "consensus", "value": 0.42}], values={"consensus": 0.42}, date="2025-12-31")
```

## 호출 동작

1. mock
"""
    return ToolResult(
        True,
        "ok",
        data={
            "id": skill_id,
            "body": body,
            "requiredEvidence": ["executionRef", "tableRef", "valueRef", "dateRef"],
            "expectedNovelty": ["consensus"],
            "falsifier": {"description": "test"},
            "testUniverse": {"market": "KR", "stockCodes": ["005930", "000660"]},
        },
    )


def _stub_run_python(code: str, *, runId=None):
    """runPython mock — 실 dartlab 호출 없이 ref 반환."""
    refs = [
        Ref(id=f"execution:{runId}:1", kind="executionRef", title="exec"),
        Ref(id=f"table:{runId}:python", kind="tableRef", title="table"),
        Ref(id=f"value:{runId}:consensus", kind="valueRef", title="consensus"),
        Ref(id=f"date:{runId}:2025-12-31", kind="dateRef", title="2025-12-31"),
    ]
    return ToolResult(
        True,
        "ok",
        refs=refs,
        data={
            "result": {
                "table": [{"metric": "consensus", "value": 0.42}],
                "values": {"consensus": 0.42},
                "date": "2025-12-31",
            },
            "stdout": "",
            "stderr": "",
            "durationMs": 50,
        },
    )


def test_validate_recipe_runs_on_test_universe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path))
    with (
        patch("dartlab.ai.tools.validateRecipe.getSkillBody", _stub_get_skill_body),
        patch("dartlab.ai.tools.validateRecipe.runPython", _stub_run_python),
    ):
        result = validateRecipe("recipes.unitProbe", capture=True)

    assert result.ok, result.summary
    assert result.data["targetCount"] == 2
    assert result.data["scorecard"]["runCount"] == 2
    assert result.data["scorecard"]["executionPassRate"] == 1.0
    # 모든 ref kind 등장 → completeness = 1.0
    assert result.data["scorecard"]["evidenceCompleteness"] == 1.0


def test_validate_recipe_caps_targets_at_five(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path))
    with (
        patch("dartlab.ai.tools.validateRecipe.getSkillBody", _stub_get_skill_body),
        patch("dartlab.ai.tools.validateRecipe.runPython", _stub_run_python),
    ):
        result = validateRecipe(
            "recipes.unitProbe",
            targets=["005930", "000660", "035420", "051910", "055550", "066570", "012450"],
            capture=False,
        )
    assert result.data["targetCount"] == 5  # _HARD_CAP_TARGETS


def test_validate_recipe_returns_missing_evidence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path))

    def _missing_kinds(code: str, *, runId=None):
        return ToolResult(
            True,
            "ok",
            refs=[Ref(id=f"execution:{runId}:1", kind="executionRef", title="exec")],
            data={"result": {}, "stdout": "", "stderr": "", "durationMs": 10},
        )

    with (
        patch("dartlab.ai.tools.validateRecipe.getSkillBody", _stub_get_skill_body),
        patch("dartlab.ai.tools.validateRecipe.runPython", _missing_kinds),
    ):
        result = validateRecipe("recipes.unitProbe", targets=["005930"], capture=False)

    assert result.ok
    assert "tableRef" in result.data["missingEvidence"]
    assert result.data["scorecard"]["executionPassRate"] == 0.0


def test_validate_recipe_rejects_missing_skill(monkeypatch: pytest.MonkeyPatch):
    def _not_found(skill_id: str):
        return ToolResult(False, "not found", error="not_found")

    with patch("dartlab.ai.tools.validateRecipe.getSkillBody", _not_found):
        result = validateRecipe("recipes.nonexistent")
    assert not result.ok
    assert result.error == "skill_not_found"


def test_validate_recipe_rejects_recipe_without_python_block(monkeypatch: pytest.MonkeyPatch):
    def _no_block(skill_id: str):
        body = "## 공개 호출 방식\n\n(missing python block)\n"
        return ToolResult(True, "ok", data={"id": skill_id, "body": body})

    with patch("dartlab.ai.tools.validateRecipe.getSkillBody", _no_block):
        result = validateRecipe("recipes.broken")
    assert not result.ok
    assert result.error == "missing_python_block"


# ── registry 통합 ─────────────────────────────────────────────────────────


def test_three_recipe_tools_registered():
    from dartlab.ai.tools.registry import _SPECS, _TOOLS

    for name in ("ListEngineGaps", "ProposeRecipe", "ValidateRecipe"):
        assert name in _SPECS, f"{name} missing from _SPECS"
        assert name in _TOOLS, f"{name} missing from _TOOLS"
