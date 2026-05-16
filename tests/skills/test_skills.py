from __future__ import annotations

import json
from pathlib import Path

import pytest

import dartlab
import dartlab.skills as skills

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_skills_cache():
    """0.10 listSkills 캐시 — user skill 추가/제거 fixture 가 stale 결과 받지 않도록 매 테스트 clear."""
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    _registry._KNOWN_CAPS_CACHE = None
    yield
    _registry._LIST_SKILLS_CACHE.clear()
    _registry._KNOWN_CAPS_CACHE = None


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
        "operation.skillDevelopmentLoop",
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


def test_quant_application_skills_have_correct_call_example() -> None:
    """각 quant 응용 skill 본문에 dartlab.quant("axis", ...) 호출 예시가 있어야 한다.

    SSOT 는 dartlab.quant._AXIS_REGISTRY. multi-stock / cross-section / single-stock
    모두 prefix dartlab.quant("axis" 로 시작하므로 prefix 매칭으로 검증.
    """
    for axis in dartlab.quant().get_column("axis").to_list():
        skill_id = f"engines.quant.{axis}"
        ids = {item.id for item in skills.list(includeUser=False)}
        if skill_id not in ids:
            continue
        body = _skill_body(skill_id)
        prefix = f'dartlab.quant("{axis}"'
        assert prefix in body, f"{skill_id} body missing expected call example prefix: {prefix}"


def test_macro_application_skills_have_correct_call_example() -> None:
    """각 macro 응용 skill 본문에 dartlab.macro("axis", ...) 호출 예시가 있어야 한다."""
    for axis in dartlab.macro().get_column("axis").to_list():
        skill_id = f"engines.macro.{axis}"
        ids = {item.id for item in skills.list(includeUser=False)}
        if skill_id not in ids:
            continue
        body = _skill_body(skill_id)
        prefix = f'dartlab.macro("{axis}"'
        assert prefix in body, f"{skill_id} body missing expected call example prefix: {prefix}"


def test_gather_application_skills_have_correct_call_example() -> None:
    """각 gather 응용 skill 본문에 dartlab.gather("axis", ...) 호출 예시가 있어야 한다.

    revenueConsensus 는 메서드 이름이 revenue_consensus 지만 skill axis slug 는
    revenueConsensus — base SKILL 의 가이드 표 매핑. axis slug 를 그대로 사용한다.
    """
    skill_dir = "src/dartlab/skills/specs/engines/gather"
    ids = {item.id for item in skills.list(includeUser=False)}
    for axis in [
        "collect",
        "consensus",
        "dividends",
        "flow",
        "history",
        "industryPeers",
        "insiderTrading",
        "macro",
        "majorShareholders",
        "news",
        "ownership",
        "price",
        "revenueConsensus",
        "sector",
        "splits",
    ]:
        skill_id = f"engines.gather.{axis}"
        if skill_id not in ids:
            continue
        body = _skill_body(skill_id)
        prefix = f'dartlab.gather("{axis}"'
        assert prefix in body, f"{skill_id} body missing expected call example prefix: {prefix}"


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
        # prefix 매칭 — target 필수 axis (account · ratio) 는 dartlab.scan("axis", "...") 형식 허용.
        prefix = f'dartlab.scan("{axis}"'
        assert prefix in body, f"{skill_id} body missing expected call example prefix: {prefix}"


