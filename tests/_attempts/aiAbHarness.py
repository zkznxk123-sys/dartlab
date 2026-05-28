"""provider A/B 비교 harness — 마스터 플랜 v2 트랙 8 PR-T3.

base provider vs fine-tuned provider (또는 두 임의 provider) 동일 질문 N 회 실행 →
strictQualityScore (PR-Q1 rubric) + latency 비교 → markdown 보고. 운영자가 SFT/DPO
학습 후 효과 정량 확인용.

진입점 (CLI):
    uv run python -X utf8 tests/_attempts/aiAbHarness.py \\
        --providerA "ollama:qwen2.5:7b-instruct-q4_K_M" \\
        --providerB "ollama:dartlab-ft:v1" \\
        --n-runs 3

성공 임계 (PR-T3 의 docstring):
    strictQualityScore (B) ≥ strictQualityScore (A) + 10 점
    AND latency p50 (B) ≤ latency p50 (A) × 1.1
"""

from __future__ import annotations

import os
import statistics
import time
from collections.abc import Callable
from typing import Any

# trace dump 보장 — A/B 두 측정 모두 trace 누적해서 후속 분석 가능.
os.environ.setdefault("DARTLAB_AI_TRACE_DUMP", "1")


def strictQualityScore(
    answerText: str, *, expectedNumber: float | None = None, expectedKeywords: tuple[str, ...] = ()
) -> float:
    """answer 1 건의 빠른 strict score (0~100) — A/B harness 안 quick eval.

    Sig:
        strictQualityScore(answerText, *, expectedNumber=None, expectedKeywords=()) -> float
    Args:
        answerText: 측정할 응답.
        expectedNumber: 정답 숫자 (있으면 ±5% 매칭 시 50 점 base).
        expectedKeywords: 필수 키워드 — 누락 비율만큼 감점.
    Returns:
        0~100 점 (단순 합산).
    Note:
        본 함수는 PR-Q1 의 evaluateStrict 의 *축약* 버전 — A/B harness 용. 정식 strict 측정은
        tests/_attempts/aiQualityBench.py 의 strict mode 사용.
    """
    if not answerText or not answerText.strip():
        return 0.0
    score = 0.0
    # 1) 길이 충분 (50 자+) → 20 점
    if len(answerText) >= 50:
        score += 20.0
    # 2) 키워드 매칭 비율 × 30 점
    if expectedKeywords:
        hits = sum(1 for k in expectedKeywords if k in answerText)
        score += 30.0 * (hits / len(expectedKeywords))
    else:
        score += 30.0
    # 3) 숫자 매칭 (있으면 ±5% 내 → 50 점)
    if expectedNumber is not None:
        import re

        m = re.findall(r"-?\d+\.?\d*", answerText)
        if m:
            try:
                vals = [float(v) for v in m]
                tol = abs(expectedNumber) * 0.05
                if any(abs(v - expectedNumber) <= tol for v in vals):
                    score += 50.0
            except ValueError:
                pass
    else:
        score += 50.0
    return min(100.0, score)


def _runOne(askFn: Callable[[str], str], question: str) -> tuple[str, float]:
    """askFn 1 회 호출 + elapsed sec 반환."""
    start = time.monotonic()
    try:
        out = askFn(question)
    except Exception as exc:  # noqa: BLE001
        return (f"ERROR: {type(exc).__name__}: {exc}", time.monotonic() - start)
    return (str(out), time.monotonic() - start)


