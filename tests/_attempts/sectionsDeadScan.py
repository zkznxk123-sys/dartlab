"""sections layer dead/redundant 탐지 v2.

목표 (2026-05-22): "sections 속도 최강, 메모리 최강, 덕지덕지 금지, 죽은 코드 제거"

확장:
- 정의 0 call 인 public 함수 (sections/ 안에서 호출 안 됨)
- repo 전체에서 호출 0 인 public 함수 (외부 caller 도 없음)
- 같은 의미 중복 정규식
"""

import ast
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SECT = REPO / "src" / "dartlab" / "providers" / "dart" / "docs" / "sections"


def collectSectionsDefs() -> tuple[dict[str, list[tuple[str, int]]], str, str]:
    """returns: {file: [(funcname, lineno), ...]}, sections_text, repo_text."""
    file_funcs: dict[str, list[tuple[str, int]]] = {}
    sect_text = ""
    for p in SECT.glob("*.py"):
        src = p.read_text(encoding="utf-8")
        sect_text += src
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        funcs = []
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if n.name.startswith("__"):
                    continue
                funcs.append((n.name, n.lineno))
        file_funcs[p.name] = funcs

    # repo-wide text
    repo_text_parts = []
    for p in (REPO / "src").rglob("*.py"):
        repo_text_parts.append(p.read_text(encoding="utf-8"))
    for p in (REPO / "tests").rglob("*.py"):
        try:
            repo_text_parts.append(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    repo_text = "\n".join(repo_text_parts)

    return file_funcs, sect_text, repo_text


def main() -> int:
    file_funcs, sect_text, repo_text = collectSectionsDefs()
    print(f"sections files: {len(file_funcs)}, repo text size: {len(repo_text):,} chars")

    # Public functions (no _) that 0 external repo usage
    public_dead = []
    for fname, funcs in file_funcs.items():
        for fn, lineno in funcs:
            if fn.startswith("_"):
                continue
            # repo 전체 사용 카운트 (정의 1 회 포함)
            usage = len(re.findall(r"\b" + re.escape(fn) + r"\b", repo_text))
            if usage <= 1:
                public_dead.append((fname, fn, lineno, usage))

    print(f"\n=== public dead (0 external usage): {len(public_dead)} ===")
    for f, fn, ln, u in public_dead[:50]:
        print(f"  {f}:{ln}::{fn} (usage={u})")

    # Private function only-1-caller
    one_caller = []
    for fname, funcs in file_funcs.items():
        for fn, lineno in funcs:
            if not fn.startswith("_") or fn.startswith("__"):
                continue
            usage = len(re.findall(r"\b" + re.escape(fn) + r"\b", sect_text))
            if usage == 2:  # def + 1 call
                one_caller.append((fname, fn, lineno))
    print(f"\n=== private fns with exactly 1 call site (inline 후보): {len(one_caller)} ===")
    for f, fn, ln in one_caller[:20]:
        print(f"  {f}:{ln}::{fn}")

    return 0


if __name__ == "__main__":
    main()
