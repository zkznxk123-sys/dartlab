"""Docstring 자동 4 섹션 sweep — P-PR2 트랙.

providers/ 의 공개 함수/메서드 docstring 에 4 섹션 (Args / Returns / SeeAlso / Requires)
자동 stub 추가. 본 도구는 누락 섹션만 채움 — 기존 섹션 보존 + 본문 무변경.

stub 형식 (operation.docstringStandard SSOT):
    Args: signature 의 parameter name → "<TODO: param desc>" stub 1 줄씩
    Returns: return type annotation → "<TODO: return desc> (<type>)" 1 줄
    SeeAlso: 같은 모듈 안 동일 prefix 함수 list (false positive 위험 → P-PR3 review)
    Requires: 본문 외부 import → dependency list ("<TODO: external requires>")

면제:
    - private (_*) 함수
    - 단순 wrapper (≤2 stmt + return) — SeeAlso/Requires 면제
    - 인자 0 + return None — Args/Returns 면제

mode:
    --dry-run (default) — diff 형식 stdout 출력 (~10 함수 head)
    --apply — 실제 file patch
    --module <path> — 1 모듈 단위
    --target <providers/dart> — provider 단위 (기본 src/dartlab/providers)
    --max <N> — 패치 함수 수 상한 (chunk 분할용, 기본 50)

P-PR3 (AI 직접 5 섹션 작성) 이 본 sweep 의 <TODO> 마커를 채우는 후속 작업.
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
    "Args": ("Args:", "Arguments:", "Parameters:", "매개변수:", "인자:"),
    "Returns": ("Returns:", "Return:"),
    "SeeAlso": ("SeeAlso:", "See Also:", "참고:"),
    "Requires": ("Requires:", "필요:", "전제:"),
}


def _hasSection(docstring: str, section: str) -> bool:
    keywords = _SECTION_KEYWORDS[section]
    return any(kw in docstring for kw in keywords)


def _isWrapper(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if len(func.body) > 2:
        return False
    last = func.body[-1] if func.body else None
    if isinstance(last, ast.Return) and last.value is not None:
        return True
    return False


def _isPureReturnNone(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """인자 0 + return None → 단순 side-effect."""
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


def _renderType(node: ast.expr | None) -> str:
    """type annotation node → 짧은 str."""
    if node is None:
        return "<unannotated>"
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _argNames(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, str]]:
    """함수 인자 list → [(name, type_str), ...]. self/cls 제외."""
    out: list[tuple[str, str]] = []
    for a in func.args.args:
        if a.arg in ("self", "cls"):
            continue
        out.append((a.arg, _renderType(a.annotation)))
    for a in func.args.kwonlyargs:
        out.append((a.arg, _renderType(a.annotation)))
    if func.args.vararg:
        out.append((f"*{func.args.vararg.arg}", _renderType(func.args.vararg.annotation)))
    if func.args.kwarg:
        out.append((f"**{func.args.kwarg.arg}", _renderType(func.args.kwarg.annotation)))
    return out


def _externalImports(tree: ast.AST) -> list[str]:
    """파일 level external import (dartlab.X / 외부 lib) 짧은 list — 상위 5 개."""
    imports: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                imports.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                imports.add(root)
    # noise 제거
    noise = {"__future__", "typing", "collections", "dataclasses", "re", "json", "sys", "os", "pathlib"}
    filtered = sorted(imports - noise)
    return filtered[:5]


def _buildStub(
    func: ast.FunctionDef | ast.AsyncFunctionDef, missing: set[str], imports: list[str], indent: str
) -> list[str]:
    """missing 섹션마다 stub 라인 list 생성 — `indent` 는 docstring 내부 들여쓰기 (보통 '    ' x level)."""
    lines: list[str] = []

    if "Args" in missing:
        args = _argNames(func)
        if args:
            lines.append("")
            lines.append(f"{indent}Args:")
            for name, typ in args:
                lines.append(f"{indent}    {name}: <TODO: param desc> ({typ})")

    if "Returns" in missing:
        ret = _renderType(func.returns)
        if ret != "None" and ret != "<unannotated>":
            lines.append("")
            lines.append(f"{indent}Returns:")
            lines.append(f"{indent}    <TODO: return desc> ({ret})")

    if "SeeAlso" in missing:
        lines.append("")
        lines.append(f"{indent}SeeAlso:")
        lines.append(f"{indent}    - <TODO: 관련 함수/엔진>")

    if "Requires" in missing:
        lines.append("")
        lines.append(f"{indent}Requires:")
        if imports:
            for imp in imports:
                lines.append(f"{indent}    - {imp}")
        else:
            lines.append(f"{indent}    - <TODO: external requires>")

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
    """소스 line 의 leading whitespace 추출."""
    return srcLine[: len(srcLine) - len(srcLine.lstrip())]


def _patchFile(srcPath: Path, dryRun: bool, maxFuncs: int) -> tuple[int, list[tuple[str, set[str]]]]:
    """파일 안 누락 4 섹션 stub 자동 추가. 반환: (patched count, [(funcName, missing), ...])."""
    try:
        text = srcPath.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return 0, []

    lines = text.splitlines(keepends=True)
    imports = _externalImports(tree)
    edits: list[tuple[int, list[str]]] = []  # (insert_at_line_1indexed, lines_to_insert)
    report: list[tuple[str, set[str]]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        docExpr = _docstringExpr(node)
        if docExpr is None:
            continue  # docstring 없는 함수는 P-F11 의 docstring4Section 가 별도 강제
        docstring = docExpr.value.value
        missing: set[str] = set()
        for section in ("Args", "Returns", "SeeAlso", "Requires"):
            if _hasSection(docstring, section):
                continue
            missing.add(section)

        isWrapper = _isWrapper(node)
        isPureNone = _isPureReturnNone(node)
        if isWrapper:
            missing.discard("SeeAlso")
            missing.discard("Requires")
        if isPureNone:
            missing.discard("Args")
            missing.discard("Returns")
        # 추가 면제: Args 인자 0 면 Args 건너뜀
        if not _argNames(node):
            missing.discard("Args")
        # Returns: return type None 또는 unannotated 면 건너뜀
        ret = _renderType(node.returns)
        if ret in ("None", "<unannotated>"):
            missing.discard("Returns")

        if not missing:
            continue

        # docstring 의 end_lineno (closing """ 줄) 직전에 stub 삽입
        endLine = docExpr.end_lineno  # 1-indexed
        if endLine is None:
            continue
        srcLine = lines[endLine - 1]
        # docstring 의 indent = closing """ 의 indent 또는 docstring 시작 줄의 indent
        indent = _detectIndent(srcLine)
        # 만약 closing """ 가 본문 첫 줄과 같은 줄 (single-line docstring) 이면 indent 추출 다름
        if endLine == docExpr.lineno:
            # single-line — open + content + close 한 줄. closing """ 줄에서 indent 추출
            indent = _detectIndent(srcLine)

        stubLines = _buildStub(node, missing, imports, indent)
        if not stubLines:
            continue

        # closing """ 의 line 에서 closing """ 직전에 stub 삽입
        # endLine 의 line text: "    \"\"\"" 또는 "    inline\"\"\"" (single-line)
        # multi-line docstring 의 경우 endLine 줄은 closing """ 만 있는 형태가 일반적
        # single-line 의 경우 closing """ 가 첫 줄에 있음 — 그 경우 docstring 을 multi-line 화

        is_single_line = endLine == docExpr.lineno
        if is_single_line:
            # 단일 줄 docstring 의 경우: """summary"""  →  """summary\n\nindent...\nindent"""
            # 변환 복잡 — 우선 skip (P-PR3 manual 처리)
            continue

        # multi-line: closing """ 줄 직전에 stub 삽입
        insertAt = endLine - 1  # 1-indexed line 의 직전 = 0-indexed list 의 endLine-1 위치 (closing """ 줄 자체)
        # python list insert (0-indexed): lines[insertAt] 가 closing """ 줄 → 그 앞에 삽입
        # 단 stub lines 에 trailing newline 추가
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

    # edits 를 line 역순으로 적용 (앞에서부터 삽입하면 lineno 변동)
    new_lines = lines[:]
    for insertAt, stubText in sorted(edits, key=lambda e: -e[0]):
        new_lines.insert(insertAt, stubText)

    if dryRun:
        try:
            disp = srcPath.relative_to(_REPO).as_posix()
        except ValueError:
            disp = srcPath.name
        print(f"  [{disp}] {len(edits)} patches")
        for funcKey, missing in report[:3]:
            print(f"    + {funcKey} missing={sorted(missing)}")
        return len(edits), report

    srcPath.write_text("".join(new_lines), encoding="utf-8")
    return len(edits), report


def main() -> int:
    parser = argparse.ArgumentParser(description="providers/ docstring 4-section auto-fill sweep")
    parser.add_argument("--target", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--module", default=None, help="1 모듈만 패치 (target 와 상호 배타)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="실제 file patch (dry-run 우회)")
    parser.add_argument("--max", type=int, default=50, help="패치 함수 수 상한 (chunk 분할)")
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
    print(f"=== docstring auto-fill sweep (P-PR2) — {'dry-run' if dryRun else 'APPLY'} ===")
    print(f"target: {args.module or args.target}  max/file: {args.max}\n")

    for srcPath in targets:
        if "__pycache__" in srcPath.parts:
            continue
        if not srcPath.is_file() or srcPath.suffix != ".py":
            continue
        count, report = _patchFile(srcPath, dryRun=dryRun, maxFuncs=args.max)
        if count:
            total_patches += count
            total_files += 1

    print(f"\n=== 결과: {total_files} files, {total_patches} patches ===")
    if dryRun:
        print("(dry-run — 실제 적용 시 --apply 추가)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
