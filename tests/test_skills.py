from __future__ import annotations

from pathlib import Path

import pytest

import dartlab.skills as skills


pytestmark = pytest.mark.unit


def test_builtin_skills_are_searchable() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}

    assert "krxIndexStrengthReview" in ids
    assert "peerComparisonReview" in ids
    assert "damodaranValuationReview" in ids
    assert {
        "basic.company",
        "basic.gather",
        "basic.scan",
        "basic.analysis",
        "basic.quant",
        "basic.macro",
        "basic.story",
        "basic.credit",
        "basic.industry",
        "basic.viz",
    } <= ids
    assert "capability:Company.analysis" in ids


def test_skill_search_finds_index_strength() -> None:
    matches = skills.search("최근 주가지수 강세", includeUser=False)
    ids = {match.skill.id for match in matches}

    assert matches
    assert "krxIndexStrengthReview" in ids
    assert {"basic.gather", "basic.scan"} & ids


def test_generated_basic_skills_map_engine_capabilities() -> None:
    spec = skills.get("basic.gather", includeUser=False)

    assert spec.kind == "generated"
    assert spec.category == "basic"
    assert spec.scope == "builtin"
    assert "gather" in spec.capabilityRefs
    assert any(ref.startswith("gather.") for ref in spec.capabilityRefs)
    assert spec.toolRefs == []
    assert "parameters" not in " ".join(spec.procedure).lower()


def test_generated_basic_visual_skill_is_engine_map_not_tool_usage() -> None:
    spec = skills.get("basic.viz", includeUser=False)

    assert spec.kind == "generated"
    assert spec.category == "basic"
    assert "ChartResult" in spec.capabilityRefs
    assert spec.toolRefs == []


def test_skill_describe_does_not_duplicate_api_schema() -> None:
    spec = skills.get("peerComparisonReview", includeUser=False)

    assert spec.capabilityRefs
    assert "returns" not in spec.to_dict()
    assert "parameters" not in spec.to_dict()


def test_skill_runtime_compatibility_exposes_pyodide_support() -> None:
    spec = skills.get("krxIndexStrengthReview", includeUser=False)

    assert spec.runtimeCompatibility["pyodide"]["status"] == "limited"
    assert "HuggingFace" in " ".join(spec.runtimeCompatibility["pyodide"]["dataSources"])


def test_builtin_skills_load_without_pyyaml(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "yaml":
            raise ImportError("yaml blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    spec = skills.get("krxIndexStrengthReview", includeUser=False)

    assert spec.runtimeCompatibility["pyodide"]["status"] == "limited"


def test_user_skill_loads_as_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    skill_dir = root / ".dartlab" / "skills"
    skill_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (root / "src" / "dartlab").mkdir(parents=True)
    (skill_dir / "custom.yaml").write_text(
        """
id: customReview
title: 사용자 절차
purpose: 사용자가 정의한 절차
whenToUse:
  - custom
capabilityRefs:
  - Company.analysis
procedure:
  - Company.analysis capability를 확인하고 필요한 evidence를 만든다.
requiredEvidence:
  - target
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(root)

    spec = skills.get("customReview")

    assert spec.kind == "user"
    assert spec.scope == "user"
    assert spec.category == "user"
    assert spec.status == "unverified"


def test_skill_lint_rejects_unknown_capability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    skill_dir = root / ".dartlab" / "skills"
    skill_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (root / "src" / "dartlab").mkdir(parents=True)
    (skill_dir / "bad.yaml").write_text(
        """
id: badReview
title: 잘못된 절차
purpose: 존재하지 않는 capability 테스트
capabilityRefs:
  - missing.capability
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(root)

    with pytest.raises(ValueError, match="unknown capabilities"):
        skills.list()


def test_skill_evidence_check_reports_missing() -> None:
    result = skills.checkEvidence("krxIndexStrengthReview", [{"payload": {"latest": {"value": "20260102"}}}], includeUser=False)

    assert not result.ok
    assert "latestAsOf" in result.present
    assert "table" in result.missing
