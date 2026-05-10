"""진행 표시는 레거시 progressCapture가 아니라 Workbench TraceEvent가 담당한다."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_workbench_emits_ordered_public_progress_events():
    from dartlab.ai.kernel import _askEvents

    events = list(_askEvents("너 뭐 할 수 있니"))
    kinds = [event.kind for event in events]

    assert "graph_node" in kinds
    assert "tool_start" in kinds
    assert "tool_result" in kinds
    assert kinds[-1] == "done"


def test_progress_events_do_not_use_legacy_runtime_module():
    import importlib.util

    assert importlib.util.find_spec("dartlab.ai.runtime") is None
