"""aiAbHarness A/B 평가 단위 — 마스터 플랜 v2 트랙 8 PR-T3.

strictQualityScore + runAbBench + renderAbReport. 실 provider 호출 0 (mock askFn 만).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests._attempts.aiAbHarness import (
    renderAbReport,
    runAbBench,
    strictQualityScore,
)

pytestmark = pytest.mark.unit


# ────────────────────────── strictQualityScore ──────────────────────────


def test_strictQualityScore_empty() -> None:
    assert strictQualityScore("") == 0.0
    assert strictQualityScore("   ") == 0.0


def test_strictQualityScore_minimal_score() -> None:
    """짧고 키워드 / 숫자 없음 → 키워드 30 + 숫자 50 = 80 (default 만점 base)."""
    score = strictQualityScore("hi")
    assert score == 80.0  # 길이 20 점 빠짐


def test_strictQualityScore_keywords_full_match() -> None:
    text = (
        "삼성전자 ROE 는 8.94% 입니다. 양호한 수준의 자기자본 수익률을 보이며 지속 가능한 성장 기반을 다지고 있습니다."
    )
    assert len(text) >= 50
    score = strictQualityScore(text, expectedKeywords=("ROE", "삼성전자"))
    # 길이 20 + 키워드 30 + 숫자 50 = 100
    assert score == 100.0


def test_strictQualityScore_keywords_partial() -> None:
    text = "삼성전자 ROE 는 8% 입니다."
    score = strictQualityScore(text, expectedKeywords=("ROE", "PER", "BPS"))
    # 1/3 매칭 → 30 × 0.33 = 10
    assert 50.0 <= score <= 80.0


def test_strictQualityScore_number_within_tolerance() -> None:
    text = "ROE 는 8.94% 입니다."
    score = strictQualityScore(text, expectedNumber=8.94)
    assert score >= 70.0


def test_strictQualityScore_number_outside_tolerance() -> None:
    text = "ROE 는 5.0% 입니다."
    score = strictQualityScore(text, expectedNumber=8.94)
    # 숫자 50 점 받지 못 함
    assert score < 60.0


# ────────────────────────── runAbBench ──────────────────────────


def _mkAsk(answers: dict[str, str], delaySec: float = 0.0) -> Callable[[str], str]:
    def ask(q: str) -> str:
        if delaySec:
            import time

            time.sleep(delaySec)
        return answers.get(q, "")

    return ask


def test_runAbBench_basic_summary() -> None:
    items = [
        {
            "id": "q1",
            "question": "ROE",
            "expectedNumber": 8.94,
            "expectedKeywords": ("ROE",),
        }
    ]
    ask_a = _mkAsk({"ROE": "ROE 5.0% 짧음"})  # 부정확 숫자
    ask_b = _mkAsk({"ROE": "삼성전자 ROE 는 8.94% 입니다. 정상 범위."})  # 정확
    stats = runAbBench(askA=ask_a, askB=ask_b, items=items, nRuns=2)
    assert stats["n"] == 1
    assert stats["nRuns"] == 2
    assert stats["B"]["scoreMean"] > stats["A"]["scoreMean"]
    assert stats["delta"]["scoreDelta"] > 0


def test_runAbBench_perItem_breakdown() -> None:
    items = [{"id": "q1", "question": "Q", "expectedKeywords": ()}]
    ask = _mkAsk({"Q": "답변 충분히 길게 sample text 응답입니다."})
    stats = runAbBench(askA=ask, askB=ask, items=items, nRuns=1)
    assert len(stats["perItem"]) == 1
    assert stats["perItem"][0]["id"] == "q1"
    assert "scoreMean" in stats["perItem"][0]["A"]


def test_runAbBench_empty_items() -> None:
    ask = _mkAsk({})
    stats = runAbBench(askA=ask, askB=ask, items=[], nRuns=1)
    assert stats["n"] == 0
    assert stats["A"]["scoreMean"] == 0.0


def test_runAbBench_ask_exception_returns_zero_score() -> None:
    """askFn 예외 → score 0 (전체 harness crash 0)."""

    def ask_err(_q: str) -> str:
        raise RuntimeError("provider failure")

    items = [{"id": "q1", "question": "Q", "expectedKeywords": ("답변",)}]
    ask_ok = _mkAsk({"Q": "답변 길게 sample text 응답 50자 이상 sample sample sample."})
    stats = runAbBench(askA=ask_err, askB=ask_ok, items=items, nRuns=1)
    # ask_err 가 ERROR 문자열 반환 → 키워드 답변 미매칭. ask_ok 는 매칭.
    assert stats["A"]["scoreMean"] < stats["B"]["scoreMean"]


# ────────────────────────── renderAbReport ──────────────────────────


def test_renderAbReport_success_threshold() -> None:
    stats = {
        "n": 5,
        "nRuns": 3,
        "A": {"scoreMean": 60.0, "latencyP50": 5.0, "latencyMean": 5.0},
        "B": {"scoreMean": 75.0, "latencyP50": 5.0, "latencyMean": 5.0},
        "delta": {"scoreDelta": 15.0, "latencyRatio": 1.0},
    }
    text = renderAbReport(stats)
    assert "A/B Bench" in text
    assert "✅" in text  # +15 ≥ +10 AND ratio 1.0 ≤ 1.1


def test_renderAbReport_failure_threshold() -> None:
    stats = {
        "n": 5,
        "nRuns": 3,
        "A": {"scoreMean": 70.0, "latencyP50": 5.0, "latencyMean": 5.0},
        "B": {"scoreMean": 75.0, "latencyP50": 8.0, "latencyMean": 8.0},
        "delta": {"scoreDelta": 5.0, "latencyRatio": 1.6},
    }
    text = renderAbReport(stats)
    assert "❌" in text  # score 5 < 10 OR ratio 1.6 > 1.1


def test_renderAbReport_includes_columns() -> None:
    stats = {
        "n": 1,
        "nRuns": 1,
        "A": {"scoreMean": 50.0, "latencyP50": 1.0, "latencyMean": 1.0},
        "B": {"scoreMean": 80.0, "latencyP50": 1.0, "latencyMean": 1.0},
        "delta": {"scoreDelta": 30.0, "latencyRatio": 1.0},
    }
    text = renderAbReport(stats)
    assert "score mean" in text
    assert "latency p50" in text
    assert "+30.0" in text
