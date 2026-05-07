from __future__ import annotations

import json
from pathlib import Path

import pytest

import dartlab
import dartlab.skills as skills

pytestmark = pytest.mark.unit


def test_builtin_skills_are_engine_owned_execution_docs() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}

    assert {
        "start.dartlabSkillOs",
        "start.installUv",
        "start.useSkillsCatalog",
        "operation.opsAsSkills",
        "operation.apiContract",
        "operation.architecture",
        "operation.testing",
        "runtime.pyodide",
        "runtime.pyodideBrowser",
        "runtime.workbenchEvidenceFlow",
        "runtime.skillDevelopmentLoop",
        "engines.company",
        "engines.gather",
        "engines.scan",
        "engines.analysis",
        "engines.credit",
        "engines.quant",
        "engines.macro",
        "engines.story",
        "engines.viz",
        "engines.data.foundation",
        "engines.analysis.profitability",
        "engines.analysis.cashflow",
        "engines.analysis.peerComparison",
        "engines.credit.creditRisk",
        "engines.scan.undervaluedQuality",
        "engines.scan.crossSectionStockScreen",
        "engines.scan.krxIndexStrength",
        "engines.viz.tableBackedChart",
        "engines.company.researchStarter",
        "engines.company.usEdgarReview",
        "engines.macro.marketReview",
        "engines.quant.damodaranValuation",
        "engines.story.companyCausal",
    } <= ids

    assert not any(item.startswith("basic.") for item in ids)
    assert not any(item.startswith("capability:") for item in ids)
    assert not {"finance", "screens", "visuals", "basic", "capability"} & {
        item.category for item in skills.list(includeUser=False)
    }


def test_engine_skills_include_public_execution_contract() -> None:
    engine_specs = [item for item in skills.list(includeUser=False) if item.category == "engines"]

    assert engine_specs
    for spec in engine_specs:
        body = spec.source.get("body", "")
        if spec.kind == "recipe":
            # recipe 는 다축 묶음 절차 — execution 3 섹션 대신 ## 연계 절차 + linkedSkills 를 본다.
            assert "## 연계 절차" in body, f"recipe skill {spec.id} missing '## 연계 절차'"
            assert spec.linkedSkills or spec.recipeSteps, f"recipe skill {spec.id} missing linkedSkills/recipeSteps"
        else:
            assert "## 공개 호출 방식" in body
            assert "## 호출 동작" in body
            assert "## 대표 반환 형태" in body
            assert spec.capabilityRefs or spec.toolRefs


def _skill_body(skill_id: str) -> str:
    return str(skills.get(skill_id, includeUser=False).source.get("body", ""))


def test_analysis_skill_covers_analysis_guide_axes() -> None:
    body = _skill_body("engines.analysis")
    guide = dartlab.Company("005930").analysis()

    for axis in guide.get_column("axis").to_list():
        assert axis in body


def test_scan_skill_covers_scan_guide_axes() -> None:
    body = _skill_body("engines.scan")
    guide = dartlab.scan()

    for axis in guide.get_column("axis").to_list():
        assert axis in body


def test_quant_skill_covers_quant_guide_axes() -> None:
    body = _skill_body("engines.quant")
    guide = dartlab.quant()

    for axis in guide.get_column("axis").to_list():
        assert axis in body


def test_macro_skill_covers_macro_guide_axes() -> None:
    body = _skill_body("engines.macro")
    guide = dartlab.macro()

    for axis in guide.get_column("axis").to_list():
        assert axis in body


def test_gather_and_company_skills_cover_public_methods() -> None:
    gather_body = _skill_body("engines.gather")
    company_body = _skill_body("engines.company")

    for method in {
        "price",
        "consensus",
        "flow",
        "revenue_consensus",
        "history",
        "news",
        "dividends",
        "splits",
        "sector",
        "insiderTrading",
        "majorShareholders",
        "ownership",
        "industryPeers",
        "macro",
        "collect",
    }:
        assert method in gather_body

    for method in {
        "show",
        "select",
        "trace",
        "diff",
        "disclosure",
        "liveFilings",
        "readFiling",
        "analysis",
        "credit",
        "gather",
        "quant",
        "macro",
        "story",
        "industry",
        "governance",
        "workforce",
        "capital",
        "debt",
    }:
        assert method in company_body


