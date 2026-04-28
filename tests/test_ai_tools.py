"""Tool loader + toolLoop 단위 테스트.

대상:
    - ai/tools/__init__.py : buildTools() — CAPABILITIES 소비 자동 생성
    - ai/tools/serialize.py : LLM/UI 직렬화
    - ai/runtime/toolLoop.py : streamWithTools 루프
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ══════════════════════════════════════
# buildTools — CAPABILITIES 직접 소비
# ══════════════════════════════════════


class TestBuildTools:
    def test_produces_core_tools(self):
        from dartlab.ai.tools import buildTools

        tools = buildTools()
        names = {t.name for t in tools}
        for required in ("show", "analysis", "credit", "gather", "story", "scan", "macro", "search", "pythonExec"):
            assert required in names, f"{required} missing"

    def test_show_has_topic_enum(self):
        from dartlab.ai.tools import buildTools

        show = next(t for t in buildTools() if t.name == "show")
        topic = show.parameters["properties"]["topic"]
        assert "enum" in topic
        assert "IS" in topic["enum"]
        assert "inventory" in topic["enum"]

    def test_show_has_fields_for_select_consolidation(self):
        from dartlab.ai.tools import buildTools

        show = next(t for t in buildTools() if t.name == "show")
        assert "fields" in show.parameters["properties"]

    def test_scan_axis_enum_from_capabilities(self):
        """scan.axis enum 이 CAPABILITIES 의 `scan.*` entry 에서 자동 수집돼야."""
        from dartlab.ai.tools import buildTools

        scan = next(t for t in buildTools() if t.name == "scan")
        axis = scan.parameters["properties"]["axis"]
        assert "enum" in axis
        assert "growth" in axis["enum"]
        assert "profitability" in axis["enum"]

    def test_macro_axis_enum_from_capabilities(self):
        from dartlab.ai.tools import buildTools

        macro = next(t for t in buildTools() if t.name == "macro")
        axis = macro.parameters["properties"]["axis"]
        assert "enum" in axis
        assert "cycle" in axis["enum"]

    def test_analysis_axis_korean_from_docstring(self):
        from dartlab.ai.tools import buildTools

        analysis = next(t for t in buildTools() if t.name == "analysis")
        axis = analysis.parameters["properties"]["axis"]
        assert "enum" in axis
        assert "수익성" in axis["enum"]

    def test_all_schemas_valid_shape(self):
        from dartlab.ai.tools import buildTools, toolsToOpenAiSchemas

        schemas = toolsToOpenAiSchemas(buildTools())
        for s in schemas:
            assert s["type"] == "function"
            fn = s["function"]
            assert "name" in fn and "description" in fn
            params = fn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    def test_select_tools_for_question_limits_schema_surface(self):
        from dartlab.ai.tools import buildTools, selectToolsForQuestion

        tools = buildTools()
        selected = selectToolsForQuestion(
            tools,
            question="삼성전자 수익성 분석해줘",
            category="finance",
            intent="act2_profit",
            hasCompany=True,
            stockCode="005930",
        )
        names = {t.name for t in selected}
        assert len(selected) < len(tools)
        assert "analysis" in names
        assert "show" in names
        assert "scan" not in names

    def test_select_tools_for_compare_prefers_market_tools(self):
        from dartlab.ai.tools import buildTools, selectToolsForQuestion

        selected = selectToolsForQuestion(
            buildTools(),
            question="반도체 업종 비교해줘",
            category="finance",
            intent="compare",
            hasCompany=False,
        )
        names = {t.name for t in selected}
        assert "scan" in names
        assert "industry" in names
        assert "analysis" not in names

    def test_select_tools_for_company_pair_compare_exposes_company_evidence_tools(self):
        from dartlab.ai.tools import buildTools, selectToolsForQuestion

        selected = selectToolsForQuestion(
            buildTools(),
            question="삼성전자와 SK하이닉스 반도체 업종 경쟁력을 비교해줘",
            category="finance",
            intent="compare",
            hasCompany=False,
        )
        names = {t.name for t in selected}
        assert "searchCompany" in names
        assert "analysis" in names
        assert "quant" in names
        assert "scan" in names
        ordered = [t.name for t in selected]
        assert ordered.index("analysis") < ordered.index("scan")

    def test_ai_tool_surface_blocks_sections_tools(self):
        from dartlab.ai.tools import buildTools

        names = {t.name for t in buildTools()}
        assert "sections" not in names
        assert "topicSummaries" not in names
        assert "sectionsCoverage" not in names

    def test_select_tools_for_recent_price_movers_exposes_krx_path(self):
        from dartlab.ai.tools import buildTools, selectToolsForQuestion

        selected = selectToolsForQuestion(
            buildTools(),
            question="최근 주가가 많이 오른 종목을 찾아줘",
            category="finance",
            intent="compare",
            hasCompany=False,
        )
        names = [t.name for t in selected]
        assert "gather" in names
        assert "pythonExec" in names
        assert names.index("gather") < names.index("macro")

    def test_gather_schema_documents_krx_price_mover_contract(self):
        from dartlab.ai.tools import buildTools

        gather = next(t for t in buildTools() if t.name == "gather")
        props = gather.parameters["properties"]
        assert "krx" in props["axis"]["enum"]
        assert "price movers" in props["axis"]["description"]
        assert "target='close'" in props["target"]["description"]
        assert {"start", "end", "market", "stockCodes"} <= set(props)

    def test_gather_handler_forwards_kwargs(self, monkeypatch):
        import dartlab
        from dartlab.ai.tools import buildTools, executeTool

        received = {}

        def fake_gather(axis=None, target=None, **kwargs):
            received.update({"axis": axis, "target": target, **kwargs})
            return received

        monkeypatch.setattr(dartlab, "gather", fake_gather)
        result = executeTool(
            buildTools(),
            "gather",
            {
                "axis": "krx",
                "target": "close",
                "start": "2026-03-15",
                "end": "2026-04-28",
                "market": "KR",
            },
        )
        assert result["axis"] == "krx"
        assert result["target"] == "close"
        assert result["start"] == "2026-03-15"
        assert result["end"] == "2026-04-28"
        assert result["market"] == "KR"

    def test_show_handler_blocks_direct_sections_access(self):
        from dartlab.ai.tools import buildTools, executeTool

        result = executeTool(buildTools(), "show", {"stockCode": "005930", "topic": "sections"})
        assert "메모리 보호" in result["info"]
        assert "sections 직접 조회를 차단" in result["info"]

    def test_ecos_catalog_resolves_fx_alias(self):
        from dartlab.gather.ecos.catalog import getEntry, resolveId

        assert resolveId("KRWUSD") == "USDKRW"
        assert resolveId("DEXKOUS") == "USDKRW"
        entry = getEntry("KRWUSD")
        assert entry is not None
        assert entry.id == "USDKRW"

    def test_runtime_sanitizes_macro_fx_alias_and_future_end_date(self):
        from datetime import date

        from dartlab.ai.runtime.contracts import sanitizeToolArguments

        args = sanitizeToolArguments(
            "gather",
            {"axis": "macro", "target": "KRWUSD", "start": "2026-01-01", "end": "2026-12-31"},
            today=date(2026, 4, 28),
        )
        assert args["target"] == "USDKRW"
        assert args["end"] == "2026-04-28"

    def test_read_tool_description_points_to_docstring_skills(self):
        from dartlab.ai.tools import buildTools

        read = next(t for t in buildTools() if t.name == "Read")
        assert "src/dartlab/{engine}/__init__.py" in read.description
        assert "src/dartlab/skills" not in read.description

    def test_search_company_alias_ranks_hyundai_motor_first(self, monkeypatch):
        import polars as pl

        import dartlab
        from dartlab.ai.tools import buildTools, executeTool

        monkeypatch.setattr(
            dartlab,
            "searchName",
            lambda keyword: pl.DataFrame(
                {
                    "회사명": ["현대차증권", "현대자동차", "현대차"],
                    "종목코드": ["001500", "005380", "TEST00"],
                }
            ),
        )
        result = executeTool(buildTools(), "searchCompany", {"keyword": "현대차"})
        assert result["종목코드"][0] == "005380"
        assert result["_matchKind"][0] == "exact"

    def test_search_company_marks_ambiguous_candidates(self, monkeypatch):
        import polars as pl

        import dartlab
        from dartlab.ai.tools import buildTools, executeTool

        monkeypatch.setattr(
            dartlab,
            "searchName",
            lambda keyword: pl.DataFrame(
                {
                    "회사명": ["삼성전자", "삼성전기"],
                    "종목코드": ["005930", "009150"],
                }
            ),
        )
        result = executeTool(buildTools(), "searchCompany", {"keyword": "삼성"})
        assert "_ambiguous" in result.columns
        assert result["_ambiguous"][0] is True

    def test_executeTool_unknown(self):
        from dartlab.ai.tools import buildTools, executeTool

        tools = buildTools()
        with pytest.raises(ValueError):
            executeTool(tools, "missing_tool", {})


# ══════════════════════════════════════
# serialize.py
# ══════════════════════════════════════


class TestSerialize:
    def test_polarsTableToMarkdown_passthrough(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown

        assert polarsTableToMarkdown("no table") == "no table"

    def test_polarsTableToMarkdown_basic(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown

        text = (
            "┌──────┬──────┐\n"
            "│ col1 ┆ col2 │\n"
            "│ ---  ┆ ---  │\n"
            "│ str  ┆ f64  │\n"
            "╞══════╪══════╡\n"
            "│ a    ┆ 1.0  │\n"
            "└──────┴──────┘"
        )
        out = polarsTableToMarkdown(text)
        assert "| col1 | col2 |" in out
        assert "| a | 1.0 |" in out

    def test_serializeForLlm_dataframe(self):
        import polars as pl

        from dartlab.ai.tools.serialize import serializeForLlm

        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        out = serializeForLlm(df, name="test", arguments={})
        assert "shape:" in out
        assert "a" in out
        assert "b" in out

    def test_serializeForLlm_dict(self):
        from dartlab.ai.tools.serialize import serializeForLlm

        data = {"_summary": "ROE 양호", "grade": "A", "score": 85, "history": [{"period": "2024", "roe": 12.5}]}
        out = serializeForLlm(data, name="test", arguments={})
        assert "## Evidence" in out
        assert "도구명: test" in out
        assert "_summary: ROE 양호" in out
        assert "grade" in out
        assert "85" in out

    def test_serializeForLlm_contract_header(self):
        from dartlab.ai.tools.serialize import serializeForLlm

        out = serializeForLlm({"rows": []}, name="gather", arguments={"axis": "krx", "target": "close"})
        assert "계약 키: gather.krx.close" in out
        assert "필수 증거: asOf, 기간, universe, metric" in out

    def test_serializeForLlm_none(self):
        from dartlab.ai.tools.serialize import serializeForLlm

        out = serializeForLlm(None, name="test", arguments={})
        assert "## Evidence" in out
        assert "None" in out

    def test_serializeForLlm_large_df_head_only(self):
        import polars as pl

        from dartlab.ai.tools.serialize import serializeForLlm

        df = pl.DataFrame({"n": list(range(100))})
        out = serializeForLlm(df, name="test", arguments={})
        assert "상위 20개" in out or "100" in out
        assert len(out) < 8500

    def test_serializeForLlm_time_series_includes_latest_tail(self):
        import polars as pl

        from dartlab.ai.tools.serialize import serializeForLlm

        df = pl.DataFrame(
            {
                "date": [f"2026-01-{i:02d}" for i in range(1, 31)],
                "value": list(range(30)),
            }
        )
        out = serializeForLlm(df, name="gather", arguments={"axis": "macro", "target": "USDKRW"})
        assert "최신" in out
        assert "2026-01-30" in out

    def test_csv_artifact_for_dataframe_tool_result(self, tmp_path, monkeypatch):
        import polars as pl

        from dartlab import config
        from dartlab.ai.runtime.artifacts import csvArtifactsForToolResult

        monkeypatch.setattr(config, "dataDir", str(tmp_path))
        df = pl.DataFrame({"stockCode": ["005930"], "returnPct": [12.34]})

        artifacts = csvArtifactsForToolResult(df, name="pythonExec", arguments={"target": "movers"})

        assert len(artifacts) == 1
        artifact = artifacts[0]
        assert artifact["format"] == "csv"
        assert artifact["primary"] is True
        assert artifact["rows"] == 1
        assert artifact["columns"] == 2
        assert artifact["url"].startswith("/api/ask/artifacts/")
        csv_path = tmp_path / "ai-artifacts" / artifact["day"] / artifact["fileName"]
        assert csv_path.is_file()
        assert "005930" in csv_path.read_text(encoding="utf-8")

    def test_csv_artifact_for_tabular_dict_block(self, tmp_path, monkeypatch):
        from dartlab import config
        from dartlab.ai.runtime.artifacts import csvArtifactsForToolResult

        monkeypatch.setattr(config, "dataDir", str(tmp_path))
        result = {"rows": [{"종목": "A", "수익률": 10.0}, {"종목": "B", "수익률": 8.5}], "_summary": "rank"}

        artifacts = csvArtifactsForToolResult(result, name="scan", arguments={"axis": "growth"})

        assert len(artifacts) == 1
        assert artifacts[0]["label"] == "rows"
        assert artifacts[0]["rows"] == 2

    def test_csv_artifact_for_python_stdout_table(self, tmp_path, monkeypatch):
        from dartlab import config
        from dartlab.ai.runtime.artifacts import csvArtifactsForToolResult

        monkeypatch.setattr(config, "dataDir", str(tmp_path))
        stdout = (
            "period: 2026-03-16~2026-04-27\n"
            "rank\tstockCode\tcorpName\treturnPct\n"
            "1\t005930\t삼성전자\t12.3\n"
            "2\t000660\tSK하이닉스\t8.7\n"
        )

        artifacts = csvArtifactsForToolResult(stdout, name="pythonExec", arguments={})

        assert len(artifacts) == 1
        path = tmp_path / "ai-artifacts" / artifacts[0]["day"] / artifacts[0]["fileName"]
        text = path.read_text(encoding="utf-8")
        assert artifacts[0]["primary"] is True
        assert "stockCode" in text
        assert "005930" in text


# ══════════════════════════════════════
# toolLoop — mock provider
# ══════════════════════════════════════


class _MockProvider:
    supports_native_tools = True

    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0

        class _Cfg:
            provider = "mock"

        self.config = _Cfg()

    def complete_with_tools(self, messages, tools):
        from dartlab.ai.types import ToolResponse

        resp = self._responses[self._idx]
        self._idx += 1
        return ToolResponse(
            answer=resp.get("answer", ""),
            provider="mock",
            model="mock",
            tool_calls=resp.get("tool_calls", []),
            finish_reason=resp.get("finish_reason", "stop"),
        )

    def stream_with_tools(self, messages, tools):
        """테스트용 — fallback 경로처럼 ToolResponse 1회만 yield."""
        yield self.complete_with_tools(messages, tools)

    def format_assistant_tool_calls(self, answer, tool_calls):
        return {
            "role": "assistant",
            "content": answer,
            "tool_calls": [{"id": tc.id, "name": tc.name} for tc in tool_calls],
        }

    def format_tool_result(self, tool_call_id, result):
        return {"role": "tool", "tool_call_id": tool_call_id, "content": result}

    def stream(self, messages):
        yield "stream fallback"


class TestToolLoop:
    def test_stop_immediately(self):
        from dartlab.ai.runtime.toolLoop import streamWithTools

        llm = _MockProvider([{"answer": "바로 답변", "tool_calls": [], "finish_reason": "stop"}])
        # META 범주 — tool 0회 응답 허용 (FINANCE 면 P8 가드가 재질문)
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}], category="meta"))
        assert any(isinstance(item, str) and "바로 답변" in item for item in out)

    def test_finance_tool_zero_triggers_retry(self):
        """P8 가드 — FINANCE 범주에서 tool 0회면 재질문 1회 후 두 번째 라운드 응답 사용."""
        from dartlab.ai.runtime.toolLoop import streamWithTools

        # 라운드1: tool 0회 답변 (가드 발동) → 라운드2: tool 0회 답변 (즉시 종료)
        llm = _MockProvider(
            [
                {"answer": "첫 시도 일반론", "tool_calls": [], "finish_reason": "stop"},
                {"answer": "재시도 답변", "tool_calls": [], "finish_reason": "stop"},
                {"answer": "품질 재작성 답변", "tool_calls": [], "finish_reason": "stop"},
            ]
        )
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}], category="finance"))
        # VIOLATION 이벤트 있어야 함
        assert any(getattr(ev, "kind", None) == "error" and "VIOLATION" in str(ev.data) for ev in out)
        # 재시도 응답이 최종 yield
        assert any(getattr(ev, "kind", None) == "quality_check" and not ev.data["passed"] for ev in out)
        assert any(isinstance(item, str) and "품질 재작성 답변" in item for item in out)

    def test_rejects_provider_without_tools(self):
        from dartlab.ai.runtime.toolLoop import streamWithTools

        class _NoTool:
            supports_native_tools = False

            class config:
                provider = "ollama"

        with pytest.raises(RuntimeError, match="tool calling"):
            list(streamWithTools(_NoTool(), []))

    def test_tool_call_execution_with_real_tool(self):
        """CAPABILITIES 기반 tool (예: show) 호출 루프.

        실행 자체는 mock provider 가 "tool call 안 함" 으로 즉시 끝나는 기본 케이스만 검증.
        실제 handler 호출은 live AI audit 에서 검증.
        """
        from dartlab.ai.runtime.toolLoop import streamWithTools

        llm = _MockProvider([{"answer": "짧은 답", "tool_calls": [], "finish_reason": "stop"}])
        # META 범주 — tool 0회 허용 (FINANCE 면 재질문 가드 발동)
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}], category="meta"))
        assert any(isinstance(item, str) and "짧은 답" in item for item in out)

    def test_tool_result_event_includes_csv_artifact(self, tmp_path, monkeypatch):
        import polars as pl

        from dartlab import config
        from dartlab.ai.runtime.toolLoop import streamWithTools
        from dartlab.ai.types import ToolCall

        monkeypatch.setattr(config, "dataDir", str(tmp_path))

        def fake_execute(_tools, _name, _arguments):
            return pl.DataFrame({"종목": ["A"], "수익률": [10.0]})

        monkeypatch.setattr("dartlab.ai.runtime.toolLoop.executeTool", fake_execute)
        llm = _MockProvider(
            [
                {
                    "answer": "",
                    "tool_calls": [ToolCall(id="call_1", name="scan", arguments={"axis": "growth"})],
                },
                {"answer": "최종 답변", "tool_calls": [], "finish_reason": "stop"},
            ]
        )

        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}], category="meta"))
        tool_results = [ev for ev in out if getattr(ev, "kind", None) == "tool_result"]

        assert tool_results
        artifacts = tool_results[0].data["artifacts"]
        assert artifacts[0]["format"] == "csv"
        assert (tmp_path / "ai-artifacts" / artifacts[0]["day"] / artifacts[0]["fileName"]).is_file()

    def test_macro_fx_auto_args_for_exchange_rate_question(self):
        from dartlab.ai.runtime.toolLoop import _macroFxAutoArgs

        args = _macroFxAutoArgs("최근 한국 금리와 환율 상황 어때?", [{"name": "macro", "arguments": {"axis": "rates"}}])

        assert args is not None
        assert args["axis"] == "macro"
        assert args["target"] == "USDKRW"

    def test_macro_fx_auto_args_skips_existing_fx_evidence(self):
        from dartlab.ai.runtime.toolLoop import _macroFxAutoArgs

        args = _macroFxAutoArgs(
            "최근 한국 금리와 환율 상황 어때?",
            [{"name": "gather", "arguments": {"axis": "macro", "target": "KRWUSD"}}],
        )

        assert args is None


class TestQualityGate:
    def test_quality_missing_parts(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자 수익성 분석해줘",
            answer="좋아 보입니다.",
            toolCalls=[],
            stockCode="005930",
        )
        assert not result.passed
        assert "missing_tool_evidence" in result.issues
        assert "missing_numeric_table" in result.issues
        assert "missing_reading_notes" in result.issues

    def test_quality_passes_analyst_shape(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "삼성전자는 수익성 방어가 양호해 보입니다.\n\n"
            "| 지표 | 값 |\n"
            "| --- | --- |\n"
            "| ROE | 12.0% |\n\n"
            "이 표에서 읽을 포인트\n"
            "- ROE가 두 자릿수라 자본효율이 양호합니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자 수익성 분석해줘",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "005930"}}],
            stockCode="005930",
        )
        assert result.passed

    def test_quality_detects_company_mismatch(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "현대차는 안정성 점검이 필요합니다.\n\n"
            "| 지표 | 값 |\n| --- | --- |\n| 부채비율 | 120% |\n\n"
            "이 표에서 읽을 포인트\n- 부채비율은 보통권입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="현대차 안정성 분석",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "001500"}}],
            stockCode="005380",
        )
        assert not result.passed
        assert "company_mismatch_risk" in result.issues

    def test_quality_requires_table_for_price_mover_questions(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        result = evaluateFinalAnswer(
            category="finance",
            question="최근 주가가 많이 오른 종목을 찾아줘",
            answer="최근 오른 종목 후보입니다.",
            toolCalls=[{"name": "gather", "arguments": {"axis": "krx", "target": "close"}}],
        )
        assert not result.passed
        assert "missing_numeric_table" in result.issues
        assert "missing_reading_notes" in result.issues

    def test_quality_rejects_krx_price_mover_without_python_computation(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "최근 오른 종목 후보입니다.\n\n"
            "| 종목 | 시작 | 종료 |\n"
            "| --- | ---: | ---: |\n"
            "| KR모터스 | 428 | 593 |\n\n"
            "이 표에서 읽을 포인트\n"
            "- 원본 표본에서 상승했습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 주가가 많이 오른 종목을 찾아줘",
            answer=answer,
            toolCalls=[{"name": "gather", "arguments": {"axis": "krx", "target": "close"}}],
        )
        assert not result.passed
        assert "missing_numeric_table" in result.issues

    def test_quality_detects_stale_recent_date(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "현재 금리 환경은 2020-01-01 기준으로 안정적이라고 판단합니다.\n\n"
            "| 지표 | 값 |\n| --- | --- |\n| 기준일 | 2020-01-01 |\n\n"
            "이 표에서 읽을 포인트\n- 기준일이 오래됐지만 현재 판단처럼 썼습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 한국 금리 상황 어때?",
            answer=answer,
            toolCalls=[{"name": "macro", "arguments": {"axis": "rates", "end": "2020-01-01"}}],
        )
        assert not result.passed
        assert "stale_date_risk" in result.issues

    def test_quality_allows_disclosed_stale_recent_limit(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "최근 확인 가능한 기준일 기준으로 금리는 동결입니다.\n\n"
            "| 지표 | asOf | 값 |\n| --- | --- | ---: |\n| 기준금리 | 2025-08-31 | 2.5% |\n\n"
            "이 표에서 읽을 포인트\n- 현재라기보다 확인 가능한 기준일 기준입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 한국 금리 상황 어때?",
            answer=answer,
            toolCalls=[{"name": "macro", "arguments": {"axis": "rates", "end": "2025-08-31"}}],
        )
        assert result.passed

    def test_quality_requires_fx_evidence_for_exchange_rate_question(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "최근 한국 금리는 동결이고 환율은 데이터가 없어 단정하지 않겠습니다.\n\n"
            "| 지표 | 값 |\n| --- | ---: |\n| 기준금리 | 2.5% |\n\n"
            "이 표에서 읽을 포인트\n- 환율은 데이터 한계가 있습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 한국 금리와 환율 상황 어때?",
            answer=answer,
            toolCalls=[{"name": "macro", "arguments": {"axis": "rates", "market": "KR"}}],
        )
        assert not result.passed
        assert "stale_date_risk" in result.issues

    def test_quality_accepts_fx_alias_evidence_for_exchange_rate_question(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "2026-04-27 기준 금리와 환율은 안정으로 판단합니다.\n\n"
            "| 지표 | asOf | 값 |\n| --- | --- | ---: |\n| USD/KRW | 2026-04-27 | 1472.5 |\n\n"
            "이 표에서 읽을 포인트\n- 환율은 최신 확인 기준입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 한국 금리와 환율 상황 어때?",
            answer=answer,
            toolCalls=[{"name": "gather", "arguments": {"axis": "macro", "target": "DEXKOUS"}}],
        )
        assert result.passed

    def test_quality_detects_partial_comparison(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "비교하면 SK하이닉스가 더 매력적이라고 판단합니다.\n\n"
            "| 회사 | 영업이익률 |\n| --- | --- |\n| 삼성전자 | 13.0% |\n| SK하이닉스 | 데이터 미제공 |\n\n"
            "이 표에서 읽을 포인트\n- 한쪽 데이터가 없어도 SK하이닉스 우위입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자와 SK하이닉스 수익성을 비교해줘",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "005930"}}],
        )
        assert not result.passed
        assert "partial_comparison" in result.issues

    def test_quality_allows_disclosed_partial_comparison_limit(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "수익성 기준으로는 SK하이닉스가 우세하지만, 일부 축은 데이터 미수신이라 강한 결론을 일부 유보합니다.\n\n"
            "| 회사 | 영업이익률 | 신용등급 |\n| --- | ---: | --- |\n| 삼성전자 | 13.07% | dCR-AA |\n"
            "| SK하이닉스 | 48.59% | 데이터 미수신 |\n\n"
            "이 표에서 읽을 포인트\n- 수익성 동일 축은 SK하이닉스가 앞섭니다.\n- 신용 축은 한계가 있습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자와 SK하이닉스 수익성을 비교해줘",
            answer=answer,
            toolCalls=[
                {"name": "analysis", "arguments": {"stockCode": "005930"}},
                {"name": "analysis", "arguments": {"stockCode": "000660"}},
            ],
        )
        assert result.passed

    def test_quality_allows_auxiliary_missing_when_same_axis_evidence_exists(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "실측치 기준으로는 SK하이닉스가 수익성 우위라고 판단합니다.\n\n"
            "| 구분 | 삼성전자 | SK하이닉스 |\n| --- | ---: | ---: |\n"
            "| 2025 매출 YoY | 10.88% | 46.76% |\n"
            "| 2025 영업이익 YoY | 33.23% | 101.16% |\n"
            "| 매출 현금전환율 | 데이터 미확인 | 124.27 |\n\n"
            "이 표에서 읽을 포인트\n- 핵심 성장성 동일 축은 양쪽 모두 확인됩니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자와 SK하이닉스 반도체 업종 경쟁력을 비교해줘",
            answer=answer,
            toolCalls=[
                {"name": "analysis", "arguments": {"stockCode": "005930"}},
                {"name": "analysis", "arguments": {"stockCode": "000660"}},
            ],
        )
        assert result.passed

    def test_quality_detects_answer_table_conflict(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "삼성전자는 수익성이 양호하다고 판단합니다. 영업이익률은 10.0%입니다.\n\n"
            "| 지표 | 값 |\n| --- | --- |\n| 영업이익률 | 13.0% |\n\n"
            "이 표에서 읽을 포인트\n- 표와 본문 숫자가 충돌합니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자 수익성 분석해줘",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "005930"}}],
        )
        assert not result.passed
        assert "answer_table_conflict" in result.issues

    def test_quality_allows_reading_note_with_multiple_table_values(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "2026-04-27 기준 금리와 물가는 중립으로 판단합니다.\n\n"
            "| 지표 | asOf | 값 |\n| --- | --- | ---: |\n"
            "| 기준금리 | 2026-04-27 | 2.5% |\n| CPI | 2026-04-27 | 2.2% |\n\n"
            "이 표에서 읽을 포인트\n- 금리는 2.5%이고 CPI는 2.2%입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 한국 금리 상황 어때?",
            answer=answer,
            toolCalls=[{"name": "macro", "arguments": {"axis": "rates"}}],
        )
        assert result.passed

    def test_quality_detects_fcf_sign_conflict(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "삼양식품은 FCF 적자지만 현금흐름은 양호하다고 판단합니다.\n\n"
            "| 지표 | 값 |\n| --- | --- |\n| FCF | -1,521억 |\n\n"
            "이 표에서 읽을 포인트\n- FCF는 적자입니다.\n\n"
            "다만 세부 metric을 보면 FCF/매출 40.9%입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼양식품 현금흐름 분석해줘",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "003230"}}],
        )
        assert not result.passed
        assert "answer_table_conflict" in result.issues

    def test_quality_detects_unsupported_claim(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "삼성전자는 HBM3E 고객사 점유율이 높아 양호하다고 판단합니다.\n\n"
            "| 지표 | 값 |\n| --- | --- |\n| ROE | 12.0% |\n\n"
            "이 표에서 읽을 포인트\n- 점유율 claim 은 tool 근거에 없습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자 AI 반도체 전망 분석해줘",
            answer=answer,
            toolCalls=[{"name": "analysis", "arguments": {"stockCode": "005930"}}],
        )
        assert not result.passed
        assert "unsupported_claim" in result.issues

    def test_quality_detects_bad_capabilities_args(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "dartlab 기능은 capabilities로 확인할 수 있습니다.\n\n"
            "| 기능 | 값 |\n| --- | --- |\n| analysis | 가능 |\n\n"
            "이 표에서 읽을 포인트\n- 기능 조회 결과입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="분석 기능 알려줘",
            answer=answer,
            toolCalls=[{"name": "capabilities", "arguments": {"key": "analysis'}] to=functions.capabilities"}}],
        )
        assert not result.passed
        assert "bad_tool_args" in result.issues

    def test_quality_allows_meta_help_with_capabilities(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = "show 함수는 Company 데이터를 topic 기준으로 보여줍니다. 예: c.show('IS')"
        result = evaluateFinalAnswer(
            category="finance",
            question="show 함수 어떻게 써?",
            answer=answer,
            toolCalls=[{"name": "capabilities", "arguments": {"key": "Company.show"}}],
        )
        assert result.passed

    def test_quality_detects_bad_date_args(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "최근 상승 종목은 기간 수익률 기준으로 판단합니다.\n\n"
            "| 종목 | 수익률 |\n| --- | --- |\n| A | 12.0% |\n\n"
            "이 표에서 읽을 포인트\n- 날짜 인자가 역주행했습니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="최근 주가가 많이 오른 종목을 찾아줘",
            answer=answer,
            toolCalls=[
                {
                    "name": "gather",
                    "arguments": {"axis": "krx", "target": "close", "start": "2026-04-27", "end": "2026-03-16"},
                },
                {"name": "pythonExec", "arguments": {"code": "print('ok')"}},
            ],
        )
        assert not result.passed
        assert "bad_tool_args" in result.issues

    def test_quality_detects_weak_disclosure_analysis(self):
        from dartlab.ai.runtime.quality import evaluateFinalAnswer

        answer = (
            "가장 중요한 공시는 투자 판단에 긍정적이라고 판단합니다.\n\n"
            "| 접수일 | 제목 |\n| --- | --- |\n| 2026-04-27 | 단일판매 공급계약 |\n\n"
            "이 표에서 읽을 포인트\n- 제목 기준으로 중요한 내용입니다."
        )
        result = evaluateFinalAnswer(
            category="finance",
            question="삼성전자 최근 공시에서 중요한 내용 찾아줘",
            answer=answer,
            toolCalls=[{"name": "search", "arguments": {"keyword": "삼성전자", "limit": 5}}],
        )
        assert not result.passed
        assert "weak_disclosure_analysis" in result.issues


class TestAuditJudgment:
    def test_write_manual_judgment_utf8_jsonl(self, tmp_path):
        import json

        from dartlab.ai.runtime.audit import writeManualJudgment

        path = writeManualJudgment(
            request_id="req-test",
            verdict="T",
            reason="데이터 기준일 한계",
            issue_code="stale_date_risk",
            suggested_fix="최신 거래일 고지",
            accepted_by="manual",
            question="최근 주가?",
            data_dir=tmp_path,
        )
        assert path is not None
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert rows[0]["verdict"] == "T"
        assert rows[0]["reason"] == "데이터 기준일 한계"
