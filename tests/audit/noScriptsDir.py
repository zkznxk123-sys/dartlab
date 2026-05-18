"""scripts/ 폴더 재생성 차단 — CLAUDE.md 강행규칙 자동 가드.

repo 루트에 `scripts/` 폴더가 존재하면 exit 2. 도메인 소유 강제 ([CLAUDE.md
"scripts/ 폴더 절대 금지"](file://./../CLAUDE.md)) 의 자동 검출.

Sig:
    main() -> int

Args:
    None — CLI argparse 없음. 진입점은 `if __name__ == "__main__":`.

Example:
    ``uv run python -X utf8 tests/audit/noScriptsDir.py``

Returns:
    exit 0 — scripts/ 부재 (정상).
    exit 2 — scripts/ 존재 (위반).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    """`scripts/` 폴더 존재 여부 검사."""
    scriptsDir = _REPO / "scripts"
    if scriptsDir.exists() and scriptsDir.is_dir():
        print(
            "[noScriptsDir] FAIL — scripts/ 폴더는 절대 금지 (CLAUDE.md 강행규칙).",
            file=sys.stderr,
        )
        print(
            "[noScriptsDir] 도구는 도메인 폴더에 — tests/audit/, src/dartlab/{engine}/,"
            " .github/scripts/, blog/_scripts/, notebooks/_scripts/, landing/_scripts/,"
            " .claude/ 중 하나.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
