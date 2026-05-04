"""Ask Workbench의 공식 경계 테스트."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_ask_workbench_uses_skill_and_capability_loop():
    from dartlab.ai.workbench.loop import GRAPH_NODES

    assert GRAPH_NODES == (
        "routeIntent",
        "selectSkill",
        "searchCapability",
        "planEvidence",
        "executeTool",
        "observeResult",
        "verifyClaims",
        "composeAnswer",
        "repairOrFail",
    )


def test_kernel_exposes_ask_not_runtime_runask():
    import dartlab

    assert callable(dartlab.ask)
    assert importlib.util.find_spec("dartlab.ai.runtime") is None


def test_ask_stream_returns_public_events():
    from dartlab.ai.kernel import _ask_events

    events = list(_ask_events("너 뭐 할 수 있니"))
    kinds = [event.kind for event in events]

    assert kinds[0] == "graph_node"
    assert "tool_start" in kinds
    assert "tool_result" in kinds
    assert kinds[-1] == "done"
    assert events[-1].data.get("responseMeta", {}).get("responseStatus") == "ok"
