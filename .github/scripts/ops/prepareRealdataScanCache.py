"""Prepare shared scan prebuild files for realData CI shards."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    from dartlab.scan.io import parquet as scan_parquet

    scan_dir = Path(scan_parquet._ensureScanData(requireReports=True))
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
