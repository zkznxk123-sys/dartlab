"""R32 audit 회귀 테스트 — viz 엔진.

R32-1: 빈 spec 또는 chartType 없는 spec 거부.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_emit_chart_rejects_empty_spec(capsys, caplog):
    """R32-1: 빈 dict 거부.

    거부 경고는 logger.warning (caplog 로 캡처), marker 는 stdout.
    """
    import logging

    from dartlab.viz import emitChart

    with caplog.at_level(logging.WARNING, logger="dartlab.viz"):
        emitChart({})
    out = capsys.readouterr().out
    log_text = caplog.text
    assert "DARTLAB_VIZ" not in out
    assert "차트 거부" in log_text
    assert "chartType" in log_text


def test_emit_chart_rejects_no_charttype(capsys, caplog):
    """R32-1: chartType / vizType 없으면 거부."""
    import logging

    from dartlab.viz import emitChart

    with caplog.at_level(logging.WARNING, logger="dartlab.viz"):
        emitChart({"title": "test", "categories": ["A"], "series": [{"data": [1]}]})
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" not in out
    assert "차트 거부" in caplog.text


def test_emit_chart_passes_with_charttype(capsys, caplog):
    """R32-1: chartType 있으면 통과."""
    import logging

    from dartlab.viz import emitChart

    with caplog.at_level(logging.WARNING, logger="dartlab.viz"):
        emitChart(
            {
                "chartType": "line",
                "title": "test",
                "categories": ["2022", "2023"],
                "series": [{"name": "A", "data": [100, 110]}],
                "evidenceIds": ["test:fixture"],
            }
        )
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" in out
    assert "차트 거부" not in caplog.text


def test_emit_chart_rejects_no_evidence(capsys, caplog):
    """evidenceBinding / evidenceIds 가 모두 비어 있으면 거부."""
    import logging

    from dartlab.viz import emitChart

    with caplog.at_level(logging.WARNING, logger="dartlab.viz"):
        emitChart(
            {
                "chartType": "line",
                "title": "no_evidence",
                "categories": ["2022", "2023"],
                "series": [{"name": "A", "data": [100, 110]}],
            }
        )
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" not in out
    assert "차트 거부" in caplog.text
    assert "evidenceBinding" in caplog.text


def test_emit_chart_passes_with_evidence_binding(capsys, caplog):
    """evidenceBinding 만 있어도 통과."""
    import logging

    from dartlab.viz import emitChart

    with caplog.at_level(logging.WARNING, logger="dartlab.viz"):
        emitChart(
            {
                "chartType": "line",
                "title": "with_binding",
                "categories": ["2022", "2023"],
                "series": [{"name": "A", "data": [100, 110]}],
                "evidenceBinding": {
                    "tableRef": "finance:IS:Y",
                    "source": "finance",
                    "stockCode": "005930",
                    "topic": "IS",
                },
            }
        )
    out = capsys.readouterr().out
    assert "DARTLAB_VIZ" in out
    assert "차트 거부" not in caplog.text
