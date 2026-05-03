from __future__ import annotations

from pathlib import Path

import pytest

from dartlab.ai.contracts import AnswerDraft, WorkbenchTask
from dartlab.ai.datasets import RuntimeDatasetCatalog
from dartlab.ai.verify import verify_answer
from dartlab.ai.visuals import compile_visual

pytestmark = pytest.mark.unit


def test_ai_package_does_not_use_data_module_name() -> None:
    import dartlab.ai as ai

    assert not (Path(ai.__file__).parent / "data").exists()
    assert (Path(ai.__file__).parent / "datasets.py").is_file()


def test_runtime_dataset_catalog_inspects_gitignored_style_root(tmp_path: Path) -> None:
    import polars as pl

    root = tmp_path / "external_data_root"
    dataset_dir = root / "krx" / "indices"
    dataset_dir.mkdir(parents=True)
    pl.DataFrame(
        {
            "BAS_DD": ["20260102", "20260103"],
            "IDX_NM": ["KOSPI", "KOSPI"],
            "CLSPRC_IDX": [100.0, 105.0],
            "FLUC_RT": [0.0, 5.0],
        }
    ).write_csv(dataset_dir / "raw-2026.csv")

    inspection = RuntimeDatasetCatalog([root]).inspect("krx.indices")

    assert inspection.ok
    assert inspection.dataset_id == "krx.indices"
    assert inspection.latest == {"column": "BAS_DD", "value": "20260103"}
    assert "IDX_NM" in inspection.semantic_profile["entityColumns"]
    assert "CLSPRC_IDX" in inspection.semantic_profile["metricCandidates"]


def test_runtime_dataset_catalog_does_not_treat_dd_metric_as_date(tmp_path: Path) -> None:
    import polars as pl

    root = tmp_path / "external_data_root"
    dataset_dir = root / "krx" / "indices"
    dataset_dir.mkdir(parents=True)
    pl.DataFrame(
        {
            "BAS_DD": ["20260102", "20260103"],
            "IDX_NM": ["KOSPI", "KOSPI"],
            "CMPPREVDD_IDX": [10.0, 20.0],
        }
    ).write_csv(dataset_dir / "raw-2026.csv")

    inspection = RuntimeDatasetCatalog([root]).inspect("krx.indices")

    assert inspection.ok
    assert inspection.semantic_profile["columnRoles"]["BAS_DD"] == "date"
    assert inspection.semantic_profile["columnRoles"]["CMPPREVDD_IDX"] == "metric"
    assert inspection.semantic_profile["dateColumns"] == ["BAS_DD"]


def test_runtime_dataset_catalog_keeps_file_extension_dot(tmp_path: Path) -> None:
    import polars as pl

    root = tmp_path / "runtime"
    path = root / "data" / "krx" / "indices" / "raw-2026.parquet"
    path.parent.mkdir(parents=True)
    pl.DataFrame({"BAS_DD": ["20260102"], "IDX_NM": ["KOSPI"], "CLSPRC_IDX": [100.0]}).write_parquet(path)

    inspection = RuntimeDatasetCatalog([root / "data"]).inspect(str(path))

    assert inspection.ok
    assert inspection.path == str(path)
    assert inspection.latest == {"column": "BAS_DD", "value": "20260102"}


def test_runtime_dataset_catalog_accepts_dataset_uri(tmp_path: Path) -> None:
    import polars as pl

    root = tmp_path / "runtime"
    path = root / "krx" / "indices" / "raw-2026.csv"
    path.parent.mkdir(parents=True)
    pl.DataFrame({"BAS_DD": ["20260102"], "IDX_NM": ["KOSPI"], "CLSPRC_IDX": [100.0]}).write_csv(path)

    inspection = RuntimeDatasetCatalog([root]).inspect("dartlab://datasets/krx.indices")

    assert inspection.ok
    assert inspection.dataset_id == "krx.indices"


def test_verifier_blocks_calculation_answer_without_execution_ref() -> None:
    task = WorkbenchTask(
        id="task:test",
        question="recent ranking",
    )
    draft = AnswerDraft(answer="KOSPI is up 15%.", evidence_refs=[])

    result = verify_answer(task, [], draft)

    assert not result.ok
    assert {issue["code"] for issue in result.issues} >= {"unsupported_numeric_claim"}
    assert "missing_execution" not in {issue["code"] for issue in result.issues}


