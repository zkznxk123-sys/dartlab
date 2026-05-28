"""aiQualityRubric baseline 회귀 가드 — 마스터 플랜 v2 트랙 5 PR-Q3.

reportsToBaseline / compareReportsToBaseline / renderQualityBaselineDiff 단위. 실 ask 호출 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.audit.aiQualityRubric import (
    _QUALITY_REGRESSION_TOLERANCE_PCT,
    DimensionScore,
    ScoreReport,
    compareReportsToBaseline,
    renderQualityBaselineDiff,
    reportsToBaseline,
)

pytestmark = pytest.mark.unit


def _mkReport(
    goldenId: str,
    total: float,
    *,
    accuracy: float = 80.0,
    completeness: float = 80.0,
    toolSelection: float = 80.0,
    refsQuality: float = 80.0,
    latency: float = 80.0,
) -> ScoreReport:
    dims = {
        "accuracy": DimensionScore(name="accuracy", raw=accuracy, weighted=accuracy * 0.35, passed=True),
        "completeness": DimensionScore(
            name="completeness", raw=completeness, weighted=completeness * 0.20, passed=True
        ),
        "toolSelection": DimensionScore(
            name="toolSelection", raw=toolSelection, weighted=toolSelection * 0.20, passed=True
        ),
        "refsQuality": DimensionScore(name="refsQuality", raw=refsQuality, weighted=refsQuality * 0.15, passed=True),
        "latency": DimensionScore(name="latency", raw=latency, weighted=latency * 0.10, passed=True),
    }
    return ScoreReport(
        goldenId=goldenId,
        totalScore=total,
        passed=total >= 70.0 and accuracy >= 60.0,
        dimensions=dims,
        answerLen=200,
        elapsedSec=10.0,
        error=None,
    )


def test_reportsToBaseline_averages_dimensions() -> None:
    reports = [_mkReport("q1", 80.0, accuracy=85.0), _mkReport("q2", 70.0, accuracy=75.0)]
    baseline = reportsToBaseline(reports)
    assert baseline["itemCount"] == 2
    assert baseline["averages"]["totalScore"] == 75.0
    assert baseline["averages"]["accuracy"] == 80.0
    assert "createdAt" in baseline
    assert "q1" in baseline["perItem"]


def test_reportsToBaseline_empty() -> None:
    baseline = reportsToBaseline([])
    assert baseline["itemCount"] == 0
    assert baseline["averages"]["totalScore"] == 0.0


def test_reportsToBaseline_skips_errored() -> None:
    """error 가 있는 report 는 평균 산정에서 제외."""
    err_report = ScoreReport(
        goldenId="qe",
        totalScore=0.0,
        passed=False,
        dimensions={},
        answerLen=0,
        elapsedSec=0.0,
        error="some error",
    )
    reports = [_mkReport("q1", 80.0), err_report]
    baseline = reportsToBaseline(reports)
    assert baseline["itemCount"] == 1
    assert baseline["averages"]["totalScore"] == 80.0


def test_compareReportsToBaseline_no_regression_when_equal() -> None:
    reports = [_mkReport("q1", 80.0)]
    base = reportsToBaseline(reports)
    rows, hasReg = compareReportsToBaseline(reports, base)
    assert hasReg is False
    assert all(not r[4] for r in rows)


def test_compareReportsToBaseline_no_regression_when_improved() -> None:
    base_reports = [_mkReport("q1", 70.0, accuracy=70.0)]
    base = reportsToBaseline(base_reports)
    cur_reports = [_mkReport("q1", 85.0, accuracy=85.0)]
    rows, hasReg = compareReportsToBaseline(cur_reports, base)
    assert hasReg is False


def test_compareReportsToBaseline_regression_when_drop_beyond_tolerance() -> None:
    """totalScore -15% → 회귀 (임계 -10% 초과)."""
    base_reports = [_mkReport("q1", 80.0)]
    base = reportsToBaseline(base_reports)
    cur_reports = [_mkReport("q1", 60.0)]  # -25%
    rows, hasReg = compareReportsToBaseline(cur_reports, base)
    assert hasReg is True
    regressed_labels = [r[0] for r in rows if r[4]]
    assert "totalScore" in regressed_labels


def test_compareReportsToBaseline_within_tolerance_no_regression() -> None:
    """-5% → 임계 이내 → 회귀 아님."""
    base_reports = [_mkReport("q1", 80.0)]
    base = reportsToBaseline(base_reports)
    cur_reports = [_mkReport("q1", 76.0)]  # -5%
    rows, hasReg = compareReportsToBaseline(cur_reports, base)
    assert hasReg is False


def test_compareReportsToBaseline_skip_zero_baseline() -> None:
    """baseline=0 차원 (미측정) → 비교 skip."""
    base = {
        "averages": {
            "totalScore": 0.0,
            "accuracy": 0.0,
            "completeness": 0.0,
            "toolSelection": 0.0,
            "refsQuality": 0.0,
            "latency": 0.0,
        }
    }
    cur_reports = [_mkReport("q1", 80.0)]
    rows, hasReg = compareReportsToBaseline(cur_reports, base)
    assert hasReg is False
    assert rows == []


def test_renderQualityBaselineDiff_includes_rows() -> None:
    rows = [
        ("totalScore", 80.0, 65.0, -18.75, True),
        ("accuracy", 80.0, 80.0, 0.0, False),
    ]
    text = renderQualityBaselineDiff(rows)
    assert "baseline 비교" in text
    assert "totalScore" in text
    assert "-18.8%" in text or "-18.7%" in text


def test_renderQualityBaselineDiff_empty() -> None:
    assert "비교 가능 차원 0" in renderQualityBaselineDiff([])


def test_tolerance_is_10_pct() -> None:
    """quality 회귀 임계 = -10% — 변경 시 baseline 재측 동행 명시."""
    assert _QUALITY_REGRESSION_TOLERANCE_PCT == 10.0


def test_baseline_json_template_present() -> None:
    """tests/audit/_baselines/aiQualityV2.json 템플릿 존재 + schema 키 확인."""
    p = Path(__file__).parent / "_baselines" / "aiQualityV2.json"
    assert p.exists(), "baseline 템플릿 누락"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "averages" in data
    for key in ("totalScore", "accuracy", "completeness", "toolSelection", "refsQuality", "latency"):
        assert key in data["averages"]


def test_baseline_round_trip(tmp_path: Path) -> None:
    """reportsToBaseline → JSON write → read → compare round-trip."""
    reports = [_mkReport("q1", 80.0), _mkReport("q2", 75.0)]
    baseline = reportsToBaseline(reports)
    out = tmp_path / "baseline.json"
    out.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["averages"]["totalScore"] == baseline["averages"]["totalScore"]
    rows, hasReg = compareReportsToBaseline(reports, loaded)
    assert hasReg is False