def runAbBench(
    *,
    askA: Callable[[str], str],
    askB: Callable[[str], str],
    items: list[dict[str, Any]],
    nRuns: int = 3,
) -> dict[str, Any]:
    """provider A vs provider B 동일 질문 N 회 실행 → 평균 score + latency 통계.

    Sig:
        runAbBench(*, askA, askB, items, nRuns=3) -> stats dict
    Args:
        askA / askB: question (str) → answerText (str) 호출 가능 함수.
        items: ``[{"id", "question", "expectedNumber", "expectedKeywords"}]`` list.
        nRuns: item 당 반복 호출 수.
    Returns:
        ``{
            "n": N items, "nRuns": nRuns,
            "A": {"scoreMean", "latencyP50", "latencyMean"},
            "B": {"scoreMean", "latencyP50", "latencyMean"},
            "delta": {"scoreDelta", "latencyRatio"},
            "perItem": [...]
        }``
    """
    scores_a: list[float] = []
    scores_b: list[float] = []
    lats_a: list[float] = []
    lats_b: list[float] = []
    per_item: list[dict[str, Any]] = []
    for item in items:
        question = str(item.get("question") or "")
        expected_num = item.get("expectedNumber")
        expected_keywords = tuple(item.get("expectedKeywords") or ())
        item_scores_a: list[float] = []
        item_scores_b: list[float] = []
        item_lats_a: list[float] = []
        item_lats_b: list[float] = []
        for _ in range(nRuns):
            ans_a, lat_a = _runOne(askA, question)
            ans_b, lat_b = _runOne(askB, question)
            score_a = strictQualityScore(ans_a, expectedNumber=expected_num, expectedKeywords=expected_keywords)
            score_b = strictQualityScore(ans_b, expectedNumber=expected_num, expectedKeywords=expected_keywords)
            item_scores_a.append(score_a)
            item_scores_b.append(score_b)
            item_lats_a.append(lat_a)
            item_lats_b.append(lat_b)
        per_item.append(
            {
                "id": item.get("id"),
                "question": question,
                "A": {"scoreMean": statistics.mean(item_scores_a), "latencyMean": statistics.mean(item_lats_a)},
                "B": {"scoreMean": statistics.mean(item_scores_b), "latencyMean": statistics.mean(item_lats_b)},
            }
        )
        scores_a.extend(item_scores_a)
        scores_b.extend(item_scores_b)
        lats_a.extend(item_lats_a)
        lats_b.extend(item_lats_b)

    def _p50(values: list[float]) -> float:
        return float(statistics.median(values)) if values else 0.0

    summary_a = {
        "scoreMean": float(statistics.mean(scores_a)) if scores_a else 0.0,
        "latencyP50": _p50(lats_a),
        "latencyMean": float(statistics.mean(lats_a)) if lats_a else 0.0,
    }
    summary_b = {
        "scoreMean": float(statistics.mean(scores_b)) if scores_b else 0.0,
        "latencyP50": _p50(lats_b),
        "latencyMean": float(statistics.mean(lats_b)) if lats_b else 0.0,
    }
    score_delta = summary_b["scoreMean"] - summary_a["scoreMean"]
    latency_ratio = summary_b["latencyP50"] / summary_a["latencyP50"] if summary_a["latencyP50"] > 0 else 0.0
    return {
        "n": len(items),
        "nRuns": nRuns,
        "A": summary_a,
        "B": summary_b,
        "delta": {"scoreDelta": score_delta, "latencyRatio": latency_ratio},
        "perItem": per_item,
    }


def renderAbReport(stats: dict[str, Any]) -> str:
    """runAbBench 결과 → markdown 보고.

    성공 임계 (PR-T3): scoreDelta ≥ +10 AND latencyRatio ≤ 1.1.
    """
    a = stats["A"]
    b = stats["B"]
    d = stats["delta"]
    success = d["scoreDelta"] >= 10.0 and 0 < d["latencyRatio"] <= 1.1
    lines = [
        f"# A/B Bench (N={stats['n']} items × {stats['nRuns']} runs)",
        "",
        "| 측정 | A | B | Δ |",
        "|---|---:|---:|---:|",
        f"| score mean | {a['scoreMean']:.1f} | {b['scoreMean']:.1f} | {d['scoreDelta']:+.1f} |",
        f"| latency p50 (s) | {a['latencyP50']:.2f} | {b['latencyP50']:.2f} | ratio {d['latencyRatio']:.2f}x |",
        f"| latency mean (s) | {a['latencyMean']:.2f} | {b['latencyMean']:.2f} | — |",
        "",
        f"성공 임계 (B ≥ A+10 점 AND latency ratio ≤ 1.1): {'✅' if success else '❌'}",
    ]
    return "\n".join(lines)


__all__ = ["runAbBench", "strictQualityScore", "renderAbReport"]


if __name__ == "__main__":
    # CLI 진입 — 운영자 명시 trigger 후 사용
    print("aiAbHarness — 모듈 import 후 runAbBench 호출하세요. 자세한 사용은 docstring 참조.")
