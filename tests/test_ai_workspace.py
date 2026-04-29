from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_workspace_extracts_evidence_from_dataframe_and_artifact(tmp_path, monkeypatch):
    import polars as pl

    from dartlab import config
    from dartlab.ai.runtime.artifacts import csvArtifactsForToolResult
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    monkeypatch.setattr(config, "dataDir", str(tmp_path))
    df = pl.DataFrame({"stockCode": ["005930", "000660"], "returnPct": [12.3, 8.7]})
    artifacts = csvArtifactsForToolResult(df, name="pythonExec", arguments={"target": "movers"})

    workspace = AnalysisWorkspace(question="recent movers")
    evidence = workspace.recordToolResult(
        sourceTool="pythonExec",
        arguments={"target": "movers"},
        result=df,
        artifacts=artifacts,
    )

    assert len(evidence) == 2
    assert evidence[0].sourceTool == "pythonExec"
    assert evidence[0].target == "005930"
    assert evidence[0].metric == "returnPct"
    assert evidence[0].artifactIds


def test_contract_graph_is_runtime_ssot_for_price_mover_contract():
    from dartlab.ai.runtime.contract_graph import contractForTool, contractsForQuestion
    from dartlab.ai.runtime.contracts import contractMetadataForTool

    contract = contractForTool("gather", {"axis": "krx", "target": "close"})
    assert contract is not None
    assert contract.contractId == "gather.krx.close"
    assert contract.evidenceSchema["valueKeys"]

    question_contracts = contractsForQuestion("최근 주가가 많이 오른 종목을 찾아줘")
    assert [item.contractId for item in question_contracts] == ["gather.krx.close"]
    assert contractMetadataForTool("gather", {"axis": "krx", "target": "close"})["contractId"] == "gather.krx.close"


def test_workspace_uses_contract_evidence_schema_for_krx_ranking():
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="최근 주가가 많이 오른 종목")
    evidence = workspace.recordToolResult(
        sourceTool="gather",
        arguments={"axis": "krx", "target": "close"},
        result=[{"rank": 1, "stockCode": "215790", "corpName": "이노인스트루먼트", "returnPct": 493.42}],
        artifacts=[],
    )

    assert evidence[0].target == "215790"
    assert evidence[0].metric == "returnPct"
    assert evidence[0].value == 493.42
    assert evidence[0].unit == "%"


def test_tool_loop_promotes_viz_marker_to_visual_and_chart_event(monkeypatch):
    from dartlab.ai.runtime.toolLoop import streamWithTools
    from dartlab.ai.runtime.workspace import AnalysisWorkspace
    from dartlab.ai.types import ToolCall, ToolResponse

    class Provider:
        supports_native_tools = True

        class config:
            provider = "mock"

        def __init__(self):
            self.calls = 0

        def stream_with_tools(self, messages, tools, tool_choice=None):
            self.calls += 1
            if self.calls == 1:
                yield ToolResponse(
                    answer="",
                    provider="mock",
                    model="mock",
                    tool_calls=[ToolCall(id="call_1", name="pythonExec", arguments={"code": "emit"})],
                )
            else:
                yield ToolResponse(answer="final", provider="mock", model="mock", tool_calls=[])

        def format_assistant_tool_calls(self, answer, tool_calls):
            return {"role": "assistant", "content": answer}

        def format_tool_result(self, tool_call_id, result):
            return {"role": "tool", "content": result}

    marker = '<!--DARTLAB_VIZ:{"vizType":"chart","chartType":"bar","title":"T","series":[{"name":"x","data":[1]}],"categories":["A"]}:VIZ_END-->'
    monkeypatch.setattr(
        "dartlab.ai.runtime.toolLoop.executeTool",
        lambda *_args, **_kwargs: marker + "\nrank\tstockCode\treturnPct\n1\t005930\t12.3",
    )

    workspace = AnalysisWorkspace(question="ranking")
    out = list(streamWithTools(Provider(), [{"role": "user", "content": "q"}], category="meta", workspace=workspace))

    assert any(getattr(ev, "kind", None) == "chart" for ev in out)
    assert workspace.visuals
    assert workspace.visuals[0].evidenceIds


