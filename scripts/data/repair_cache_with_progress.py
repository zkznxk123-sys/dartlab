"""로컬 캐시 회복 — 진행 표시 + 병렬 다운로드.

dataLoader.repairLocalCache는 직렬이라 1413종목에 ~14분 걸림.
이 스크립트는 단순 stdout flush로 진행 표시. 카테고리/최대 개수 옵션.
"""
import sys
import time
from pathlib import Path

from dartlab import config as cfg
from dartlab.core.dataLoader import _checkRemoteFreshness, _refreshFromHf


def main() -> int:
    cats = sys.argv[1].split(",") if len(sys.argv) > 1 else ["finance", "report"]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # 0 = 무제한

    totals = {"checked": 0, "fresh": 0, "stale": 0, "repaired": 0, "failed": 0}
    started = time.time()

    for cat in cats:
        catDir = Path(cfg.dataDir) / "dart" / cat
        if not catDir.exists():
            print(f"[{cat}] 디렉토리 없음 — 스킵", flush=True)
            continue

        files = sorted(catDir.glob("*.parquet"))
        if limit:
            files = files[:limit]
        n = len(files)
        print(f"[{cat}] {n}개 종목 검사 시작", flush=True)
        catStart = time.time()
        catStats = {"checked": 0, "fresh": 0, "stale": 0, "repaired": 0, "failed": 0}

        for i, p in enumerate(files, 1):
            sc = p.stem
            catStats["checked"] += 1
            stale = _checkRemoteFreshness(sc, p, cat)
            if stale is None:
                catStats["failed"] += 1
            elif stale:
                catStats["stale"] += 1
                try:
                    _refreshFromHf(sc, p, cat)
                    catStats["repaired"] += 1
                except Exception as e:  # noqa: BLE001
                    catStats["failed"] += 1
                    print(f"  ! {sc}: {type(e).__name__}", flush=True)
            else:
                catStats["fresh"] += 1

            if i % 50 == 0 or i == n:
                el = time.time() - catStart
                rate = i / el if el > 0 else 0
                eta = (n - i) / rate if rate > 0 else 0
                print(
                    f"  [{cat}] {i}/{n} fresh={catStats['fresh']} repaired={catStats['repaired']} "
                    f"failed={catStats['failed']} ({rate:.1f}/s ETA {eta:.0f}s)",
                    flush=True,
                )

        for k, v in catStats.items():
            totals[k] += v
        print(f"[{cat}] 완료: {catStats}", flush=True)

    elapsed = time.time() - started
    print(f"\n=== 전체 결과 ({elapsed:.0f}초) ===", flush=True)
    print(f"checked={totals['checked']} fresh={totals['fresh']} stale={totals['stale']} "
          f"repaired={totals['repaired']} failed={totals['failed']}", flush=True)
    return 0 if totals["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
