"""viewer.py / companyApi.py 의 changeSummary 회귀 차단 lint guard.

Phase B 슬림화 결과 ChangeSummary / InlineDiff / ChangeDigest / AnnotatedLine dataclass
와 관련 함수가 모두 폐기됨. 후속 PR 이 부주의하게 re-import 하지 않도록 본 lint guard.

검사:
1. viewer.py 안 `ChangeSummary` / `InlineDiff` / `ChangeDigest` / `AnnotatedLine` /
   `ViewerDiffChunk` 류 이름이 다시 나타나지 않음.
2. viewer.py 안 `_buildChangeSummary` / `_computeInlineDiff` / `_buildDigest` /
   `_buildAnnotatedBlame` 함수 정의가 다시 나타나지 않음.
3. companyApi.py 안 `_breakParagraphs` / `_PARA_BREAK_PATTERNS` 정의가 다시 나타나지
   않음 (frontend `_bodyParagraphs` 와 중복 회귀 차단).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

VIEWER_PATH = REPO_ROOT / "src" / "dartlab" / "providers" / "dart" / "docs" / "viewer.py"
COMPANY_API_PATH = REPO_ROOT / "src" / "dartlab" / "server" / "services" / "companyApi.py"

# viewer.py 안 금지 패턴 — Phase B 슬림화 후 회귀
_VIEWER_FORBIDDEN = (
    (
        re.compile(
            r"^class\s+(?:ChangeSummary|InlineDiff|ChangeDigest|AnnotatedLine|ViewerDiffChunk|ChangeDigestItem)\b"
        ),
        "dead dataclass 정의",
    ),
    (re.compile(r"^def\s+_buildChangeSummary\b"), "dead function _buildChangeSummary"),
    (re.compile(r"^def\s+_computeInlineDiff\b"), "dead function _computeInlineDiff"),
    (re.compile(r"^def\s+_buildDigest(?:Direct)?\b"), "dead function _buildDigest / _buildDigestDirect"),
    (re.compile(r"^def\s+_buildAnnotatedBlame\b"), "dead function _buildAnnotatedBlame"),
    (re.compile(r"^def\s+_serializeChangeDigest\b"), "dead function _serializeChangeDigest"),
    (re.compile(r"^def\s+_serializeViewerDiffChunk\b"), "dead function _serializeViewerDiffChunk"),
)

_COMPANY_API_FORBIDDEN = (
    (re.compile(r"^_PARA_BREAK_PATTERNS\b"), "dead constant _PARA_BREAK_PATTERNS"),
    (re.compile(r"^def\s+_breakParagraphs\b"), "dead function _breakParagraphs"),
)


def _scan(path: Path, rules: tuple[tuple[re.Pattern[str], str], ...]) -> list[tuple[int, str, str]]:
    if not path.exists():
        return []
    violations: list[tuple[int, str, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for pattern, reason in rules:
            if pattern.match(line):
                violations.append((idx, reason, line))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    viewer_v = _scan(VIEWER_PATH, _VIEWER_FORBIDDEN)
    company_api_v = _scan(COMPANY_API_PATH, _COMPANY_API_FORBIDDEN)
    total = len(viewer_v) + len(company_api_v)

    if viewer_v:
        print(f"[FAIL] {VIEWER_PATH.name}: {len(viewer_v)} violations")
        for line_no, reason, content in viewer_v[:10]:
            print(f"    L{line_no} {reason}: {content[:80]}")
    else:
        print(f"[OK] {VIEWER_PATH.name}: 0 violations")

    if company_api_v:
        print(f"[FAIL] {COMPANY_API_PATH.name}: {len(company_api_v)} violations")
        for line_no, reason, content in company_api_v[:10]:
            print(f"    L{line_no} {reason}: {content[:80]}")
    else:
        print(f"[OK] {COMPANY_API_PATH.name}: 0 violations")

    print(f"\n=== TOTAL: {total} violations ===")

    if args.strict and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