def test_tool_loop_auto_visualizes_stdout_ranking_table(monkeypatch):
    from dartlab.ai.runtime.toolLoop import streamWithTools
    from dartlab.ai.runtime.workspace import AnalysisWorkspace
    from dartlab.ai.types import ToolCall, ToolResponse

    class Provider:
        supports_native_tools = True

        class config:
            provider = "mock"

        def __init__(self):
            self.calls = 0

        def stream_with_tools(self, messages, tools, tool_choice=None):
            self.calls += 1
            if self.calls == 1:
                yield ToolResponse(
                    answer="",
                    provider="mock",
                    model="mock",
                    tool_calls=[ToolCall(id="call_1", name="pythonExec", arguments={"code": "rank"})],
                )
            else:
                yield ToolResponse(answer="final", provider="mock", model="mock", tool_calls=[])

        def format_assistant_tool_calls(self, answer, tool_calls):
            return {"role": "assistant", "content": answer}

        def format_tool_result(self, tool_call_id, result):
            return {"role": "tool", "content": result}

    monkeypatch.setattr(
        "dartlab.ai.runtime.toolLoop.executeTool",
        lambda *_args, **_kwargs: "rank\tstockCode\treturnPct\n1\t005930\t12.3\n2\t000660\t8.7",
    )

    workspace = AnalysisWorkspace(question="recent stock return ranking")
    out = list(streamWithTools(Provider(), [{"role": "user", "content": "q"}], category="meta", workspace=workspace))
    chart_events = [ev for ev in out if getattr(ev, "kind", None) == "chart"]

    assert chart_events
    assert chart_events[0].data["charts"][0]["series"][0]["data"] == [12.3, 8.7]


def test_tool_loop_appends_workspace_freshness_limit_to_final_answer():
    from dartlab.ai.runtime.toolLoop import streamWithTools
    from dartlab.ai.runtime.workspace import AnalysisWorkspace
    from dartlab.ai.types import ToolResponse

    class Provider:
        supports_native_tools = True

        class config:
            provider = "mock"

        def stream_with_tools(self, messages, tools, tool_choice=None):
            yield ToolResponse(answer="final answer", provider="mock", model="mock", tool_calls=[])

        def format_assistant_tool_calls(self, answer, tool_calls):
            return {"role": "assistant", "content": answer}

        def format_tool_result(self, tool_call_id, result):
            return {"role": "tool", "content": result}

    workspace = AnalysisWorkspace(question="macro freshness")
    workspace.addLimit("freshness: USDKRW:value available through 2025-01-01")
    workspace.addLimit("freshness: USDKRW:value available through 2025-02-28")

    out = list(streamWithTools(Provider(), [{"role": "user", "content": "q"}], category="meta", workspace=workspace))
    text = "".join(item for item in out if isinstance(item, str))

    assert "데이터 한계" in text
    assert "available through 2025-02-28" in text
    assert "available through 2025-01-01" not in text


def test_tool_loop_prefers_workspace_freshness_latest_asof_over_raw_limits():
    from dartlab.ai.runtime.toolLoop import streamWithTools
    from dartlab.ai.runtime.workspace import AnalysisWorkspace
    from dartlab.ai.types import ToolResponse

    class Provider:
        supports_native_tools = True

        class config:
            provider = "mock"

        def stream_with_tools(self, messages, tools, tool_choice=None):
            yield ToolResponse(answer="final answer", provider="mock", model="mock", tool_calls=[])

        def format_assistant_tool_calls(self, answer, tool_calls):
            return {"role": "assistant", "content": answer}

        def format_tool_result(self, tool_call_id, result):
            return {"role": "tool", "content": result}

    workspace = AnalysisWorkspace(question="macro freshness")
    workspace.addLimit("freshness: USDKRW:value available through 2024-02-14")
    workspace.freshness["USDKRW:value"] = {"latestAsOf": "2025-02-28", "staleDaily": True}

    out = list(streamWithTools(Provider(), [{"role": "user", "content": "q"}], category="meta", workspace=workspace))
    text = "".join(item for item in out if isinstance(item, str))

    assert "available through 2025-02-28" in text
    assert "available through 2024-02-14" not in text


