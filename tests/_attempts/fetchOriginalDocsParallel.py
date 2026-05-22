"""DART 원본 zip 전체 종목 병렬 수집 — 본진 collectAllOriginalZips driver.

사용자 지시 (2026-05-22):
- "api키가 많은데 동시호출가능할텐데??"
- "병렬호출 안전하게 받는 로직을 본진에만들고 동시호출해라 서로 간섭없이
   그리고 안전저장 그리고 키제한됐을때 다른 키로이관하는 로직까지"
- "집문서받는기능도본진에둬라 나중에 쓸수도있으니까"

본진 (재사용 가능):
- src/dartlab/providers/dart/openapi/client.py — _KeySlot 풀 + sequential exhausted
- src/dartlab/providers/dart/openapi/bulkZipFetcher.py — fetchZipsParallel +
  collectAllOriginalZips (전체 종목 일괄 진입)

본 스크립트 = state file 로깅 + progress 표시 만 책임 (thin CLI).

실행: uv run python -X utf8 tests/_attempts/fetchOriginalDocsParallel.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dartlab.providers.dart.openapi import collectAllOriginalZips  # noqa: E402

STATE = REPO_ROOT / ".dartlab" / "audit" / "fetchOriginalDocsParallel.txt"


def main() -> int:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    state_f = STATE.open("w", encoding="utf-8")
    state_f.write(f"# fetchOriginalDocsParallel start {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    state_f.flush()

    def _progress(done: int, total: int, stats: dict) -> None:
        elapsed = time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate / 60 if rate > 0 else 0
        line = (
            f"[{done}/{total}] saved={stats['saved']} skipped={stats['skipped']} "
            f"failed={stats['failed']} bytes={stats['bytesTotal'] / 1e9:.2f}GB "
            f"({rate:.1f}/s ETA {eta:.1f}m)"
        )
        print(line, flush=True)
        state_f.write(line + "\n")
        state_f.flush()

    stats = collectAllOriginalZips(
        workers=4,
        progressEvery=500,
        progressCallback=_progress,
    )
    state_f.close()
    elapsed = time.time() - t0
    print(f"\n=== DONE === elapsed={elapsed / 60:.1f}m {stats.asDict()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
