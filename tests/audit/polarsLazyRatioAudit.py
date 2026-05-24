"""Polars lazy 활용 비율 측정 (T3-5).

Polars 의 lazy evaluation (`scan_parquet`, `LazyFrame`) 은 query optimizer + 메모리
효율 + push-down 최적화. eager (`read_parquet`, `DataFrame`) 대비 대용량 처리에서
2-10x 성능 차이.

측정 대상 (src/dartlab/ AST grep):
    - `pl.DataFrame(` / `pl.read_parquet(` / `pl.read_csv(` → eager 카운트
    - `pl.LazyFrame(` / `pl.scan_parquet(` / `pl.scan_csv(` → lazy 카운트
    - `.lazy()` / `.collect()` 호출 분석

비율: lazy / (lazy + eager) × 100.
baseline: 추정 ~70% (2026-05-23).
목표: Q3 ≥ 90% (T3-5 트랙).

실행::

    uv run python -X utf8 tests/audit/polarsLazyRatioAudit.py
    uv run python -X utf8 tests/audit/polarsLazyRatioAudit.py --json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src" / "dartlab"

_EAGER_PATTERNS: tuple[str, ...] = (
    r"\bpl\.DataFrame\(",
    r"\bpl\.read_parquet\(",
    r"\bpl\.read_csv\(",
    r"\bpl\.read_ipc\(",
    r"\bpl\.read_json\(",
)
_LAZY_PATTERNS: tuple[str, ...] = (
    r"\bpl\.LazyFrame\(",
    r"\bpl\.scan_parquet\(",
    r"\bpl\.scan_csv\(",
    r"\bpl\.scan_ipc\(",
    r"\bpl\.scan_ndjson\(",
    r"\.lazy\(\)",
)

_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "__pycache__",
    "_generated",
)


def scanFile(filePath: Path) -> tuple[int, int]:
    """단일 파일에서 (eager_count, lazy_count) 반환."""
    try:
        text = filePath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    eagerCount = sum(len(re.findall(p, text)) for p in _EAGER_PATTERNS)
    lazyCount = sum(len(re.findall(p, text)) for p in _LAZY_PATTERNS)
    return eagerCount, lazyCount


def measure() -> dict:
    """src/dartlab/ 전체 스캔 — sub-namespace 별 eager/lazy 카운트 합."""
    bySubNamespace: dict[str, dict[str, int]] = {}
    totalEager = 0
    totalLazy = 0

    for pyFile in SRC.rglob("*.py"):
        relParts = pyFile.relative_to(SRC).parts
        if any(p in _SKIP_PATH_PREFIXES for p in relParts):
            continue
        eager, lazy = scanFile(pyFile)
        if eager == 0 and lazy == 0:
            continue
        subKey = relParts[0] if len(relParts) > 1 else "__root__"
        sub = bySubNamespace.setdefault(subKey, {"eager": 0, "lazy": 0})
        sub["eager"] += eager
        sub["lazy"] += lazy
        totalEager += eager
        totalLazy += lazy

    totalCalls = totalEager + totalLazy
    lazyRatio = round((totalLazy / totalCalls * 100) if totalCalls > 0 else 0.0, 2)

    return {
        "measuredAt": dt.datetime.now(dt.UTC).isoformat(),
        "totalEager": totalEager,
        "totalLazy": totalLazy,
        "totalCalls": totalCalls,
        "lazyRatio": lazyRatio,
        "bySubNamespace": dict(sorted(bySubNamespace.items(), key=lambda x: -(x[1]["eager"] + x[1]["lazy"]))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Polars lazy 비율 측정 (T3-5)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--strict", action="store_true", help="비율 < threshold 시 exit 2")
    parser.add_argument("--threshold", type=float, default=70.0, help="strict 임계값 (baseline 70 / Q3 90)")
    args = parser.parse_args()

    result = measure()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"[polarsLazy] 총 Polars 호출 {result['totalCalls']:,} (eager {result['totalEager']:,} / lazy {result['totalLazy']:,})"
        )
        print(f"[polarsLazy] lazy 비율: {result['lazyRatio']:.2f} percent (임계 {args.threshold:.0f} percent)")

        # 상위 eager 비율 sub-namespace (개선 후보)
        eagerHeavy = [(name, data) for name, data in result["bySubNamespace"].items() if data["eager"] > 0]
        eagerHeavy.sort(key=lambda x: -x[1]["eager"])
        print("\neager 호출 상위 5 sub-namespace (lazy 전환 후보):")
        for name, data in eagerHeavy[:5]:
            ratio = (data["lazy"] / (data["eager"] + data["lazy"]) * 100) if (data["eager"] + data["lazy"]) > 0 else 0
            print(f"  {name:20s} eager={data['eager']:>4d}  lazy={data['lazy']:>4d}  lazy_ratio={ratio:.1f}%")

    if args.strict and result["lazyRatio"] < args.threshold:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
