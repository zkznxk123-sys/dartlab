"""회귀 가드 — registry 가 canonical 도구 보호 + V2 6 종 등록 확인."""

from __future__ import annotations

import pytest

from dartlab.ai.tools.registry import (
    CANONICAL_TOOL_NAMES,
    CANONICAL_V2,
    registerTool,
    unregisterTool,
)


@pytest.mark.unit
def test_canonical_v2_six_tools_registered() -> None:
    for name in CANONICAL_V2:
        assert name in CANONICAL_TOOL_NAMES, f"{name} 미등록"


@pytest.mark.unit
def test_canonical_tool_cannot_be_overridden_by_plugin() -> None:
    def _evil(**kwargs):  # noqa: ANN
        return None

    with pytest.raises(ValueError, match="canonical"):
        registerTool("run_python", _evil)


@pytest.mark.unit
def test_canonical_tool_cannot_be_unregistered() -> None:
    with pytest.raises(ValueError, match="canonical"):
        unregisterTool("read_skill")


@pytest.mark.unit
def test_plugin_tool_register_unregister_round_trip() -> None:
    def _hello(**kwargs):  # noqa: ANN
        return None

    registerTool("plugin_hello", _hello, description="hello plugin")
    try:
        from dartlab.ai.tools.registry import listToolNames

        assert "plugin_hello" in listToolNames()
    finally:
        unregisterTool("plugin_hello")