def test_verifier_allows_numeric_claim_from_reference_ref() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="doc:test",
            kind="doc",
            source="search_reference",
            payload={"snippet": "DartLab scan finance-lite는 주요 30계정을 사용한다."},
        )
    ]
    draft = AnswerDraft(answer="finance-lite는 주요 30계정을 사용합니다.", evidence_refs=["doc:test"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_allows_rounded_numeric_claim_from_table_ref() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "A", "ret": 47.6411019877}], "metric": "ret"},
        )
    ]
    draft = AnswerDraft(answer="A의 수익률은 47.6%입니다.", evidence_refs=["table:test"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_uses_linked_table_when_evidence_ref_points_to_execution() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="execution:test",
            kind="execution",
            source="run_python",
            payload={"ok": True, "stdout": "", "stderr": "", "returncode": 0},
        ),
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"executionRef": "execution:test", "rows": [{"name": "A", "ret": 47.6411019877}], "metric": "ret"},
        ),
    ]
    draft = AnswerDraft(answer="A의 수익률은 47.6%입니다.", evidence_refs=["execution:test"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_uses_all_runtime_numeric_refs_when_final_evidence_refs_are_incomplete() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="dataset:test",
            kind="dataset",
            source="inspect_dataset",
            payload={"ok": True, "latest": {"value": "20260428"}},
        ),
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "A", "ret": 12.34}], "metric": "ret"},
        ),
    ]
    draft = AnswerDraft(answer="A의 수익률은 12.34%입니다.", evidence_refs=["dataset:test"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_ignores_markdown_rank_and_formula_multiplier() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "A", "ret": 47.6411019877}], "metric": "ret"},
        )
    ]
    draft = AnswerDraft(
        answer="수익률 = (최신 종가 / 기준 종가 - 1)×100\n\n|순위|종목|수익률|\n|---:|---|---:|\n|11|A|47.6|",
        evidence_refs=["table:test"],
    )

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_ignores_markdown_identifier_code_numbers() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"rows": [{"code": "058450", "name": "A", "ret": 47.6411019877}], "metric": "ret"},
        )
    ]
    draft = AnswerDraft(
        answer="|종목코드|종목|수익률|\n|---|---|---:|\n|058450|A|47.6|",
        evidence_refs=["table:test"],
    )

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_ignores_usage_example_numbers_in_code() -> None:
    task = WorkbenchTask(id="task:test", question="show 함수 어떻게 써?")
    draft = AnswerDraft(
        answer='사용법 예시는 `Company("005930").show("is")`처럼 씁니다.\n\n```python\nCompany("005930").show("is", years=3)\n```'
    )

    result = verify_answer(task, [], draft)

    assert result.ok


def test_verifier_allows_numeric_claim_from_visual_or_limit_ref() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="visual:test",
            kind="visual",
            source="compile_visual",
            payload={
                "title": "시총 500억 이상",
                "series": [{"data": [1, 2]}],
                "categories": ["A", "B"],
                "sourceRef": "table:test",
            },
        )
    ]
    draft = AnswerDraft(
        answer="시총 500억 이상 기준입니다.", evidence_refs=["visual:test"], limits=["시총 500억 이상 필터"]
    )

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_ignores_question_text_for_execution_requirement() -> None:
    task = WorkbenchTask(
        id="task:test",
        question="최근 주가지수를 보고 강세 지수를 찾아봐라",
    )
    draft = AnswerDraft(answer="데이터를 확인하지 못했습니다.", evidence_refs=[])

    result = verify_answer(task, [], draft)

    assert result.ok


def test_verifier_blocks_tool_call_transcript_as_answer() -> None:
    task = WorkbenchTask(id="task:test", question="anything")
    draft = AnswerDraft(answer='[tool_calls]\n- run_python id=call args={"code": "print(1)"}')

    result = verify_answer(task, [], draft)

    assert not result.ok
    assert "tool_transcript_released" in {issue["code"] for issue in result.issues}