def test_tool_loop_removes_empty_markdown_heading_lines():
    from dartlab.ai.runtime.toolLoop import _cleanFinalText

    assert _cleanFinalText("A\n\n##\n\nB") == "A\n\nB"


def test_tool_loop_compiles_workspace_answer_when_max_rounds_exhausted(monkeypatch):
    from dartlab.ai.runtime.toolLoop import streamWithTools
    from dartlab.ai.runtime.workspace import AnalysisWorkspace
    from dartlab.ai.types import ToolCall, ToolResponse

    class Provider:
        supports_native_tools = True

        class config:
            provider = "mock"

        def __init__(self):
            self.calls = 0

        def stream_with_tools(self, messages, tools, tool_choice=None):
            self.calls += 1
            yield ToolResponse(
                answer="",
                provider="mock",
                model="mock",
                tool_calls=[
                    ToolCall(
                        id=f"call_{self.calls}",
                        name="pythonExec",
                        arguments={"code": f"print({self.calls})"},
                    )
                ],
            )

        def format_assistant_tool_calls(self, answer, tool_calls):
            return {"role": "assistant", "content": answer}

        def format_tool_result(self, tool_call_id, result):
            return {"role": "tool", "content": result}

    monkeypatch.setattr(
        "dartlab.ai.runtime.toolLoop.executeTool",
        lambda *_args, **_kwargs: "target\tmetric\tvalue\nA\treturnPct\t12.3",
    )

    workspace = AnalysisWorkspace(question="compare A and B")
    out = list(
        streamWithTools(
            Provider(),
            [{"role": "user", "content": "q"}],
            category="finance",
            question="compare A and B",
            workspace=workspace,
            maxRounds=2,
        )
    )

    text = "".join(item for item in out if isinstance(item, str))
    assert "근거 장부 기준" in text
    assert "이 표에서 읽을 포인트" in text
    assert not any(getattr(item, "kind", None) == "error" for item in out)


def test_compare_runtime_budget_skips_quant_axes():
    from dartlab.ai.runtime.toolLoop import _toolBudgetBypass

    result = _toolBudgetBypass(
        "quant",
        {"stockCode": "005930", "axis": "가치평가"},
        observedToolCalls=[],
        intent="compare",
    )

    assert result is not None
    assert result["basis"] == "runtime_tool_budget"


def test_cashflow_preflight_uses_analysis_and_cf_statement():
    from dartlab.ai.runtime.toolLoop import _cashflowPreflightCalls

    calls = _cashflowPreflightCalls(category="finance", intent="act3_cash", stockCode="003230")

    assert calls[0] == ("analysis", {"stockCode": "003230", "axis": "현금흐름"})
    assert calls[1][0] == "show"
    assert calls[1][1]["topic"] == "CF"


def test_comparison_preflight_extracts_two_targets():
    from dartlab.ai.runtime.toolLoop import _comparisonPreflightCalls

    calls = _comparisonPreflightCalls(
        category="finance",
        intent="compare",
        question="삼성전자와 SK하이닉스 반도체 업종 경쟁력을 비교해줘",
    )

    assert [args["stockCode"] for _name, args in calls] == ["005930", "000660"]
    assert all(name == "analysis" for name, _args in calls)


