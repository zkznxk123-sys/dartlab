"""행동 테스트 커버리지 — P-PR 트랙 측정 게이트.

providers/{provider}/{path}.py 의 공개 method 마다 대응 tests/providers/{provider}/{path}.py
안 behavior test 가 매핑되는지 검증. smoke `test_imports()` 1 줄은 매핑으로 인정 안 함.

테스트 매칭 pattern (`_TestNameMatcher`, camelCase ↔ snake_case 호환):
    def test_<methodName>_*    또는    def test_<methodName>(
    def test_<method_name>_*   또는    def test_<method_name>(
    class Test*: def test_<methodName>_*
    class Test*: def test_<method_name>_*

mode:
    --mode baseline (default) — 현 violation 등록 + new violation 만 fail
    --mode strict — 전 violation fail

baseline JSON 형식:
    {"_note": "...", "violations": ["path::ClassName.methodName" or "path::funcName"]}

P-PR4/P-PR5 통과마다 baseline 카운트 축소. P-PR5 종료 시 strict 전환.
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
_PROVIDERS_SRC = _REPO / "src" / "dartlab" / "providers"
_PROVIDERS_TESTS = _REPO / "tests" / "providers"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "behaviorCoverage.json"

_DUNDER_RE = re.compile(r"^__.+__$")
_CAMEL_SPLIT_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _camelToSnake(name: str) -> str:
    """fetchFiling → fetch_filing."""
    return _CAMEL_SPLIT_RE.sub("_", name).lower()


def _testPatterns(methodName: str) -> list[re.Pattern[str]]:
    """공개 method 한 개에 매칭될 test 함수 이름 정규식 패턴들.

    camelCase 원형 + snake_case 변환 둘 다 매칭.
    """
    variants = {methodName, _camelToSnake(methodName)}
    patterns: list[re.Pattern[str]] = []
    for variant in variants:
        # def test_<variant>(  또는  def test_<variant>_<scenario>(
        patterns.append(re.compile(rf"^test_{re.escape(variant)}(_.+)?$"))
    return patterns


def _publicMethods(tree: ast.AST) -> list[tuple[str, int]]:
    """모듈 안 공개 method 목록 추출 — `(qualifiedName, lineno)` list.

    qualifiedName:
        - module-level function → "funcName"
        - class method → "ClassName.methodName"

    제외:
        - underscore prefix (`_`/`__`)
        - dunder (`__init__`/`__exit__` 등)
        - `@property` 데코레이터 (속성 — behavior 테스트 대상 아님)
    """
    out: list[tuple[str, int]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            if _isProperty(node):
                continue
            out.append((node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if sub.name.startswith("_") and not _DUNDER_RE.match(sub.name):
                        continue
                    if _DUNDER_RE.match(sub.name):
                        continue
                    if _isProperty(sub):
                        continue
                    out.append((f"{node.name}.{sub.name}", sub.lineno))
    return out


def _isProperty(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in func.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "property":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr in {"setter", "deleter", "getter"}:
            return True
    return False


def _testFunctionNames(testPath: Path) -> set[str]:
    """test 파일 안 test 함수/메서드 이름 set.

    `def test_*` (module-level) + `class Test*: def test_*` 모두 포함.
    """
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


def _testPathFor(srcPath: Path) -> Path:
    """src/dartlab/providers/{provider}/X/Y.py → tests/providers/{provider}/X/test_Y.py."""
    rel = srcPath.relative_to(_PROVIDERS_SRC)
    parent = rel.parent
    stem = rel.stem
    return _PROVIDERS_TESTS / parent / f"test_{stem}.py"


def _matchAny(methodName: str, testNames: set[str]) -> bool:
    """method 한 개에 매칭되는 test 가 testNames 에 하나라도 있나."""
    patterns = _testPatterns(methodName)
    for testName in testNames:
        for pat in patterns:
            if pat.match(testName):
                return True
    return False


def _scan() -> list[dict]:
    """providers/ 전 .py 의 공개 method ↔ tests/ behavior test 매핑 검증."""
    violations: list[dict] = []
    for srcPath in _PROVIDERS_SRC.rglob("*.py"):
        if "__pycache__" in srcPath.parts:
            continue
        if srcPath.name == "__init__.py":
            continue
        try:
            tree = ast.parse(srcPath.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        methods = _publicMethods(tree)
        if not methods:
            continue
        testPath = _testPathFor(srcPath)
        testNames = _testFunctionNames(testPath)
        rel = str(srcPath.relative_to(_REPO).as_posix())
        for methodName, lineno in methods:
            # qualifiedName ("ClassName.method" 또는 "func") 에서 method 마지막 부분만 매칭에 사용
            leafName = methodName.rsplit(".", 1)[-1]
            if not _matchAny(leafName, testNames):
                violations.append(
                    {
                        "path": rel,
                        "method": methodName,
                        "line": lineno,
                        "testPath": str(testPath.relative_to(_REPO).as_posix()),
                    }
                )
    return sorted(violations, key=lambda v: (v["path"], v["method"]))


def _key(v: dict) -> str:
    return f"{v['path']}::{v['method']}"


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"_note": "P-PR 트랙 — behavior test 매핑 baseline. P-PR4/P-PR5 통과마다 축소.", "violations": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="providers behavior test coverage audit")
    parser.add_argument("--mode", choices=["baseline", "strict"], default="strict")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--baseline", default=None, help="baseline JSON path")
    args = parser.parse_args()

    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE
    violations = _scan()

    print("=== behavior coverage audit (P-PR 트랙) — src/dartlab/providers ===")
    print(f"위반 {len(violations)} 건 (공개 method 에 대응 test 부재)")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        baselinePath.write_text(
            json.dumps(
                {
                    "_note": "P-PR 트랙 — behavior test 매핑 baseline. P-PR4/P-PR5 통과마다 축소. P-PR5 종료 시 strict.",
                    "violations": sorted(_key(v) for v in violations),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)} ({len(violations)} 건 기록)")
        return 0

    if args.mode == "strict":
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations[:20]:
                print(f"  {v['path']}:{v['line']} {v['method']}() — test 누락: {v['testPath']}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    # baseline 모드
    baseline = _loadBaseline(baselinePath)
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if _key(v) not in allowed]

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations[:20]:
            print(f"  {v['path']}:{v['line']} {v['method']}() — test 누락: {v['testPath']}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
