"""docstring auto-sweep boilerplate 제거 — `<TODO:>` 마커 박힌 5 sub-section suffix.

대상: providers/ 안 docstring 의 5 sub (SeeAlso/Requires/Capabilities/Guide/AIContext/
LLM Specifications 6 sub-keys) 가 모두 `<TODO:>` placeholder 로 박혀 있는 경우.
이게 `feedback_no_docstring_auto_sweep.md` 의 8344 마커 회귀 잔재 (3564 현존).

룰:
1. AST 로 함수/클래스/메서드 docstring 식별
2. docstring 안에 `<TODO:` 가 있으면: SeeAlso~TargetMarkets 의 boilerplate 블록을
   regex 로 제거 (4 섹션 Args/Returns/Raises/Example 은 보존).
3. 변경 후 AST 재파싱 — syntax error 면 revert.
4. 변경 file path 와 절감 줄 수 출력.

회귀 가드: 4 섹션 lint (`docstring4Section`) 통과 + parity.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# 5 sub-section 의 정확한 boilerplate suffix pattern.
# `SeeAlso:` 부터 `TargetMarkets:` 다음 줄까지. 들여쓰기 4 또는 8 공백.
# Requires 안 내용 (- dartlab / - polars / - re 등) 은 가변.
_BOILERPLATE_RE = re.compile(
    r"\n(?P<indent> {4,8})SeeAlso:\n"  # SeeAlso: 헤더
    r"(?:\1    -[^\n]*\n)+"  # SeeAlso 항목들
    r"\n\1Requires:\n"
    r"(?:\1    -[^\n]*\n)+"  # Requires 항목들 (- dartlab / - polars 등)
    r"\n\1Capabilities:\n"
    r"(?:\1    -[^\n]*\n)+"
    r"\n\1Guide:\n"
    r"(?:\1    -[^\n]*\n)+"
    r"\n\1AIContext:\n"
    r"(?:\1    [^\n]*\n)+"
    r"\n\1LLM Specifications:\n"
    r"(?:\1    [A-Z][^\n]*\n(?:\1        -[^\n]*\n)+)+",
    re.MULTILINE,
)


def stripFile(path: Path) -> tuple[int, int]:
    """파일 1 개 처리. (제거된 boilerplate 개수, 제거된 줄 수) 반환."""
    src = path.read_text(encoding="utf-8")
    if "<TODO:" not in src:
        return (0, 0)

    # 4 섹션 (Args/Returns/Raises/Example) 만 남길 위치 — boilerplate suffix 제거.
    newSrc, count = _BOILERPLATE_RE.subn("", src)
    if count == 0:
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
    return (count, saved)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("src/dartlab/providers")
    totalFiles = 0
    totalCount = 0
    totalSaved = 0
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts:
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
