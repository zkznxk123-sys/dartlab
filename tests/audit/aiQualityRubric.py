"""엄격 quality eval 5 차원 rubric — 마스터 플랜 v2 트랙 5 PR-Q1.

cryptic-discovering-kettle.md v2 트랙 5 (Q-strict). 현 ``tests/_attempts/
aiQualityBench.py`` 의 ``expected_substrings`` 가 *질문 키워드 포함* 만 검증 →
score 100% 가 거짓 통과 (답변에 ROE 숫자 없어도 "ROE" 단어만 있으면 통과). 본
모듈이 5 차원 rubric (accuracy / completeness / toolSelection / refsQuality /
latency) + accuracy hard gate 로 거짓 통과 차단.

5 차원 가중치
-------------
- accuracy 0.35 (hard gate ≥ 60) — ground-truth 와 ±5% 이내
- completeness 0.20 — requiredSlots 매칭 비율
- toolSelection 0.20 — expectedTools ⊆ actualTools (subset / exact)
- refsQuality 0.15 — refCount ≥ minRefCount + kind 분포
- latency 0.10 — TTFC ≤ 5s + 전체 ≤ 90s

통과 기준 = 총점 ≥ 70 AND accuracy.raw ≥ 60. accuracy 미달은 다른 차원으로
보상 불가 (거짓 정답 가드).

사용
----
>>> events = list(dartlab.ask(question, events=True))
>>> answer = "".join(e.data.get("text", "") for e in events if e.kind == "chunk")
>>> report = evaluateStrict(goldenItem=q, answerText=answer, traceEvents=events)
>>> report.totalScore, report.passed
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from dartlab.ai.contracts import TraceEvent

# rubric 가중치 SSOT — 변경 시 baseline 재측 동행 (회귀 비교 깨짐).
_WEIGHTS: dict[str, float] = {
    "accuracy": 0.35,
    "completeness": 0.20,
    "toolSelection": 0.20,
    "refsQuality": 0.15,
    "latency": 0.10,
}

# 차원별 통과 임계 — DimensionScore.passed 결정.
_DIM_PASS_THRESHOLD: dict[str, float] = {
    "accuracy": 60.0,
    "completeness": 70.0,
    "toolSelection": 70.0,
    "refsQuality": 60.0,
    "latency": 50.0,
}

# 종합 통과 = 총점 ≥ 70 AND accuracy.raw ≥ 60 (hard gate).
_TOTAL_PASS_THRESHOLD: float = 70.0
_ACCURACY_HARD_GATE: float = 60.0


@dataclass(frozen=True)
class DimensionScore:
    """5 차원 중 1 차원의 raw + weighted + 진단.

    Sig:
        DimensionScore(name, raw, weighted, passed, details)
    Args:
        name: 차원명 — accuracy / completeness / toolSelection / refsQuality / latency
        raw: 0~100 점.
        weighted: raw * 가중치.
        passed: 차원별 게이트 통과 여부.
        details: 진단 dict (mismatchedNumbers / missingSlots / forbiddenHit 등).
    """

    name: str
    raw: float
    weighted: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreReport:
    """1 질문 1 답변의 종합 score 보고.

    Sig:
        ScoreReport(goldenId, totalScore, passed, dimensions, answerLen, elapsedSec, error)
    Args:
        goldenId: golden dataset item id.
        totalScore: 0~100 가중 합산.
        passed: 총점 ≥ 70 AND accuracy.raw ≥ 60.
        dimensions: 5 차원 DimensionScore dict.
        answerLen: 답변 텍스트 문자 수.
        elapsedSec: 전체 응답 시간 (TraceEvent ts 차이).
        error: 평가 자체 실패 사유 (provider error 등) — None 이면 정상.
    """

    goldenId: str
    totalScore: float
    passed: bool
    dimensions: dict[str, DimensionScore]
    answerLen: int
    elapsedSec: float
    error: str | None = None


def evaluateStrict(
    *,
    goldenItem: dict[str, Any],
    answerText: str,
    traceEvents: Sequence[TraceEvent],
    groundTruthOverride: dict[str, float] | None = None,
) -> ScoreReport:
    """5 차원 rubric 기반 엄격 평가.

    Sig:
        evaluateStrict(*, goldenItem, answerText, traceEvents,
                       groundTruthOverride=None) -> ScoreReport
    Args:
        goldenItem: GoldenItemV2 양식 dict — id / question / rubric 키 필수.
        answerText: dartlab.ask(stream=False) 답변 텍스트.
        traceEvents: dartlab.ask(events=True) 수집 TraceEvent 시퀀스.
        groundTruthOverride: numericChecks[].label → 실측 ground-truth 매핑.
    Returns:
        ScoreReport — passed 가 게이트 결과, dimensions 가 5 축 진단.
    Example:
        >>> events = list(dartlab.ask(q["question"], events=True))
        >>> answer = "".join(e.data.get("text","") for e in events if e.kind == "chunk")
        >>> rpt = evaluateStrict(goldenItem=q, answerText=answer, traceEvents=events)
        >>> rpt.totalScore, rpt.passed
    """
    rubric = goldenItem.get("rubric") or {}
    gt = dict(groundTruthOverride or {})

    indexed = _indexTraceEvents(traceEvents)
    actualTools = indexed["actualTools"]
    refs = indexed["refs"]
    firstChunkMs = indexed["firstChunkMs"]
    totalElapsed = indexed["totalElapsedSec"]

    accuracyDim = _scoreAccuracy(rubric.get("accuracy") or {}, answerText, gt)
    completenessDim = _scoreCompleteness(rubric.get("completeness") or {}, answerText)
    toolDim = _scoreToolSelection(rubric.get("toolSelection") or {}, actualTools)
    refsDim = _scoreRefsQuality(rubric.get("refsQuality") or {}, refs)
    latencyDim = _scoreLatency(rubric.get("latency") or {}, totalElapsed, firstChunkMs)

    dimensions = {d.name: d for d in (accuracyDim, completenessDim, toolDim, refsDim, latencyDim)}
    total = round(sum(d.weighted for d in dimensions.values()), 1)
    passed = total >= _TOTAL_PASS_THRESHOLD and accuracyDim.raw >= _ACCURACY_HARD_GATE

    return ScoreReport(
        goldenId=str(goldenItem.get("id") or "?"),
        totalScore=total,
        passed=passed,
        dimensions=dimensions,
        answerLen=len(answerText),
        elapsedSec=round(totalElapsed, 2),
        error=None,
    )


def renderRubricReport(reports: Sequence[ScoreReport]) -> str:
    """ScoreReport N 종 → 회귀 추적용 마크다운 요약 표.

    Sig:
        renderRubricReport(reports) -> str
    Args:
        reports: ScoreReport 시퀀스.
    Returns:
        마크다운 요약 문자열 (총점 + 5 차원 분해).
    Example:
        >>> print(renderRubricReport([rpt1, rpt2]))
    """
    if not reports:
        return "(결과 없음)"
    avg = sum(r.totalScore for r in reports) / len(reports)
    pass_count = sum(1 for r in reports if r.passed)
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"strict quality rubric — N={len(reports)}")
    lines.append("=" * 60)
    lines.append(f"avg total: {avg:.1f}/100  pass: {pass_count}/{len(reports)}")
    lines.append("")
    lines.append(f"{'id':<22} {'total':>6} {'acc':>5} {'comp':>5} {'tool':>5} {'ref':>5} {'lat':>5}")
    lines.append("-" * 60)
    for r in reports:
        mark = "✓" if r.passed else "✗"
        dims = r.dimensions
        lines.append(
            f"{mark} {r.goldenId:<20} {r.totalScore:>5.1f}% "
            f"{dims['accuracy'].raw:>4.0f} {dims['completeness'].raw:>4.0f} "
            f"{dims['toolSelection'].raw:>4.0f} {dims['refsQuality'].raw:>4.0f} "
            f"{dims['latency'].raw:>4.0f}"
        )
    return "\n".join(lines)


# ── 내부 helper ──


def _indexTraceEvents(traceEvents: Sequence[TraceEvent]) -> dict[str, Any]:
    """TraceEvent 시퀀스 → tool_start / refs / first_chunk_ms / total elapsed 인덱스."""
    actualTools: list[str] = []
    refs: list[dict[str, Any]] = []
    firstChunkMs: float | None = None
    timestamps: list[float] = []
    for ev in traceEvents:
        if ev.kind == "tool_start":
            tool = ev.data.get("tool")
            if isinstance(tool, str):
                actualTools.append(tool)
        elif ev.kind == "done":
            done_refs = ev.data.get("refs") or []
            if isinstance(done_refs, list):
                refs = [r for r in done_refs if isinstance(r, dict)]
        elif ev.kind == "first_chunk_ms":
            ms = ev.data.get("ms")
            if isinstance(ms, (int, float)):
                firstChunkMs = float(ms)
        ts = _parseTsToSec(ev.ts)
        if ts is not None:
            timestamps.append(ts)
    totalElapsedSec = 0.0
    if len(timestamps) >= 2:
        totalElapsedSec = max(0.0, timestamps[-1] - timestamps[0])
    return {
        "actualTools": actualTools,
        "refs": refs,
        "firstChunkMs": firstChunkMs,
        "totalElapsedSec": totalElapsedSec,
    }


def _parseTsToSec(ts: str) -> float | None:
    """ISO 8601 ts → epoch seconds. 실패 시 None."""
    try:
        import datetime as dt

        # TraceEvent._nowIso 양식 가정 — 끝에 Z 가 있어도 OK
        normalized = ts.rstrip("Z")
        return dt.datetime.fromisoformat(normalized).timestamp()
    except (ValueError, ImportError):
        return None


def _scoreAccuracy(spec: dict[str, Any], answerText: str, gt: dict[str, float]) -> DimensionScore:
    """숫자 정확성 — patternRegex 추출 + ground-truth ±tolerance 비교."""
    checks = spec.get("numericChecks") or []
    if not checks:
        # vacuous truth — numericChecks 없으면 100. golden 작성자 명시 책임.
        return DimensionScore("accuracy", 100.0, 100.0 * _WEIGHTS["accuracy"], True, {"checks": []})
    details: list[dict[str, Any]] = []
    hits = 0
    for chk in checks:
        label = str(chk.get("label") or "?")
        pattern = chk.get("patternRegex")
        if not isinstance(pattern, str):
            details.append({"label": label, "status": "noPattern"})
            continue
        m = re.search(pattern, answerText)
        if not m:
            details.append({"label": label, "status": "notFound"})
            continue
        try:
            actual = float(m.group(1).replace(",", ""))
        except (ValueError, IndexError):
            details.append({"label": label, "status": "unparseable"})
            continue
        truth = float(gt.get(label, chk.get("groundTruth", 0.0)))
        tol = float(chk.get("tolerancePct", 5.0))
        rel = abs(actual - truth) / max(abs(truth), 1e-9) * 100.0
        ok = rel <= tol
        details.append(
            {
                "label": label,
                "status": "ok" if ok else "drift",
                "actual": actual,
                "truth": truth,
                "relErrPct": round(rel, 2),
            }
        )
        if ok:
            hits += 1
    raw = 100.0 * hits / max(1, len(checks))
    return DimensionScore(
        "accuracy",
        raw,
        raw * _WEIGHTS["accuracy"],
        raw >= _DIM_PASS_THRESHOLD["accuracy"],
        {"checks": details},
    )


def _scoreCompleteness(spec: dict[str, Any], answerText: str) -> DimensionScore:
    """requiredSlots 매칭 비율 + forbiddenSlots 페널티."""
    required = spec.get("requiredSlots") or []
    forbidden = spec.get("forbiddenSlots") or []
    matched = [s for s in required if isinstance(s, str) and re.search(s, answerText)]
    forbiddenHit = [s for s in forbidden if isinstance(s, str) and re.search(s, answerText)]
    if not required:
        raw = 100.0
    else:
        raw = 100.0 * len(matched) / len(required)
    raw -= 20.0 * len(forbiddenHit)
    raw = max(0.0, min(100.0, raw))
    return DimensionScore(
        "completeness",
        raw,
        raw * _WEIGHTS["completeness"],
        raw >= _DIM_PASS_THRESHOLD["completeness"],
        {
            "matched": matched,
            "missing": [s for s in required if s not in matched],
            "forbiddenHit": forbiddenHit,
        },
    )


def _scoreToolSelection(spec: dict[str, Any], actualTools: list[str]) -> DimensionScore:
    """expectedTools ⊆ actualTools (subset / exact mode) + forbiddenTools 페널티."""
    expected = set(spec.get("expectedTools") or [])
    forbidden = set(spec.get("forbiddenTools") or [])
    mode = str(spec.get("matchMode", "subset"))
    actual = set(actualTools)
    if not expected:
        raw = 100.0
    elif mode == "exact":
        raw = 100.0 if actual == expected else 0.0
    else:  # subset
        covered = len(expected & actual)
        raw = 100.0 * covered / len(expected)
    forbiddenHit = forbidden & actual
    if forbiddenHit:
        raw = max(0.0, raw - 50.0)
    return DimensionScore(
        "toolSelection",
        raw,
        raw * _WEIGHTS["toolSelection"],
        raw >= _DIM_PASS_THRESHOLD["toolSelection"],
        {
            "expected": sorted(expected),
            "actual": actualTools,
            "forbiddenHit": sorted(forbiddenHit),
        },
    )


def _scoreRefsQuality(spec: dict[str, Any], refs: list[dict[str, Any]]) -> DimensionScore:
    """refCount ≥ minRefCount + kind 분포 매칭."""
    minCount = int(spec.get("minRefCount", 0))
    expectedKinds = set(spec.get("expectedKinds") or [])
    actualKinds = {str(r.get("kind") or "") for r in refs}
    if minCount <= 0:
        countRaw = 100.0
    else:
        countRaw = 100.0 * min(1.0, len(refs) / minCount)
    if not expectedKinds:
        kindRaw = 100.0
    else:
        kindRaw = 100.0 if expectedKinds & actualKinds else 0.0
    raw = (countRaw + kindRaw) / 2.0
    return DimensionScore(
        "refsQuality",
        raw,
        raw * _WEIGHTS["refsQuality"],
        raw >= _DIM_PASS_THRESHOLD["refsQuality"],
        {
            "refCount": len(refs),
            "kinds": sorted(k for k in actualKinds if k),
        },
    )


def _scoreLatency(spec: dict[str, Any], totalElapsedSec: float, firstChunkMs: float | None) -> DimensionScore:
    """전체 응답 시간 + 첫 chunk 시간 — soft-clipped linear."""
    maxTotal = float(spec.get("maxTotalSec", 90.0))
    maxFirst = float(spec.get("maxFirstChunkMs", 5000.0))
    # totalElapsed soft-clip
    if totalElapsedSec <= 0:
        latTotal = 50.0  # unknown — vacuous
    else:
        excess = max(0.0, totalElapsedSec - maxTotal)
        latTotal = max(0.0, 100.0 * (1.0 - excess / maxTotal))
    # firstChunk soft-clip
    if firstChunkMs is None:
        latFirst = 50.0  # provider streaming 미발행 — neutral
    else:
        excess = max(0.0, firstChunkMs - maxFirst)
        latFirst = max(0.0, 100.0 * (1.0 - excess / maxFirst))
    raw = (latTotal + latFirst) / 2.0
    return DimensionScore(
        "latency",
        raw,
        raw * _WEIGHTS["latency"],
        raw >= _DIM_PASS_THRESHOLD["latency"],
        {"totalSec": round(totalElapsedSec, 2), "firstChunkMs": firstChunkMs},
    )


def evaluateBatch(
    *,
    goldenItems: Sequence[dict[str, Any]],
    askFn: Any,
    maxItems: int | None = None,
    groundTruthProvider: Any = None,
) -> list[ScoreReport]:
    """golden N 종에 대해 askFn (예: dartlab.ask) 실 호출 + evaluateStrict 직렬화.

    Sig:
        evaluateBatch(*, goldenItems, askFn, maxItems=None, groundTruthProvider=None) -> list[ScoreReport]
    Args:
        goldenItems: GoldenItemV2 시퀀스.
        askFn: dartlab.ask 같은 callable (question, events=True) → TraceEvent iterator.
        maxItems: 평가할 최대 갯수 — None 이면 전체.
        groundTruthProvider: golden item 의 ``groundTruthProbe`` 키 → dict[label, value]
            함수. None 이면 골든 item 의 ``groundTruth`` 정적 값 사용.
    Returns:
        ScoreReport list.
    Example:
        >>> import dartlab
        >>> reports = evaluateBatch(goldenItems=_GOLDEN_V2, askFn=dartlab.ask)
    """
    targets = list(goldenItems[:maxItems] if maxItems else goldenItems)
    out: list[ScoreReport] = []
    for item in targets:
        try:
            events = list(askFn(item["question"], events=True))
        except Exception as exc:  # noqa: BLE001
            out.append(
                ScoreReport(
                    goldenId=str(item.get("id") or "?"),
                    totalScore=0.0,
                    passed=False,
                    dimensions={},
                    answerLen=0,
                    elapsedSec=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        answerText = "".join(ev.data.get("text", "") for ev in events if ev.kind == "chunk")
        gt: dict[str, float] | None = None
        if groundTruthProvider is not None:
            probe = item.get("groundTruthProbe")
            if probe:
                try:
                    gt = groundTruthProvider(probe)
                except Exception:  # noqa: BLE001
                    gt = None
        report = evaluateStrict(
            goldenItem=item,
            answerText=answerText,
            traceEvents=events,
            groundTruthOverride=gt,
        )
        out.append(report)
    return out


__all__ = [
    "DimensionScore",
    "ScoreReport",
    "evaluateStrict",
    "evaluateBatch",
    "renderRubricReport",
]
