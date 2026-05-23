"""107 종목 일괄 XML→새 schema parquet 변환 + docs/ swap + audit.

전제:
- data/dart/original/docs/{code}/{rcept_no}.zip — 107 종목 zip 다운 완료
- data/dart/docs/{code}.parquet 백업: tests/_attempts/docs_backup_v6/

순서:
1. data/dart/docs/ 전체 백업 (tests/_attempts/docs_backup_v6/)
2. 107 종목 모두 새 schema 변환 (tests/_attempts/xml_docs_v6/{code}.parquet)
3. swap: 새 parquet → data/dart/docs/{code}.parquet
4. sectionsRawCompare audit 100 종목 → spurious/missing 비교

실행: uv run python -X utf8 tests/_attempts/xmlBulkBuildSwap.py
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests._attempts.xmlDocsBuilder import buildCodeParquet  # noqa: E402

ORIGINAL_DIR = REPO_ROOT / "data" / "dart" / "original" / "docs"
DOCS_DIR = REPO_ROOT / "data" / "dart" / "docs"
BACKUP_DIR = REPO_ROOT / "tests" / "_attempts" / "docs_backup_v6"
NEW_DIR = REPO_ROOT / "tests" / "_attempts" / "xml_docs_v6"


def main() -> int:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    NEW_DIR.mkdir(parents=True, exist_ok=True)

    codes = sorted(p.name for p in ORIGINAL_DIR.iterdir() if p.is_dir())
    print(f"target: {len(codes)} codes")

    # Phase 1: 백업 + 빌드
    t0 = time.time()
    built = 0
    for i, code in enumerate(codes, 1):
        oldP = DOCS_DIR / f"{code}.parquet"
        backupP = BACKUP_DIR / f"{code}.parquet"
        newP = NEW_DIR / f"{code}.parquet"
        if oldP.exists() and not backupP.exists():
            shutil.copy2(oldP, backupP)
        if newP.exists():
            built += 1
            continue
        try:
            df = buildCodeParquet(code, ORIGINAL_DIR)
            if df.shape[0] == 0:
                print(f"  [{i}/{len(codes)}] {code}: empty df")
                continue
            df.write_parquet(newP)
            built += 1
            elapsed = time.time() - t0
            eta = elapsed / built * (len(codes) - i)
            print(f"  [{i}/{len(codes)}] {code}: rows={df.shape[0]} ETA={eta:.0f}s")
            sys.stdout.flush()
        except Exception as exc:
            print(f"  [{i}/{len(codes)}] {code}: ERR {exc!s}[:100]")

    print(f"\nbuilt {built}/{len(codes)} parquets")

    # Phase 2: swap
    swapped = 0
    for code in codes:
        newP = NEW_DIR / f"{code}.parquet"
        oldP = DOCS_DIR / f"{code}.parquet"
        if newP.exists() and newP.stat().st_size > 1000:
            shutil.copy2(newP, oldP)
            swapped += 1
    print(f"swapped {swapped}/{len(codes)} parquets to docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