def test_gather_application_skills_cover_public_methods() -> None:
    ids = {item.id for item in skills.list(includeUser=False)}

    for slug in {
        "price",
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


def testRecipeVisualGuidanceIsOptionalButExecutable() -> None:
    """recipe 시각화는 의무 차트가 아니라 실행 가능한 선택 계약이다."""
    recipeSpecs = [item for item in skills.list(includeUser=False) if item.category == "recipes"]
    knownIds = {item.id for item in skills.list(includeUser=False)}

    assert recipeSpecs
    visualRecipeCount = 0
    for spec in recipeSpecs:
        if not spec.visualGuidance:
            continue
        visualRecipeCount += 1
        assert spec.visualRefs, f"{spec.id} has visualGuidance without visualRefs"
        for visualRef in spec.visualRefs:
            assert visualRef in knownIds, f"{spec.id} references unknown visual skill {visualRef}"
            assert visualRef.startswith("engines.viz."), f"{spec.id} visualRef must be engines.viz.*"
        joined = " ".join(spec.visualGuidance).lower()
        assert any(
            token in joined
            for token in (
                "chart",
                "table",
                "diagram",
                "mermaid",
                "heatmap",
                "matrix",
                "price-chart",
                "시각화",
                "차트",
                "표",
                "다이어그램",
            )
        ), f"{spec.id} visualGuidance does not name a concrete visual surface"
    assert visualRecipeCount < len(recipeSpecs)
    assert skills.get("recipes.etc.usageAndApi", includeUser=False).visualGuidance == []


def testReadSkillExposesRecipeVisualGuidance() -> None:
    from dartlab.ai.tools.readSkill import readSkill

    result = readSkill("기업 깊이 분석", limit=5, includeUser=False)

    assert result.ok
    rows = result.data["skills"]
    recipeRows = [row for row in rows if str(row["id"]).startswith("recipes.")]
    assert recipeRows
    assert any(row.get("visualGuidance") for row in recipeRows)


def testSkillArtifactsKeepRecipeCategorySeparateFromEngines() -> None:
    """랜딩/외부 산출물에서 recipes.* 가 engines sidebar 로 섞이지 않아야 한다."""
    artifactDir = Path("src/dartlab/skills")
    for name in ("index.json", "agent.json", "web.json", "mcp.json", "pyodide.json"):
        rows = json.loads((artifactDir / name).read_text(encoding="utf-8")).get("skills", [])
        bad = [
            row["id"]
            for row in rows
            if isinstance(row, dict)
            and str(row.get("id", "")).startswith("recipes.")
            and row.get("category") != "recipes"
        ]
        assert not bad, f"{name} has recipes categorized outside recipes: {bad[:5]}"


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


def test_skill_lint_rejects_unknown_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """user spec 의 unknown capability lint 실패 — warning + skip (raise X).

    P-revised (registry.py graceful fallback): user spec 1 개의 lint 실패가 ReadSkill
    tool 전체를 못 돌게 만들지 않도록 spec 단위 skip + warning. builtin spec 의 lint
    실패는 여전히 raise (별도 경로).
    """
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

    with caplog.at_level("WARNING", logger="dartlab.skills.registry"):
        result = skills.list()

    # listSkills 가 raise 안 함, 결과에 bad spec 미포함, warning 로깅
    assert all(spec.id != "badReview" for spec in result)
    assert any("unknown capabilities" in record.message for record in caplog.records)


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


# test_skill_compiler_builds_web_index 폐기. 산출물 6 종은
# 운영자·사용자·사용자가 위임한 AI 가 명시적으로 관리하고,
# 별도 검증 (validateSkills) 으로 확인한다.


def test_builtin_skill_specs_are_package_sources() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    specs_root = repo_root / "src" / "dartlab" / "skills" / "specs"

    assert specs_root.exists()

    start = skills.get("start.dartlabSkillOs", includeUser=False)
    source_path = str(start.source.get("path", "")).replace("\\", "/")

    assert "/src/dartlab/skills/specs/start/dartlabSkillOs.md" in source_path


def test_list_skills_caches_result_for_repeat_calls() -> None:
    """0.10 — listSkills() 결과는 process-lifetime 캐시. e2e probe 의 alias 호출 11s → 25ms 회귀 가드.

    이전 회귀: 매 호출마다 74+N skill 의 lintSkill() 재실행으로 alias dispatch 가 11 s 까지.
    """
    import time

    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()

    t0 = time.perf_counter()
    first = listSkills(includeUser=True)
    first_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    second = listSkills(includeUser=True)
    second_ms = (time.perf_counter() - t1) * 1000

    assert len(first) == len(second), "캐시 hit 결과는 같은 갯수"
    assert second_ms < first_ms / 5, (
        f"두 번째 호출이 첫 호출보다 5x 이상 빨라야 (현재: 1st={first_ms:.0f} ms, 2nd={second_ms:.0f} ms)"
    )
    assert second_ms < 50, f"캐시 hit 은 ms 단위여야 함 ({second_ms:.0f} ms)"


def test_skills_cache_disabled_via_env(monkeypatch) -> None:
    """DARTLAB_SKILL_NO_CACHE=1 escape — dev 환경에서 spec 변경 즉시 반영용."""
    import time

    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    monkeypatch.setenv("DARTLAB_SKILL_NO_CACHE", "1")
    _registry._LIST_SKILLS_CACHE.clear()

    listSkills(includeUser=True)  # 첫 호출 — 캐시 안 들어감
    assert not _registry._LIST_SKILLS_CACHE, "no-cache 모드에선 캐시 비어 있음"

    t0 = time.perf_counter()
    listSkills(includeUser=True)
    elapsed = (time.perf_counter() - t0) * 1000
    assert elapsed > 50, f"no-cache 모드에선 두 번째 호출도 빌드 비용 발생 (현재 {elapsed:.0f} ms)"