def test_quality_requires_visual_when_workspace_has_visual_policy_question():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="recent ranking")
    workspace.recordToolResult(
        sourceTool="pythonExec",
        arguments={"target": "movers"},
        result="rank\tstockCode\treturnPct\n1\t005930\t12.3\n2\t000660\t8.7",
        artifacts=[],
    )
    workspace.recordFinalAnswer(
        "Recent ranking judgment is supported.\n\n"
        "| stockCode | returnPct |\n| --- | ---: |\n| 005930 | 12.3% |\n\n"
        "이 표에서 읽을 포인트\n- 005930 leads."
    )

    result = evaluateFinalAnswer(
        category="finance",
        question="recent stock return ranking",
        answer=(
            "Recent ranking judgment is supported.\n\n"
            "| stockCode | returnPct |\n| --- | ---: |\n| 005930 | 12.3% |\n\n"
            "이 표에서 읽을 포인트\n- 005930 leads."
        ),
        toolCalls=[{"name": "pythonExec", "arguments": {"code": "rank"}}],
        workspace=workspace,
    )

    assert not result.passed
    assert "missing_visual_explanation" in result.issues


def test_quality_rejects_visual_without_evidence_link():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="ranking")
    workspace.recordToolResult(
        sourceTool="pythonExec",
        arguments={"target": "movers"},
        result="rank\tstockCode\treturnPct\n1\t005930\t12.3",
        artifacts=[],
    )
    workspace.visuals.append(
        type(
            "Visual",
            (),
            {"evidenceIds": [], "toDict": lambda self: {"id": "viz_1", "evidenceIds": []}},
        )()
    )

    result = evaluateFinalAnswer(
        category="finance",
        question="recent stock return ranking",
        answer=(
            "Recent ranking judgment is supported.\n\n"
            "| stockCode | returnPct |\n| --- | ---: |\n| 005930 | 12.3% |\n\n"
            "이 표에서 읽을 포인트\n- 005930 leads."
        ),
        toolCalls=[{"name": "pythonExec", "arguments": {"code": "rank"}}],
        workspace=workspace,
    )

    assert not result.passed
    assert "unsupported_visual" in result.issues


def test_workspace_bundle_handles_array_values():
    import numpy as np

    from dartlab.ai.runtime.workspace import EvidenceItem

    item = EvidenceItem(id="ev_1", sourceTool="analysis", value=np.array([1, 2]))

    payload = item.toDict()

    assert payload["value"] == [1, 2]


def test_workspace_bundle_handles_polars_dataframe_values():
    import polars as pl

    from dartlab.ai.runtime.workspace import EvidenceItem

    item = EvidenceItem(
        id="ev_1",
        sourceTool="analysis",
        value=pl.DataFrame({"a": [1], "b": [2.0]}),
    )

    payload = item.toDict()

    assert payload["value"] == [{"a": 1, "b": 2.0}]


def test_workspace_compiles_visual_from_request_level_comparison_evidence():
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="삼성전자와 SK하이닉스 경쟁력 비교")
    workspace.recordToolResult(
        sourceTool="analysis",
        arguments={"stockCode": "005930", "axis": "profitability"},
        result=[{"stockCode": "005930", "score": 7}],
        artifacts=[],
    )
    workspace.recordToolResult(
        sourceTool="analysis",
        arguments={"stockCode": "000660", "axis": "profitability"},
        result=[{"stockCode": "000660", "score": 9}],
        artifacts=[],
    )

    visuals = workspace.ensureRequiredVisuals(answer="comparison")

    assert len(visuals) == 1
    assert visuals[0].evidenceIds
    assert visuals[0].spec["vizType"] == "chart"
    assert workspace.summary()["visualRequirement"]["satisfied"] is True


