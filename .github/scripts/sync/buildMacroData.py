"""Thin shim — FRED/ECOS/관세청 macro 벌크 빌드 진입점.

빌드 오케스트레이션은 in-library SSOT ``dartlab.pipeline.stages.macro.runMacroData`` 로
흡수됨(별도빌드 0·gather 위임 보존). 본 스크립트는 CLI 계약(--source/--out/--repo-id/
--push)만 보존하는 진입점이며, 정식 호출은 ``python -m dartlab.pipeline macro``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["fred", "ecos", "customs", "all"], default="all")
    parser.add_argument("--out", default="data/macro")
    parser.add_argument("--repo-id", default="eddmpython/dartlab-data")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    # --out 은 data/macro 형태 — runMacroData 는 DARTLAB_DATA_DIR/macro 에 쓴다.
    outPath = Path(args.out)
    if outPath.name == "macro":
        os.environ["DARTLAB_DATA_DIR"] = str(outPath.parent)

    from dartlab.pipeline.stages.macro import runMacroData

    result = runMacroData(source=args.source, upload=args.push)
    return 0 if result.report.err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
