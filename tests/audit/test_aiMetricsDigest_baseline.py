"""aiMetricsDigest baseline 비교 — 마스터 플랜 v2 트랙 6 PR-L5.

--baseline / --write-baseline 옵션 단위 검증. 실 trace 호출 0 (mock stats).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.audit.aiMetricsDigest import (
    _KPI_REGRESSION_TOLERANCE_PCT,
    _compareWithBaseline,
    _renderBaselineDiff,
    _statsToBaseline,
)

pytestmark = pytest.mark.unit


def _mkStats(turnsP95: float, firstChunkP95: float, turnElapsedP95: float, turnElapsedP50: float = 0.0) -> dict:
    return {
        "sessionCount": 5,
        "turnsPerSession": {"mean": 2.0, "p50": 2.0, "p95": turnsP95, "max": 3},
        "firstChunkMs": {"count": 5, "p50": 1000.0, "p95": firstChunkP95},
        "turnElapsedMs": {"count": 5, "p50": turnElapsedP50, "p95": turnElapsedP95},
        "toolTop20": [],
        "errors": {},
        "questionsSample": [],
    }


def test_statsToBaseline_extracts_4_kpis() -> None:
    stats = _mkStats(turnsP95=3.8, firstChunkP95=1500.0, turnElapsedP95=2800.0, turnElapsedP50=1500.0)
    baseline = _statsToBaseline(stats)
    assert baseline["sessionCount"] == 5
    assert "createdAt" in baseline
    assert baseline["kpis"]["turnsPerSession.p95"] == 3.8
    assert baseline["kpis"]["firstChunkMs.p95"] == 1500.0
    assert baseline["kpis"]["turnElapsedMs.p95"] == 2800.0
    assert baseline["kpis"]["turnElapsedMs.p50"] == 1500.0


def test_compareWithBaseline_no_regression_when_equal() -> None:
    stats = _mkStats(turnsP95=3.8, firstChunkP95=1500.0, turnElapsedP95=2800.0)
    baseline = _statsToBaseline(stats)
    rows, hasReg = _compareWithBaseline(stats, baseline)
    assert hasReg is False
    assert all(not r[4] for r in rows)


def test_compareWithBaseline_no_regression_when_improved() -> None:
    """latency 감소 (좋은 쪽) → 회귀 아님."""
    base_stats = _mkStats(turnsP95=4.0, firstChunkP95=2000.0, turnElapsedP95=3000.0)
    baseline = _statsToBaseline(base_stats)
    # 모두 -20% 개선
    improved = _mkStats(turnsP95=3.2, firstChunkP95=1600.0, turnElapsedP95=2400.0)
    rows, hasReg = _compareWithBaseline(improved, baseline)
    assert hasReg is False


def test_compareWithBaseline_regression_when_degraded_beyond_tolerance() -> None:
    """latency 25% 증가 → 회귀 (15% 임계 초과)."""
    base_stats = _mkStats(turnsP95=3.0, firstChunkP95=1500.0, turnElapsedP95=2000.0)
    baseline = _statsToBaseline(base_stats)
    degraded = _mkStats(turnsP95=3.0, firstChunkP95=1500.0, turnElapsedP95=2600.0)  # +30%
    rows, hasReg = _compareWithBaseline(degraded, baseline)
    assert hasReg is True
    regressed_row = [r for r in rows if r[4]]
    assert len(regressed_row) >= 1
    assert "turnElapsedMs.p95" in [r[0] for r in regressed_row]


def test_compareWithBaseline_within_tolerance_no_regression() -> None:
    """latency 10% 증가 → 임계 이내 → 회귀 아님."""
    base_stats = _mkStats(turnsP95=3.0, firstChunkP95=1500.0, turnElapsedP95=2000.0)
    baseline = _statsToBaseline(base_stats)
    near = _mkStats(turnsP95=3.0, firstChunkP95=1500.0, turnElapsedP95=2200.0)  # +10%
    rows, hasReg = _compareWithBaseline(near, baseline)
    assert hasReg is False


def test_compareWithBaseline_handles_missing_data() -> None:
    """현 측정값 None → skip (회귀 판단 불가)."""
    base_stats = _mkStats(turnsP95=3.0, firstChunkP95=1500.0, turnElapsedP95=2000.0)
    baseline = _statsToBaseline(base_stats)
    stats_no_first_chunk = _mkStats(turnsP95=3.0, firstChunkP95=0.0, turnElapsedP95=2000.0)
    stats_no_first_chunk["firstChunkMs"]["p95"] = None
    rows, hasReg = _compareWithBaseline(stats_no_first_chunk, baseline)
    # firstChunkMs.p95 는 비교 skip
    kpi_labels = [r[0] for r in rows]
    assert "firstChunkMs.p95" not in kpi_labels
    assert hasReg is False


def test_renderBaselineDiff_includes_kpi_rows() -> None:
    rows = [
        ("turnElapsedMs.p95", 2000.0, 2600.0, 30.0, True),
        ("firstChunkMs.p95", 1500.0, 1500.0, 0.0, False),
    ]
    text = _renderBaselineDiff(rows)
    assert "baseline 비교" in text
    assert "turnElapsedMs.p95" in text
    assert "+30.0%" in text


def test_renderBaselineDiff_empty_returns_placeholder() -> None:
    assert "baseline 비교 가능" in _renderBaselineDiff([])


def test_tolerance_is_15_pct() -> None:
    """회귀 임계 = ±15% — 변경 시 baseline 재측 동행 명시."""
    assert _KPI_REGRESSION_TOLERANCE_PCT == 15.0


def test_baseline_json_round_trip(tmp_path: Path) -> None:
    """baseline JSON write → read round-trip 일치."""
    stats = _mkStats(turnsP95=3.8, firstChunkP95=1500.0, turnElapsedP95=2800.0)
    baseline = _statsToBaseline(stats)
    out = tmp_path / "baseline.json"
    out.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["kpis"] == baseline["kpis"]
