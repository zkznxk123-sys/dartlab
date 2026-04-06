"""R32 audit 회귀 테스트 — viz 엔진.

R32-1: 빈 spec 또는 chartType 없는 spec 거부.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_emit_chart_rejects_empty_spec(capsys):
    """R32-1: 빈 dict 거부."""
    from dartlab.viz import emit_chart
    emit_chart({})
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" not in out
    assert "차트 거부" in out
    assert "chartType" in out


def test_emit_chart_rejects_no_charttype(capsys):
    """R32-1: chartType / vizType 없으면 거부."""
    from dartlab.viz import emit_chart
    emit_chart({"title": "test", "categories": ["A"], "series": [{"data": [1]}]})
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" not in out
    assert "차트 거부" in out


def test_emit_chart_passes_with_charttype(capsys):
    """R32-1: chartType 있으면 통과."""
    from dartlab.viz import emit_chart
    emit_chart({
        "chartType": "line",
        "title": "test",
        "categories": ["2022", "2023"],
        "series": [{"name": "A", "data": [100, 110]}],
    })
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" in out
    assert "차트 거부" not in out
