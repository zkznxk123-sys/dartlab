"""recipes/runs.py + scorecard.py + drift.py unit — append-only Parquet 라운드트립 + 6 신호 산출.

graph node 없음. ValidateRecipe 가 호출하는 stateless 라이브러리만 검증.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dartlab.ai.recipes import (
    RecipeRunRecord,
    ScorecardThresholds,
    appendRun,
    computeScorecard,
    detectDrift,
    loadRuns,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def runsDir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path))
    return tmp_path


def _make_record(skillId: str = "recipes.x", **overrides) -> RecipeRunRecord:
    base = {
        "runId": "r1",
        "skillId": skillId,
        "target": "005930",
        "market": "KR",
        "ok": True,
        "evidenceKinds": ["skillRef", "tableRef", "valueRef", "dateRef"],
        "headlineMetric": "consensus",
        "headlineValue": "0.5",
        "durationMs": 120,
        "refs": ["skill:x", "table:bs", "value:v", "date:2025"],
        "errorClass": None,
        "asOf": "2025-12-31",
        "capturedAt": "2026-05-09T15:30:00+00:00",
    }
    base.update(overrides)
    return RecipeRunRecord(**base)


def test_append_run_creates_file_then_appends(runsDir: Path) -> None:
    rec = _make_record()
    path = appendRun(rec)
    assert path.exists()
    df_first = loadRuns(rec.skillId)
    assert df_first.height == 1

    rec2 = _make_record(runId="r2", target="000660", headlineValue="0.7")
    appendRun(rec2)
    df_second = loadRuns(rec.skillId)
    assert df_second.height == 2
    assert sorted(df_second["runId"].to_list()) == ["r1", "r2"]


def test_load_runs_returns_empty_for_unknown_skill(runsDir: Path) -> None:
    df = loadRuns("recipes.quality.nonexistent")
    assert df.is_empty()
    assert "runId" in df.columns


def test_scorecard_pass_rate_and_completeness(runsDir: Path) -> None:
    appendRun(_make_record(runId="r1", target="A", headlineValue="0.4", ok=True))
    appendRun(_make_record(runId="r2", target="B", headlineValue="0.6", ok=True))
    appendRun(_make_record(runId="r3", target="C", headlineValue="0.5", ok=True))
    appendRun(_make_record(runId="r4", target="D", headlineValue="0.7", ok=False, evidenceKinds=["skillRef"]))

    runs = loadRuns("recipes.x")
    sc = computeScorecard(
        "recipes.x",
        runs,
        requiredEvidence=["skillRef", "tableRef", "valueRef", "dateRef"],
        expectedNovelty=["consensus"],
        falsifierPresent=True,
    )
    assert sc.runCount == 4
    assert sc.executionPassRate == pytest.approx(3 / 4)
    # 3 ok runs → completeness 1.0; 1 fail run → 0.25 (1/4 kinds 등장).
    expected_completeness = (1.0 + 1.0 + 1.0 + 0.25) / 4
    assert sc.evidenceCompleteness == pytest.approx(expected_completeness)
    # cross-target stability — 4 target std-dev > 0
    assert sc.crossTargetStability > 0
    assert sc.novelty
    assert sc.falsifierEvaluated


def test_scorecard_meets_thresholds_only_when_all_signals_pass(runsDir: Path) -> None:
    # 5 target × 모든 ok=True × 다양한 headline.
    for i, code in enumerate(["005930", "000660", "035420", "051910", "055550"]):
        appendRun(_make_record(runId=f"r{i}", target=code, headlineValue=str(0.3 + i * 0.15), ok=True))
    runs = loadRuns("recipes.x")
    sc = computeScorecard(
        "recipes.x",
        runs,
        requiredEvidence=["skillRef", "tableRef", "valueRef", "dateRef"],
        expectedNovelty=["consensus"],
        falsifierPresent=True,
    )
    assert sc.executionPassRate == 1.0
    assert sc.evidenceCompleteness == 1.0
    # cross-target std-dev — 0.3..0.9 → 표본 stdev ~ 0.21, 임계 [0.10, 0.50] 통과.
    assert (
        ScorecardThresholds().minCrossTargetStability
        <= sc.crossTargetStability
        <= ScorecardThresholds().maxCrossTargetStability
    )
    assert sc.meetsThresholds


def test_scorecard_fails_threshold_when_no_novelty(runsDir: Path) -> None:
    appendRun(_make_record(runId="r1", target="A", headlineValue="0.5"))
    runs = loadRuns("recipes.x")
    sc = computeScorecard(
        "recipes.x",
        runs,
        requiredEvidence=["skillRef"],
        expectedNovelty=[],  # 빈 → novelty=False
        falsifierPresent=True,
    )
    assert not sc.novelty
    assert not sc.meetsThresholds


def test_scorecard_handles_empty_runs(runsDir: Path) -> None:
    sc = computeScorecard(
        "recipes.empty",
        loadRuns("recipes.empty"),
        requiredEvidence=["skillRef"],
        expectedNovelty=["x"],
        falsifierPresent=True,
    )
    assert sc.runCount == 0
    assert not sc.meetsThresholds
    assert "no runs" in sc.notes


def test_drift_suggests_deprecate_on_high_schema_error_rate(runsDir: Path) -> None:
    # 30 baseline ok + 10 recent KeyError
    for i in range(30):
        appendRun(
            _make_record(
                runId=f"b{i}",
                target=f"C{i}",
                headlineValue=str(0.5),
                ok=True,
                capturedAt=f"2026-01-{(i % 28) + 1:02d}T00:00:00+00:00",
            )
        )
    for i in range(10):
        appendRun(
            _make_record(
                runId=f"r{i}",
                target=f"R{i}",
                headlineValue="",
                ok=False,
                errorClass="KeyError",
                capturedAt=f"2026-05-{i + 1:02d}T00:00:00+00:00",
            )
        )
    runs = loadRuns("recipes.x")
    report = detectDrift("recipes.x", runs, recentN=10, baselineN=30)
    assert report.schemaDriftRate == 1.0
    assert report.suggestDeprecate


def test_drift_returns_pending_when_run_count_low(runsDir: Path) -> None:
    for i in range(3):
        appendRun(_make_record(runId=f"r{i}"))
    runs = loadRuns("recipes.x")
    report = detectDrift("recipes.x", runs, recentN=10, baselineN=30)
    assert not report.suggestDeprecate
    assert any("진단 보류" in note for note in report.notes)
