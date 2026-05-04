"""coding runtime 레거시는 canonical run_python tool로 대체된다."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_coding_backend_module_is_removed():
    assert importlib.util.find_spec("dartlab.ai.tools.coding") is None


def test_run_python_is_registered_as_canonical_tool():
    from dartlab.ai.tools import CANONICAL_TOOL_NAMES, executeTool

    assert "run_python" in CANONICAL_TOOL_NAMES
    result = executeTool("run_python", {"code": "print('ok')", "runId": "unit"})

    assert result["ok"] is True
    assert "ok" in result["data"]["stdout"]