def test_verifier_accepts_failed_execution_disclosure_in_limits() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="execution:failed",
            kind="execution",
            source="run_python",
            payload={"ok": False, "stderr": "missing column", "stdout": "", "returncode": 1},
        )
    ]
    draft = AnswerDraft(answer="확인 가능한 범위만 답합니다.", limits=["공시 목록 조회 실행 1건이 실패했습니다."])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_allows_superseded_failed_execution_when_successful_evidence_exists() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="execution:failed",
            kind="execution",
            source="run_python",
            payload={"ok": False, "stderr": "missing column", "stdout": "", "returncode": 1},
        ),
        Ref(
            id="execution:ok",
            kind="execution",
            source="run_python",
            payload={"ok": True, "stderr": "", "stdout": "", "returncode": 0},
        ),
        Ref(
            id="table:ok",
            kind="table",
            source="run_python",
            payload={"executionRef": "execution:ok", "rows": [{"name": "A", "value": 2}], "metric": "value"},
        ),
    ]
    draft = AnswerDraft(answer="A는 2입니다.", evidence_refs=["table:ok", "execution:ok"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_verifier_allows_visual_limitation_without_visual_claim() -> None:
    task = WorkbenchTask(id="task:test", question="anything")
    draft = AnswerDraft(answer="차트는 아직 생성하지 않았습니다. 표 기반 근거가 생기면 만들 수 있습니다.")

    result = verify_answer(task, [], draft)

    assert result.ok


def test_verifier_allows_visual_capability_language_without_visual_ref() -> None:
    task = WorkbenchTask(id="task:test", question="anything")
    draft = AnswerDraft(answer="저는 표와 차트도 만들 수 있습니다.")

    result = verify_answer(task, [], draft)

    assert result.ok


def test_verifier_blocks_dataset_unavailable_conflict() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [Ref(id="dataset:test", kind="dataset", source="unit", payload={"ok": True, "path": "data/krx/prices"})]
    draft = AnswerDraft(answer="현재 세션에서는 데이터 디렉터리에서 parquet/csv를 찾지 못했습니다.")

    result = verify_answer(task, refs, draft)

    assert not result.ok
    assert "dataset_availability_conflict" in {issue["code"] for issue in result.issues}


def test_verifier_blocks_implausible_percentage_without_disclosure() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [Ref(id="value:test", kind="value", source="unit", payload={"value": 2107.15})]
    draft = AnswerDraft(answer="비금속은 +2107.15% 상승했습니다.", evidence_refs=["value:test"])

    result = verify_answer(task, refs, draft)

    assert not result.ok
    assert "implausible_percentage_claim" in {issue["code"] for issue in result.issues}


def test_verifier_blocks_implausible_ratio_table_even_with_disclosure() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "A", "ret_21d": 4583.67}], "metric": "ret_21d"},
        )
    ]
    draft = AnswerDraft(
        answer="A는 +4583.67%입니다.", evidence_refs=["table:test"], limits=["비정상 수익률 가능성 고지"]
    )

    result = verify_answer(task, refs, draft)

    assert not result.ok
    assert "implausible_table_value" in {issue["code"] for issue in result.issues}


def test_verifier_blocks_answer_table_anchor_date_conflict() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:test",
            kind="table",
            source="run_python",
            payload={
                "rows": [
                    {"name": "A", "종료일": "20260428", "ret_5d": 10.0},
                    {"name": "B", "종료일": "20260123", "ret_5d": 20.0},
                ],
                "metric": "ret_5d",
            },
        )
    ]
    draft = AnswerDraft(
        answer="기준일 20260428 수익률 상위입니다. A는 10%, B는 20%입니다.", evidence_refs=["table:test"]
    )

    result = verify_answer(task, refs, draft)

    assert not result.ok
    assert "answer_table_date_conflict" in {issue["code"] for issue in result.issues}


def test_verifier_ignores_uncited_intermediate_implausible_table() -> None:
    from dartlab.ai.contracts import Ref

    task = WorkbenchTask(id="task:test", question="anything")
    refs = [
        Ref(
            id="table:raw",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "raw", "ret": 2107.15}], "metric": "ret"},
        ),
        Ref(
            id="table:final",
            kind="table",
            source="run_python",
            payload={"rows": [{"name": "final", "ret": 47.64}], "metric": "ret"},
        ),
    ]
    draft = AnswerDraft(answer="final 수익률은 47.6%입니다.", evidence_refs=["table:final"])

    result = verify_answer(task, refs, draft)

    assert result.ok


