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

        data = {"grade": "A", "score": 85, "history": [{"period": "2024", "roe": 12.5}]}
        out = serializeForLlm(data, name="test", arguments={})
        assert "grade" in out
        assert "85" in out

    def test_serializeForLlm_none(self):
        from dartlab.ai.tools.serialize import serializeForLlm

        out = serializeForLlm(None, name="test", arguments={})
        assert "None" in out

    def test_serializeForLlm_large_df_head_only(self):
        import polars as pl

        from dartlab.ai.tools.serialize import serializeForLlm

        df = pl.DataFrame({"n": list(range(100))})
        out = serializeForLlm(df, name="test", arguments={})
        assert "상위 20개" in out or "100" in out
        assert len(out) < 8500


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
            ]
        )
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}], category="finance"))
        # VIOLATION 이벤트 있어야 함
        assert any(getattr(ev, "kind", None) == "error" and "VIOLATION" in str(ev.data) for ev in out)
        # 재시도 응답이 최종 yield
        assert any(isinstance(item, str) and "재시도 답변" in item for item in out)

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
