"""providers/ 폴더 mirror 검증 — P-트랙 룰 2.

기본 strict 대상은 dart/edgar 이다. edinet 은 API 통신 불가 deferred provider 라서
명시적으로 --providers 에 넣을 때만 검사한다.
baseline (`_baselines/folderMirror.json`) 외 갭만 fail. --strict 면 baseline 무시.

사용법:
    uv run python -X utf8 tests/audit/folderMirror.py
    uv run python -X utf8 tests/audit/folderMirror.py --providers dart,edgar
    uv run python -X utf8 tests/audit/folderMirror.py --strict
    uv run python -X utf8 tests/audit/folderMirror.py --update-baseline

종료 코드:
    0  통과 (baseline 안 + --update-baseline 모드)
    1  baseline 외 신규 갭 발견 또는 --strict 위반
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_PROVIDERS = _REPO / "src" / "dartlab" / "providers"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "folderMirror.json"
_DEFAULT_TARGETS = ("dart", "edgar")


def _parseProviders(raw: str) -> tuple[str, ...]:
    providers = tuple(p.strip() for p in raw.split(",") if p.strip())
    if len(providers) < 2:
        raise SystemExit("--providers 는 2개 이상이어야 합니다. 예: --providers dart,edgar")
    missing = [p for p in providers if not (_PROVIDERS / p).exists()]
    if missing:
        raise SystemExit(f"알 수 없는 provider: {missing}")
    return providers


def _subfolders(providerName: str) -> set[str]:
    root = _PROVIDERS / providerName
    if not root.exists():
        return set()
    return {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_") and p.name != "__pycache__"}


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"asymmetry": {}, "_note": "P0.5 baseline"}


def _computeAsymmetry(targets: tuple[str, ...]) -> dict[str, dict[str, list[str]]]:
    """각 provider 가 보유한 폴더 vs 다른 provider 와 비교한 갭."""
    sets = {name: _subfolders(name) for name in targets}
    union = set().union(*sets.values())
    asymmetry: dict[str, dict[str, list[str]]] = {}
    for name in targets:
        missing = sorted(union - sets[name])
        extra = sorted(sets[name] - set().union(*(sets[o] for o in targets if o != name)))
        if missing or extra:
            asymmetry[name] = {"missing": missing, "extra": extra}
    return asymmetry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--providers",
        default=",".join(_DEFAULT_TARGETS),
        help="쉼표 구분 provider 목록. 기본 dart,edgar. edinet 은 API 불가 deferred 로 기본 제외.",
    )
    parser.add_argument("--strict", action="store_true", help="baseline 무시, 모든 갭 fail")
    parser.add_argument("--update-baseline", action="store_true", help="현 상태로 baseline 덮어쓰기")
    args = parser.parse_args()
    targets = _parseProviders(args.providers)

    asymmetry = _computeAsymmetry(targets)

    print("=== providers/ folder mirror audit (룰 2) ===")
    print(f"대상 provider: {', '.join(targets)}")
    for name in targets:
        folders = sorted(_subfolders(name))
        print(f"  {name}: {folders}")

    if args.update_baseline:
        _BASELINE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE.write_text(
            json.dumps(
                {"_note": "P-트랙 phase 통과마다 축소", "asymmetry": asymmetry},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {_BASELINE.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline()
    baseline_asymmetry = baseline.get("asymmetry", {})

    new_violations: list[str] = []
    for name, gap in asymmetry.items():
        allowed = baseline_asymmetry.get(name, {"missing": [], "extra": []})
        for missing in gap["missing"]:
            if missing not in allowed.get("missing", []):
                new_violations.append(f"{name}: 누락 폴더 신규 {missing}")
        for extra in gap["extra"]:
            if extra not in allowed.get("extra", []):
                new_violations.append(f"{name}: 단독 폴더 신규 {extra}")

    if args.strict:
        violations = [f"{name}: 누락 {missing}" for name, gap in asymmetry.items() for missing in gap["missing"]] + [
            f"{name}: 단독 {extra}" for name, gap in asymmetry.items() for extra in gap["extra"]
        ]
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations:
                print(f"  - {v}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 갭 ===")
        for v in new_violations:
            print(f"  - {v}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
