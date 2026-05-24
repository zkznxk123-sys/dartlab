"""모듈 크기 audit — sub-namespace 별 LOC 격차 측정 (T9-4).

src/dartlab/ 아래 sub-namespace (providers / scan / analysis / quant / ...) 의
의미있는 라인 수를 합산. 최대/최소 격차가 임계값 (Q2 15x, Q4 10x) 초과 시 경고.

목적: providers 가 104K monolithic 인 반면 industry 가 5.8K 인 18× 격차 →
유지보수성 저하 + 신규 기여자 진입 장벽. T9-1 providers 분해 트랙의 측정 기반.

baseline: 2026-05-23 측정 약 18× 격차.
목표: Q4 (2026-12-31) ≤ 10x.

실행::

    uv run python -X utf8 tests/audit/moduleSizeAudit.py
    uv run python -X utf8 tests/audit/moduleSizeAudit.py --json
    uv run python -X utf8 tests/audit/moduleSizeAudit.py --strict --max-ratio 15

종료 코드:
    0 — 격차 ≤ max-ratio 또는 --strict 없음
    2 — --strict + 격차 > max-ratio
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "src" / "dartlab"

# sub-namespace 명시 (재귀 검색 root). 그 외 (top-level *.py) 는 "__root__" 로 합산.
_SKIP_NAMESPACES: tuple[str, ...] = ("__pycache__", "_generated")


def countMeaningfulLines(filePath: Path) -> int:
    """파일 안 의미있는 라인 수 (empty + 순수 주석 제외)."""
    try:
        text = filePath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def measure() -> dict[str, int]:
    """src/dartlab/ 아래 sub-namespace 별 LOC 합."""
    bySubNamespace: dict[str, int] = {}
    if not SRC_ROOT.exists():
        return {}

    for pyFile in SRC_ROOT.rglob("*.py"):
        relParts = pyFile.relative_to(SRC_ROOT).parts
        if any(part in _SKIP_NAMESPACES for part in relParts):
            continue
        # sub-namespace = src/dartlab 다음 첫 폴더 또는 top-level 파일
        if len(relParts) > 1:
            subKey = relParts[0]
        else:
            subKey = "__root__"
        loc = countMeaningfulLines(pyFile)
        bySubNamespace[subKey] = bySubNamespace.get(subKey, 0) + loc

    return dict(sorted(bySubNamespace.items(), key=lambda x: -x[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="모듈 크기 audit (T9-4)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--strict", action="store_true", help="격차 초과 시 exit 2")
    parser.add_argument(
        "--max-ratio",
        type=float,
        default=15.0,
        help="허용 최대 격차 (max/min). 기본 15 (Q2). Q4 목표 10.",
    )
    args = parser.parse_args()

    bySubNamespace = measure()
    if not bySubNamespace:
        print("[moduleSize] src/dartlab/ 없음")
        return 1

    sortedItems = list(bySubNamespace.items())
    maxName, maxLoc = sortedItems[0]
    minName, minLoc = sortedItems[-1]
    ratio = (maxLoc / minLoc) if minLoc > 0 else 0.0

    result = {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "totalSubNamespaces": len(bySubNamespace),
        "maxSubNamespace": {"name": maxName, "loc": maxLoc},
        "minSubNamespace": {"name": minName, "loc": minLoc},
        "ratio": round(ratio, 2),
        "maxRatioAllowed": args.max_ratio,
        "distribution": bySubNamespace,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[moduleSize] sub-namespace {len(bySubNamespace)} 개")
        print(f"[moduleSize] 최대 {maxName}: {maxLoc:,} LOC")
        print(f"[moduleSize] 최소 {minName}: {minLoc:,} LOC")
        print(f"[moduleSize] 격차 {ratio:.2f}x (허용 {args.max_ratio:.0f}x)")
        if ratio > args.max_ratio:
            print(f"[moduleSize] OVER — {maxName} 분해 검토 권장 (T9-1 트랙)")
        else:
            print("[moduleSize] OK — 격차 임계값 이하")

        # 상위 5 / 하위 5 표시
        print("\n상위 5 sub-namespace:")
        for name, loc in sortedItems[:5]:
            print(f"  {name:20s} {loc:>8,} LOC")
        print("\n하위 5 sub-namespace:")
        for name, loc in sortedItems[-5:]:
            print(f"  {name:20s} {loc:>8,} LOC")

    if args.strict and ratio > args.max_ratio:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
