"""table helper 레거시는 run_python 표 산출로 대체된다."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_table_helper_module_is_removed():
    assert importlib.util.find_spec("dartlab.ai.tools.table") is None


def test_run_python_table_result_is_the_table_surface():
    from dartlab.ai.tools import executeTool

    result = executeTool("run_python", {"code": "emit_result(table=[{'year': 2024, 'value': 100}])"})

    assert result["ok"] is True
    assert any(ref["kind"] == "tableRef" for ref in result["refs"])
