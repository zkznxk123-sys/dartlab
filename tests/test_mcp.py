"""MCP 서버 기본 테스트 — 도구 정의, 실행, 캐싱."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_mcp_tools_defined():
    from dartlab.mcp import _advertisedTools

    names = {t["name"] for t in _advertisedTools()}
    assert names == {
        "start_ask_session",
        "ask_kernel_status",
        "search_reference",
        "read_context",
        "inspect_dataset",
        "run_python",
        "compile_visual",
        "finalize_answer",
        "listDartlabSkills",
        "searchDartlabSkills",
        "explainDartlabSkill",
        "checkDartlabSkillEvidence",
    }
    assert "companyInsights" not in names
    assert "searchCompany" not in names
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


def test_mcp_workbench_tools_execute():
    from dartlab.mcp import _advertisedTools, _executeTool

    status = _executeTool("ask_kernel_status", {})
    assert "Ask Workbench Kernel" in status
    assert "datasetRoots" in status

    found = _executeTool("search_reference", {"query": "Ask Workbench", "limit": 3})
    assert "refs" in found

    executed = _executeTool("run_python", {"code": "emit_result(values={'x': 1})"})
    assert "DARTLAB_RESULT_JSON" in executed

    skills = _executeTool("searchDartlabSkills", {"query": "주가지수 강세"})
    assert "krxIndexStrengthReview" in skills

    operation = _executeTool("searchDartlabSkills", {"query": "테스트 규칙"})
    assert "operation.testing" in operation

    explained = _executeTool("explainDartlabSkill", {"skillId": "operation.testing", "includeUser": False})
    assert "operation.testing" in explained
    assert "DartLab Skill OS" in "".join(t["description"] for t in _advertisedTools())


def test_mcp_workbench_session_keeps_refs_between_tools():
    import json

    from dartlab.mcp import _executeTool

    session = json.loads(_executeTool("start_ask_session", {"question": "세션 ref 검산"}))
    session_id = session["sessionId"]

    executed = json.loads(
        _executeTool(
            "run_python",
            {
                "sessionId": session_id,
                "code": "emit_result(values={'sample_value': 42}, units={'sample_value': '점'})",
            },
        )
    )
    assert executed["refCount"] >= 2

    finalized = json.loads(
        _executeTool(
            "finalize_answer",
            {
                "sessionId": session_id,
                "answer": "sample_value는 42점입니다.",
            },
        )
    )
    assert finalized["ok"] is True
    assert finalized["session"]["refs"]


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