def test_compile_visual_rejects_single_value_chart() -> None:
    with pytest.raises(ValueError):
        compile_visual(
            source_ref="table:test",
            rows=[{"name": "summary", "value": 1.0}],
            category="name",
            metric="value",
        )


def test_search_reference_returns_skill_capability_and_knowledge_refs() -> None:
    from dartlab.ai.reference import search_reference

    refs = search_reference("최근 주가지수 강세", limit=8)
    kinds = {ref.kind for ref in refs}
    skill_ids = {ref.payload.get("skillId") for ref in refs if ref.kind == "skill"}

    assert "skill" in kinds
    assert "capability" in kinds
    assert "knowledge" in kinds
    assert "krxIndexStrengthReview" in skill_ids
    skill_ref = next(ref for ref in refs if ref.payload.get("skillId") == "krxIndexStrengthReview")
    assert skill_ref.payload["runtimeCompatibility"]["pyodide"]["status"] == "limited"
    assert skill_ref.payload["category"] == "screens"
    assert skill_ref.payload["procedure"]
    assert "datasetRefs" in skill_ref.payload


def test_search_reference_can_return_generated_basic_engine_skills() -> None:
    from dartlab.ai.reference import search_reference

    refs = search_reference("gather scan 최근 주가지수 강세", limit=10)
    skill_ids = {ref.payload.get("skillId") for ref in refs if ref.kind == "skill"}
    knowledge_refs = {item for ref in refs if ref.kind == "skill" for item in ref.payload.get("knowledgeRefs", [])}

    assert {"basic.gather", "basic.scan"} & (skill_ids | knowledge_refs)


def test_generated_capability_return_schema_preserves_units() -> None:
    from dartlab.core._generated import CAPABILITIES

    schema = CAPABILITIES["Company.capital"]["returnSchema"]
    by_name = {item["name"]: item for item in schema}

    assert by_name["배당수익률"]["unit"] == "%"
    assert by_name["배당성향"]["unit"] == "%"
    assert by_name["자사주매입"]["unit"] == "주"
    assert by_name["총환원율"]["unit"] == "%"


def test_search_reference_exposes_capability_return_schema_units() -> None:
    from dartlab.ai.reference import search_reference

    refs = search_reference("배당수익률 자사주매입 주주환원 Company.capital", limit=10)
    capital_ref = next(
        ref for ref in refs if ref.kind == "capability" and ref.payload.get("apiRef") == "Company.capital"
    )
    by_name = {item["name"]: item for item in capital_ref.payload["returnSchema"]}

    assert by_name["배당수익률"]["unit"] == "%"
    assert by_name["자사주매입"]["unit"] == "주"


def test_kernel_task_does_not_classify_questions() -> None:
    from dartlab.ai.kernel import create_task

    first = create_task("최근 주가지수를 보고 강세 지수를 찾아봐라").to_dict()
    second = create_task("삼성전자와 SK하이닉스 경쟁력 비교").to_dict()

    assert first["actions"] == second["actions"]
    assert "question_class" not in first
    assert "candidate_datasets" not in first


def test_kernel_task_preserves_target_hints_without_classification() -> None:
    from dartlab.ai.kernel import create_task

    task = create_task("인텔 분석해줘", {"company": "INTC"}).to_dict()

    assert task["hints"]["company"] == "INTC"
    assert "question_class" not in task


def test_kernel_task_capsule_includes_basic_skill_floor() -> None:
    import json

    from dartlab.ai.kernel import AskSession, _initial_provider_messages, create_task

    messages = _initial_provider_messages(AskSession(question="뭘 분석할 수 있나"), create_task("뭘 분석할 수 있나"))
    capsule = json.loads(messages[1]["content"])
    assert capsule["skillOs"]["entrySkillId"] == "start.dartlabSkillOs"
    assert capsule["skillOs"]["requiredRefKind"] == "skill"
    basic_ids = {item["id"] for item in capsule["skillOs"]["basicSkills"]}

    assert "basic.company" in basic_ids
    assert "basic.gather" in basic_ids
    assert "basic.scan" in basic_ids
    assert "basic.viz" in basic_ids
    assert "basicPythonExecution" not in basic_ids
    assert all("toolRefs" not in item for item in capsule["skillOs"]["basicSkills"])


