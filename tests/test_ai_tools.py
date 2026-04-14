"""Tool calling 인프라 단위 테스트.

대상:
    - ai/tools/schemas.py : JSON Schema 생성
    - ai/tools/registry.py : 등록/조회/실행
    - ai/tools/serialize.py : LLM/UI 직렬화
    - ai/tools/bootstrap.py : 기본 tool 10종 bootstrap
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ══════════════════════════════════════
# schemas.py
# ══════════════════════════════════════


class TestToolSchemas:
    def test_buildToolSchemas_returns_10_tools(self):
        from dartlab.ai.tools.schemas import buildToolSchemas

        schemas = buildToolSchemas()
        assert len(schemas) == 10
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "show",
            "select",
            "analysis",
            "scan",
            "macro",
            "credit",
            "gather",
            "search",
            "review",
            "pythonExec",
        }

    def test_show_schema_has_topic_enum(self):
        from dartlab.ai.tools.schemas import buildToolSchemas

        show = next(s for s in buildToolSchemas() if s["function"]["name"] == "show")
        topic = show["function"]["parameters"]["properties"]["topic"]
        assert "enum" in topic
        assert "IS" in topic["enum"]
        assert "BS" in topic["enum"]
        assert "inventory" in topic["enum"]

    def test_scan_schema_has_axis_enum(self):
        from dartlab.ai.tools.schemas import buildToolSchemas

        scan = next(s for s in buildToolSchemas() if s["function"]["name"] == "scan")
        axis = scan["function"]["parameters"]["properties"]["axis"]
        assert "enum" in axis
        assert "growth" in axis["enum"]
        assert "profitability" in axis["enum"]

    def test_analysis_schema_has_axis_enum_korean(self):
        from dartlab.ai.tools.schemas import buildToolSchemas

        analysis = next(s for s in buildToolSchemas() if s["function"]["name"] == "analysis")
        axis = analysis["function"]["parameters"]["properties"]["axis"]
        assert "enum" in axis
        assert "수익성" in axis["enum"]
        assert "현금흐름" in axis["enum"]
        assert "가치평가" in axis["enum"]

    def test_all_schemas_valid_json_schema_shape(self):
        from dartlab.ai.tools.schemas import buildToolSchemas

        for s in buildToolSchemas():
            assert s["type"] == "function"
            fn = s["function"]
            assert "name" in fn
            assert "description" in fn
            params = fn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params


# ══════════════════════════════════════
# registry.py
# ══════════════════════════════════════


class TestRegistry:
    def test_register_and_execute(self):
        from dartlab.ai.tools.registry import AITool, AIToolRegistry

        reg = AIToolRegistry()
        reg.register(
            AITool(
                name="echo",
                description="echo back",
                parameters={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
                handler=lambda msg: msg.upper(),
            )
        )
        assert reg.has("echo")
        assert reg.execute("echo", {"msg": "hi"}) == "HI"

    def test_unknown_tool_raises(self):
        from dartlab.ai.tools.registry import AIToolRegistry

        reg = AIToolRegistry()
        with pytest.raises(ValueError):
            reg.execute("missing", {})

    def test_getOpenaiSchemas_shape(self):
        from dartlab.ai.tools.registry import AITool, AIToolRegistry

        reg = AIToolRegistry()
        reg.register(
            AITool(
                name="t1",
                description="d1",
                parameters={"type": "object", "properties": {}},
                handler=lambda: None,
            )
        )
        schemas = reg.getOpenaiSchemas()
        assert len(schemas) == 1
        assert schemas[0] == {
            "type": "function",
            "function": {"name": "t1", "description": "d1", "parameters": {"type": "object", "properties": {}}},
        }


# ══════════════════════════════════════
# bootstrap.py
# ══════════════════════════════════════


class TestBootstrap:
    def test_bootstrap_registers_10_tools(self):
        from dartlab.ai.tools.bootstrap import bootstrapDefaultTools
        from dartlab.ai.tools.registry import getDefaultRegistry, resetDefaultRegistry

        resetDefaultRegistry()
        bootstrapDefaultTools()
        reg = getDefaultRegistry()
        assert len(reg.list_names()) == 10
        assert reg.has("show")
        assert reg.has("scan")
        assert reg.has("pythonExec")

    def test_ensureBootstrapped_idempotent(self):
        from dartlab.ai.tools.bootstrap import ensureBootstrapped
        from dartlab.ai.tools.registry import getDefaultRegistry, resetDefaultRegistry

        resetDefaultRegistry()
        ensureBootstrapped()
        n1 = len(getDefaultRegistry().list_names())
        ensureBootstrapped()
        n2 = len(getDefaultRegistry().list_names())
        assert n1 == n2 == 10


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
        # head(20) 만 들어감
        assert "상위 20개" in out or "100" in out  # shape/trunc note
        assert len(out) < 8500


# ══════════════════════════════════════
# toolLoop.py (mock provider)
# ══════════════════════════════════════


class _MockProvider:
    """Mock LLM — tool call 시나리오 시뮬레이션."""

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
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}]))
        assert any(isinstance(item, str) and "바로 답변" in item for item in out)

    def test_rejects_provider_without_tools(self):
        from dartlab.ai.runtime.toolLoop import streamWithTools

        class _NoTool:
            supports_native_tools = False

            class config:
                provider = "ollama"

        with pytest.raises(RuntimeError, match="tool calling"):
            list(streamWithTools(_NoTool(), []))

    def test_tool_call_execution(self):
        from dartlab.ai.runtime.events import AnalysisEvent
        from dartlab.ai.runtime.toolLoop import streamWithTools
        from dartlab.ai.tools.bootstrap import ensureBootstrapped
        from dartlab.ai.tools.registry import (
            AITool,
            getDefaultRegistry,
            resetDefaultRegistry,
        )
        from dartlab.ai.types import ToolCall

        resetDefaultRegistry()
        reg = getDefaultRegistry()
        reg.register(
            AITool(
                name="ping",
                description="ping",
                parameters={"type": "object", "properties": {}},
                handler=lambda: "pong",
            )
        )

        llm = _MockProvider(
            [
                {
                    "answer": "",
                    "tool_calls": [ToolCall(id="t1", name="ping", arguments={})],
                    "finish_reason": "tool_use",
                },
                {"answer": "답변 완료", "tool_calls": [], "finish_reason": "stop"},
            ]
        )
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}]))
        # tool_call + tool_result + final text
        kinds = [e.kind for e in out if isinstance(e, AnalysisEvent)]
        assert "tool_call" in kinds
        assert "tool_result" in kinds
        # 최종 텍스트
        texts = [x for x in out if isinstance(x, str)]
        assert any("답변 완료" in t for t in texts)

        # 원상복구 — 다른 테스트 영향 방지
        resetDefaultRegistry()
        ensureBootstrapped()

    def test_repeat_detection(self):
        """동일 tool_call 반복 시 강제 stop."""
        from dartlab.ai.runtime.events import AnalysisEvent
        from dartlab.ai.runtime.toolLoop import streamWithTools
        from dartlab.ai.tools.bootstrap import ensureBootstrapped
        from dartlab.ai.tools.registry import (
            AITool,
            getDefaultRegistry,
            resetDefaultRegistry,
        )
        from dartlab.ai.types import ToolCall

        resetDefaultRegistry()
        reg = getDefaultRegistry()
        reg.register(
            AITool(
                name="echo",
                description="echo",
                parameters={"type": "object", "properties": {"x": {"type": "string"}}},
                handler=lambda x: x,
            )
        )

        same_call = lambda _idx: {  # noqa: E731
            "answer": "",
            "tool_calls": [ToolCall(id=f"t{_idx}", name="echo", arguments={"x": "a"})],
            "finish_reason": "tool_use",
        }
        llm = _MockProvider([same_call(i) for i in range(5)])
        out = list(streamWithTools(llm, [{"role": "user", "content": "q"}]))
        errors = [e for e in out if isinstance(e, AnalysisEvent) and e.kind == "error"]
        assert any("반복" in e.data.get("error", "") for e in errors)

        resetDefaultRegistry()
        ensureBootstrapped()
