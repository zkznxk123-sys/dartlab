"""엄격 quality rubric 단위 테스트 — 마스터 플랜 v2 트랙 5 PR-Q1.

mock TraceEvent 시퀀스 + mock 답변 → 5 차원 score 검증. 외부 LLM 호출 0.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dartlab.ai.contracts import TraceEvent
from tests.audit._aiQualityGoldenV2 import _GOLDEN_V2
from tests.audit.aiQualityRubric import (
    DimensionScore,
    ScoreReport,
    _scoreAccuracy,
    _scoreCompleteness,
    _scoreLatency,
    _scoreRefsQuality,
    _scoreToolSelection,
    evaluateBatch,
    evaluateStrict,
    renderRubricReport,
)

pytestmark = pytest.mark.unit


def _mkTraceEvent(kind: str, data: dict, ts_offset_sec: float = 0.0) -> TraceEvent:
    base = dt.datetime(2026, 5, 28, 12, 0, 0)
    ts = (base + dt.timedelta(seconds=ts_offset_sec)).isoformat()
    return TraceEvent(kind=kind, data=data, ts=ts)


# ── _scoreAccuracy ──


def test_scoreAccuracy_no_checks_returns_vacuous_100() -> None:
    """numericChecks 빈 list → vacuous 100 (passed)."""
    d = _scoreAccuracy({}, "any answer", {})
    assert d.raw == 100.0
    assert d.passed is True


def test_scoreAccuracy_pattern_match_within_tolerance() -> None:
    """답변에 8.94% → groundTruth 8.94 와 일치 → 100."""
    spec = {
        "numericChecks": [
            {
                "label": "samsungRoe",
                "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                "groundTruth": 8.94,
                "tolerancePct": 5.0,
            }
        ]
    }
    d = _scoreAccuracy(spec, "삼성전자 ROE 는 8.94% 다.", {})
    assert d.raw == 100.0
    assert d.passed is True
    assert d.details["checks"][0]["status"] == "ok"


def test_scoreAccuracy_pattern_drift_exceeds_tolerance() -> None:
    """답변 12.0% vs truth 8.94 → 5% 초과 → drift."""
    spec = {
        "numericChecks": [
            {
                "label": "samsungRoe",
                "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                "groundTruth": 8.94,
                "tolerancePct": 5.0,
            }
        ]
    }
    d = _scoreAccuracy(spec, "ROE 12.0%", {})
    assert d.raw == 0.0
    assert d.passed is False
    assert d.details["checks"][0]["status"] == "drift"


def test_scoreAccuracy_pattern_not_found() -> None:
    """답변에 숫자 없음 → notFound."""
    spec = {
        "numericChecks": [
            {
                "label": "samsungRoe",
                "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                "groundTruth": 8.94,
                "tolerancePct": 5.0,
            }
        ]
    }
    d = _scoreAccuracy(spec, "ROE 숫자 미반환", {})
    assert d.raw == 0.0
    assert d.details["checks"][0]["status"] == "notFound"


def test_scoreAccuracy_groundTruthOverride_used() -> None:
    """gt override > spec.groundTruth."""
    spec = {
        "numericChecks": [
            {
                "label": "samsungRoe",
                "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                "groundTruth": 8.94,
                "tolerancePct": 5.0,
            }
        ]
    }
    # 답변 12.0% — override truth 12.0 시 일치
    d = _scoreAccuracy(spec, "ROE 12.0%", {"samsungRoe": 12.0})
    assert d.raw == 100.0


# ── _scoreCompleteness ──


def test_scoreCompleteness_all_required_matched() -> None:
    spec = {"requiredSlots": ["삼성전자", "ROE"]}
    d = _scoreCompleteness(spec, "삼성전자 ROE 분석")
    assert d.raw == 100.0
    assert d.passed is True


def test_scoreCompleteness_forbidden_penalty() -> None:
    spec = {"requiredSlots": ["삼성전자"], "forbiddenSlots": ["오류가 발생"]}
    d = _scoreCompleteness(spec, "삼성전자 분석 중 오류가 발생했다")
    # 100 - 20 = 80
    assert d.raw == 80.0


def test_scoreCompleteness_missing_slots_partial() -> None:
    spec = {"requiredSlots": ["삼성전자", "SK하이닉스", "비교"]}
    d = _scoreCompleteness(spec, "삼성전자 단독 분석")
    # 1/3 = 33.33
    assert abs(d.raw - 33.33) < 0.1
    assert d.passed is False


# ── _scoreToolSelection ──


def test_scoreToolSelection_subset_full_match() -> None:
    spec = {"expectedTools": ["DCFValuation"], "matchMode": "subset"}
    d = _scoreToolSelection(spec, ["DCFValuation", "ReadSkill"])
    assert d.raw == 100.0


def test_scoreToolSelection_subset_partial() -> None:
    spec = {"expectedTools": ["DCFValuation", "PeerCompareN"], "matchMode": "subset"}
    d = _scoreToolSelection(spec, ["DCFValuation"])
    assert d.raw == 50.0


def test_scoreToolSelection_forbidden_penalty() -> None:
    spec = {
        "expectedTools": ["DCFValuation"],
        "forbiddenTools": ["RunPython"],
        "matchMode": "subset",
    }
    d = _scoreToolSelection(spec, ["DCFValuation", "RunPython"])
    # 100 - 50 = 50
    assert d.raw == 50.0


def test_scoreToolSelection_exact_mode() -> None:
    spec = {"expectedTools": ["A", "B"], "matchMode": "exact"}
    d = _scoreToolSelection(spec, ["A", "B", "C"])
    assert d.raw == 0.0


# ── _scoreRefsQuality ──


def test_scoreRefsQuality_meets_min_and_kind() -> None:
    spec = {"minRefCount": 1, "expectedKinds": ["tableRef"]}
    refs = [{"kind": "tableRef", "id": "x"}]
    d = _scoreRefsQuality(spec, refs)
    assert d.raw == 100.0


def test_scoreRefsQuality_kind_mismatch() -> None:
    spec = {"minRefCount": 1, "expectedKinds": ["tableRef"]}
    refs = [{"kind": "valueRef"}]
    d = _scoreRefsQuality(spec, refs)
    # countRaw=100, kindRaw=0 → 50
    assert d.raw == 50.0


def test_scoreRefsQuality_count_below_min() -> None:
    spec = {"minRefCount": 2, "expectedKinds": []}
    refs = [{"kind": "tableRef"}]
    d = _scoreRefsQuality(spec, refs)
    # countRaw=50, kindRaw=100 → 75
    assert d.raw == 75.0


# ── _scoreLatency ──


def test_scoreLatency_within_budget() -> None:
    spec = {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0}
    d = _scoreLatency(spec, totalElapsedSec=30.0, firstChunkMs=2000.0)
    # latTotal=100, latFirst=100 → 100
    assert d.raw == 100.0


def test_scoreLatency_first_chunk_unknown_neutral() -> None:
    spec = {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0}
    d = _scoreLatency(spec, totalElapsedSec=30.0, firstChunkMs=None)
    # latTotal=100, latFirst=50 (neutral) → 75
    assert d.raw == 75.0


def test_scoreLatency_exceeds_budget() -> None:
    spec = {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0}
    d = _scoreLatency(spec, totalElapsedSec=120.0, firstChunkMs=3000.0)
    # latTotal=0 (excess=60), latFirst=100 → 50
    assert d.raw == 50.0


# ── evaluateStrict E2E ──


def test_evaluateStrict_passes_full_rubric() -> None:
    """모든 차원 통과 → totalScore ≥ 70, passed=True."""
    golden = {
        "id": "q1_test",
        "question": "삼성전자 ROE",
        "rubric": {
            "accuracy": {
                "numericChecks": [
                    {
                        "label": "roe",
                        "patternRegex": r"ROE[^0-9\-]{0,20}(-?\d+\.?\d*)\s*%",
                        "groundTruth": 8.94,
                        "tolerancePct": 5.0,
                    }
                ]
            },
            "completeness": {"requiredSlots": ["삼성전자", "ROE"]},
            "toolSelection": {"expectedTools": ["EngineCall"], "matchMode": "subset"},
            "refsQuality": {"minRefCount": 1, "expectedKinds": ["tableRef"]},
            "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
        },
    }
    events = [
        _mkTraceEvent("first_chunk_ms", {"ms": 1500}, ts_offset_sec=0.0),
        _mkTraceEvent("tool_start", {"tool": "EngineCall"}, ts_offset_sec=1.0),
        _mkTraceEvent(
            "done",
            {"refs": [{"kind": "tableRef", "id": "t1"}]},
            ts_offset_sec=10.0,
        ),
    ]
    answer = "삼성전자 ROE 는 8.94% 다."
    rpt = evaluateStrict(goldenItem=golden, answerText=answer, traceEvents=events)
    assert rpt.passed is True
    assert rpt.totalScore >= 70.0
    assert "accuracy" in rpt.dimensions


def test_evaluateStrict_fails_accuracy_hard_gate() -> None:
    """accuracy.raw < 60 → 총점 70 넘어도 passed=False (hard gate)."""
    golden = {
        "id": "q_fail_acc",
        "question": "?",
        "rubric": {
            "accuracy": {
                "numericChecks": [
                    {
                        "label": "x",
                        "patternRegex": r"VALUE[^0-9]*(\d+)",
                        "groundTruth": 100.0,
                        "tolerancePct": 5.0,
                    }
                ]
            },
            "completeness": {"requiredSlots": []},
            "toolSelection": {"expectedTools": []},
            "refsQuality": {"minRefCount": 0, "expectedKinds": []},
            "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
        },
    }
    # 답변에 VALUE 500 → drift (truth 100)
    events = [_mkTraceEvent("done", {"refs": []})]
    rpt = evaluateStrict(goldenItem=golden, answerText="VALUE 500", traceEvents=events)
    assert rpt.dimensions["accuracy"].raw == 0.0
    # 다른 차원 모두 vacuous 100 → 총점 약 65 — total ≥ 70 도 미달 + acc hard gate
    assert rpt.passed is False


def test_evaluateStrict_uses_done_event_refs() -> None:
    """done event 의 refs 가 refsQuality 입력."""
    golden = {
        "id": "q_refs",
        "question": "?",
        "rubric": {
            "accuracy": {"numericChecks": []},
            "completeness": {"requiredSlots": []},
            "toolSelection": {"expectedTools": []},
            "refsQuality": {"minRefCount": 2, "expectedKinds": ["valueRef"]},
            "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
        },
    }
    events = [_mkTraceEvent("done", {"refs": [{"kind": "valueRef"}, {"kind": "valueRef"}]})]
    rpt = evaluateStrict(goldenItem=golden, answerText="x", traceEvents=events)
    assert rpt.dimensions["refsQuality"].raw == 100.0


# ── renderRubricReport ──


def test_renderRubricReport_includes_summary() -> None:
    reports = [
        ScoreReport(
            goldenId="q1",
            totalScore=85.0,
            passed=True,
            dimensions={
                k: DimensionScore(k, 80.0, 80.0 * 0.2, True, {})
                for k in ("accuracy", "completeness", "toolSelection", "refsQuality", "latency")
            },
            answerLen=100,
            elapsedSec=30.0,
        )
    ]
    text = renderRubricReport(reports)
    assert "strict quality rubric" in text
    assert "q1" in text
    assert "85.0%" in text


def test_renderRubricReport_empty_returns_placeholder() -> None:
    assert "결과 없음" in renderRubricReport([])


# ── evaluateBatch ──


def test_evaluateBatch_with_mock_askFn() -> None:
    """mock askFn → ScoreReport list 반환 (외부 LLM 호출 0)."""
    golden = [
        {
            "id": "q_mock",
            "question": "test",
            "rubric": {
                "accuracy": {"numericChecks": []},
                "completeness": {"requiredSlots": ["test"]},
                "toolSelection": {"expectedTools": []},
                "refsQuality": {"minRefCount": 0, "expectedKinds": []},
                "latency": {"maxTotalSec": 60.0, "maxFirstChunkMs": 5000.0},
            },
        }
    ]

    def mockAsk(question: str, *, events: bool = False):
        yield TraceEvent("chunk", {"text": "test 답변"}, ts="2026-05-28T12:00:00")
        yield TraceEvent("done", {"refs": []}, ts="2026-05-28T12:00:05")

    reports = evaluateBatch(goldenItems=golden, askFn=mockAsk)
    assert len(reports) == 1
    assert reports[0].goldenId == "q_mock"
    # completeness 통과 — "test" 매칭
    assert reports[0].dimensions["completeness"].raw == 100.0


def test_evaluateBatch_handles_askFn_exception() -> None:
    """askFn 예외 → ScoreReport 의 error 필드 채움, 다른 item 계속."""
    golden = [{"id": "q_err", "question": "?", "rubric": {}}]

    def boomAsk(question: str, *, events: bool = False):
        raise RuntimeError("provider down")

    reports = evaluateBatch(goldenItems=golden, askFn=boomAsk)
    assert len(reports) == 1
    assert reports[0].error is not None
    assert "RuntimeError" in reports[0].error


# ── golden v2 schema validation ──


def test_goldenV2_has_10_items() -> None:
    assert len(_GOLDEN_V2) == 10


def test_goldenV2_each_item_has_required_keys() -> None:
    for item in _GOLDEN_V2:
        assert "id" in item
        assert "question" in item
        assert "rubric" in item
        rubric = item["rubric"]
        for dim in ("accuracy", "completeness", "toolSelection", "refsQuality", "latency"):
            assert dim in rubric, f"{item['id']} missing rubric.{dim}"
