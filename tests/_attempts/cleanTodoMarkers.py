"""`<TODO: return desc>` / `<TODO: param desc>` 등 placeholder 정리.

각 위치마다 의미 채움이 어렵지만, placeholder 자체 제거는 안전.
- `<TODO: return desc> (TYPE)` → `TYPE — 결과.` (type 만 남김)
- `paramname: <TODO: param desc> (TYPE)` → `paramname: TYPE — 인자.`
- 기타 `- <TODO: ...>` 항목은 line 자체 제거 (의미 없는 placeholder)

회귀 가드:
- AST 재파싱 → SyntaxError 면 revert
- docstring4Section lint 통과 유지 (Args/Returns/Raises/Example header 유지)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# `<TODO: return desc> (TYPE)` → `TYPE — 결과.`
_RE_TODO_RETURN = re.compile(r"<TODO:\s*return desc>\s*\(([^)]+)\)")

# `paramname: <TODO: param desc> (TYPE)` → `paramname: TYPE.`
_RE_TODO_PARAM = re.compile(r"<TODO:\s*param desc>\s*\(([^)]+)\)")

# 빈 placeholder list 항목 (`- <TODO: ...>`) 줄 제거 (예: SeeAlso 안 잔재)
_RE_TODO_LIST_LINE = re.compile(r"^[ \t]*-[ \t]*<TODO:[^\n]*>\s*$\n?", re.MULTILINE)

# 일반 inline `<TODO: ...>` placeholder (다른 위치)
_RE_TODO_GENERIC = re.compile(r"<TODO:\s*([^>]+)>")


def cleanFile(path: Path) -> tuple[int, int]:
    src = path.read_text(encoding="utf-8")
    if "<TODO:" not in src:
        return (0, 0)

    newSrc = src

    # return desc 정리
    newSrc = _RE_TODO_RETURN.sub(r"\1 — 결과.", newSrc)
    # param desc 정리
    newSrc = _RE_TODO_PARAM.sub(r"\1.", newSrc)
    # 빈 - <TODO: ...> 라인 제거
    newSrc = _RE_TODO_LIST_LINE.sub("", newSrc)
    # 잔여 generic `<TODO: foo>` → `(foo)` 로 축약
    newSrc = _RE_TODO_GENERIC.sub(r"(\1)", newSrc)

    if newSrc == src:
        return (0, 0)

    # AST 검증
    try:
        ast.parse(newSrc)
    except SyntaxError as exc:
        print(f"SyntaxError in {path}: {exc} — revert", file=sys.stderr)
        return (0, 0)

    countBefore = src.count("<TODO:")
    countAfter = newSrc.count("<TODO:")
    saved = src.count("\n") - newSrc.count("\n")
    path.write_text(newSrc, encoding="utf-8")
    return (countBefore - countAfter, saved)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("src/dartlab/providers")
    totalFiles = 0
    totalCleared = 0
    totalSaved = 0
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts or "edinet" in p.parts:
            continue
        cleared, saved = cleanFile(p)
        if cleared:
            totalFiles += 1
            totalCleared += cleared
            totalSaved += saved
            print(f"{p}: cleared {cleared} markers, saved {saved} lines")
    print(f"\n=== TOTAL: {totalFiles} files, {totalCleared} markers, {totalSaved} lines ===")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
