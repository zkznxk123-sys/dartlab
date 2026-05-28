"""외부 한국 benchmark 공통 dispatch + scoring + baseline write (G 트랙).

3 runner (KRX-Bench · WON · KFinEval-Pilot) 가 공유. 각 benchmark 의 dataset 양식
별 loader 는 runner 별 박히고, 본 모듈은 dispatch + string-match scoring + baseline
JSON append 만 책임.

Scoring 룰 (LLM judge 의존 X):
- exact-match (단답 비교) — case-insensitive substring
- multi-keyword match (정답이 list 면 모두 등장하는지)
- skip 케이스 (dataset 미설치 또는 dartlab AI provider 미설정) 는 score 계산 제외
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

_BASELINE_PATH = Path("tests/audit/_baselines/externalBenchBaseline.json")


@dataclass(frozen=True)
class BenchmarkResult:
    """단일 benchmark run 의 집계 결과 (baseline 에 append 형식)."""

    benchmark: str
    sample: int
    completed: int
    skipped: int
    correct: int
    score: float  # correct / completed (0~1)
    elapsedSeconds: float
    capturedAt: str
    cases: list[dict[str, Any]] = field(default_factory=list)


def _matchExpected(answer: str, expected: Any) -> bool:
    """string-match scoring — expected 가 str 면 substring, list 면 모두 등장."""
    if not answer:
        return False
    text = str(answer).lower()
    if isinstance(expected, str):
        return expected.lower() in text
    if isinstance(expected, (list, tuple)):
        return all(str(kw).lower() in text for kw in expected if kw)
    return False


def _writeBaseline(result: BenchmarkResult) -> Path:
    """externalBenchBaseline.json 에 benchmark 별 entry append (overwrite by benchmark name)."""
    path = _BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    existing[result.benchmark] = asdict(result)
    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def runBenchmark(
    *,
    benchmark: str,
    cases: Iterable[dict[str, Any]],
    askFn: Callable[[str], str] | None = None,
    sample: int | None = None,
    writeBaseline: bool = True,
) -> BenchmarkResult:
    """dataset cases 를 dartlab AI 로 dispatch + string-match scoring.

    Parameters
    ----------
    benchmark
        Identifier (e.g. ``"KRX-Bench"``, ``"WON"``, ``"KFinEval-Pilot"``).
    cases
        Iterable of dict — ``{question, expected}`` 형식. expected 는 str 또는 list[str].
    askFn
        Question → answer 함수. None 이면 ``dartlab.ai.ask`` (lazy import). external
        benchmark 환경에서 dartlab 미설치 시 skip.
    sample
        앞에서 N case 만 run. None 이면 전체.
    writeBaseline
        ``tests/audit/_baselines/externalBenchBaseline.json`` 에 결과 append 여부.

    Returns
    -------
    BenchmarkResult
        run 집계 + per-case detail.
    """
    if askFn is None:
        try:
            from dartlab.ai import ask as _ask
        except ImportError as exc:
            raise RuntimeError(f"dartlab.ai.ask import 실패 — benchmark {benchmark} 측정 불가. {exc}") from exc
        askFn = _ask

    started = time.time()
    capturedAt = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cases_list = list(cases)
    if sample is not None:
        cases_list = cases_list[: max(0, sample)]

    completed = 0
    skipped = 0
    correct = 0
    case_records: list[dict[str, Any]] = []
    for case in cases_list:
        question = str(case.get("question") or "")
        expected = case.get("expected")
        if not question:
            skipped += 1
            case_records.append({"question": question, "skipped": True, "reason": "empty_question"})
            continue
        try:
            answer = askFn(question)
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            case_records.append(
                {
                    "question": question[:120],
                    "skipped": True,
                    "reason": f"{type(exc).__name__}: {str(exc)[:120]}",
                }
            )
            continue
        completed += 1
        matched = _matchExpected(answer, expected)
        if matched:
            correct += 1
        case_records.append(
            {
                "question": question[:120],
                "expectedKeywords": expected if not isinstance(expected, str) else [expected],
                "matched": matched,
            }
        )

    elapsed = time.time() - started
    score = (correct / completed) if completed else 0.0
    result = BenchmarkResult(
        benchmark=benchmark,
        sample=len(cases_list),
        completed=completed,
        skipped=skipped,
        correct=correct,
        score=score,
        elapsedSeconds=elapsed,
        capturedAt=capturedAt,
        cases=case_records,
    )
    if writeBaseline:
        _writeBaseline(result)
    return result
