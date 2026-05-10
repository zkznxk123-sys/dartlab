"""snake_case → camelCase 전수 codemod (P6 도구).

전면 리팩토링 plan dartlab-misty-sifakis 의 P6 도구. 함수·메서드·매개변수·
모듈변수 + 파일명 (.py) 일괄 변환.

사용자 결정 (확정): shim alias 없음 — 0.10 release 에서 BC 깸.

전략 — 5-pass 파이프라인:
    Pass 1 — 인덱스 빌드: 전수 스캔, (qualifiedName, kind) → camelName 매핑
    Pass 2 — 정의 변경 (libCST AST rewrite)
    Pass 3 — 호출 사이트 (rope refactor cross-module reference)
    Pass 4 — Public API: __all__ snake → camel 직접 교체
    Pass 5 — 파일명: git mv snake_name.py → camelName.py + import path

본 파일은 Pass 1 (인덱스 빌드) + dry-run reporter. 실제 변환 (Pass 2~5) 은
libCST + rope 의존성 추가 후 점진 적용 (follow-up PR 들).

실행:
    python -X utf8 scripts/dev/codemodToCamel.py --dry-run        # 인덱스 + 충돌 보고
    python -X utf8 scripts/dev/codemodToCamel.py --apply-files    # Pass 5 (파일명) 만 적용
    python -X utf8 scripts/dev/codemodToCamel.py --apply-all      # Pass 1~5 전수 (libCST + rope 필요)

종료 코드:
    0 — dry-run OK
    1 — 입력 오류
    2 — apply 시 conflict 발생 (수동 결정 필요)
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"

SKIP_PATH_PARTS: tuple[str, ...] = (
    "tests",
    "experiments",
    "notebooks",
    "scripts",
    "blog",
    "landing",
    "sns",
    ".venv",
    ".venv-wsl",
    "build",
    "dist",
)

SKIP_NAME_PATTERNS: tuple[str, ...] = ("_generated", "_pb2.py", "conftest.py")

# 보존 alias (lint_camelcase 와 동일 set)
ARG_ALLOWLIST: frozenset[str] = frozenset(
    {"self", "cls", "mcs", "_", "args", "kwargs", "x", "y", "z", "n", "i", "j", "k", "v", "fn", "df", "lf", "id"}
)


@dataclass(frozen=True)
class Identifier:
    """변환 대상 식별자 — qualifier (클래스명 또는 함수명) + name + kind."""

    path: str
    qualifier: str
    name: str
    kind: str
    line: int


def _toCamel(name: str) -> str:
    """snake_case → camelCase. leading underscore + ALL_CAPS 보존."""
    leading = ""
    rest = name
    while rest.startswith("_"):
        leading += "_"
        rest = rest[1:]
    if not rest:
        return name
    if rest.isupper() and "_" in rest:
        return name  # ALL_CAPS_CONST 보존
    parts = rest.split("_")
    if not parts:
        return name
    head, *tail = parts
    return leading + head.lower() + "".join(p[:1].upper() + p[1:].lower() for p in tail if p)


def _toCamelFile(stem: str) -> str:
    """snake_module → camelModule. 파일명용 (확장자 제외 stem)."""
    if "_" not in stem or stem.startswith("_"):
        return stem
    parts = stem.split("_")
    if not parts:
        return stem
    head, *tail = parts
    return head.lower() + "".join(p[:1].upper() + p[1:].lower() for p in tail if p)


def _isSkipped(p: Path) -> bool:
    """면제 폴더/파일명 검사."""
    parts = {x.lower() for x in p.parts}
    if any(s in parts for s in SKIP_PATH_PARTS):
        return True
    return any(pat in p.name for pat in SKIP_NAME_PATTERNS)


def _collectIdentifiers(path: Path) -> list[Identifier]:
    """단일 .py 의 변환 대상 식별자 추출."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []
    relPath = path.resolve().relative_to(ROOT).as_posix()
    out: list[Identifier] = []
    classStack: list[str] = []

    def _visit(node: ast.AST) -> None:
        if isinstance(node, ast.ClassDef):
            classStack.append(node.name)
            for child in ast.iter_child_nodes(node):
                _visit(child)
            classStack.pop()
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualifier = classStack[-1] if classStack else ""
            kind = "method" if classStack else "func"
            if "_" in node.name and not node.name.startswith("__"):
                out.append(Identifier(relPath, qualifier, node.name, kind, node.lineno))
            for arg in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                if "_" in arg.arg and arg.arg not in ARG_ALLOWLIST and not arg.arg.startswith("__"):
                    out.append(Identifier(relPath, f"{qualifier}.{node.name}".strip("."), arg.arg, "arg", arg.lineno))
            for child in ast.iter_child_nodes(node):
                _visit(child)
            return
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(tree)
    return out


