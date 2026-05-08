"""MCP 서버 기본 테스트 — canonical 7 tool surface, resources, alias 6."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def test_mcp_tools_defined():
    from dartlab.mcp import _advertisedTools

    names = {tool["name"] for tool in _advertisedTools()}
    # PascalCase canonical 6 종 + ask
    expected = {"ask", "ReadSkill", "ReadCapability", "RunPython", "WebSearch", "SaveArtifact", "CompileVisual"}
    assert expected.issubset(names)
    # 0.10 제거된 옛 33 generated 도구 + Discovery + Analysis Graph 도구는 advertised 에서 빠짐.
    deprecated = {
        "skill_search",
        "generated_spec_search",
        "engine_call",
        "verify_answer",
        "propose_skill",
        "companyInsights",
        "companyStory",
        "marketScan",
        "macroAnalysis",
        "listDartlabApi",
        "searchDartlabApi",
        "verifyDartlabApi",
    }
    assert deprecated.isdisjoint(names)


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
    """canonical tool dispatch (registry SSOT 경유)."""
    from dartlab.mcp import _executeWorkspaceAgentTool

    found = json.loads(_executeWorkspaceAgentTool("ReadSkill", {"query": "테스트 규칙", "limit": 3}))
    assert found["refs"][0]["id"] == "skill:operation.testing"

    spec = json.loads(_executeWorkspaceAgentTool("ReadCapability", {"query": "재무상태표", "limit": 5}))
    assert spec["refs"]

    executed = json.loads(_executeWorkspaceAgentTool("RunPython", {"code": "emit_result(values={'x': 1})"}))
    assert executed["ok"] is True
    assert any(ref["kind"] == "executionRef" for ref in executed["refs"])


def test_mcp_legacy_snake_alias_dispatch():
    """0.10 부터 _executeCompatAskTool 6 alias (snake_case + camelCase) 가 PascalCase canonical 로 정렬."""
    from dartlab.mcp import _executeWorkspaceAgentTool

    # skill_search alias → ReadSkill 로 정규화
    via_alias = json.loads(_executeWorkspaceAgentTool("skill_search", {"query": "테스트 규칙", "limit": 3}))
    direct = json.loads(_executeWorkspaceAgentTool("ReadSkill", {"query": "테스트 규칙", "limit": 3}))
    assert {ref["id"] for ref in via_alias["refs"]} == {ref["id"] for ref in direct["refs"]}


def test_mcp_unknown_tool_message():
    """0.10 에서 폐기된 옛 33 generated 도구 호출 시 마이그레이션 안내 포함 메시지 반환."""
    from dartlab.mcp import _executeWorkspaceAgentTool

    payload = json.loads(_executeWorkspaceAgentTool("companyInsights", {"stockCode": "005930"}))
    assert payload["ok"] is False
    assert "RunPython" in payload["error"]
    assert "0.10" in payload["error"]


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


def test_mcp_logger_handler_no_duplicate():
    """logger handler 가드 — stream identity 비교로 stderr handler 1 개만."""
    import logging
    import sys

    import dartlab.mcp  # noqa: F401 — 모듈 로드

    log = logging.getLogger("dartlab.mcp")
    stderr_handlers = [
        h for h in log.handlers if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stderr
    ]
    assert len(stderr_handlers) == 1
    assert log.propagate is False


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