def test_provider_workbench_loop_executes_actions_and_verifies(monkeypatch) -> None:
    from dartlab.ai import kernel
    from dartlab.ai.providers import ProviderTurn, ToolCall

    class FakeProvider:
        config = None

        def __init__(self) -> None:
            self.round = 0

        def generate(self, messages, tools):
            self.round += 1
            if self.round == 1:
                return ProviderTurn(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            name="run_python",
                            args={
                                "code": 'print("ok")\nprint("DARTLAB_RESULT_JSON=" + __import__("json").dumps({"rows": [{"name": "A", "value": 2}, {"name": "B", "value": 1}], "meta": {"asOf": "20260102"}}))'
                            },
                        )
                    ],
                )
            if self.round == 2:
                return ProviderTurn(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="call-2",
                            name="compile_visual",
                            args={
                                "source_ref": "table:external",
                                "rows": [{"name": "A", "value": 2}, {"name": "B", "value": 1}],
                                "category": "name",
                                "metric": "value",
                                "title": "비교",
                            },
                        )
                    ],
                )
            return ProviderTurn(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call-3",
                        name="finalize_answer",
                        args={
                            "answer": "A는 2이고 B는 1입니다.",
                            "evidence_refs": [],
                            "material_claims": [],
                            "limits": ["unit test provider loop"],
                        },
                    )
                ],
            )

    monkeypatch.setattr(kernel, "create_provider", lambda **_kwargs: FakeProvider())
    events = list(kernel.runAsk("삼성전자와 SK하이닉스 경쟁력 비교", provider="openai"))

    assert any(event.kind == "execute" for event in events)
    assert any(event.kind == "visual" for event in events)
    done = [event for event in events if event.kind == "done"][-1]
    assert done.data["verification"]["ok"] is True


def test_kernel_traces_rejected_draft_for_audit(monkeypatch) -> None:
    from dartlab.ai import kernel
    from dartlab.ai.providers import ProviderTurn

    class FakeProvider:
        config = None

        def __init__(self) -> None:
            self.round = 0

        def generate(self, messages, tools):
            self.round += 1
            if self.round == 1:
                return ProviderTurn(content="근거 없는 숫자 12345", tool_calls=[])
            return ProviderTurn(content="근거 없는 숫자 없음", tool_calls=[])

    monkeypatch.setattr(kernel, "create_provider", lambda **_kwargs: FakeProvider())
    events = list(kernel.runAsk("기능 설명", provider="openai"))
    rejected = [event for event in events if event.kind == "draft_rejected"]

    assert rejected
    assert rejected[0].data["reason"] == "prose_without_finalize"
    assert "근거 없는 숫자" in rejected[0].data["answerPreview"]
    assert rejected[0].data["verification"]["issues"]


def test_kernel_extracts_python_literal_result_json() -> None:
    from dartlab.ai.kernel import _extract_result_json, _refs_from_execution
    from dartlab.ai.notebook import ExecutionResult

    stdout = "DARTLAB_RESULT_JSON= {'asOf': '20260428', 'rows': [{'name': 'A', 'value': 1.5}, {'name': 'B', 'value': 1.0}]}\n"
    payload = _extract_result_json(stdout)
    refs = _refs_from_execution(
        ExecutionResult(ok=True, code="", returncode=0, stdout=stdout, stderr="", duration_ms=1, timeout=False),
        "execution:test",
    )

    assert payload and payload["asOf"] == "20260428"
    assert {ref.kind for ref in refs} >= {"table", "date"}


def test_kernel_table_metric_inference_skips_identifier_columns() -> None:
    from dartlab.ai.kernel import _refs_from_execution
    from dartlab.ai.notebook import ExecutionResult

    stdout = (
        "DARTLAB_RESULT_JSON="
        '{"rows": [{"ISU_CD": "038880", "ISU_NM": "A", "start_close": 133, "end_close": 1134, "ret_1m": 7.52}]}'
    )
    refs = _refs_from_execution(
        ExecutionResult(ok=True, code="", returncode=0, stdout=stdout, stderr="", duration_ms=1, timeout=False),
        "execution:test",
    )
    table = next(ref for ref in refs if ref.kind == "table")

    assert table.payload["metric"] == "ret_1m"


