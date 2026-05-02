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
    assert "start.installUv" in ids
    assert "runtime.pyodideBrowser" in ids
    assert "screens.findUndervaluedQualityStocks" in ids
    assert "visuals.tableBackedChart" in ids
    assert "start.useSkillsCatalog" in ids
    assert "runtime.workbenchEvidenceFlow" in ids
    assert "runtime.dataAvailabilityCheck" in ids
    assert "runtime.skillDevelopmentLoop" in ids
    assert "companyResearchStarter" in ids
    assert {
        "engines.dataEngineFoundation",
    } <= ids
    assert "macroMarketReview" in ids
    assert "usEdgarCompanyReview" in ids
    assert "creditRiskReview" in ids
    assert "profitabilityReview" in ids
    assert "cashflowReview" in ids
    assert "dividendCapitalReturnReview" in ids
    assert "governanceAuditReview" in ids
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


def test_skill_search_finds_scan_screen_use_case() -> None:
    matches = skills.search("스캔엔진으로 저평가 종목 찾기", includeUser=False)
    ids = [match.skill.id for match in matches]

    assert ids[0] == "screens.findUndervaluedQualityStocks"
    assert {"basic.scan", "engines.dataEngineFoundation"} & set(ids)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("데이터 엔진 기본기 Company gather scan", "engines.dataEngineFoundation"),
    ],
)
def test_skill_search_prioritizes_curated_engine_composition_playbooks(query: str, expected: str) -> None:
    matches = skills.search(query, includeUser=False)

    assert matches[0].skill.id == expected


def test_single_engine_usage_is_generated_not_curated() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}

    assert "engines.companyRouterUsage" not in ids
    assert "engines.gatherUsage" not in ids
    assert "engines.scanUsage" not in ids
    assert {"basic.company", "basic.gather", "basic.scan"} <= ids


def test_curated_engine_skills_are_composition_not_single_engine_usage() -> None:
    specs = [item for item in skills.list(includeUser=False) if item.id.startswith("engines.")]

    assert {item.id for item in specs} == {"engines.dataEngineFoundation"}
    assert all(item.runtimeCompatibility.get("pyodide") for item in specs)
    assert all(item.capabilityRefs for item in specs)
    assert all("parameters" not in item.to_dict() for item in specs)
    assert all("returns" not in item.to_dict() for item in specs)


def test_data_engine_foundation_references_basic_data_skills() -> None:
    spec = skills.get("engines.dataEngineFoundation", includeUser=False)

    assert {"Company", "gather", "scan"} <= set(spec.capabilityRefs)
    assert {"basic.company", "basic.gather", "basic.scan"} <= set(spec.knowledgeRefs)
    assert {"target", "universe", "latestAsOf", "rank"} <= set(spec.requiredEvidence)


def test_data_engine_docstrings_feed_generated_capabilities() -> None:
    from dartlab.core._generated import CAPABILITIES

    for ref in ("Company", "gather", "scan"):
        guide = str(CAPABILITIES[ref].get("guide") or "")
        assert "데이터 기본기" in guide

    assert "Handoff" in str(CAPABILITIES["Company"].get("guide") or "")
    assert 'scan("fields")' in str(CAPABILITIES["scan"].get("guide") or "")


def test_skill_search_prioritizes_skills_catalog_start() -> None:
    matches = skills.search("dartlab skills 어떻게 써", includeUser=False)

    assert matches[0].skill.id == "start.useSkillsCatalog"


def test_skill_search_prioritizes_capability_help_start() -> None:
    matches = skills.search("dartlab 뭐 할 수 있어", includeUser=False)

    assert matches[0].skill.id == "start.useSkillsCatalog"


def test_skill_search_prioritizes_skill_development_loop() -> None:
    matches = skills.search("엔진에 없는 분석을 조합해서 스킬 개발", includeUser=False)

    assert matches[0].skill.id == "runtime.skillDevelopmentLoop"


def test_skill_search_prioritizes_company_research_start() -> None:
    matches = skills.search("종목 분석 어떻게 시작", includeUser=False)

    assert matches[0].skill.id == "companyResearchStarter"


def test_skill_search_prioritizes_data_availability_check() -> None:
    matches = skills.search("데이터가 있는지 확인", includeUser=False)

    assert matches[0].skill.id == "runtime.dataAvailabilityCheck"


def test_skill_search_prioritizes_workbench_evidence_flow() -> None:
    matches = skills.search("검산하고 답변 마무리", includeUser=False)

    assert matches[0].skill.id == "runtime.workbenchEvidenceFlow"


def test_skill_search_prioritizes_visual_chart_intent() -> None:
    matches = skills.search("차트 만들어줘", includeUser=False)

    assert matches[0].skill.id == "visuals.tableBackedChart"


def test_skill_search_prioritizes_us_edgar_intent() -> None:
    matches = skills.search("미국 주식 분석", includeUser=False)

    assert matches[0].skill.id == "usEdgarCompanyReview"


def test_skill_search_prioritizes_ticker_intent() -> None:
    matches = skills.search("AAPL 분석", includeUser=False)

    assert matches[0].skill.id == "usEdgarCompanyReview"


def test_skill_search_prioritizes_macro_intent() -> None:
    matches = skills.search("금리 환율 매크로", includeUser=False)

    assert matches[0].skill.id == "macroMarketReview"


