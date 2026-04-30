from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_ai_tool_schema_still_supports_workspace_tools():
    from dartlab.ai.tools import AITool, toolsToOpenAiSchemas

    tool = AITool(
        name="workspace_status",
        description="Return workspace status.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: {"ok": True},
    )

    schemas = toolsToOpenAiSchemas([tool])

    assert schemas[0]["function"]["name"] == "workspace_status"
    assert schemas[0]["function"]["parameters"]["type"] == "object"


def test_contracts_keep_capabilities_arg_sanitizer():
    from dartlab.ai.runtime.contracts import sanitizeCapabilitiesArgs

    assert sanitizeCapabilitiesArgs({"key": "functions.capabilities(arguments={scan})"})["key"] == "scan"


def test_plugin_hints_do_not_recommend_unverified_packages():
    from dartlab.ai.runtime.plugin_hints import detect_plugin_hints, format_plugin_hints

    hints = detect_plugin_hints("최근 주가 분석해줘")

    assert hints == []
    assert format_plugin_hints(hints) is None


def test_legacy_tool_loop_fails_loudly():
    from dartlab.ai.runtime.toolLoop import streamWithTools

    with pytest.raises(RuntimeError, match="retired"):
        streamWithTools()
