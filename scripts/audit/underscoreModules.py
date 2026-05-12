"""`_*.py` 파일명 검증 — P-트랙 룰 5.

generic helper 파일명 (`_helpers.py`/`_utils.py`/`_*.py`) 폐지. 도메인 명시 이름 또는
사용처 안으로 흡수.

면제: `__init__.py`, `__main__.py` 같은 dunder.

baseline (`_baselines/underscoreModules.json`) 외 위반만 fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_TARGET = _REPO / "src" / "dartlab" / "providers"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "underscoreModules.json"


def _scan(target: Path) -> list[str]:
    violations: list[str] = []
    for p in target.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if p.name.startswith("__") and p.name.endswith("__.py"):
            # dunder (`__init__.py`, `__main__.py`) 면제
            continue
        if p.name.startswith("_"):
            violations.append(str(p.relative_to(_REPO).as_posix()))
    return sorted(violations)


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "P0.5 baseline"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--baseline", default=None, help="baseline JSON path (기본 _baselines/underscoreModules.json)")
    args = parser.parse_args()
    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE

    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    violations = _scan(target)
    print(f"=== underscore module audit (룰 5) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (_*.py generic helper, dunder 제외)")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        baselinePath.write_text(
            json.dumps(
                {"_note": "P-트랙 P1 에서 도메인 명시 rename 시 축소", "violations": violations},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline(baselinePath)
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if v not in allowed]

    if args.strict:
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations:
                print(f"  {v}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations:
            print(f"  {v}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
