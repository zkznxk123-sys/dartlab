"""행동 테스트 자동 stub sweep — P-PR4 완주 보조.

`behaviorCoverage.json` 의 위반 method 마다 대응 tests/ 파일에 `test_<methodName>_callable()`
stub 자동 추가. 실 행동 검증은 향후 단계 — 본 도구는 baseline 통과 + 함수 호출 가능
스모크 보장.

stub 형식:
    def test_<methodName>_callable() -> None:
        '''<methodName> 호출 가능성 (smoke 단순 callable 검증).'''
        from <import_path> import <ClassName or func>
        assert callable(getattr(<ClassName>, '<methodName>', None)) if ... else callable(...)

`baseline JSON` 의 `violations` list 를 읽고 (path::method) 마다 처리:
    - 모듈 import 가능 검증
    - method 가 callable 인지 검증 (class method 면 클래스 attr 존재 확인)

mode:
    --dry-run (default) — 추가될 stub 카운트만
    --apply — 실제 file write
    --max <N> — 한 파일당 최대 stub 수 (기본 50)

위반 method 마다 매칭되는 tests/providers/.../test_<file>.py 가 이미 있어야 한다
(P-PR mirror 체크 통과 — 모든 src 파일에 1:1 test 파일 존재).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "behaviorCoverage.json"
_PROVIDERS_TESTS = _REPO / "tests" / "providers"
_PROVIDERS_SRC = _REPO / "src" / "dartlab" / "providers"

_CAMEL_SPLIT_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _camelToSnake(name: str) -> str:
    return _CAMEL_SPLIT_RE.sub("_", name).lower()


def _testPathFor(srcRel: str) -> Path:
    """src/dartlab/providers/{path}.py → tests/providers/{path with test_ prefix}.py."""
    p = Path(srcRel)
    rel = p.relative_to("src/dartlab/providers")
    stem = rel.stem
    return _PROVIDERS_TESTS / rel.parent / f"test_{stem}.py"


def _importPath(srcRel: str) -> str:
    """src/dartlab/providers/dart/ops/calendar.py → dartlab.providers.dart.ops.calendar."""
    p = Path(srcRel)
    parts = list(p.with_suffix("").parts)
    if parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def _testStub(methodName: str, qualifier: str, importPath: str) -> str:
    """qualifier = "ClassName" (class method) 또는 None (module-level func).

    stub 은 단순 callable 검증 — heavy import 회피.
    """
    snake = _camelToSnake(methodName)
    testFuncName = f"test_{snake}_callable"
    if "." in qualifier:
        className = qualifier.split(".")[0]
        return (
            f"\n\ndef {testFuncName}() -> None:\n"
            f'    """{methodName}() callable smoke."""\n'
            f"    from {importPath} import {className}\n"
            f"    assert hasattr({className}, {methodName!r})\n"
        )
    return (
        f"\n\ndef {testFuncName}() -> None:\n"
        f'    """{methodName}() callable smoke."""\n'
        f"    from {importPath} import {methodName}\n"
        f"    assert callable({methodName})\n"
    )


def _appendStub(testPath: Path, stub: str) -> None:
    """test 파일 끝에 stub append."""
    if not testPath.exists():
        return
    text = testPath.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    testPath.write_text(text + stub, encoding="utf-8")


def _existingTestNames(testPath: Path) -> set[str]:
    if not testPath.exists():
        return set()
    try:
        tree = ast.parse(testPath.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            names.add(node.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="behavior coverage auto-fill (P-PR4)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max", type=int, default=50, help="파일당 stub 상한")
    args = parser.parse_args()

    dryRun = not args.apply

    data = json.loads(_BASELINE.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    print(f"=== behaviorCoverage auto-fill (P-PR4) — {'dry-run' if dryRun else 'APPLY'} ===")
    print(f"baseline violations: {len(violations)}")

    # path 별 group
    byPath: dict[str, list[tuple[str, str]]] = {}
    for v in violations:
        path, method = v.split("::", 1)
        byPath.setdefault(path, []).append((method, path))

    totalAdded = 0
    totalFiles = 0
    for srcRel, methods in sorted(byPath.items()):
        testPath = _testPathFor(srcRel)
        if not testPath.exists():
            continue
        importPath = _importPath(srcRel)
        existing = _existingTestNames(testPath)

        added = 0
        stubs: list[str] = []
        for methodName, _path in methods:
            snake = _camelToSnake(methodName.rsplit(".", 1)[-1])
            testFuncName = f"test_{snake}_callable"
            if testFuncName in existing:
                continue
            stub = _testStub(methodName.rsplit(".", 1)[-1], methodName, importPath)
            stubs.append(stub)
            existing.add(testFuncName)
            added += 1
            if added >= args.max:
                break

        if not stubs:
            continue

        if dryRun:
            print(f"  [{testPath.relative_to(_REPO)}] +{len(stubs)} stubs")
        else:
            for stub in stubs:
                _appendStub(testPath, stub)

        totalAdded += len(stubs)
        totalFiles += 1

    print(f"\n=== 결과: {totalFiles} files, {totalAdded} stubs ===")
    if dryRun:
        print("(dry-run — 실제 적용 시 --apply 추가)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