def test_quality_detects_stale_daily_workspace_freshness_without_disclosure():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="최근 한국 금리와 환율 상황 어때?")
    workspace.recordToolResult(
        sourceTool="gather",
        arguments={"axis": "macro", "target": "USDKRW"},
        result=[{"date": "2020-01-02", "value": 1200.0}],
        artifacts=[],
    )

    result = evaluateFinalAnswer(
        category="finance",
        question="최근 한국 금리와 환율 상황 어때?",
        answer=(
            "환율은 높은 수준입니다.\n\n"
            "| item | value |\n| --- | ---: |\n| USDKRW | 1200 |\n\n"
            "???쒖뿉???쎌쓣 ?ъ씤??n- 환율 판단입니다."
        ),
        toolCalls=[{"name": "gather", "arguments": {"axis": "macro", "target": "USDKRW"}}],
        workspace=workspace,
    )

    assert not result.passed
    assert "stale_date_risk" in result.issues


def test_quality_accepts_stale_daily_workspace_when_answer_discloses_date_basis():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="recent macro")
    workspace.freshness["USDKRW:value"] = {"latestAsOf": "2025-02-28", "staleDaily": True}

    result = evaluateFinalAnswer(
        category="finance",
        question="recent macro",
        answer=(
            "기준금리 데이터 기준일은 2025-02-15, 환율 데이터 기준일은 2026-04-27로 "
            "서로 다르기 때문에 같은 시점 비교로 단정하긴 어렵습니다.\n\n"
            "| metric | value |\n| --- | ---: |\n| USDKRW | 1472.5 |\n\n"
            "이 표에서 읽을 포인트\n- 기준일 차이가 핵심 한계입니다.\n\n"
            "판단: 가용 데이터 기준의 제한적 판단입니다."
        ),
        toolCalls=[{"name": "gather", "arguments": {"axis": "macro", "target": "USDKRW"}}],
        workspace=workspace,
    )

    assert "stale_date_risk" not in result.issues


def test_quality_accepts_plain_korean_judgment_words():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer

    result = evaluateFinalAnswer(
        category="finance",
        question="삼성전자와 SK하이닉스 비교",
        answer=(
            "결론은 SK하이닉스가 수익성 우위이고 삼성전자는 안정성이 강합니다.\n\n"
            "| 지표 | 삼성전자 | SK하이닉스 |\n| --- | ---: | ---: |\n| ROE | 10.3% | 35.5% |\n\n"
            "이 표에서 읽을 포인트\n- ROE 차이가 큽니다."
        ),
        toolCalls=[{"name": "analysis", "arguments": {"stockCode": "005930"}}],
    )

    assert "missing_judgment" not in result.issues


def test_quality_does_not_treat_repeated_generic_flag_rows_as_table_conflict():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer

    result = evaluateFinalAnswer(
        category="finance",
        question="기업이야기",
        answer=(
            "판단: 성장성은 강하지만 변동성은 봐야 합니다.\n\n"
            "| 구분 | 수치 | 의미 |\n|---|---:|---|\n"
            "| 종합평가 플래그 | 매출 고성장 46.8% | 성장주 프로파일 |\n"
            "| 종합평가 플래그 | 부채비율 46% | 재무안정성 우수 |\n\n"
            "이 표에서 읽을 포인트\n- 종합평가 플래그에는 이익 변동성 높음도 포함됩니다."
        ),
        toolCalls=[{"name": "analysis", "arguments": {"stockCode": "000660"}}],
    )

    assert "answer_table_conflict" not in result.issues


def test_quality_does_not_treat_rank_rows_as_table_conflict():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer

    result = evaluateFinalAnswer(
        category="finance",
        question="최근 오른 종목 찾아줘",
        answer=(
            "판단: 상위 급등주는 변동성이 큽니다.\n\n"
            "| 순위 | 종목 | 수익률 |\n|---:|---|---:|\n| 10 | 셀레믹스 | 176.35% |\n\n"
            "이 표에서 읽을 포인트\n- 10위인 셀레믹스도 +176.35%입니다."
        ),
        toolCalls=[{"name": "pythonExec", "arguments": {"code": "rank"}}],
    )

    assert "answer_table_conflict" not in result.issues


