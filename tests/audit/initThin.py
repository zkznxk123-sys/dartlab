"""`__init__.py` thin 검증 — P-트랙 룰 4.

__init__.py 는 함수/클래스 정의 0 + 본문 노드 화이트리스트:
- docstring (str expr)
- import / from import
- `__all__` 대입 (Assign / AnnAssign)
- DI register 호출 (Expr Call)
- `if TYPE_CHECKING` / `if sys.version_info`(conditional import) 같은 If 블록

LoC 임계는 두지 않는다 — ruff `format` 의 magic-trailing-comma 와 충돌. 본질은 "로직 0".

baseline (`_baselines/initThin.json`) 외 위반만 fail.

사용법:
    uv run python -X utf8 tests/audit/initThin.py [target_path]
    uv run python -X utf8 tests/audit/initThin.py --strict
    uv run python -X utf8 tests/audit/initThin.py --update-baseline
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
_BASELINE = _REPO / "tests" / "audit" / "_baselines" / "initThin.json"


def _isThinBody(node: ast.AST) -> tuple[bool, str]:
    """본문 노드 화이트리스트 검증. 통과면 (True, ""), 위반이면 (False, 이유)."""
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return True, ""
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return True, ""
        if isinstance(node.value, ast.Call):
            return True, ""
        return False, f"expr {type(node.value).__name__}"
    if isinstance(node, ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "__all__":
            return True, ""
        # alias 대입: target=Name + value=Name/Attribute (예: ``affiliate = affiliates``)
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Name, ast.Attribute))
        ):
            return True, ""
        return False, f"assign {ast.unparse(node.targets[0]) if node.targets else '?'}"
    if isinstance(node, ast.AnnAssign):
        return True, ""
    if isinstance(node, ast.If):
        return True, ""
    if isinstance(node, ast.Try):
        return True, ""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False, f"함수 정의 {node.name}"
    if isinstance(node, ast.ClassDef):
        return False, f"클래스 정의 {node.name}"
    return False, f"{type(node).__name__}"


def _checkInit(path: Path) -> dict | None:
    """위반 dict 반환 (없으면 None)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"path": str(path.relative_to(_REPO).as_posix()), "reason": "syntax error"}

    reasons: list[str] = []
    for node in tree.body:
        ok, why = _isThinBody(node)
        if not ok:
            reasons.append(why)

    if not reasons:
        return None
    return {
        "path": str(path.relative_to(_REPO).as_posix()),
        "reason": "; ".join(reasons[:5]),
    }


def _scan(target: Path) -> list[dict]:
    violations: list[dict] = []
    for p in target.rglob("__init__.py"):
        if "__pycache__" in p.parts:
            continue
        v = _checkInit(p)
        if v is not None:
            violations.append(v)
    return sorted(violations, key=lambda x: x["path"])


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--baseline", default=None, help="baseline JSON path (기본 _baselines/initThin.json)")
    args = parser.parse_args()
    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE

    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    violations = _scan(target)
    print(f"=== __init__.py thin audit (룰 4) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (함수/클래스 정의 존재 또는 비-허용 노드)")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        baselinePath.write_text(
            json.dumps(
                {
                    "_note": "AST 기반 — 함수/클래스 정의 0 + 본문 노드 화이트리스트",
                    "violations": [v["path"] for v in violations],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline(baselinePath)
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if v["path"] not in allowed]

    if args.strict:
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations[:20]:
                print(f"  {v['path']} — {v['reason']}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations:
            print(f"  {v['path']} — {v['reason']}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