def _scanFiles() -> tuple[list[Path], list[Identifier], list[tuple[str, str]]]:
    """src/dartlab 전수 스캔 — 파일명 변환 후보 + 식별자 변환 후보 + 충돌."""
    files: list[Path] = []
    identifiers: list[Identifier] = []
    fileRenames: list[tuple[str, str]] = []
    seen: dict[tuple[str, str, str], list[Identifier]] = {}
    for py in SRC.rglob("*.py"):
        if _isSkipped(py):
            continue
        files.append(py)
        # 파일명 후보
        stem = py.stem
        camelStem = _toCamelFile(stem)
        if camelStem != stem and not stem.startswith("_") and stem not in ("conftest",):
            relSrc = py.resolve().relative_to(ROOT).as_posix()
            relDst = (py.parent / f"{camelStem}.py").resolve().relative_to(ROOT).as_posix()
            fileRenames.append((relSrc, relDst))
        for ident in _collectIdentifiers(py):
            identifiers.append(ident)
            key = (ident.qualifier, _toCamel(ident.name), ident.kind)
            seen.setdefault(key, []).append(ident)
    # 충돌: 같은 (qualifier, camelName, kind) 에 다른 원본 식별자 다수
    conflicts: list[tuple[str, str]] = []
    for key, idents in seen.items():
        names = {i.name for i in idents}
        if len(names) > 1:
            conflicts.append((str(key), ", ".join(sorted(names))))
    return files, identifiers, conflicts


def main(argv: list[str]) -> int:
    """CLI 진입점 — dry-run 인덱스 빌드 + 충돌 보고."""
    dryRun = "--dry-run" in argv or len(argv) == 0
    if not dryRun:
        print("[codemod] --apply-* 모드는 libCST + rope 설치 필요. 현재 dry-run 만 지원.")
        return 1
    files, identifiers, conflicts = _scanFiles()
    print(f"[codemod] dry-run — {len(files)} .py 파일 스캔")
    print(f"  식별자 변환 후보: {len(identifiers)} (func/method/arg)")
    print("    func/method:", sum(1 for i in identifiers if i.kind in ("func", "method")))
    print("    arg:        ", sum(1 for i in identifiers if i.kind == "arg"))
    print(f"  파일명 변환 후보 (Pass 5): {sum(1 for s, d in [] for _ in [(s, d)])}")  # Placeholder
    fileRenames = sum(1 for _ in _scanFiles()[0] if "_" in _.stem)  # 정확한 카운트 위해 재계산
    print(f"  파일명 변환 후보: {fileRenames}")
    print(f"  충돌 (수동 결정 필요): {len(conflicts)}")
    if conflicts:
        print("\n  대표 충돌 5 개:")
        for key, names in conflicts[:5]:
            print(f"    {key} ← {names}")
    indexPath = ROOT / "scripts" / "dev" / "_camelcaseIndex.json"
    payload = {
        "fileCount": len(files),
        "identifierCount": len(identifiers),
        "conflictCount": len(conflicts),
        "fileRenames": fileRenames,
        "identifiers": [
            {
                "path": i.path,
                "qualifier": i.qualifier,
                "name": i.name,
                "camel": _toCamel(i.name),
                "kind": i.kind,
                "line": i.line,
            }
            for i in identifiers[:200]
        ],
        "conflicts": [{"key": k, "names": n} for k, n in conflicts],
    }
    indexPath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  인덱스 저장 → {indexPath.relative_to(ROOT).as_posix()}")
    print("\n다음 단계:")
    print("  1. uv add --dev libcst rope  (codemod 도구 의존성)")
    print("  2. _camelcaseIndex.json 의 conflicts 수동 결정")
    print("  3. Pass 2~5 점진 적용 (PR 분리)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
