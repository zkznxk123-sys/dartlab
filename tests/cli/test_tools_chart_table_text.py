"""canonical tools와 viz smoke 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_canonical_tools_registered_without_table_text_helpers():
    from dartlab.ai.tools import CANONICAL_TOOL_NAMES

    assert "RunPython" in CANONICAL_TOOL_NAMES
    assert "verify_answer" not in CANONICAL_TOOL_NAMES
    assert "table" not in CANONICAL_TOOL_NAMES
    assert "text" not in CANONICAL_TOOL_NAMES


def test_run_python_can_produce_table_ref():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("emit_result(table=[{'name': 'A', 'value': 1}])", runId="unit")

    assert result.ok is True
    assert any(ref.kind == "tableRef" for ref in result.refs)


def test_viz_spec_generators_still_registered():
    from dartlab import viz

    assert "revenue_trend" in viz.SPEC_GENERATORS
    assert "insight_radar" in viz.SPEC_GENERATORS
    assert callable(viz.autoChart)
    assert callable(viz.chart_from_spec)
