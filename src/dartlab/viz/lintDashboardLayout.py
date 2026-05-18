"""lint — dashboard 카드 catalog 의 layout 변형 한도 검증.

CI gate. 모든 catalog entry 가 KIND_DEFAULT_TIER 의 variance 한도 안에 있어야.
한도 밖 layout 명시 시 PR 거부.

사용:
    uv run python -X utf8 src/dartlab/viz/lintDashboardLayout.py
    uv run python -X utf8 src/dartlab/viz/lintDashboardLayout.py --strict  # CI mode

exit code:
    0 — 모든 카드 통과.
    1 — 위반 있음 (변형 한도 밖 또는 kind 미지원).

설계 SSOT: src/dartlab/skills/specs/engines/dashboard/cardCatalog.md
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="Dashboard layout lint")
    parser.add_argument("--strict", action="store_true", help="CI mode — sankey 잔존도 거부")
    args = parser.parse_args()

    from dartlab.viz import CATALOG
    from dartlab.viz.layout import resolveLayout

    violations: list[str] = []
    for cardKey, entry in CATALOG.items():
        try:
            resolveLayout(entry)
        except ValueError as exc:
            violations.append(f"{cardKey}: {exc}")

    # strict: sankey 0 카드 보장.
    if args.strict:
        sankeyCount = sum(1 for k, e in CATALOG.items() if e.get("kind") == "sankey")
        if sankeyCount > 0:
            violations.append(f"strict: sankey 카드 {sankeyCount} 개 잔존 (P-DASH-V1 D6 폐기 미완)")

    if violations:
        print(f"[lintDashboardLayout] 위반 {len(violations)} 건:")
        for v in violations:
            print(f"  - {v}")
        return 1

    nCards = len(CATALOG)
    print(f"[lintDashboardLayout] OK — {nCards} 카드 모두 variance 한도 안.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