def test_skill_search_prioritizes_credit_intent() -> None:
    matches = skills.search("기업 신용 위험", includeUser=False)

    assert matches[0].skill.id == "creditRiskReview"


def test_skill_search_prioritizes_profitability_intent() -> None:
    matches = skills.search("삼성전자 수익성 분석", includeUser=False)

    assert matches[0].skill.id in {"profitabilityReview", "companyCausalReview"}


def test_generated_basic_skills_map_engine_capabilities() -> None:
    spec = skills.get("basic.gather", includeUser=False)

    assert spec.kind == "generated"
    assert spec.category == "basic"
    assert spec.scope == "builtin"
    assert "gather" in spec.capabilityRefs
    assert any(ref.startswith("gather.") for ref in spec.capabilityRefs)
    assert spec.toolRefs == []
    assert "parameters" not in " ".join(spec.procedure).lower()
    assert spec.source["aiRole"].startswith("AI는")
    assert any(item.startswith("AI 역할:") for item in spec.procedure)


def test_all_generated_basic_skills_expose_ai_role() -> None:
    specs = [item for item in skills.list(includeUser=False) if item.id.startswith("basic.")]

    assert specs
    assert all(item.source.get("aiRole") for item in specs)
    assert all("capabilityRefs와 requiredEvidence" not in item.source.get("aiRole", "") for item in specs)
    assert all(any(step.startswith("AI 역할:") for step in item.procedure) for item in specs)


def test_engine_capability_guides_expose_ai_role() -> None:
    from dartlab.core._generated import CAPABILITIES

    engine_refs = {
        "Company",
        "gather",
        "scan",
        "analysis",
        "Company.analysis",
        "quant",
        "macro",
        "credit",
        "industry",
        "Story",
        "ChartResult",
    }

    missing = [ref for ref in sorted(engine_refs) if "AI 역할:" not in str(CAPABILITIES[ref].get("guide") or "")]
    assert missing == []


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


def test_markdown_skill_source_is_loaded() -> None:
    spec = skills.get("runtime.pyodideBrowser", includeUser=False)

    assert spec.category == "runtime"
    assert spec.source["format"] == "markdown"
    assert spec.runtimeCompatibility["pyodide"]["status"] == "supported"


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
    (skill_dir / "custom.md").write_text(
        """
---
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
runtimeCompatibility:
  pyodide:
    status: unknown
---

## 절차

- 사용자 절차를 실행한다.
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
    (skill_dir / "bad.md").write_text(
        """
---
id: badReview
title: 잘못된 절차
purpose: 존재하지 않는 capability 테스트
capabilityRefs:
  - missing.capability
runtimeCompatibility:
  pyodide:
    status: unknown
---

## 절차

- 잘못된 capability를 참조한다.
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(root)

    with pytest.raises(ValueError, match="unknown capabilities"):
        skills.list()


def test_skill_lint_rejects_curated_without_pyodide_runtime() -> None:
    spec = skills.SkillSpec(
        id="missingPyodide",
        title="Pyodide 누락",
        kind="curated",
        purpose="runtimeCompatibility.pyodide 누락 검증",
    )

    with pytest.raises(ValueError, match="runtimeCompatibility.pyodide"):
        skills.lintSkill(spec)


def test_skill_lint_rejects_api_schema_duplicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    skill_dir = root / ".dartlab" / "skills"
    skill_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (root / "src" / "dartlab").mkdir(parents=True)
    (skill_dir / "schema.md").write_text(
        """
---
id: schemaDuplicate
title: API schema 중복
purpose: schema 중복 검증
parameters:
  stockCode: str
runtimeCompatibility:
  pyodide:
    status: unknown
---

## 절차

- schema를 중복한다.
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(root)

    with pytest.raises(ValueError, match="duplicates API schema"):
        skills.list()


def test_skill_lint_rejects_final_answer_template() -> None:
    spec = skills.SkillSpec(
        id="templateSkill",
        title="템플릿 금지",
        kind="curated",
        purpose="final answer template 금지 검증",
        procedure=["최종 답변: {{answer}}"],
        runtimeCompatibility={"pyodide": {"status": "unknown"}},
    )

    with pytest.raises(ValueError, match="final-answer template"):
        skills.lintSkill(spec)


def test_skill_lint_rejects_official_without_audit_and_user_confirmation() -> None:
    spec = skills.SkillSpec(
        id="prematureOfficial",
        title="성급한 공식화",
        kind="curated",
        status="official",
        purpose="official 승격 근거 검증",
        runtimeCompatibility={"pyodide": {"status": "unknown"}},
    )

    with pytest.raises(ValueError, match="official requires"):
        skills.lintSkill(spec)


def test_skill_evidence_check_reports_missing() -> None:
    result = skills.checkEvidence(
        "krxIndexStrengthReview", [{"payload": {"latest": {"value": "20260102"}}}], includeUser=False
    )

    assert not result.ok
    assert "latestAsOf" in result.present
    assert "table" in result.missing


def test_skill_compiler_builds_web_index_without_docs_markdown(tmp_path: Path) -> None:
    result = skills.buildSkillArtifacts(webDir=tmp_path / "web")

    assert result["skillCount"] > 0
    assert "docsDir" not in result
    assert not (tmp_path / "docs").exists()
    assert (tmp_path / "web" / "index.json").exists()
    assert (tmp_path / "web" / "pyodide.json").exists()
