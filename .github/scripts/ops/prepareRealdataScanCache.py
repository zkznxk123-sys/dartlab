"""Build shared scan prebuild files for realData CI shards."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    from dartlab.scan.builders.kr.common import scanDir
    from dartlab.scan.builders.kr.core import buildChanges, buildFinance, buildFinanceLite, buildReport
    from dartlab.scan.builders.kr.shares import buildSharesOutstandingSafe
    from dartlab.scan.io import parquet as scan_parquet

    scan_dir = Path(scanDir())
    scan_dir.mkdir(parents=True, exist_ok=True)

    print(f"[prepareRealdataScanCache] build into: {scan_dir}")
    buildChanges(sinceYear=2021, verbose=True)
    finance_path = buildFinance(sinceYear=2021, verbose=True)
    if finance_path is not None:
        buildFinanceLite(verbose=True)
    buildReport(sinceYear=2021, verbose=True)
    buildSharesOutstandingSafe(verbose=True)

    missing = scan_parquet._missingScanFiles(scan_dir, requireReports=True)
    if missing:
        print("[prepareRealdataScanCache] scan prebuild incomplete", file=sys.stderr)
        for rel in missing[:20]:
            print(f"  - {rel}", file=sys.stderr)
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more", file=sys.stderr)
        return 1

    files = sorted(p for p in scan_dir.rglob("*.parquet") if p.is_file())
    total_size = sum(p.stat().st_size for p in files)
    print(f"[prepareRealdataScanCache] ready: {scan_dir}")
    print(f"[prepareRealdataScanCache] files={len(files)} size_mb={total_size / 1024 / 1024:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
