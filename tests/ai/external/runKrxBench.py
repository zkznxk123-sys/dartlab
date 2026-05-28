"""KRX-Bench (ACL 2024) runner — Korean stock market QA benchmark.

Source: dialect-lab/KRX-Bench (HuggingFace · ACL 2024 paper).
Dataset 양식 (HF datasets):
    {
        "question": str (한국어 KRX market 질문),
        "answer": str or list[str] (정답 키워드),
    }

사용:
    PYTHONPATH=. uv run python -X utf8 tests/ai/external/runKrxBench.py \\
        --dataset-path <HF_DATASET_DIR or .jsonl> --sample 50

dataset 다운로드 = 사용자 트리거 (HF datasets 또는 paper repo).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from tests.ai.external._common import runBenchmark

_BENCHMARK = "KRX-Bench"


def _loadKrxBench(path: Path) -> Iterable[dict[str, Any]]:
    """KRX-Bench dataset loader — jsonl or HF datasets dir."""
    if not path.exists():
        raise FileNotFoundError(f"KRX-Bench dataset 미존재: {path}")
    if path.is_file() and path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                yield {
                    "question": row.get("question") or row.get("query") or "",
                    "expected": row.get("answer") or row.get("expected") or "",
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
                "expected": row.get("answer") or row.get("expected") or "",
            }
        return
    raise ValueError(f"KRX-Bench dataset 양식 미인식: {path} (jsonl 또는 HF datasets dir)")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{_BENCHMARK} runner")
    parser.add_argument("--dataset-path", required=True, type=Path, help="jsonl 또는 HF datasets dir")
    parser.add_argument("--sample", type=int, default=50, help="앞 N case 만 run (default 50)")
    parser.add_argument("--no-baseline", action="store_true", help="externalBenchBaseline.json 갱신 skip")
    args = parser.parse_args()

    cases = _loadKrxBench(args.dataset_path)
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
