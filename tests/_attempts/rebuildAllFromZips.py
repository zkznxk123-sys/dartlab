"""전체 종목 rebuildFromZips — data/dart/original/docs/{code}/*.zip → data/dart/docs/{code}.parquet.

사용자 지시 (2026-05-22): "다시수집하고 전체 docs파케 갈아끼우면서 전면검사".
Phase R2 — Phase R1 (fetchOriginalDocs.py) 완료 후 또는 진행 중 일괄 실행.

resume-safe — 이미 작업된 종목 skip (출력 parquet 의 mtime > 입력 zip 디렉토리 mtime).
실행: uv run python -X utf8 tests/_attempts/rebuildAllFromZips.py
       uv run python -X utf8 tests/_attempts/rebuildAllFromZips.py --skip-existing
       uv run python -X utf8 tests/_attempts/rebuildAllFromZips.py --limit 50
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

ORIGINAL_DIR = REPO / "data" / "dart" / "original" / "docs"
DOCS_DIR = REPO / "data" / "dart" / "docs"
STATE = REPO / ".dartlab" / "audit" / "rebuildAllFromZips.txt"


def _zipMtime(code: str) -> float:
    """code 의 zip 디렉토리 가장 최근 zip mtime."""
    d = ORIGINAL_DIR / code
    if not d.exists():
        return 0.0
    return max((z.stat().st_mtime for z in d.glob("*.zip")), default=0.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-existing", action="store_true", help="parquet 이 zip 보다 새로우면 skip")
    parser.add_argument("--codes", default="", help="콤마 구분 (빈 값 = 전체)")
    args = parser.parse_args()

    from dartlab.providers.dart.openapi.corpCode import _CACHE_FILE
    from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    else:
        # zip 디렉토리가 있는 종목만 (≥ 1 zip)
        codes = []
        for d in sorted(ORIGINAL_DIR.iterdir()):
            if not d.is_dir():
                continue
            if any(d.glob("*.zip")):
                codes.append(d.name)

    if args.limit > 0:
        codes = codes[: args.limit]

    print(f"target: {len(codes)} codes")
    STATE.parent.mkdir(parents=True, exist_ok=True)

    # corp meta lookup — 디스크 캐시 직독 (loadCorpCodes 의 24h freshness 회피 + API 차단 회피)
    import polars as pl

    if _CACHE_FILE.exists():
        try:
            corpDf = pl.read_parquet(_CACHE_FILE)
        except Exception:
            corpDf = None
    else:
        corpDf = None

    written_total = 0
    error_count = 0
    skipped_count = 0
    t0 = time.time()
    with STATE.open("w", encoding="utf-8") as state_f:
        state_f.write(f"# rebuildAllFromZips start {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        state_f.flush()
        for i, code in enumerate(codes, 1):
            parquet = DOCS_DIR / f"{code}.parquet"
            zip_mtime = _zipMtime(code)
            if args.skip_existing and parquet.exists() and parquet.stat().st_mtime > zip_mtime:
                skipped_count += 1
                continue

            # corp meta lookup. corp_code/name 둘 다 truthy 여야 ZipDocsCollector
            # 가 API 회피 (init 의 `if corpCode and corpName:` 분기). 캐시에 없을 때는
            # stockCode 자체를 fallback — 의미 0 이지만 빈 string 회피로 API 차단.
            corp_code = code  # fallback (truthy)
            corp_name = code
            if corpDf is not None:
                try:
                    m = corpDf.filter(pl.col("stock_code") == code)
                    if m.height > 0:
                        cc = m["corp_code"][0]
                        cn = m["corp_name"][0]
                        if cc:
                            corp_code = cc
                        if cn:
                            corp_name = cn
                except Exception:
                    pass

            try:
                c = ZipDocsCollector(code, corpCode=corp_code, corpName=corp_name)
                n = c.rebuildFromZips()
                written_total += n
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(codes) - i) / rate if rate > 0 else 0
                msg = f"[{i}/{len(codes)}] {code}: rows={n} ({rate:.1f}/s, ETA {eta / 60:.1f}m)"
                print(msg)
                state_f.write(f"{code} {n}\n")
                state_f.flush()
            except Exception as exc:
                error_count += 1
                print(f"[{i}/{len(codes)}] {code}: ERR {str(exc)[:100]}")
                state_f.write(f"{code} ERR {str(exc)[:80]}\n")
                state_f.flush()

    print(f"\n=== DONE === written_total={written_total:,} errors={error_count} skipped={skipped_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
