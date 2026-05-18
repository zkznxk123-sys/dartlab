"""camelCase 100% 인벤토리 — snake_case 식별자 카운트.

위반 카운트 + 파일 단위 우선순위 출력. 자동 변환 절대 금지
(operation.code · feedback_no_bulk_rename_codemod).

검사 대상: 함수/메서드/매개변수/모듈 레벨 assignment.
면제: dunder · _prefix · ALL_CAPS · setUp/tearDown · cls/self.

실행:
    uv run python -X utf8 tests/audit/snakeCaseInventory.py
    uv run python -X utf8 tests/audit/snakeCaseInventory.py --top 30
    uv run python -X utf8 tests/audit/snakeCaseInventory.py --file src/dartlab/...
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"

SNAKE_RE = re.compile(r"^[a-z]+(_[a-z0-9]+)+$")
ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

EXEMPT_NAMES = {
    "__init__",
    "__call__",
    "__repr__",
    "__str__",
    "__enter__",
    "__exit__",
    "__getitem__",
    "__setitem__",
    "__contains__",
    "__iter__",
    "__next__",
    "__len__",
    "__eq__",
    "__hash__",
    "__bool__",
    "__add__",
    "__sub__",
    "__mul__",
    "__truediv__",
    "__neg__",
    "__abs__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__post_init__",
    "__class_getitem__",
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "_",
    "args",
    "kwargs",
    "cls",
    "self",
    # stdlib HTMLParser override — 시그니처 강제, rename 불가
    "handle_starttag",
    "handle_endtag",
    "handle_data",
    "handle_comment",
    "handle_decl",
    "handle_pi",
    "handle_entityref",
    "handle_charref",
    "handle_startendtag",
}


def isSnake(name: str) -> bool:
    if name in EXEMPT_NAMES:
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    bare = name.lstrip("_")
    if not bare:
        return False
    if ALL_CAPS_RE.match(bare):
        return False
    return bool(SNAKE_RE.match(bare))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=20, help="상위 N 파일 출력")
    parser.add_argument("--file", help="단일 파일 detail")
    args = parser.parse_args()

    if args.file:
        return _detailFile(Path(args.file))

    byTopLevel: Counter[str] = Counter()
    byFile: Counter[str] = Counter()
    byKind: Counter[str] = Counter()
    samples: dict[str, list[tuple[str, str, int]]] = {}

    files = list(ROOT.rglob("*.py"))
    for pyFile in files:
        if pyFile.name == "conftest.py" or pyFile.name.startswith("_generated"):
            continue
        rel = pyFile.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        top = rel.split("/", 1)[0]
        # module-level assignment 도 검사 (ALL_CAPS 제외)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and isSnake(tgt.id):
                        byTopLevel[top] += 1
                        byFile[rel] += 1
                        byKind["module_var"] += 1
                        samples.setdefault(rel, [])
                        if len(samples[rel]) < 3:
                            samples[rel].append(("mvar", tgt.id, node.lineno))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if isSnake(node.target.id):
                    byTopLevel[top] += 1
                    byFile[rel] += 1
                    byKind["module_var"] += 1
                    samples.setdefault(rel, [])
                    if len(samples[rel]) < 3:
                        samples[rel].append(("mvar", node.target.id, node.lineno))
        # 함수/메서드 (재귀)
        for node in ast.walk(tree):
            names: list[tuple[str, str, int]] = []
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                names.append(("func", node.name, node.lineno))
                for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                    names.append(("arg", a.arg, node.lineno))
            for kind, n, lineno in names:
                if isSnake(n):
                    byTopLevel[top] += 1
                    byFile[rel] += 1
                    byKind[kind] += 1
                    samples.setdefault(rel, [])
                    if len(samples[rel]) < 3:
                        samples[rel].append((kind, n, lineno))

    total = sum(byTopLevel.values())
    print(f"Total files scanned: {len(files)}")
    print(f"Files with snake_case: {len(byFile)}")
    print(f"Total snake violations: {total}")
    print(f"  func:  {byKind['func']}")
    print(f"  arg:   {byKind['arg']}")
    print()
    print("By top-level package:")
    for t, c in byTopLevel.most_common():
        print(f"  {c:>4}  {t}")
    print()
    print(f"Top {args.top} files:")
    for f, c in byFile.most_common(args.top):
        print(f"  {c:>3}  {f}")
        for kind, n, lineno in samples[f]:
            print(f"         {kind:>4} {n} (line {lineno})")
    return 0 if total == 0 else 1


def _detailFile(p: Path) -> int:
    if not p.exists():
        print(f"NOT FOUND: {p}")
        return 1
    tree = ast.parse(p.read_text(encoding="utf-8"))
    rows: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if isSnake(node.name):
                rows.append((node.lineno, "func", node.name))
            for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                if isSnake(a.arg):
                    rows.append((node.lineno, "arg ", a.arg))
    rows.sort()
    print(f"{p} — {len(rows)} violations:")
    for lineno, kind, n in rows:
        print(f"  line {lineno:>4}: {kind} {n}")
    return 0 if not rows else 1


if __name__ == "__main__":
    sys.exit(main())