def test_quality_allows_percent_rounding_between_table_and_text():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer

    result = evaluateFinalAnswer(
        category="finance",
        question="기업이야기",
        answer=(
            "판단: 수익성은 강합니다.\n\n"
            "| 지표 | 2025 |\n|---|---:|\n| ROE | 35.59% |\n\n"
            "이 표에서 읽을 포인트\n- ROE 35.6%는 높은 수익성을 뜻합니다."
        ),
        toolCalls=[{"name": "analysis", "arguments": {"stockCode": "000660"}}],
    )

    assert "answer_table_conflict" not in result.issues


def test_disclosure_list_only_requires_title_or_body_basis():
    from dartlab.ai.runtime.quality import evaluateFinalAnswer
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="삼성전자 최근 공시에서 중요한 내용 찾아줘")
    workspace.recordToolResult(
        sourceTool="disclosure",
        arguments={"stockCode": "005930"},
        result=[{"date": "2026-04-24", "title": "자기주식취득결과보고서"}],
        artifacts=[],
    )

    result = evaluateFinalAnswer(
        category="finance",
        question="삼성전자 최근 공시에서 중요한 내용 찾아줘",
        answer=(
            "중요 공시는 자기주식 관련 공시입니다.\n\n"
            "| date | title |\n| --- | --- |\n| 2026-04-24 | 자기주식취득결과보고서 |\n\n"
            "???쒖뿉???쎌쓣 ?ъ씤??n- 중요합니다."
        ),
        toolCalls=[{"name": "disclosure", "arguments": {"stockCode": "005930"}}],
        workspace=workspace,
    )

    assert not result.passed
    assert "weak_disclosure_analysis" in result.issues


def test_workspace_latency_summary_records_slow_reasons():
    from dartlab.ai.runtime.workspace import AnalysisWorkspace

    workspace = AnalysisWorkspace(question="SK하이닉스 기업이야기")
    workspace.recordLlmRound(1000)
    workspace.recordToolLatency(name="story", durationMs=61_000, resultSizeBytes=10_000, round=1)
    workspace.noteQualityRewrite()

    summary = workspace.summary()

    assert summary["toolTotalMs"] == 61_000
    assert "story_tool_slow" in summary["slowReason"]
    assert "quality_rewrite" in summary["slowReason"]


def test_audit_collector_records_tool_latency(tmp_path):
    import json

    from dartlab.ai.runtime.audit import AuditCollector

    audit = AuditCollector(question="q", data_dir=tmp_path)
    audit.observe("tool_call", {"name": "story", "arguments": {"stockCode": "000660"}})
    audit.observe(
        "tool_result",
        {
            "name": "story",
            "status": "ok",
            "durationMs": 1234,
            "resultSizeBytes": 4567,
            "artifacts": [],
        },
    )
    audit.observe("done", {"responseMeta": {"toolTotalMs": 1234, "llmRoundMs": 50, "slowReason": ["story_tool_slow"]}})
    audit.flush()

    path = next((tmp_path / "audit" / "ai-ask").glob("*.jsonl"))
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

    assert row["tool_calls"][0]["duration_ms"] == 1234
    assert row["tool_calls"][0]["result_size_bytes"] == 4567
    assert row["tool_total_ms"] == 1234
    assert row["llm_round_ms"] == 50
    assert row["slow_reason"] == ["story_tool_slow"]


def test_audit_collector_records_contract_ids(tmp_path):
    import json

    from dartlab.ai.runtime.audit import AuditCollector

    audit = AuditCollector(question="q", data_dir=tmp_path)
    audit.observe(
        "done",
        {
            "responseMeta": {
                "coverage": {
                    "contractIds": ["gather.krx.close"],
                    "contractViolations": ["stale_date_risk"],
                }
            }
        },
    )
    audit.flush()

    path = next((tmp_path / "audit" / "ai-ask").glob("*.jsonl"))
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

    assert row["contract_ids"] == ["gather.krx.close"]
    assert row["contract_violations"] == ["stale_date_risk"]