def test_application_skills_cover_engine_guide_axes() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}
    analysis_slugs = {
        "수익구조": "revenueStructure",
        "자금조달": "financing",
        "자산구조": "assetStructure",
        "현금흐름": "cashflow",
        "수익성": "profitability",
        "성장성": "growth",
        "안정성": "stability",
        "효율성": "efficiency",
        "종합평가": "scorecard",
        "이익품질": "earningsQuality",
        "비용구조": "costStructure",
        "자본배분": "capitalAllocation",
        "투자효율": "investmentEfficiency",
        "재무정합성": "financialConsistency",
        "가치평가": "valuation",
        "지배구조": "governance",
        "공시변화": "disclosureChange",
        "비교분석": "peerComparison",
        "매출전망": "revenueForecast",
        "예측신호": "predictionSignal",
        "매크로민감도": "macroSensitivity",
        "밸류에이션밴드": "valuationBand",
    }

    for axis in dartlab.Company("005930").analysis().get_column("axis").to_list():
        assert f"engines.analysis.{analysis_slugs[axis]}" in ids

    for axis in dartlab.scan().get_column("axis").to_list():
        assert f"engines.scan.{axis}" in ids

    for axis in dartlab.quant().get_column("axis").to_list():
        assert f"engines.quant.{axis}" in ids

    for axis in dartlab.macro().get_column("axis").to_list():
        assert f"engines.macro.{axis}" in ids


def test_analysis_application_skills_have_correct_call_example() -> None:
    """각 analysis 응용 skill 본문에 자기 axis 의 정확한 c.analysis("group", "axis") 호출이 있어야 한다.

    SSOT 는 dartlab.analysis.financial._GROUPS / _AXIS_TO_GROUP. 응용 skill 본문이 자기
    axis 가 아닌 다른 axis 호출을 박아두면 사용자가 그대로 복사 실행 시 다른 분석이 나온다.
    """
    from dartlab.analysis.financial import _AXIS_TO_GROUP

    analysis_slugs = {
        "수익구조": "revenueStructure",
        "자금조달": "financing",
        "자산구조": "assetStructure",
        "현금흐름": "cashflow",
        "수익성": "profitability",
        "성장성": "growth",
        "안정성": "stability",
        "효율성": "efficiency",
        "종합평가": "scorecard",
        "이익품질": "earningsQuality",
        "비용구조": "costStructure",
        "자본배분": "capitalAllocation",
        "투자효율": "investmentEfficiency",
        "재무정합성": "financialConsistency",
        "가치평가": "valuation",
        "지배구조": "governance",
        "공시변화": "disclosureChange",
        "비교분석": "peerComparison",
        "매출전망": "revenueForecast",
        "예측신호": "predictionSignal",
        "매크로민감도": "macroSensitivity",
        "밸류에이션밴드": "valuationBand",
    }

    for axis_kr, slug in analysis_slugs.items():
        body = _skill_body(f"engines.analysis.{slug}")
        group = _AXIS_TO_GROUP[axis_kr]
        expected = f'c.analysis("{group}", "{axis_kr}")'
        assert expected in body, f"engines.analysis.{slug} body missing expected call example: {expected}"


def test_scan_application_skills_have_correct_call_example() -> None:
    """각 scan 응용 skill 본문에 dartlab.scan("axis") 호출이 있어야 한다.

    응용 skill 본문이 generic boilerplate 이거나 자기 axis 가 아닌 호출을 박아두면
    사용자가 그대로 복사 실행 시 잘못된 결과가 나온다.
    """
    for axis in dartlab.scan().get_column("axis").to_list():
        skill_id = f"engines.scan.{axis}"
        ids = {item.id for item in skills.list(includeUser=False)}
        if skill_id not in ids:
            continue  # axis 응용 skill 미생성 — test_application_skills_cover_engine_guide_axes 가 잡음
        body = _skill_body(skill_id)
        expected = f'dartlab.scan("{axis}")'
        assert expected in body, f"{skill_id} body missing expected call example: {expected}"


def test_gather_application_skills_cover_public_methods() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}

    for slug in {
        "price",
        "consensus",
        "flow",
        "revenueConsensus",
        "history",
        "news",
        "dividends",
        "splits",
        "sector",
        "insiderTrading",
        "majorShareholders",
        "ownership",
        "industryPeers",
        "macro",
        "collect",
    }:
        assert f"engines.gather.{slug}" in ids


def test_skill_search_routes_to_engine_owned_application_skills() -> None:
    assert skills.search("삼성전자 수익성 분석", includeUser=False)[0].skill.id == "engines.analysis.profitability"
    assert skills.search("스캔엔진으로 저평가 종목 찾기", includeUser=False)[0].skill.id == (
        "engines.scan.undervaluedQuality"
    )
    assert skills.search("최근 주가지수 강세", includeUser=False)[0].skill.id == "engines.scan.krxIndexStrength"
    assert skills.search("차트 만들어줘", includeUser=False)[0].skill.id == "engines.viz.tableBackedChart"
    assert skills.search("미국 주식 분석", includeUser=False)[0].skill.id == "engines.company.usEdgarReview"
    assert skills.search("금리 환율 매크로", includeUser=False)[0].skill.id == "engines.macro.marketReview"
    assert skills.search("기업 신용 위험", includeUser=False)[0].skill.id == "engines.credit.creditRisk"


