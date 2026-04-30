"""MCP 서버 기본 테스트 — 도구 정의, 실행, 캐싱."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_mcp_tools_defined():
    from dartlab.mcp import _TOOLS

    assert len(_TOOLS) > 10
    names = {t["name"] for t in _TOOLS}
    assert "companyInsights" in names
    assert "searchCompany" in names
    assert "companyStory" in names
    assert "marketScan" in names
    assert "contextForQuestion" in names
    assert "queryAnalysisGraph" in names
    assert "planDartlabQuestion" in names
    assert "validateDartlabPlan" in names
    assert "explainDartlabTool" in names
    assert "describeDartlabIntelligenceMap" in names
    assert "describeDartlabIntelligencePack" in names
    assert "workspace_status" in names
    assert "inspect_data" in names
    assert "run_python" in names
    assert "finalize_answer" in names
    assert "companySections" not in names


def test_mcp_tool_schema_valid():
    from dartlab.mcp import _TOOLS

    for tool in _TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "params" in tool
        assert "required" in tool
        assert isinstance(tool["params"], dict)
        assert isinstance(tool["required"], list)
        assert "_STOCK" not in str(tool["params"])


def test_mcp_graph_tools_execute():
    from dartlab.mcp import _executeTool

    context = _executeTool("contextForQuestion", {"question": "최근 주가가 많이 오른 종목을 찾아줘"})
    assert "gather.krx.close" in context

    found = _executeTool("queryAnalysisGraph", {"query": "gather.krx.close"})
    assert "contract:gather.krx.close" in found

    plan = _executeTool("planDartlabQuestion", {"question": "최근 주가가 많이 오른 종목을 찾아줘"})
    assert "recent_price_mover.default" in plan
    assert "primaryCsv" in plan
    assert "acceptanceCriteria" in plan
    assert "failurePolicy" in plan

    validated = _executeTool(
        "validateDartlabPlan",
        {"question": "최근 주가가 많이 오른 종목을 찾아줘", "proposedTools": ["pythonExec"]},
    )
    assert '"ok": true' in validated
    assert "acceptanceCriteria" in validated

    intelligence = _executeTool("describeDartlabIntelligenceMap", {"question": "최근 주가가 많이 오른 종목을 찾아줘"})
    assert "DartLab Financial Workspace Agent" in intelligence
    assert "recipeMap" in intelligence

    pack = _executeTool("describeDartlabIntelligencePack", {})
    assert '"schemaVersion": 1' in pack
    assert "capabilitySkillMap" in pack


def test_mcp_workspace_agent_tools_execute():
    from dartlab.mcp import _executeTool

    status = _executeTool("workspace_status", {})
    assert "workspaceRoot" in status
    assert "dataRoot" in status
    assert "intelligenceMap" in status

    found = _executeTool("search_workspace", {"query": "ops ai", "kind": "docs", "limit": 3})
    assert "results" in found


def test_fmt_none():
    from dartlab.mcp import _fmt

    assert _fmt(None) == "데이터 없음"


def test_fmt_dict():
    from dartlab.mcp import _fmt

    result = _fmt({"key": "value"})
    assert "key" in result
    assert "value" in result


def test_fmt_list():
    from dartlab.mcp import _fmt

    result = _fmt(["a", "b"])
    assert "a" in result
    assert "b" in result


def test_create_server_requires_mcp_sdk(monkeypatch):
    import dartlab.mcp as mcp_mod

    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def mock_import(name, *args, **kwargs):
        if name == "mcp.server":
            raise ImportError("no mcp")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    with pytest.raises(ImportError, match="MCP SDK"):
        mcp_mod.create_server()
