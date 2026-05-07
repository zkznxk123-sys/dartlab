from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_canonical_tool_registry_exposes_expected_tools():
    from dartlab.ai.tools import CANONICAL_TOOL_NAMES, toolSpecs

    names = set(CANONICAL_TOOL_NAMES)
    specs = {spec["name"] for spec in toolSpecs()}

    # P-revised: deprecated tools (skill_search/generated_spec_search/engine_call/verify_answer/read/write) 삭제됨
    assert {"run_python", "read_skill", "read_capability", "web_search", "save_artifact", "compile_visual"}.issubset(
        names
    )
    assert names == specs


def test_deprecated_tools_not_in_registry():
    """P-revised — legacy 도구는 registry 에서 제거되어야 한다."""
    from dartlab.ai.tools import CANONICAL_TOOL_NAMES

    deprecated = {"skill_search", "generated_spec_search", "engine_call", "verify_answer", "read", "write"}
    assert deprecated.isdisjoint(set(CANONICAL_TOOL_NAMES))


def test_read_capability_uses_capability_ssot():
    """후속 도구 read_capability 가 dartlab.core.capability.search 를 그대로 활용."""
    from dartlab.ai.tools.readCapability import readCapability

    result = readCapability("scan growth")

    assert result.ok is True
    assert any(ref.payload.get("apiRef") in {"dartlab.scan", "scan"} for ref in result.refs)


def test_engine_call_internal_helper_blocks_unknown_api():
    """engineCall 은 휴리스틱 helper 로 보존 (registry 미노출). plan 검증 동작 유지 확인."""
    from dartlab.ai.tools.engineCall import engineCall

    result = engineCall({"apiRef": "Nope.missing"})

    assert result.ok is False
    assert result.error == "unknown_api_ref"


def test_legacy_runtime_tool_loop_is_not_importable():
    import importlib.util

    assert importlib.util.find_spec("dartlab.ai.runtime") is None