def test_kernel_ignores_invalid_emit_result_metric_hint() -> None:
    from dartlab.ai.kernel import _refs_from_execution
    from dartlab.ai.notebook import ExecutionResult

    stdout = (
        "DARTLAB_RESULT_JSON="
        '{"rows": [{"stockCode": "005930", "corp_name": "삼성전자", "op_margin_pct": 13.1}], '
        '"meta": {"metric": "target_id"}}'
    )
    refs = _refs_from_execution(
        ExecutionResult(ok=True, code="", returncode=0, stdout=stdout, stderr="", duration_ms=1, timeout=False),
        "execution:test",
    )
    table = next(ref for ref in refs if ref.kind == "table")

    assert table.payload["metric"] == "op_margin_pct"


def test_kernel_drops_non_numeric_emit_result_metric_hint() -> None:
    from dartlab.ai.kernel import _refs_from_execution
    from dartlab.ai.notebook import ExecutionResult

    stdout = (
        "DARTLAB_RESULT_JSON="
        '{"rows": [{"stockCode": "005930", "corp_name": "삼성전자"}], "meta": {"metric": "target_id"}}'
    )
    refs = _refs_from_execution(
        ExecutionResult(ok=True, code="", returncode=0, stdout=stdout, stderr="", duration_ms=1, timeout=False),
        "execution:test",
    )
    table = next(ref for ref in refs if ref.kind == "table")

    assert table.payload["metric"] is None


def test_search_reference_returns_short_dataset_resource_first() -> None:
    from dartlab.ai.reference import search_reference

    refs = search_reference("최근 주가지수 강세", limit=3)

    assert refs
    assert refs[0].kind == "skill"
    assert refs[0].payload.get("skillId") == "krxIndexStrengthReview"
    assert all("src/dartlab/ai/kernel.py" not in str(ref.payload.get("path") or "") for ref in refs)
    assert all(len(str(ref.payload.get("snippet") or "")) <= 2200 for ref in refs)


def test_search_reference_prioritizes_skill_for_capability_help() -> None:
    from dartlab.ai.reference import search_reference

    refs = search_reference("dartlab 뭐 할 수 있어", limit=5)

    assert refs[0].kind == "skill"
    assert refs[0].payload.get("skillId") == "start.useSkillsCatalog"


def test_search_reference_prioritizes_operation_and_start_skills() -> None:
    from dartlab.ai.reference import search_reference

    cases = {
        "테스트 규칙 확인": "operation.testing",
        "api contract 규칙": "operation.apiContract",
        "처음 온 외부 AI가 어디서 시작해야 해": "start.dartlabSkillOs",
    }

    for query, expected in cases.items():
        refs = search_reference(query, limit=5)
        assert refs[0].kind == "skill"
        assert refs[0].payload.get("skillId") == expected
        assert "sourceRefs" in refs[0].payload


def test_ask_workbench_release_policy_requires_skill_ref() -> None:
    from dartlab.ai.contracts import AnswerDraft
    from dartlab.ai.kernel import create_task
    from dartlab.ai.verify import verify_answer

    task = create_task("테스트 규칙 알려줘")
    result = verify_answer(task, [], AnswerDraft(answer="테스트 규칙은 Skill OS에서 확인합니다."))

    assert not result.ok
    assert any(issue["code"] == "missing_skill_ref" for issue in result.issues)


def test_run_python_emit_result_creates_refs() -> None:
    from dartlab.ai.kernel import _limits_from_execution, _refs_from_execution
    from dartlab.ai.notebook import run_python

    execution = run_python(
        "emit_result(rows=[{'name':'A','score':2.0},{'name':'B','score':1.0}], values={'topScore': 2.0}, meta={'asOf':'20260428','metric':'score'}, limits=['sample limit'])"
    )
    refs = _refs_from_execution(execution, "execution:test")

    assert execution.ok
    assert {ref.kind for ref in refs} >= {"table", "value", "date"}
    assert _limits_from_execution(execution) == ["sample limit"]


