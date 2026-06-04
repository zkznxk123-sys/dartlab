"""bitemporal schema 마이그레이션 — 옛 HF parquet → 신 schema (1 회용).

Sprint 4 (Bitemporal + PIT) 활성화 도구. 기존 ``data/krx/prices/raw-{year}.parquet``
은 ``BAS_DD`` (단일 시간) 만 보유 — 본 도구가 ``business_time`` + ``knowledge_time``
2 컬럼 추가해서 신 parquet 출력.

```
실행::

    uv run python -X utf8 .github/scripts/prebuild/migrateBitemporalSchema.py --dry-run
    uv run python -X utf8 .github/scripts/prebuild/migrateBitemporalSchema.py --year 2024 --out data/krx/prices/v2/

루트 정책:
    - business_time = BAS_DD (string YYYYMMDD → pl.Date)
    - knowledge_time = parquet file_mtime (당일 자정 UTC 보수적)
    - 기존 컬럼 모두 보존 (additive only — 다운스트림 회귀 0)

검증:
    - --dry-run: 옛 parquet 읽기 + 메모리 변환 + row count 보고 (디스크 write 0)
    - --year: 단일 연도만
    - 출력 디렉터리 (--out) 신규 — 기존 raw-*.parquet 파일 절대 덮어쓰기 금지

본 도구 실행 후:
    1. ``data/krx/prices/v2/raw-{year}.parquet`` 검증 — schema 확인
    2. HF Hub push (별도 도구 — bulkUploadHf.py)
    3. hfBulk.py 의 _CATEGORY 변경 (현재 'krxPrices' → 'krxPricesV2' or HF dataset 교체)
    4. 사용자 명시 결심 — production 활성

미동작 시 fallback: hfBulk.loadFiltered 의 BAS_DD fallback 분기 (Sprint 4 PR3 commit 18ba39185)
가 자동 동작 → 다운스트림 영향 0.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]

_log = logging.getLogger("migrateBitemporalSchema")

_DEFAULT_IN_DIR = REPO_ROOT / "data" / "krx" / "prices"
_DEFAULT_OUT_DIR = REPO_ROOT / "data" / "krx" / "prices" / "v2"


def _migrateOne(src: Path, dst: Path | None, *, dry_run: bool) -> dict:
    """단일 raw-{year}.parquet 읽어 신 schema 로 변환.

    Sig: ``_migrateOne(src, dst, *, dry_run) -> {'rows', 'mtime', 'written'}``
    """
    df = pl.read_parquet(src)
    rows = df.height
    mtime = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).date()

    if "BAS_DD" not in df.columns:
        _log.warning("BAS_DD 컬럼 부재 — skip: %s", src.name)
        return {"rows": rows, "mtime": mtime.isoformat(), "written": False}

    # BAS_DD (string YYYYMMDD) → pl.Date 변환 → business_time
    # 옛 컬럼 BAS_DD 유지 (additive only — 다운스트림 영향 0)
    df2 = df.with_columns(
        pl.col("BAS_DD").str.strptime(pl.Date, "%Y%m%d", strict=False).alias("business_time"),
        pl.lit(mtime).alias("knowledge_time"),
    )

    if dry_run:
        _log.info("DRY %s — rows=%d, mtime=%s", src.name, rows, mtime)
        return {"rows": rows, "mtime": mtime.isoformat(), "written": False}

    dst.parent.mkdir(parents=True, exist_ok=True)
    df2.write_parquet(dst)
    _log.info("WROTE %s → %s (rows=%d, +business_time, +knowledge_time)", src.name, dst, rows)
    return {"rows": rows, "mtime": mtime.isoformat(), "written": True}


def main(argv: list[str] | None = None) -> int:
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()  # prebuild = offline only (로컬 parquet 읽기/쓰기뿐, 네트워크 0)
    parser = argparse.ArgumentParser(description="HF parquet bitemporal schema 1 회용 마이그레이션")
    parser.add_argument("--in-dir", type=Path, default=_DEFAULT_IN_DIR)
    parser.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT_DIR)
    parser.add_argument("--year", type=int, help="단일 연도 (생략 시 전체)")
    parser.add_argument("--dry-run", action="store_true", help="디스크 write 0, 메모리 변환만")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    in_dir: Path = args.in_dir
    out_dir: Path = args.out_dir
    if not in_dir.exists():
        _log.error("in-dir 부재: %s", in_dir)
        return 1
    if in_dir.resolve() == out_dir.resolve():
        _log.error("in-dir 와 out-dir 같음 — 덮어쓰기 차단")
        return 1

    if args.year:
        files = [in_dir / f"raw-{args.year}.parquet"]
    else:
        files = sorted(in_dir.glob("raw-*.parquet"))

    if not files:
        _log.warning("대상 parquet 0 건 (in-dir=%s)", in_dir)
        return 0

    total_rows = 0
    total_written = 0
    for src in files:
        if not src.exists():
            _log.warning("skip 부재: %s", src.name)
            continue
        dst = out_dir / src.name
        meta = _migrateOne(src, dst, dry_run=args.dry_run)
        total_rows += meta["rows"]
        if meta["written"]:
            total_written += 1

    _log.info(
        "완료 — %d 파일 변환, %d rows, write %d (dry_run=%s)",
        len(files),
        total_rows,
        total_written,
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
