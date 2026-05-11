"""`__init__.py` thin 검증 — P-트랙 룰 4.

__init__.py 는 LoC ≤ 30 + 함수/클래스 정의 0. re-export (`from X import Y`) 와 `__all__` 만.
로직이 들어가면 .py 분리.

baseline (`_baselines/initThin.json`) 외 위반만 fail.

사용법:
    uv run python -X utf8 scripts/audit/initThin.py [target_path]
    uv run python -X utf8 scripts/audit/initThin.py --strict
    uv run python -X utf8 scripts/audit/initThin.py --update-baseline
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
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "initThin.json"
_MAX_LOC = 30


def _checkInit(path: Path) -> dict | None:
    """위반 dict 반환 (없으면 None)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    loc = sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"path": str(path.relative_to(_REPO).as_posix()), "loc": loc, "reason": "syntax error"}

    has_function = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in tree.body)
    has_class = any(isinstance(node, ast.ClassDef) for node in tree.body)
    too_long = loc > _MAX_LOC

    if not (has_function or has_class or too_long):
        return None

    reasons = []
    if has_function:
        reasons.append("함수 정의 존재")
    if has_class:
        reasons.append("클래스 정의 존재")
    if too_long:
        reasons.append(f"LoC {loc} > {_MAX_LOC}")

    return {"path": str(path.relative_to(_REPO).as_posix()), "loc": loc, "reason": ", ".join(reasons)}


def _scan(target: Path) -> list[dict]:
    violations: list[dict] = []
    for p in target.rglob("__init__.py"):
        if "__pycache__" in p.parts:
            continue
        v = _checkInit(p)
        if v is not None:
            violations.append(v)
    return sorted(violations, key=lambda x: x["path"])


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


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
    print(f"=== __init__.py thin audit (룰 4) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (LoC > {_MAX_LOC} 또는 함수/클래스 정의 존재)")

    if args.update_baseline:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(
            json.dumps(
                {"_note": "P-트랙 phase 통과마다 축소", "violations": [v["path"] for v in violations]},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {_BASELINE.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline()
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