def test_data_engine_foundation_references_manual_engine_skills() -> None:
    spec = skills.get("engines.data.foundation", includeUser=False)

    assert {"Company", "gather", "scan"} <= set(spec.capabilityRefs)
    assert {"engines.company", "engines.gather", "engines.scan"} <= set(spec.knowledgeRefs)
    assert {"target", "universe", "latestAsOf", "rank"} <= set(spec.requiredEvidence)


def test_skill_search_prioritizes_start_and_operation_rules() -> None:
    assert skills.search("dartlab skills 어떻게 써", includeUser=False)[0].skill.id == "start.useSkillsCatalog"
    assert skills.search("처음 온 외부 AI가 어디서 시작해야 해", includeUser=False)[0].skill.id == (
        "start.dartlabSkillOs"
    )
    assert skills.search("ops 문서를 스킬 체계로 통합", includeUser=False)[0].skill.id == "operation.opsAsSkills"
    assert skills.search("데이터가 있는지 확인", includeUser=False)[0].skill.id == "runtime.dataAvailabilityCheck"
    assert skills.search("검산하고 답변 마무리", includeUser=False)[0].skill.id == "runtime.workbenchEvidenceFlow"


def test_markdown_skill_source_is_loaded_without_pyyaml(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    original_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "yaml":
            raise ImportError("yaml blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    spec = skills.get("engines.scan.krxIndexStrength", includeUser=False)

    assert spec.category == "engines"
    assert spec.source["format"] == "markdown"
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
  - Company.analysis 공개 호출을 확인하고 필요한 evidence를 만든다.
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


def test_skill_lint_rejects_engine_skill_without_execution_contract() -> None:
    spec = skills.SkillSpec(
        id="engines.bad",
        title="실행 섹션 누락",
        kind="curated",
        category="engines",
        purpose="엔진 스킬 실행 섹션 검증",
        runtimeCompatibility={"pyodide": {"status": "unknown"}},
        source={"body": "## 절차\n\n- 부족한 문서"},
    )

    with pytest.raises(ValueError, match="missing execution sections"):
        skills.lintSkill(spec)


def test_skill_lint_allows_public_api_shape_in_skill() -> None:
    spec = skills.SkillSpec(
        id="engines.example",
        title="공개 API 포함",
        kind="curated",
        category="engines",
        purpose="스킬은 공개 호출과 대표 반환 형태를 담을 수 있다.",
        runtimeCompatibility={"pyodide": {"status": "unknown"}},
        source={
            "body": "## 공개 호출 방식\n\n- `c.analysis()`\n\n## 호출 동작\n\n- 실행\n\n## 대표 반환 형태\n\n- DataFrame"
        },
        docs={"returns": "DataFrame"},
    )

    skills.lintSkill(spec)


def test_skill_evidence_check_reports_missing() -> None:
    result = skills.checkEvidence(
        "engines.scan.krxIndexStrength", [{"payload": {"latest": {"value": "20260102"}}}], includeUser=False
    )

    assert not result.ok
    assert "latestAsOf" in result.present
    assert "table" in result.missing


def test_skill_compiler_builds_web_index(tmp_path: Path) -> None:
    result = skills.buildSkillArtifacts(webDir=tmp_path / "web")

    assert result["skillCount"] > 0
    assert (tmp_path / "web" / "index.json").exists()
    assert (tmp_path / "web" / "pyodide.json").exists()

    payload = json.loads((tmp_path / "web" / "index.json").read_text(encoding="utf-8"))
    public_items = payload["skills"]
    assert public_items
    assert all(item["category"] != "capability" for item in public_items)
    assert all(not item["id"].startswith("basic.") for item in public_items)
    assert all(not item["id"].startswith("capability:") for item in public_items)
    assert payload["meta"]["entrySkillId"] == "start.dartlabSkillOs"
    assert "Basic Engine Maps" not in json.dumps(payload, ensure_ascii=False)
    assert "Capability Reference" not in json.dumps(payload, ensure_ascii=False)


def test_builtin_skill_specs_are_package_sources() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    specs_root = repo_root / "src" / "dartlab" / "skills" / "specs"

    assert specs_root.exists()

    start = skills.get("start.dartlabSkillOs", includeUser=False)
    source_path = str(start.source.get("path", "")).replace("\\", "/")

    assert "/src/dartlab/skills/specs/start/dartlabSkillOs.md" in source_path
