"""Docstring 4-섹션 검증 — P-트랙 룰 6.

public 함수/메서드/클래스 docstring 에 다음 섹션 모두 명시:
    - Args (또는 Parameters / Returns) — 인자/반환 설명
    - Example (또는 Usage / Examples) — 사용 예
    - Raises (또는 Errors / Throws) — 발생 예외

(Sig 는 시그니처 자체로 자동 충족 — 별도 검사 X)

heuristic: 함수가 인자 0 + 반환 None 이면 Args 면제. 단순 wrapper 면 Example/Raises 면제.

baseline (`_baselines/docstring4Section.json`) 외 위반만 fail.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_TARGET = _REPO / "src" / "dartlab" / "providers"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "docstring4Section.json"

_ARGS_KEYWORDS = (
    "Args:",
    "Arguments:",
    "Parameters:",
    "Parameters\n",
    "매개변수:",
    "인자:",
    "Returns:",
    "Returns\n",
    "Return:",
)
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
_RAISES_KEYWORDS = (
    "Raises:",
    "Raises\n",
    "Errors:",
    "Throws:",
    "예외:",
    "에러:",
)


def _hasSection(docstring: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in docstring for kw in keywords)


def _needsArgs(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """인자 (self/cls 제외) 가 있거나 None 이 아닌 return 있으면 Args 섹션 필요."""
    posargs = [a for a in func.args.args if a.arg not in ("self", "cls")]
    if posargs or func.args.kwonlyargs or func.args.vararg or func.args.kwarg:
        return True
    # 반환 타입 명시되어 있고 None 이 아니면 Returns 필요
    if func.returns:
        if isinstance(func.returns, ast.Constant) and func.returns.value is None:
            return False
        if isinstance(func.returns, ast.Name) and func.returns.id == "None":
            return False
        return True
    return False


def _scanFile(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    violations: list[dict] = []
    rel = str(path.relative_to(_REPO).as_posix())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            docstring = ast.get_docstring(node) or ""
            missing: list[str] = []
            if _needsArgs(node) and not _hasSection(docstring, _ARGS_KEYWORDS):
                missing.append("Args/Returns")
            if not _hasSection(docstring, _EXAMPLE_KEYWORDS):
                missing.append("Example")
            if not _hasSection(docstring, _RAISES_KEYWORDS):
                missing.append("Raises")
            if missing:
                violations.append(
                    {
                        "path": rel,
                        "line": node.lineno,
                        "function": node.name,
                        "missing": missing,
                    }
                )
    return violations


def _scan(target: Path) -> list[dict]:
    all_violations: list[dict] = []
    for p in target.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        all_violations.extend(_scanFile(p))
    return sorted(all_violations, key=lambda v: (v["path"], v["line"]))


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


def _key(v: dict) -> str:
    return f"{v['path']}::{v['function']}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    violations = _scan(target)
    print(f"=== docstring 4-section audit (룰 6) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (Args/Example/Raises 섹션 부재)")

    if args.update_baseline:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(
            json.dumps(
                {
                    "_note": "P-트랙 P4 에서 docstring 메우며 축소",
                    "violations": sorted(_key(v) for v in violations),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {_BASELINE.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline()
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if _key(v) not in allowed]

    if args.strict:
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations[:20]:
                print(f"  {v['path']}:{v['line']} {v['function']}() — 누락: {v['missing']}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations[:20]:
            print(f"  {v['path']}:{v['line']} {v['function']}() — 누락: {v['missing']}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
