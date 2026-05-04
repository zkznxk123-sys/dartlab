from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_canonical_tool_registry_exposes_expected_tools():
    from dartlab.ai.tools import CANONICAL_TOOL_NAMES, toolSpecs

    names = set(CANONICAL_TOOL_NAMES)
    specs = {spec["name"] for spec in toolSpecs()}

    assert {"skill_search", "generated_spec_search", "engine_call", "run_python", "verify_answer"}.issubset(names)
    assert names == specs


def test_generated_spec_search_uses_capability_ssot():
    from dartlab.ai.tools.generatedSpecSearch import generatedSpecSearch

    result = generatedSpecSearch("scan growth")

    assert result.ok is True
    assert any(ref.payload.get("apiRef") in {"dartlab.scan", "scan"} for ref in result.refs)


def test_engine_call_blocks_unknown_api():
    from dartlab.ai.tools.engineCall import engineCall

    result = engineCall({"apiRef": "Nope.missing"})

    assert result.ok is False
    assert result.error == "unknown_api_ref"


def test_legacy_runtime_tool_loop_is_not_importable():
    import importlib.util

    assert importlib.util.find_spec("dartlab.ai.runtime") is None
