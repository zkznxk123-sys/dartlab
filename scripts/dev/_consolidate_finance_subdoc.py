"""[일회성, P2 전용] dart/docs/finance/<type>/ 4-파일 패턴을 단일 <type>.py 통합.

사용:
    uv run python -X utf8 scripts/dev/_consolidate_finance_subdoc.py <name>
    예: uv run python -X utf8 scripts/dev/_consolidate_finance_subdoc.py bond

input: src/dartlab/providers/dart/docs/finance/<name>/{parser,pipeline,types,__init__}.py
output: src/dartlab/providers/dart/docs/finance/<name>.py (단일 모듈)
        + 원본 <name>/ 폴더 git rm 준비 (수동 단계)

전략:
- types.py 의 dataclass + parser.py 의 helper + pipeline.py 의 entry 를 순서대로 흡수
- import 는 dedup + sorted
- 내부 cross-import (`from dartlab.providers.dart.docs.finance.<name>.X`) 는 제거 (동일 모듈 안)
- TYPE_CHECKING 블록은 보존
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _extractImports(src: str, subname: str) -> tuple[set[str], set[str]]:
    """소스에서 import 추출. (top-level imports, type_checking imports) 반환.

    동일 sub-doc 내부 cross-import 는 제외.
    """
    tree = ast.parse(src)
    top_imports: set[str] = set()
    tc_imports: set[str] = set()
    in_tc: list[bool] = [False]

    self_module_prefix = f"dartlab.providers.dart.docs.finance.{subname}."

    def _walk(node, in_type_checking: bool):
        if isinstance(node, ast.If):
            # TYPE_CHECKING 블록 감지
            test = ast.unparse(node.test)
            if "TYPE_CHECKING" in test:
                for child in node.body:
                    _walk(child, True)
                return
        if isinstance(node, ast.Import):
            for n in node.names:
                stmt = f"import {n.name}" + (f" as {n.asname}" if n.asname else "")
                (tc_imports if in_type_checking else top_imports).add(stmt)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith(self_module_prefix):
                return  # 동일 sub-doc 내부 cross-import — 흡수 후 불필요
            names = ", ".join(n.name + (f" as {n.asname}" if n.asname else "") for n in node.names)
            stmt = f"from {mod} import {names}"
            (tc_imports if in_type_checking else top_imports).add(stmt)
        else:
            for child in ast.iter_child_nodes(node):
                _walk(child, in_type_checking)

    for node in tree.body:
        _walk(node, False)

    return top_imports, tc_imports


def _stripImports(src: str) -> str:
    """소스에서 import 줄과 TYPE_CHECKING 블록 + module docstring 제거 → 본문만."""
    tree = ast.parse(src)
    keep_lines = src.splitlines()
    skip_ranges: list[tuple[int, int]] = []  # (start, end) 1-based inclusive

    # module docstring
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        skip_ranges.append((tree.body[0].lineno, tree.body[0].end_lineno))

    # imports + TYPE_CHECKING
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            skip_ranges.append((node.lineno, node.end_lineno))
        elif isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            skip_ranges.append((node.lineno, node.end_lineno))

    # __future__ import (already separate)
    skip_ranges.sort()
    skip_lines: set[int] = set()
    for start, end in skip_ranges:
        for i in range(start, end + 1):
            skip_lines.add(i)

    return "\n".join(line for i, line in enumerate(keep_lines, start=1) if i not in skip_lines).strip()


def main(name: str) -> int:
    folder = _REPO / "src" / "dartlab" / "providers" / "dart" / "docs" / "finance" / name
    if not folder.is_dir():
        print(f"ERROR: {folder} 폴더 부재", file=sys.stderr)
        return 1

    # 1) 각 파일 읽기
    types_src = (folder / "types.py").read_text(encoding="utf-8") if (folder / "types.py").exists() else ""
    parser_src = (folder / "parser.py").read_text(encoding="utf-8") if (folder / "parser.py").exists() else ""
    pipeline_src = (folder / "pipeline.py").read_text(encoding="utf-8") if (folder / "pipeline.py").exists() else ""
    # extra files (builder, extractor 등) — 통합 안 함, 폴더 유지 신호
    extras = [
        p
        for p in folder.glob("*.py")
        if p.name not in ("__init__.py", "parser.py", "pipeline.py", "types.py", "__pycache__")
    ]
    if extras:
        print(f"WARNING: extras 파일 발견 — 폴더 유지 권장: {[p.name for p in extras]}")

    # 2) imports 추출
    all_top: set[str] = set()
    all_tc: set[str] = set()
    for src in (types_src, parser_src, pipeline_src):
        if not src:
            continue
        t, tc = _extractImports(src, name)
        all_top |= t
        all_tc |= tc

    # __future__ separate
    future_imports = {imp for imp in all_top if imp.startswith("from __future__")}
    all_top -= future_imports

    # 3) 본문 추출 + 결합 (types → parser → pipeline)
    body_parts: list[str] = []
    if types_src:
        body_parts.append("# types\n" + _stripImports(types_src))
    if parser_src:
        body_parts.append("# parser\n" + _stripImports(parser_src))
    if pipeline_src:
        body_parts.append("# pipeline\n" + _stripImports(pipeline_src))

    # 4) module docstring (pipeline.py 의 module docstring 사용)
    docstring = '"""(P2 통합)"""'
    for src in (pipeline_src, types_src, parser_src):
        tree = ast.parse(src) if src else None
        if (
            tree
            and tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            ds = tree.body[0].value.value
            docstring = '"""' + ds + "\n\nP2 통합: 기존 " + name + '/{parser,pipeline,types}.py 단일 모듈로 흡수.\n"""'
            break

    # 5) 출력
    out_lines: list[str] = [docstring, ""]
    if future_imports:
        out_lines.extend(sorted(future_imports))
        out_lines.append("")

    # imports — stdlib / 3rd-party / dartlab 으로 그룹화 (간단 휴리스틱)
    std_libs = {
        imp
        for imp in all_top
        if any(
            imp.startswith(f"from {m}") or imp.startswith(f"import {m}")
            for m in (
                "ast",
                "re",
                "io",
                "os",
                "sys",
                "json",
                "typing",
                "dataclasses",
                "collections",
                "datetime",
                "pathlib",
                "functools",
                "hashlib",
            )
        )
    }
    dartlab = {imp for imp in all_top if "dartlab" in imp}
    third = all_top - std_libs - dartlab

    for group in (sorted(std_libs), sorted(third), sorted(dartlab)):
        if group:
            out_lines.extend(group)
            out_lines.append("")

    if all_tc:
        out_lines.append("if TYPE_CHECKING:")
        for imp in sorted(all_tc):
            out_lines.append("    " + imp)
        out_lines.append("")

    out_lines.append("")
    out_lines.append("\n\n".join(body_parts))

    out_file = folder.parent / f"{name}.py"
    out_file.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"  → {out_file.relative_to(_REPO).as_posix()} 작성")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: _consolidate_finance_subdoc.py <name> [<name> ...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        rc = main(arg)
        if rc != 0:
            sys.exit(rc)
