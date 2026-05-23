"""폴더 vs 단일 .py 임계 검증 — P-트랙 룰 3.

도메인 합계 LoC:
    ≤ 400   단일 `.py` (예 `dividend.py`)
    401~800 폴더 + 1~2 sub-module
    > 800   폴더 + parser/pipeline/types 분할

임계 외 폴더화 (≤ 400 인데 폴더로 남아있음) 또는 단일화 (> 800 인데 분할 안 됨) 위반 보고.

baseline (`_baselines/folderSize.json`) 외 위반만 fail.

사용법:
    uv run python -X utf8 tests/audit/folderSize.py [target_path]
    uv run python -X utf8 tests/audit/folderSize.py --strict
    uv run python -X utf8 tests/audit/folderSize.py --update-baseline

종료 코드:
    0  통과
    1  baseline 외 위반 또는 --strict 위반
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
_BASELINE = _REPO / "tests" / "audit" / "_baselines" / "folderSize.json"

_SMALL_THRESHOLD = 400
_MEDIUM_THRESHOLD = 800

# 룰 2 (folder mirror) 가 강제하는 직속 sub-folder set — over_split 임계에서 제외.
# providers/{dart,edgar,edinet}/<MIRROR_FOLDERS> 는 LoC 작아도 mirror 만족 위해 유지.
_MIRROR_FOLDERS: frozenset[str] = frozenset(
    {"accessor", "builder", "bulk", "docs", "finance", "openapi", "ops", "parse", "report", "search"}
)

# gather/ 의 도메인 직속 subpackage — mirror 대상은 아니지만 도메인 응집 위해
# LoC 작아도 폴더 유지. providers/ 의 _MIRROR_FOLDERS 와 같은 의도, 다른 엔진.
_GATHER_EXEMPT_FOLDERS: frozenset[str] = frozenset(
    {"bulkData", "dart", "domains", "ecos", "fred", "infra", "krx", "mapping", "sources", "transforms"}
)


def _isMirrorFolder(folder: Path) -> bool:
    """provider 직속 sub-folder 인지 — providers/{X}/{MIRROR}/ 패턴 매칭."""
    parts = folder.parts
    if "providers" not in parts:
        return False
    idx = parts.index("providers")
    # providers/<provider>/<sub>  → 정확히 idx+2 가 mirror folder
    if len(parts) <= idx + 2:
        return False
    return parts[idx + 2] in _MIRROR_FOLDERS and len(parts) == idx + 3


def _isGatherExemptFolder(folder: Path) -> bool:
    """gather/ 직속 도메인 sub-folder 인지 — gather/<EXEMPT>/ 패턴 매칭."""
    parts = folder.parts
    if "gather" not in parts:
        return False
    idx = parts.index("gather")
    # gather/<sub> → 정확히 idx+1 이 exempt folder
    if len(parts) <= idx + 1:
        return False
    return parts[idx + 1] in _GATHER_EXEMPT_FOLDERS and len(parts) == idx + 2


def _countLoc(path: Path) -> int:
    try:
        return sum(1 for _ in path.read_text(encoding="utf-8").splitlines())
    except (UnicodeDecodeError, OSError):
        return 0


def _folderLoc(folder: Path) -> int:
    total = 0
    for p in folder.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        total += _countLoc(p)
    return total


def _scan(target: Path) -> dict[str, list[dict]]:
    """target 아래 sub-folder + 단일 .py 각각의 LoC 분류."""
    violations: dict[str, list[dict]] = {"over_split": [], "under_split": []}

    for child in target.rglob("*"):
        if "__pycache__" in child.parts:
            continue
        if child.is_dir():
            # 폴더 — LoC 합 ≤ 400 이면 over_split (단일화 권장)
            pyFiles = [p for p in child.glob("*.py") if p.name != "__init__.py" and not p.name.startswith("_")]
            if not pyFiles or any(p.is_dir() for p in child.iterdir() if p.name != "__pycache__"):
                continue  # 상위 폴더 (sub-folder 보유) 는 스킵
            if _isMirrorFolder(child):
                continue  # 룰 2 mirror 강제 폴더 — LoC 임계 면제
            if _isGatherExemptFolder(child):
                continue  # gather/ 도메인 응집 폴더 — LoC 임계 면제
            loc = _folderLoc(child)
            if loc <= _SMALL_THRESHOLD:
                violations["over_split"].append(
                    {
                        "path": str(child.relative_to(_REPO).as_posix()),
                        "loc": loc,
                        "files": len(pyFiles),
                        "recommendation": f"단일 {child.name}.py 로 통합 (LoC ≤ {_SMALL_THRESHOLD})",
                    }
                )
        elif child.suffix == ".py" and child.name not in ("__init__.py",) and not child.name.startswith("_"):
            # 단일 파일 — LoC > 800 이면 under_split (분할 권장)
            loc = _countLoc(child)
            if loc > _MEDIUM_THRESHOLD:
                violations["under_split"].append(
                    {
                        "path": str(child.relative_to(_REPO).as_posix()),
                        "loc": loc,
                        "recommendation": f"parser/pipeline/types 폴더로 분할 (LoC > {_MEDIUM_THRESHOLD})",
                    }
                )

    return violations


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"over_split": [], "under_split": [], "_note": "P0.5 baseline"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        nargs="?",
        default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()),
        help="검사 대상 path (기본 src/dartlab/providers)",
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--baseline",
        default=None,
        help="baseline JSON path (기본 _baselines/folderSize.json — gather 같은 별도 target 은 _baselines/gatherSize.json 권장)",
    )
    args = parser.parse_args()
    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE

    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    violations = _scan(target)

    print(f"=== folder size audit (룰 3) — {args.target} ===")
    print(
        f"임계: ≤ {_SMALL_THRESHOLD} 단일 / {_SMALL_THRESHOLD + 1}~{_MEDIUM_THRESHOLD} 폴더+sub / > {_MEDIUM_THRESHOLD} 분할"
    )
    print(f"over_split (폴더화 과잉): {len(violations['over_split'])} 건")
    print(f"under_split (분할 부족): {len(violations['under_split'])} 건")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        # baseline 에는 path 만 기록 (단순화)
        baseline_data = {
            "_note": "P-트랙 phase 통과마다 축소",
            "over_split": sorted(v["path"] for v in violations["over_split"]),
            "under_split": sorted(v["path"] for v in violations["under_split"]),
        }
        baselinePath.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline(baselinePath)
    allowed_over = set(baseline.get("over_split", []))
    allowed_under = set(baseline.get("under_split", []))
    # 사용자 룰로 영구 동결된 항목 — strict 모드에서도 면제.
    # 예 providers/{dart,edgar}/company.py 는 mixin/composition/파일 분리 금지 (사용자 룰).
    user_frozen = set(baseline.get("userFrozen", []))

    new_over = [v for v in violations["over_split"] if v["path"] not in allowed_over]
    new_under = [v for v in violations["under_split"] if v["path"] not in allowed_under]

    if args.strict:
        # strict 에서도 user_frozen 만큼은 면제.
        strict_over = [v for v in violations["over_split"] if v["path"] not in user_frozen]
        strict_under = [v for v in violations["under_split"] if v["path"] not in user_frozen]
        if strict_over or strict_under:
            print("\n=== STRICT FAIL ===")
            for v in strict_over[:20]:
                print(f"  [over]  {v['path']} — {v['loc']} LoC")
            for v in strict_under[:20]:
                print(f"  [under] {v['path']} — {v['loc']} LoC")
            return 1
        print("\n=== STRICT PASS ===")
        if user_frozen:
            print(f"(userFrozen 면제 {len(user_frozen)} 항목)")
        return 0

    if new_over or new_under:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_over:
            print(f"  [over] {v['path']} — {v['loc']} LoC → {v['recommendation']}")
        for v in new_under:
            print(f"  [under] {v['path']} — {v['loc']} LoC → {v['recommendation']}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
