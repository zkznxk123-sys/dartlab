"""YoY 보강은 레거시 aiview가 아니라 실행 ref로 남긴다."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_ai_context_package_is_removed():
    assert importlib.util.find_spec("dartlab.ai.context") is None


def test_run_python_can_emit_yoy_values():
    from dartlab.ai.tools.runPython import runPython

    code = """
current = 120
previous = 100
emit_result(values={"revenue_yoy": (current - previous) / previous * 100}, units={"revenue_yoy": "%"})
"""
    result = runPython(code, runId="yoy")

    assert result.ok is True
    assert any(ref.kind == "valueRef" and ref.payload["key"] == "revenue_yoy" for ref in result.refs)
