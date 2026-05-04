"""표/숫자 직렬화는 ToolResult ref payload 계약으로 검증한다."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_run_python_table_payload_preserves_rows():
    from dartlab.ai.tools.runPython import runPython

    rows = [
        {"period": "2024", "revenue": 4.7e12},
        {"period": "2025", "revenue": 6.2e12},
    ]
    result = runPython(f"emit_result(table={rows!r})", runId="serialize")

    table_refs = [ref for ref in result.refs if ref.kind == "tableRef"]
    assert table_refs
    assert table_refs[0].payload["rows"] == rows


def test_execution_ref_keeps_stdout_without_polars_box():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("print('hello')", runId="serialize")

    assert result.ok is True
    assert result.refs[0].payload["stdout"].strip() == "hello"
