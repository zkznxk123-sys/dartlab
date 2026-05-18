"""tests/audit/mutationSmoke.py 자체 회귀 — Track 5 (Windows 호환 mutation gate).

본 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 5.

mutationSmoke 가 7 패턴 100% killed 를 강제 — oracle test 의 *실 회귀 차단력*
을 측정하는 단일 표면. 본 self-test 는 그 게이트가 동작하는지 검증.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_SMOKE_PATH = _REPO / "scripts" / "audit" / "mutationSmoke.py"


def _loadSmokeModule():
    spec = importlib.util.spec_from_file_location("mutationSmoke", _SMOKE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mutationSmoke"] = module
    spec.loader.exec_module(module)
    return module


def test_smoke_module_loads() -> None:
    smoke = _loadSmokeModule()
    assert hasattr(smoke, "runAll")
    assert hasattr(smoke, "_runOne")
    assert hasattr(smoke, "_MUTATIONS")


def test_mutations_target_exist() -> None:
    """모든 mutation 의 target file 존재."""
    smoke = _loadSmokeModule()
    for mut in smoke._MUTATIONS:
        assert mut.target.exists(), f"mutation target 없음: {mut.target}"


def test_mutations_pattern_present_in_target() -> None:
    """mutation 의 find pattern 이 실제 target 파일에 존재 — 변형 가능 가드."""
    smoke = _loadSmokeModule()
    for mut in smoke._MUTATIONS:
        content = mut.target.read_text(encoding="utf-8")
        assert mut.find in content, f"mutation pattern not in {mut.target.name}: {mut.find[:60]}"


def test_report_mutation_score_calculation() -> None:
    """Report.mutation_score = killed / (killed + survived). skip 제외."""
    smoke = _loadSmokeModule()
    Report = smoke.Report
    Result = smoke.Result

    report = Report()
    report.results = [
        Result(mutation="m1", status="killed"),
        Result(mutation="m2", status="killed"),
        Result(mutation="m3", status="survived"),
        Result(mutation="m4", status="skip"),
    ]
    report.killed = 2
    report.survived = 1
    report.skipped = 1
    report.total = 4

    assert report.mutation_score == pytest.approx(2 / 3)


def test_report_mutation_score_all_killed() -> None:
    """모두 killed → score 1.0."""
    smoke = _loadSmokeModule()
    Report = smoke.Report
    Result = smoke.Result

    report = Report()
    report.killed = 5
    report.survived = 0
    report.skipped = 0
    report.total = 5
    report.results = [Result(mutation=f"m{i}", status="killed") for i in range(5)]

    assert report.mutation_score == 1.0


def test_report_mutation_score_zero_applied() -> None:
    """모두 skip → score 1.0 (분모 0 안전)."""
    smoke = _loadSmokeModule()
    Report = smoke.Report
    Result = smoke.Result

    report = Report()
    report.killed = 0
    report.survived = 0
    report.skipped = 3
    report.total = 3
    report.results = [Result(mutation=f"m{i}", status="skip") for i in range(3)]

    assert report.mutation_score == 1.0


def test_mutations_count_at_least_seven() -> None:
    """본 PR 도입 시점 mutation 7 종 — 후속 증설 시 감소 가드."""
    smoke = _loadSmokeModule()
    assert len(smoke._MUTATIONS) >= 7