def test_run_python_emit_result_accepts_label_positional_rows() -> None:
    from dartlab.ai.kernel import _refs_from_execution
    from dartlab.ai.notebook import run_python

    execution = run_python("emit_result('scores', [{'name':'A','score':2.0},{'name':'B','score':1.0}])")
    refs = _refs_from_execution(execution, "execution:test")
    table = next(ref for ref in refs if ref.kind == "table")

    assert execution.ok
    assert table.payload["metric"] == "score"
    assert table.payload["meta"]["label"] == "scores"


def test_run_python_emit_result_accepts_named_table_rows() -> None:
    from dartlab.ai.kernel import _refs_from_execution
    from dartlab.ai.notebook import run_python

    execution = run_python(
        "emit_result(rows={'snapshot': [{'fy': 2025, 'revenue': 10.0}, {'fy': 2026, 'revenue': 12.0}]})"
    )
    refs = _refs_from_execution(execution, "execution:test")
    table = next(ref for ref in refs if ref.kind == "table")

    assert execution.ok
    assert table.payload["metric"] == "revenue"
    assert table.payload["meta"]["label"] == "snapshot"


def test_run_python_rejects_emit_result_redefinition() -> None:
    from dartlab.ai.notebook import run_python

    execution = run_python("def emit_result(**kwargs):\n    return kwargs\nemit_result(values={'x': 1})")

    assert not execution.ok
    assert "Do not define or assign emit_result" in execution.stderr


def test_kernel_does_not_release_calculation_answer_without_provider() -> None:
    from dartlab.ai import kernel
    from dartlab.ai.providers import ProviderConfig, UnavailableProvider

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        kernel, "create_provider", lambda **_kwargs: UnavailableProvider(ProviderConfig(provider="missing"))
    )
    try:
        events = list(kernel.runAsk("최근 주가지수를 보고 강세 지수를 찾아봐라"))
    finally:
        monkeypatch.undo()

    assert not any(event.kind == "execute" for event in events)
    done = [event for event in events if event.kind == "done"][-1]
    assert done.data["verification"]["ok"] is False
    assert done.data["verification"]["issues"][0]["code"] == "provider_unavailable"


def test_kernel_reports_unable_to_finalize_when_provider_cannot_finalize(monkeypatch) -> None:
    from dartlab.ai import kernel
    from dartlab.ai.providers import ProviderTurn

    class FakeProvider:
        def check_available(self):
            return True

        def generate(self, _messages, _tools):
            return ProviderTurn(content="", tool_calls=[])

    monkeypatch.setattr(kernel, "create_provider", lambda **_kwargs: FakeProvider())

    events = list(kernel.runAsk("너 뭐 분석할수있나"))

    done = [event for event in events if event.kind == "done"][-1]
    assert done.data["verification"]["issues"][0]["code"] == "unable_to_finalize"
    assert "provider_unavailable" not in done.data["limits"]


def test_kernel_uses_provider_loop_without_explicit_provider(monkeypatch) -> None:
    from dartlab.ai import kernel
    from dartlab.ai.providers import ProviderTurn, ToolCall

    class FakeProvider:
        def check_available(self):
            return True

        def generate(self, _messages, _tools):
            return ProviderTurn(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call-final",
                        name="finalize_answer",
                        args={"answer": "DartLab 문서와 데이터셋을 읽고 Python으로 실행해 분석합니다."},
                    )
                ],
            )

    called = {}
    monkeypatch.setattr(
        kernel, "create_provider", lambda **kwargs: called.setdefault("kwargs", kwargs) or FakeProvider()
    )

    events = list(kernel.runAsk("너 뭐 분석할수있나"))

    assert called["kwargs"] == {}
    done = [event for event in events if event.kind == "done"][-1]
    assert done.data["verification"]["ok"] is True


def test_kernel_has_no_question_specific_runner_names() -> None:
    import inspect

    import dartlab.ai.kernel as kernel

    source = inspect.getsource(kernel)

    assert "_run_krx" not in source
    assert "_run_peer" not in source
    assert "_run_disclosure" not in source
    assert "_index_strength_code" not in source
    assert "_price_strength_code" not in source
    assert "question_class" not in source
    assert "candidate_datasets" not in source
    assert "krx.indices" not in source


