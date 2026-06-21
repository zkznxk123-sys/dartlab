"""Thin shim — macro regime(forecast 4모델 + 수익률곡선 + GaR + Hamilton band) JSON 빌드.

빌드 오케스트레이션은 in-library SSOT ``dartlab.pipeline.stages.macro.runMacroRegime`` 로
흡수됨(analyzeForecast/analyzeRates/growthAtRisk/hamiltonRegime L2 위임 보존). 본 스크립트는
CLI 계약(--out/--repo-id/--push)만 보존하는 진입점이며, 정식 호출은
``python -m dartlab.pipeline macro``.

실행::

    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py
    uv run python -X utf8 .github/scripts/sync/buildMacroRegime.py --push
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
    parser.add_argument("--out", default="data/macro/regime", help="출력 디렉토리 (기본 data/macro/regime)")
    parser.add_argument("--repo-id", default="eddmpython/dartlab-data")
    parser.add_argument("--push", action="store_true", help="HF dataset publish 활성화")
    args = parser.parse_args()

    # --out 은 data/macro/regime 형태 — runMacroRegime 는 DARTLAB_DATA_DIR/macro/regime 에 쓴다.
    outPath = Path(args.out)
    if outPath.name == "regime" and outPath.parent.name == "macro":
        os.environ["DARTLAB_DATA_DIR"] = str(outPath.parent.parent)

    from dartlab.pipeline.stages.macro import runMacroRegime

    result = runMacroRegime(upload=args.push)
    return 0 if result.report.err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
