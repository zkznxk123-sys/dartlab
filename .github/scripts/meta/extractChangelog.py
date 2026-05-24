"""CHANGELOG.md 의 특정 버전 섹션 추출 — release.yml workflow 보조.

T14-4 — gh release create 의 --notes-file 입력 생성.

실행::

    python -X utf8 .github/scripts/meta/extractChangelog.py \
        --version 0.10.3 --output release-notes.md

입력 형식 (Keep a Changelog 1.1.0):
    ## [0.10.3] - 2026-06-15

    Added/Changed/Fixed/... 섹션들

    ## [0.10.2] - ...   ← 다음 버전 헤딩에서 멈춤
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def extractSection(text: str, version: str) -> str:
    """version 헤딩 직후부터 다음 ## 헤딩 직전까지 본문 추출."""
    # 헤딩 패턴: "## [0.10.3] - 2026-06-15" 또는 "## [0.10.3]"
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^# )",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="CHANGELOG 버전 섹션 추출 (T14-4)")
    parser.add_argument("--version", required=True, help="추출할 버전 (예: 0.10.3)")
    parser.add_argument("--output", required=True, help="출력 markdown 파일")
    args = parser.parse_args()

    if not CHANGELOG.exists():
        print(f"[extract] CHANGELOG.md 없음: {CHANGELOG}")
        return 1

    text = CHANGELOG.read_text(encoding="utf-8")
    section = extractSection(text, args.version)
    if not section:
        print(f"[extract] 버전 [{args.version}] 섹션 없음 — RELEASE.md 체크리스트 1 위반")
        return 2

    outputPath = Path(args.output)
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    outputPath.write_text(section + "\n", encoding="utf-8")
    print(f"[extract] {args.version} 섹션 → {outputPath} ({len(section)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
