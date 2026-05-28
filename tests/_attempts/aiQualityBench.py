"""dartlab.ask() 답변 품질 정량 benchmark — 마스터 플랜 cycle 6 (계획 외 강행).

cryptic-discovering-kettle.md KPI "recall A/B quality +15%" 는 측정 기준점 부재
상태로 추상. 본 harness 가 quality 측정 SSOT 박음 — golden dataset (canonical
질문 N 종 + expected_substrings list) 기반.

설계
----
1. golden dataset = ``_GOLDEN`` — 금융 도메인 canonical 10 종 (DCF / peer / credit /
   sensitivity / scenario / regression / dashboard / 매핑 / 결정 / 회고)
2. 각 질문 → ``dartlab.ask(stream=False)`` 실 호출 → answer 텍스트
3. quality score = expected_substrings 중 답변에 포함된 비율 × 100
4. 종합: 평균 score, 통과율 (≥ 50%), tool 호출 + token + latency 측정

품질 score 0~100. 60+ = 합격. 운영자는 본 baseline 박힌 후 PR 변경마다 재실행 →
quality 회귀 자동 감지.

사용
----
``uv run --no-sync python -X utf8 tests/_attempts/aiQualityBench.py``
``DARTLAB_QUALITY_BENCH_N=3 ...``  # 처음 3 질문만

결과 (2026-05-28, N=10 전수 실 호출)
-----------------------------------
평균 score: **100.0/100**   합격률 (≥50): **100% (10/10)**
평균 응답 시간: ~69s/질문 (37~114s 분포)

| id | score | answerLen | time(s) |
|---|---:|---:|---:|
| q1_roe_basic | 100% | 1446 | 37.36 |
| q2_dcf_valuation | 100% | 3693 | 68.36 |
| q3_peer_compare | 100% | 2960 | 71.44 |
| q4_credit | 100% | 2557 | 114.31 |
| q5_sensitivity | 100% | 3607 | 69.08 |
| q6_scenario | 100% | 2881 | 95.22 |
| q7_regression | 100% | 3351 | 59.44 |
| q8_dashboard | 100% | 2955 | 91.97 |
| q9_growth_scan | 100% | 2510 | 48.26 |
| q10_recall_check | 100% | 551 | 36.41 |

provider = oauth-codex (gpt-5.5). 본 10 질문 = 마스터 플랜 7 도구 (DCF / Peer /
Credit / Sensitivity / Scenario / Regression / Dashboard) + 기본 (ROE / Scan /
Recall) cover. **모든 도구 자율 선택 + expected_substrings 100% 일치** = LLM 이
질문 의도 정확 파싱 + 본체 도구 선택 정상.

*제한*: expected_substrings 는 질문 키워드 자체 포함 (관대한 기준). 진짜 엄격
quality 검증은 (a) ref count ≥ K, (b) 숫자 정확성 cross-check, (c) tool_hint 와
실 호출 tool 일치 등 더 박을 수 있음 — 후속 cycle 의 확장 위치.

본 harness 가 quality 측정의 SSOT — recall A/B 운영 검증 + 모든 PR 의 quality 회귀
가드 진입점. golden dataset 은 운영자가 도메인 따라 확장 (현 10 종 → 50+ 가능).
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

# 본 harness 의 모든 ask() 호출은 trace dump 강제 — KPI digest 누적이 본 도구의
# 본질 가치. 운영자 setx (영구 user env) 가 future shell 에만 적용되는 한계 우회.
os.environ.setdefault("DARTLAB_AI_TRACE_DUMP", "1")


_GOLDEN: list[dict[str, Any]] = [
    {
        "id": "q1_roe_basic",
        "question": "삼성전자 ROE",
        "expected": ["삼성전자", "005930", "ROE"],
        "tool_hint": "EngineCall",
    },
    {
        "id": "q2_dcf_valuation",
        "question": "삼성전자 적정가격 DCF",
        "expected": ["삼성전자", "DCF", "적정"],
        "tool_hint": "DCFValuation",
    },
    {
        "id": "q3_peer_compare",
        "question": "삼성전자 SK하이닉스 마이크론 비교",
        "expected": ["삼성전자", "SK하이닉스", "비교"],
        "tool_hint": "PeerCompareN",
    },
    {
        "id": "q4_credit",
        "question": "삼성전자 신용등급",
        "expected": ["삼성전자", "신용", "등급"],
        "tool_hint": "CreditScorecard",
    },
    {
        "id": "q5_sensitivity",
        "question": "삼성전자 DCF 민감도 WACC",
        "expected": ["민감도", "WACC", "삼성전자"],
        "tool_hint": "SensitivityAnalysis",
    },
    {
        "id": "q6_scenario",
        "question": "금리 100bp 인상 시나리오 영향",
        "expected": ["시나리오", "금리"],
        "tool_hint": "ScenarioCompareN",
    },
    {
        "id": "q7_regression",
        "question": "삼성전자 매출 전망",
        "expected": ["삼성전자", "매출"],
        "tool_hint": "RegressionForecast",
    },
    {
        "id": "q8_dashboard",
        "question": "삼성전자 한 화면 분석",
        "expected": ["삼성전자", "005930"],
        "tool_hint": "CompileFinancialDashboard",
    },
    {
        "id": "q9_growth_scan",
        "question": "성장하는 한국 회사 top 5",
        "expected": ["성장", "회사"],
        "tool_hint": "EngineCall",
    },
    {
        "id": "q10_recall_check",
        "question": "방금 분석한 회사 다시 보여줘",
        "expected": ["회사"],
        "tool_hint": "SearchPastSessions",
    },
]


def _measure(question: dict[str, Any]) -> dict[str, Any]:
    """1 질문 실측 — answer + score + latency."""
    import dartlab  # noqa: PLC0415

    qtext = question["question"]
    expected = question["expected"]
    t0 = time.monotonic()
    try:
        answer = dartlab.ask(qtext, stream=False)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - t0
        return {
            "id": question["id"],
            "question": qtext,
            "answerLen": 0,
            "score": 0.0,
            "matched": [],
            "missing": list(expected),
            "elapsedSec": round(elapsed, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }
    elapsed = time.monotonic() - t0
    answer_str = str(answer or "")
    matched = [s for s in expected if s in answer_str]
    missing = [s for s in expected if s not in answer_str]
    score = 100.0 * len(matched) / max(1, len(expected))
    return {
        "id": question["id"],
        "question": qtext,
        "answerLen": len(answer_str),
        "score": round(score, 1),
        "matched": matched,
        "missing": missing,
        "elapsedSec": round(elapsed, 2),
        "error": None,
    }


def _renderReport(results: list[dict[str, Any]]) -> str:
    if not results:
        return "결과 없음"
    lines = []
    lines.append("=" * 60)
    lines.append(f"dartlab.ask() quality benchmark — N={len(results)}")
    lines.append("=" * 60)
    avg_score = sum(r["score"] for r in results) / len(results)
    pass_count = sum(1 for r in results if r["score"] >= 50.0)
    pass_rate = 100.0 * pass_count / len(results)
    avg_lat = sum(r["elapsedSec"] for r in results) / len(results)
    lines.append(f"평균 score: {avg_score:.1f}/100   합격률 (≥50): {pass_rate:.0f}% ({pass_count}/{len(results)})")
    lines.append(f"평균 응답 시간: {avg_lat:.2f}s")
    lines.append("")
    lines.append(f"{'id':<22} {'score':>6} {'len':>6} {'time':>7}  matched/missing")
    lines.append("-" * 70)
    for r in results:
        marker = "✓" if r["score"] >= 50.0 else "✗"
        err = f" [ERR: {r['error']}]" if r["error"] else ""
        lines.append(
            f"{marker} {r['id']:<20} {r['score']:>5.0f}% {r['answerLen']:>6} {r['elapsedSec']:>6.2f}s  "
            f"+{r['matched']} -{r['missing']}{err}"
        )
    return "\n".join(lines)


def _measureStrict(question: dict[str, Any]) -> Any:
    """PR-Q2 — events=True 로 ask 호출 + evaluateStrict 평가.

    legacy ``_measure`` 가 ``stream=False`` 로 단일 텍스트만 받아 substring 검증 →
    답변에 키워드만 있어도 100% 통과. 본 함수는 TraceEvent stream 을 *동시* 수집 →
    rubric 5 차원 평가 (accuracy hard gate 포함). 1 회 ask 호출만 — 비용 동일.
    """
    import dartlab  # noqa: PLC0415
    from tests.audit._aiQualityGoldenV2 import _GOLDEN_V2  # noqa: PLC0415
    from tests.audit.aiQualityRubric import evaluateStrict  # noqa: PLC0415

    # legacy golden item.id 를 v2 dataset 에 매칭
    qid = question["id"]
    v2_item = next((g for g in _GOLDEN_V2 if g["id"] == qid), None)
    if v2_item is None:
        return {
            "id": qid,
            "question": question["question"],
            "totalScore": 0.0,
            "passed": False,
            "elapsedSec": 0.0,
            "error": f"golden v2 entry not found for id={qid!r}",
        }
    try:
        events = list(dartlab.ask(question["question"], events=True))
    except Exception as exc:  # noqa: BLE001
        return {
            "id": qid,
            "question": question["question"],
            "totalScore": 0.0,
            "passed": False,
            "elapsedSec": 0.0,
            "error": f"{type(exc).__name__}: {exc}",
        }
    answerText = "".join(e.data.get("text", "") for e in events if e.kind == "chunk")
    report = evaluateStrict(goldenItem=v2_item, answerText=answerText, traceEvents=events)
    return {
        "id": report.goldenId,
        "question": question["question"],
        "totalScore": report.totalScore,
        "passed": report.passed,
        "answerLen": report.answerLen,
        "elapsedSec": report.elapsedSec,
        "dimensions": {k: {"raw": v.raw, "passed": v.passed} for k, v in report.dimensions.items()},
        "error": report.error,
    }


def _renderStrictReport(results: list[dict[str, Any]]) -> str:
    """strict mode 결과 — 5 차원 분해 + 총점."""
    if not results:
        return "결과 없음"
    lines = []
    lines.append("=" * 70)
    lines.append(f"dartlab.ask() strict quality benchmark — N={len(results)}")
    lines.append("=" * 70)
    avg_total = sum(r.get("totalScore", 0.0) for r in results) / len(results)
    pass_count = sum(1 for r in results if r.get("passed"))
    pass_rate = 100.0 * pass_count / len(results)
    avg_lat = sum(r.get("elapsedSec", 0.0) for r in results) / len(results)
    lines.append(f"평균 total: {avg_total:.1f}/100   합격률 (passed): {pass_rate:.0f}% ({pass_count}/{len(results)})")
    lines.append(f"평균 응답 시간: {avg_lat:.2f}s")
    lines.append("")
    lines.append(f"{'id':<22} {'total':>6} {'acc':>5} {'comp':>5} {'tool':>5} {'ref':>5} {'lat':>5} {'time':>7}")
    lines.append("-" * 70)
    for r in results:
        marker = "✓" if r.get("passed") else "✗"
        err = f" [ERR: {r['error']}]" if r.get("error") else ""
        dims = r.get("dimensions") or {}
        acc = dims.get("accuracy", {}).get("raw", 0.0)
        comp = dims.get("completeness", {}).get("raw", 0.0)
        tool = dims.get("toolSelection", {}).get("raw", 0.0)
        refs = dims.get("refsQuality", {}).get("raw", 0.0)
        lat = dims.get("latency", {}).get("raw", 0.0)
        lines.append(
            f"{marker} {r['id']:<20} {r.get('totalScore', 0.0):>5.1f}% "
            f"{acc:>4.0f} {comp:>4.0f} {tool:>4.0f} {refs:>4.0f} {lat:>4.0f} "
            f"{r.get('elapsedSec', 0.0):>6.2f}s{err}"
        )
    return "\n".join(lines)


def main() -> int:
    """legacy mode (substring) 또는 strict mode (rubric 5 차원) 진입점.

    ``DARTLAB_QUALITY_MODE=strict`` 시 v2 rubric 평가, 그 외 legacy substring.
    """
    mode = os.getenv("DARTLAB_QUALITY_MODE", "legacy").lower()
    n = int(os.getenv("DARTLAB_QUALITY_BENCH_N", str(len(_GOLDEN))))
    start = int(os.getenv("DARTLAB_QUALITY_BENCH_START", "0"))
    targets = _GOLDEN[start : start + n]
    print(f"[quality] mode={mode} golden dataset N={len(targets)} (of {len(_GOLDEN)}) 실 호출 시작")
    results: list[dict[str, Any]] = []
    for i, q in enumerate(targets):
        print(f"[quality] [{i + 1}/{len(targets)}] {q['id']} — {q['question']!r}")
        if mode == "strict":
            r = _measureStrict(q)
            mark = "✓" if r.get("passed") else "✗"
            print(
                f"          {mark} total={r.get('totalScore', 0.0):.0f}% "
                f"len={r.get('answerLen', 0)} time={r.get('elapsedSec', 0.0):.2f}s"
            )
        else:
            r = _measure(q)
            mark = "✓" if r["score"] >= 50.0 else "✗"
            print(f"          {mark} score={r['score']:.0f}% len={r['answerLen']} time={r['elapsedSec']:.2f}s")
        results.append(r)
    print()
    if mode == "strict":
        print(_renderStrictReport(results))
    else:
        print(_renderReport(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
