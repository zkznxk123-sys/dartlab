"""KFinEval-Pilot (arXiv 2504.13216, 2025-04) runner — Korean finance evaluation.

Source: arXiv 2504.13216 "KFinEval-Pilot: Korean Financial Evaluation Benchmark".
Dataset 양식 (jsonl 또는 HF):
    {
        "question": str (한국어 금융 평가 질문),
        "answer": str (단답 또는 옵션 라벨),
        "domain": str (optional — banking/insurance/securities/accounting metadata),
    }

사용:
    PYTHONPATH=. uv run python -X utf8 tests/ai/external/runKFinEval.py \\
        --dataset-path <path> --sample 50

dataset 다운로드 = 사용자 트리거.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from tests.ai.external._common import runBenchmark

_BENCHMARK = "KFinEval-Pilot"


def _loadKFinEval(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"KFinEval-Pilot dataset 미존재: {path}")
    if path.is_file() and path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                yield {
                    "question": row.get("question") or row.get("query") or "",
                    "expected": row.get("answer") or row.get("label") or "",
                }
        return
    if path.is_file() and path.suffix == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(rows, list):
            for row in rows:
                yield {
                    "question": row.get("question") or row.get("query") or "",
                    "expected": row.get("answer") or row.get("label") or "",
                }
            return
    if path.is_dir():
        try:
            from datasets import load_from_disk  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("HuggingFace datasets 미설치 — pip install datasets 후 재실행") from exc
        ds = load_from_disk(str(path))
        for row in ds:
            yield {
                "question": row.get("question") or row.get("query") or "",
                "expected": row.get("answer") or row.get("label") or "",
            }
        return
    raise ValueError(f"KFinEval-Pilot dataset 양식 미인식: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{_BENCHMARK} runner")
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--sample", type=int, default=50)
    parser.add_argument("--no-baseline", action="store_true")
    args = parser.parse_args()

    cases = _loadKFinEval(args.dataset_path)
    result = runBenchmark(
        benchmark=_BENCHMARK,
        cases=cases,
        sample=args.sample,
        writeBaseline=not args.no_baseline,
    )
    print(
        f"[{_BENCHMARK}] sample={result.sample} completed={result.completed} "
        f"skipped={result.skipped} correct={result.correct} score={result.score:.3f} "
        f"elapsed={result.elapsedSeconds:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
