"""Ask Workbench의 공식 경계 테스트 — 5 패스 SSOT."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_ask_workbench_uses_5_pass_ssot():
    from dartlab.ai.workbench.loop import GRAPH_NODES

    assert GRAPH_NODES == (
        "brief",
        "work",
        "critique",
        "compose",
        "gate",
        "harvest",
    )


def test_kernel_exposes_ask_not_runtime_runask():
    import dartlab

    assert callable(dartlab.ask)
    assert importlib.util.find_spec("dartlab.ai.runtime") is None


def test_ask_stream_returns_public_events():
    """첫 이벤트는 graph_node, 마지막은 done. tool 이벤트는 두 path 중 하나로 발행된다.

    - 휴리스틱 path: tool_start / tool_result
    - LLM path: llm_tool_use / tool_result
    responseStatus 는 환경 상태 (provider/data) 에 따라 ok 또는 gate_blocked/failed 가능.
    """
    from dartlab.ai.kernel import _ask_events

    events = list(_ask_events("너 뭐 할 수 있니"))
    kinds = [event.kind for event in events]

    assert kinds[0] == "graph_node"
    assert "tool_result" in kinds or "gate_result" in kinds
    assert kinds[-1] == "done"
    assert events[-1].data.get("responseMeta", {}).get("responseStatus") in {"ok", "gate_blocked", "failed"}
