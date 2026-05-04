"""MCP 서버 기본 테스트 — canonical tools, resources, compat gating."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def test_mcp_tools_defined():
    from dartlab.mcp import _advertisedTools

    names = {tool["name"] for tool in _advertisedTools()}
    assert names == {"ask", "skill_search", "generated_spec_search", "engine_call", "run_python", "read"}
    assert "companyInsights" not in names
    assert "search_reference" not in names
    assert "finalize_answer" not in names


def test_mcp_tool_schema_valid():
    from dartlab.mcp import _advertisedTools

    for tool in _advertisedTools():
        assert "name" in tool
        assert "description" in tool
        assert "params" in tool
        assert "required" in tool
        assert isinstance(tool["params"], dict)
        assert isinstance(tool["required"], list)


def test_mcp_canonical_tools_execute():
    from dartlab.mcp import _executeTool

    found = json.loads(_executeTool("skill_search", {"query": "테스트 규칙", "limit": 3}))
    assert found["refs"][0]["id"] == "skill:operation.testing"

    spec = json.loads(_executeTool("generated_spec_search", {"query": "재무상태표", "limit": 5}))
    assert spec["refs"]

    private = json.loads(_executeTool("engine_call", {"plan": {"apiRef": "Company._private", "target": "005930"}}))
    assert private["ok"] is False
    assert private["error"] == "private_api_blocked"

    executed = json.loads(_executeTool("run_python", {"code": "emit_result(values={'x': 1})"}))
    assert executed["ok"] is True
    assert any(ref["kind"] == "executionRef" for ref in executed["refs"])


def test_mcp_skill_resources_are_readable():
    from dartlab.mcp import _resourcePayload

    listing, listing_mime = _resourcePayload("dartlab://skills")
    detail, detail_mime = _resourcePayload("dartlab://skills/start.dartlabSkillOs")

    listing_payload = json.loads(listing)
    detail_payload = json.loads(detail)

    assert listing_mime == "application/json"
    assert detail_mime == "application/json"
    assert any(item["id"] == "start.dartlabSkillOs" for item in listing_payload["skills"])
    assert detail_payload["id"] == "start.dartlabSkillOs"
    assert detail_payload["source"]["path"].replace("\\", "/").endswith("/skills/specs/start/dartlabSkillOs.md")


def test_mcp_legacy_generated_tools_hidden_by_default():
    from dartlab.mcp import _executeTool

    assert _executeTool("companyInsights", {"stockCode": "005930"}).startswith("Unknown tool")


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