def test_kernel_and_verifier_have_no_domain_specific_hardcoding() -> None:
    import inspect

    import dartlab.ai.kernel as kernel
    import dartlab.ai.verify as verify

    source = inspect.getsource(kernel) + "\n" + inspect.getsource(verify)
    forbidden = [
        "삼성전자",
        "인텔",
        "005930",
        "INTC",
        "AAPL",
        "edgar.finance",
        "finance-lite",
        "profitabilityReview",
        "macroMarketReview",
        "usEdgarCompanyReview",
    ]

    assert not any(token in source for token in forbidden)


def test_verifier_has_no_question_word_execution_gate() -> None:
    import inspect

    import dartlab.ai.verify as verify

    source = inspect.getsource(verify)

    assert "_needs_execution" not in source
    assert "_is_analytical" not in source
    assert "missing_execution" not in source


def test_ai_public_surface_has_code_standard_docstrings() -> None:
    import inspect

    from dartlab.ai.datasets import inspect_dataset
    from dartlab.ai.kernel import ask, runAsk
    from dartlab.ai.mcp import execute_tool, tool_specs
    from dartlab.ai.notebook import run_python
    from dartlab.ai.reference import read_context, search_reference
    from dartlab.ai.verify import verify_answer
    from dartlab.ai.visuals import compile_visual

    required = ["Parameters", "Returns", "Raises", "Examples", "Notes", "Guide", "See Also"]
    for fn in [
        runAsk,
        ask,
        search_reference,
        read_context,
        inspect_dataset,
        run_python,
        compile_visual,
        verify_answer,
        tool_specs,
        execute_tool,
    ]:
        doc = inspect.getdoc(fn) or ""
        missing = [section for section in required if section not in doc]
        assert not missing, f"{fn.__module__}.{fn.__name__} missing {missing}"


def test_mcp_default_tools_are_canonical_workbench_only() -> None:
    from dartlab.ai.mcp import CANONICAL_TOOL_NAMES, execute_tool, tool_specs
    from dartlab.mcp import _executeTool

    names = [spec["name"] for spec in tool_specs()]

    assert names == CANONICAL_TOOL_NAMES
    assert "inspect_dataset" in names
    assert "inspect_data" not in names
    assert "web_search" not in names
    assert execute_tool("inspect_data", {"target": "__missing__"})["ok"] is False
    assert "Unknown tool" in _executeTool("searchCompany", {"query": "삼성전자"})


def test_provider_support_imports_without_legacy_ai(monkeypatch) -> None:
    from dartlab.ai.providers.oauth_codex import availableModels
    from dartlab.ai.providers.support.cli_setup import detect_codex
    from dartlab.ai.providers.support.oauth_token import load_token, revoke_token
    from dartlab.core.ai.model_resolver import latest_openai_model

    monkeypatch.delenv("DARTLAB_OAUTH_MODELS", raising=False)

    assert availableModels() == [latest_openai_model()]
    assert "installed" in detect_codex()
    assert callable(load_token)
    assert callable(revoke_token)


def test_openai_family_default_ignores_stale_profile_model(monkeypatch) -> None:
    import dartlab.ai.providers as providers
    from dartlab.core.ai.model_resolver import latest_openai_model

    monkeypatch.setattr(
        providers,
        "_resolve_profile",
        lambda *_args, **_kwargs: {"model": "gpt-5.4", "temperature": 0.3},
    )

    assert providers.get_config(provider="oauth-codex").model == latest_openai_model()
    assert providers.get_config(provider="openai").model == latest_openai_model()
    assert providers.get_config(provider="openai", model="gpt-5.4").model == "gpt-5.4"


def test_oauth_provider_requires_token_and_compatible_base_url(monkeypatch) -> None:
    from dartlab.ai.providers import create_provider
    from dartlab.ai.providers.oauth_codex import availableModels
    from dartlab.ai.types import LLMConfig

    monkeypatch.setenv("DARTLAB_OAUTH_TOKEN", "token-for-test")
    monkeypatch.setenv("DARTLAB_OAUTH_BASE_URL", "https://example.invalid/v1")

    provider = create_provider(LLMConfig(provider="oauth-codex"))

    assert provider.check_available()
    assert provider.resolved_model in availableModels()
