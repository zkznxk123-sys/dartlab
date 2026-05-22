"""DART 원본 zip 전체 종목 병렬 수집 — 본진 bulkZipFetcher 사용.

사용자 지시 (2026-05-22):
- "api키가 많은데 동시호출가능할텐데??"
- "병렬호출 안전하게 받는 로직을 본진에만들고 동시호출해라 서로 간섭없이
   그리고 안전저장 그리고 키제한됐을때 다른 키로이관하는 로직까지"

본 스크립트는 thin driver — 핵심 로직은:
- src/dartlab/providers/dart/openapi/client.py — _KeySlot 풀 (스레드 안전 + 020 cooldown)
- src/dartlab/providers/dart/openapi/bulkZipFetcher.py — ThreadPoolExecutor + atomic write

실행: uv run python -X utf8 tests/_attempts/fetchOriginalDocsParallel.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dartlab.providers.dart.openapi.bulkZipFetcher import fetchZipsParallel  # noqa: E402
from dartlab.providers.dart.openapi.client import DartClient  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "dart" / "original" / "docs"
DOCS_DIR = REPO_ROOT / "data" / "dart" / "docs"
STATE = REPO_ROOT / ".dartlab" / "audit" / "fetchOriginalDocsParallel.txt"


def _collectTargets() -> list[tuple[str, str]]:
    """모든 docs.parquet → (code, rcept_no) 페어 list."""
    import polars as pl

    codes = sorted(p.stem for p in DOCS_DIR.glob("*.parquet"))
    targets: list[tuple[str, str]] = []
    for code in codes:
        parquet = DOCS_DIR / f"{code}.parquet"
        df = pl.read_parquet(parquet, columns=["rcept_no"])
        rcepts = df.select("rcept_no").unique().to_series().to_list()
        for r in rcepts:
            targets.append((code, str(r)))
    return targets


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("collecting targets ...", flush=True)
    targets = _collectTargets()
    print(f"target: {len(targets)} (code, rcept) pairs", flush=True)

    client = DartClient()
    print(f"workers: {len(client._slots)} keys", flush=True)

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

    # workers=4 — finance/syncRecent 의 `asyncio.Semaphore(4)` 패턴 동일.
    # client._acquireSlot 가 sequential exhausted 모드 (키 1개로 580 rpm 소진 후
    # 다음 키) — 4 워커가 같은 키로 동시 요청. DART per-IP anti-abuse 회피.
    stats = fetchZipsParallel(
        client,
        targets,
        outDir=OUT_DIR,
        workers=4,
        progressEvery=500,
        progressCallback=_progress,
    )
    state_f.close()
    elapsed = time.time() - t0
    print(
        f"\n=== DONE === elapsed={elapsed / 60:.1f}m {stats.asDict()}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
