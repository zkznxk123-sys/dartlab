"""provider collection-반환 메서드의 `limit` keyword 기본값 검증 — P-트랙 룰 8.

heuristic: providers/ 의 public 함수 중 이름이 `fetch*`/`list*`/`search*` 로 시작하는
collection-반환 메서드는 `limit: int = N` keyword 의무. cross-company full-df 반환 차단.

`get*` 은 단건 응답 (HTTP getBytes/getJson, 단일 값 getXxx) 비중이 압도적이라 prefix 검사 제외.
collection 반환 의도면 이름을 `list*`/`search*`/`fetch*` 로 정렬.

iter* 패밀리는 yield 가 메모리-bound 라 limit 불필요 (룰 10 이 별도로 강제).

baseline (`_baselines/limitDefault.json`) 외 위반만 fail.
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
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "limitDefault.json"

_TARGET_PREFIXES = ("fetch", "list", "search")


_LIMIT_KEYWORD_ALIASES = frozenset({"limit", "maxFilings", "maxResults", "maxRows", "topK", "n", "topN"})


def _hasLimitKwarg(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """함수 시그니처에 limit 역할 keyword 가 있는지 (별칭 인정)."""
    names = {arg.arg for arg in func.args.args + func.args.kwonlyargs}
    if func.args.vararg:
        names.add(func.args.vararg.arg)
    return bool(names & _LIMIT_KEYWORD_ALIASES)


def _matchesTarget(name: str) -> bool:
    if name.startswith("_"):
        return False
    return (
        any(
            name.startswith(prefix) and len(name) > len(prefix) and name[len(prefix)].isupper()
            for prefix in _TARGET_PREFIXES
        )
        or name in _TARGET_PREFIXES
    )


def _scanFile(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    violations: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _matchesTarget(node.name) and not _hasLimitKwarg(node):
                violations.append(
                    {
                        "path": str(path.relative_to(_REPO).as_posix()),
                        "line": node.lineno,
                        "function": node.name,
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


def _violationKey(v: dict) -> str:
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
    print(f"=== limit default audit (룰 8) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (fetch*/get*/list*/search* 함수 중 limit keyword 부재)")

    if args.update_baseline:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(
            json.dumps(
                {"_note": "P-트랙 phase 통과마다 축소", "violations": sorted(_violationKey(v) for v in violations)},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {_BASELINE.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline()
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if _violationKey(v) not in allowed]

    if args.strict:
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations[:20]:
                print(f"  {v['path']}:{v['line']} {v['function']}()")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations:
            print(f"  {v['path']}:{v['line']} {v['function']}()")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
