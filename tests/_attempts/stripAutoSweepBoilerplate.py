"""docstring auto-sweep boilerplate 제거 — `<TODO:>` 마커 박힌 5 sub-section suffix.

대상: providers/ 안 docstring 의 5 sub (SeeAlso/Requires/Capabilities/Guide/AIContext/
LLM Specifications 6 sub-keys) 가 `<TODO:>` placeholder 로 박혀 있는 경우.

룰:
1. 각 section 별로 독립 regex — 순서 무관 (filingHelpers 같은 후순 배치도 대응)
2. section 내용이 *오직 `<TODO:>` placeholder + 정적 항목 (- dartlab 등)* 이면 제거
3. AST 재파싱 검증 — error 면 revert
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# 각 section: 헤더 한 줄 + 다음 빈 줄까지의 들여쓰기 block.
# 다음 section/text/closing """ 가 등장하면 종료.
# pattern: 들여쓰기 4~8, 헤더 colon, 빈 줄 X (empty separator 가 다음 stmt 시작),
# 라인은 ` ` * (indent+4) 또는 더 깊은 들여쓰기 (sub-section).

# 5 stub sections — `<TODO:>` 만 또는 정적 `- dartlab/polars` 류만 가지는 boilerplate.
# 비-stub (이미 의미 채워진) section 은 보존.
_TODO_BOILERPLATE_PATTERNS = [
    # SeeAlso block — `<TODO:>` 만이거나 짧은 placeholder
    re.compile(
        r"\n(?P<i> {4,8})SeeAlso:\n"
        r"(?:\1    - ?<TODO: ?[^\n]*>\n)+",
        re.MULTILINE,
    ),
    # Requires block — 자동 박힌 dartlab/polars/datetime 류 (의미 없는 박물관)
    re.compile(
        r"\n(?P<i> {4,8})Requires:\n"
        r"(?:\1    - (?:dartlab|polars|datetime|re|json|os|sys|pathlib|typing|collections|functools|hashlib|gc|time|threading|logging|html|httpx|requests)\n)+",
        re.MULTILINE,
    ),
    re.compile(
        r"\n(?P<i> {4,8})Capabilities:\n"
        r"(?:\1    - ?<TODO: ?[^\n]*>\n)+",
        re.MULTILINE,
    ),
    re.compile(
        r"\n(?P<i> {4,8})Guide:\n"
        r"(?:\1    - ?<TODO: ?[^\n]*>\n)+",
        re.MULTILINE,
    ),
    re.compile(
        r"\n(?P<i> {4,8})AIContext:\n"
        r"\1    ?<TODO: ?[^\n]*>\n",
        re.MULTILINE,
    ),
    # LLM Specifications — 6 sub-key block 모두 <TODO:>
    re.compile(
        r"\n(?P<i> {4,8})LLM Specifications:\n"
        r"\1    AntiPatterns:\n\1        -[^\n]*\n"
        r"\1    OutputSchema:\n\1        -[^\n]*\n"
        r"\1    Prerequisites:\n\1        -[^\n]*\n"
        r"\1    Freshness:\n\1        -[^\n]*\n"
        r"\1    Dataflow:\n\1        -[^\n]*\n"
        r"\1    TargetMarkets:\n\1        -[^\n]*\n",
        re.MULTILINE,
    ),
    # Returns <TODO:> placeholder (간단 변환만)
    re.compile(
        r"\n(?P<i> {4,8})Returns:\n"
        r"\1    <TODO: ?return desc[^\n]*>\n",
        re.MULTILINE,
    ),
]


def stripFile(path: Path) -> tuple[int, int]:
    src = path.read_text(encoding="utf-8")
    if "<TODO:" not in src:
        return (0, 0)

    newSrc = src
    totalCount = 0
    for pattern in _TODO_BOILERPLATE_PATTERNS:
        newSrc, count = pattern.subn("", newSrc)
        totalCount += count

    if totalCount == 0:
        return (0, 0)

    # 결과 syntax 검증
    try:
        ast.parse(newSrc)
    except SyntaxError as exc:
        print(f"  SyntaxError in {path}: {exc} — revert", file=sys.stderr)
        return (0, 0)

    linesBefore = src.count("\n")
    linesAfter = newSrc.count("\n")
    saved = linesBefore - linesAfter
    path.write_text(newSrc, encoding="utf-8")
    return (totalCount, saved)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("src/dartlab/providers")
    totalFiles = 0
    totalCount = 0
    totalSaved = 0
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts or "edinet" in p.parts:
            continue
        count, saved = stripFile(p)
        if count:
            totalFiles += 1
            totalCount += count
            totalSaved += saved
            print(f"{p}: removed {count} blocks, saved {saved} lines")
    print(f"\n=== TOTAL: {totalFiles} files, {totalCount} blocks, {totalSaved} lines ===")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
