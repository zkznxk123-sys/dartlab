"""Workspace agent 레거시는 ask/workbench 5 패스 루프로 통합한다."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_workbench_is_the_workspace_agent_entry():
    from dartlab.ai.workbench.loop import GRAPH_NODES

    assert GRAPH_NODES == (
        "brief",
        "work",
        "critique",
        "compose",
        "gate",
        "harvest",
    )


def test_workspace_agent_runtime_is_removed():
    import importlib.util

    assert importlib.util.find_spec("dartlab.ai.runtime") is None
