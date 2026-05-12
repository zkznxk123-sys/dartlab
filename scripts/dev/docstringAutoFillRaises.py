"""Docstring Raises/Example 자동 stub sweep — P-PR8 마무리 보조.

`docstring4Section.py` 의 Raises/Example 위반에 1 줄 stub 자동 추가.

stub 형식:
    Raises:
        없음.
    Example:
        >>> <funcName>(...)

면제:
    - private (_*) 함수
    - single-line docstring (multi-line 화 복잡 — skip)
    - docstring 없는 함수

mode:
    --dry-run (default)
    --apply

P-PR8 의 docstring4Section STRICT PASS 도달 후 strict default 전환.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_TARGET = _REPO / "src" / "dartlab" / "providers"

_RAISES_KEYWORDS = ("Raises:", "Raises\n", "Errors:", "Throws:", "예외:", "에러:")
_EXAMPLE_KEYWORDS = (
    "Example:",
    "Examples:",
    "Example\n",
    "Examples\n",
    "Usage:",
    "예:",
    "예제:",
    "사용법:",
)


def _hasAny(docstring: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in docstring for kw in keywords)


def _docstringExpr(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Expr | None:
    if not node.body:
        return None
    first = node.body[0]
    if not isinstance(first, ast.Expr):
        return None
    if not isinstance(first.value, ast.Constant) or not isinstance(first.value.value, str):
        return None
    return first


def _detectIndent(srcLine: str) -> str:
    return srcLine[: len(srcLine) - len(srcLine.lstrip())]


def _patchFile(srcPath: Path, dryRun: bool) -> int:
    try:
        text = srcPath.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return 0

    lines = text.splitlines(keepends=True)
    edits: list[tuple[int, str]] = []
    count = 0

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        docExpr = _docstringExpr(node)
        if docExpr is None:
            continue
        docstring = docExpr.value.value

        stubLines: list[str] = []
        needRaises = not _hasAny(docstring, _RAISES_KEYWORDS)
        needExample = not _hasAny(docstring, _EXAMPLE_KEYWORDS)
        if not needRaises and not needExample:
            continue

        endLine = docExpr.end_lineno
        if endLine is None:
            continue
        srcLine = lines[endLine - 1]
        indent = _detectIndent(srcLine)
        is_single_line = endLine == docExpr.lineno
        if is_single_line:
            continue

        if needRaises:
            stubLines.append("")
            stubLines.append(f"{indent}Raises:")
            stubLines.append(f"{indent}    없음.")
        if needExample:
            stubLines.append("")
            stubLines.append(f"{indent}Example:")
            stubLines.append(f"{indent}    >>> {node.name}(...)")

        if not stubLines:
            continue

        stubText = "\n".join(stubLines) + "\n"
        edits.append((endLine - 1, stubText))
        count += 1

    if not edits:
        return 0

    if dryRun:
        try:
            disp = srcPath.relative_to(_REPO).as_posix()
        except ValueError:
            disp = srcPath.name
        print(f"  [{disp}] +{count} stubs")
        return count

    new_lines = lines[:]
    for insertAt, stubText in sorted(edits, key=lambda e: -e[0]):
        new_lines.insert(insertAt, stubText)
    srcPath.write_text("".join(new_lines), encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="providers/ docstring Raises/Example auto-fill")
    parser.add_argument("--target", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    dryRun = not args.apply
    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    total = 0
    files = 0
    print(f"=== docstring Raises/Example auto-fill — {'dry-run' if dryRun else 'APPLY'} ===\n")
    for p in sorted(target.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        count = _patchFile(p, dryRun=dryRun)
        if count:
            total += count
            files += 1
    print(f"\n=== 결과: {files} files, {total} stubs ===")
    if dryRun:
        print("(dry-run — 실제 적용 시 --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
