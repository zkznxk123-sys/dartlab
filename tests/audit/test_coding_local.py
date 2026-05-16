"""run_python canonical tool 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_run_python_simple_output():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("print(2 + 3)", runId="unit")

    assert result.ok is True
    assert "5" in result.data["stdout"]
    assert result.refs[0].kind == "executionRef"


def test_run_python_runtime_error_returns_failed_result():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("1/0", runId="unit")

    assert result.ok is False
    assert result.error == "python_execution_failed"
    assert result.refs[0].kind == "executionRef"


def test_run_python_emit_result_creates_value_ref():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("emit_result(values={'answer': 42}, units={'answer': 'x'})", runId="unit")

    assert result.ok is True
    assert any(ref.kind == "valueRef" and ref.payload["value"] == 42 for ref in result.refs)
