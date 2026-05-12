"""Docstring 자동 6 sub-section sweep — P-PR3 완주 보조.

providers/ 공개 함수 docstring 에 누락 6 sub-section 자동 stub 추가.
SeeAlso/Requires 는 docstringAutoFill.py (P-PR2) 가 처리 — 본 도구는 4 신규
sub-section 만:
    Capabilities: 1 줄 stub
    Guide: 1 줄 stub
    AIContext: 1 줄 stub
    LLM Specifications: 6 sub-keys (AntiPatterns/OutputSchema/Prerequisites/
                        Freshness/Dataflow/TargetMarkets) 각 1 줄 stub

면제 (audit 와 일치):
    - private (_*) 함수
    - 단순 wrapper (≤2 stmt + return) — Capabilities/Guide/AIContext 면제
    - 인자 0 + return None — Specifications 면제
    - docstring 없는 함수 (별도 4 섹션 audit 가 강제)
    - single-line docstring (변환 복잡 — skip)

mode:
    --dry-run (default) — patches 카운트만
    --apply — 실제 file patch
    --module <path> — 1 모듈만
    --target <providers/dart> — provider 단위
    --max <N> — 파일당 패치 함수 상한 (기본 50)

P-PR3 종료 commit 직전 1 회 sweep + 수동 채우기는 후속 P-PR3b.
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

_SECTION_KEYWORDS = {
    "Capabilities": ("Capabilities:", "Capabilities\n", "기능:", "기능\n"),
    "Guide": ("Guide:", "Guide\n", "가이드:", "가이드\n"),
    "AIContext": ("AIContext:", "AI Context:", "AIContext\n", "AI 컨텍스트:"),
    "Specifications": ("LLM Specifications:", "## LLM Specifications", "LLM Specifications\n"),
}


def _hasSection(docstring: str, section: str) -> bool:
    return any(kw in docstring for kw in _SECTION_KEYWORDS[section])


def _isWrapper(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if len(func.body) > 2:
        return False
    last = func.body[-1] if func.body else None
    return bool(isinstance(last, ast.Return) and last.value is not None)


def _isPureReturnNone(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    posargs = [a for a in func.args.args if a.arg not in ("self", "cls")]
    if posargs or func.args.kwonlyargs or func.args.vararg or func.args.kwarg:
        return False
    if func.returns is None:
        return True
    if isinstance(func.returns, ast.Constant) and func.returns.value is None:
        return True
    if isinstance(func.returns, ast.Name) and func.returns.id == "None":
        return True
    return False


def _buildStub(missing: set[str], indent: str) -> list[str]:
    """missing 섹션마다 stub 라인 list — indent 는 docstring 내부 들여쓰기."""
    lines: list[str] = []

    if "Capabilities" in missing:
        lines.append("")
        lines.append(f"{indent}Capabilities:")
        lines.append(f"{indent}    - <TODO: 함수 핵심 책임 요약>")

    if "Guide" in missing:
        lines.append("")
        lines.append(f"{indent}Guide:")
        lines.append(f"{indent}    - <TODO: 사용 시나리오>")

    if "AIContext" in missing:
        lines.append("")
        lines.append(f"{indent}AIContext:")
        lines.append(f"{indent}    <TODO: AI 호출 컨텍스트>")

    if "Specifications" in missing:
        lines.append("")
        lines.append(f"{indent}LLM Specifications:")
        lines.append(f"{indent}    AntiPatterns:")
        lines.append(f"{indent}        - <TODO: 안티패턴>")
        lines.append(f"{indent}    OutputSchema:")
        lines.append(f"{indent}        - <TODO: 출력 형태>")
        lines.append(f"{indent}    Prerequisites:")
        lines.append(f"{indent}        - <TODO: 사전조건>")
        lines.append(f"{indent}    Freshness:")
        lines.append(f"{indent}        - <TODO: 데이터 freshness>")
        lines.append(f"{indent}    Dataflow:")
        lines.append(f"{indent}        - <TODO: 데이터 흐름>")
        lines.append(f"{indent}    TargetMarkets:")
        lines.append(f"{indent}        - <TODO: 대상 시장>")

    return lines


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


def _patchFile(srcPath: Path, dryRun: bool, maxFuncs: int) -> tuple[int, list[tuple[str, set[str]]]]:
    try:
        text = srcPath.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return 0, []

    lines = text.splitlines(keepends=True)
    edits: list[tuple[int, str]] = []
    report: list[tuple[str, set[str]]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        docExpr = _docstringExpr(node)
        if docExpr is None:
            continue
        docstring = docExpr.value.value
        missing: set[str] = set()
        for section in ("Capabilities", "Guide", "AIContext", "Specifications"):
            if _hasSection(docstring, section):
                continue
            missing.add(section)

        isWrapper = _isWrapper(node)
        isPureNone = _isPureReturnNone(node)
        if isWrapper:
            missing.discard("Capabilities")
            missing.discard("Guide")
            missing.discard("AIContext")
        if isPureNone:
            missing.discard("Specifications")

        if not missing:
            continue

        endLine = docExpr.end_lineno
        if endLine is None:
            continue
        srcLine = lines[endLine - 1]
        indent = _detectIndent(srcLine)

        is_single_line = endLine == docExpr.lineno
        if is_single_line:
            continue

        stubLines = _buildStub(missing, indent)
        if not stubLines:
            continue

        insertAt = endLine - 1
        stubText = "\n".join(stubLines) + "\n"
        edits.append((insertAt, stubText))
        try:
            relPath = srcPath.relative_to(_REPO).as_posix()
        except ValueError:
            relPath = srcPath.name
        funcKey = f"{relPath}::{node.name}"
        report.append((funcKey, missing))
        if len(report) >= maxFuncs:
            break

    if not edits:
        return 0, []

    new_lines = lines[:]
    for insertAt, stubText in sorted(edits, key=lambda e: -e[0]):
        new_lines.insert(insertAt, stubText)

    if dryRun:
        try:
            disp = srcPath.relative_to(_REPO).as_posix()
        except ValueError:
            disp = srcPath.name
        print(f"  [{disp}] {len(edits)} patches")
        return len(edits), report

    srcPath.write_text("".join(new_lines), encoding="utf-8")
    return len(edits), report


def main() -> int:
    parser = argparse.ArgumentParser(description="providers/ docstring 6 sub-section auto-fill")
    parser.add_argument("--target", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--module", default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max", type=int, default=50)
    args = parser.parse_args()

    dryRun = not args.apply

    if args.module:
        targets = [(_REPO / args.module).resolve()]
    else:
        target = (_REPO / args.target).resolve()
        if not target.exists():
            print(f"ERROR: target 부재 — {target}", file=sys.stderr)
            return 1
        targets = sorted(target.rglob("*.py"))

    total_patches = 0
    total_files = 0
    print(f"=== docstring 6-section auto-fill (P-PR3) — {'dry-run' if dryRun else 'APPLY'} ===")
    print(f"target: {args.module or args.target}  max/file: {args.max}\n")

    for srcPath in targets:
        if "__pycache__" in srcPath.parts:
            continue
        if not srcPath.is_file() or srcPath.suffix != ".py":
            continue
        count, _report = _patchFile(srcPath, dryRun=dryRun, maxFuncs=args.max)
        if count:
            total_patches += count
            total_files += 1

    print(f"\n=== 결과: {total_files} files, {total_patches} patches ===")
    if dryRun:
        print("(dry-run — 실제 적용 시 --apply 추가)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
