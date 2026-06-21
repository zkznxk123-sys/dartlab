"""Thin shim — macro.json (대시보드 v20) offline prebuild 진입점.

offline 합성 오케스트레이션은 in-library SSOT
``dartlab.pipeline.stages.prebuild.runMacroJson`` 으로 흡수됨(enforceOffline 첫 stmt 보존·
SECTOR_SENSITIVITY 이전·analyzeTransmission fetch-independent 위임). 본 스크립트는 진입점
계약만 보존하며, 정식 호출은 ``python -m dartlab.pipeline macroJson``.

⛔ offline 불변: main() 첫 stmt = ``enforceOffline()`` (test_prebuild_offline AST 게이트).

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildMacroJson.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()

    from dartlab.pipeline.stages.prebuild import runMacroJson

    result = runMacroJson()
    return 0 if result.report.err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
