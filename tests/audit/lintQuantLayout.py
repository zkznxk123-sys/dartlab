"""quant 탭 layout 강행 검증 — bento 12-col row 합=12 + KIND_DEFAULT_TIER variance.

[[feedback_row_fills_12col_no_gap]] · [[feedback_dashboard_world_class_assets]]
룰 강행. 카드 추가 / size 변경 시 row 합 ≠ 12 또는 variance 위반 회귀 차단.

PR gate 등록 — `uv run python -X utf8 -m pytest tests/audit/lintQuantLayout.py -v`.
"""

from __future__ import annotations

import pytest

from dartlab.viz.catalog import CATALOG, TAB_KEYS
from dartlab.viz.layout import KIND_DEFAULT_TIER, planTabLayout


def test_quantRowSums12() -> None:
    """quant 탭 모든 row 의 colSpan 합 == 12 강행. bento 2026 §4."""
    placed = planTabLayout("quant")
    assert len(placed) > 0, "quant 탭 카드 0 — catalog/quant.py 등록 확인"

    rows: dict[int, list[tuple[str, int]]] = {}
    for p in placed:
        rows.setdefault(p["y"], []).append((p["cardKey"], p["w"]))

    failed: list[str] = []
    for y in sorted(rows):
        ws = [w for _, w in rows[y]]
        total = sum(ws)
        if total != 12:
            keys = " · ".join(f"{k}({w})" for k, w in rows[y])
            failed.append(f"row y={y} sum={total} (≠12): {keys}")
    assert not failed, "12-col row 합 위반:\n" + "\n".join(failed)


def test_quantKindVariance() -> None:
    """quant catalog 모든 카드의 layout 이 KIND_DEFAULT_TIER variance 준수."""
    invalid: list[str] = []
    for cardKey in TAB_KEYS.get("quant", []):
        entry = CATALOG.get(cardKey)
        if entry is None:
            invalid.append(f"{cardKey}: CATALOG 미등록")
            continue
        kind = entry.get("kind", "trend")
        layout = entry.get("layout") or {}
        if not layout:
            continue  # 기본 tier — 통과.
        cs = layout.get("colSpan")
        rs = layout.get("rowSpan")
        if cs is None or rs is None:
            continue
        tier = KIND_DEFAULT_TIER.get(kind)
        if tier is None:
            invalid.append(f"{cardKey}: unknown kind '{kind}'")
            continue
        defaultTier = f"{tier['cs']}x{tier['rs']}"
        thisTier = f"{cs}x{rs}"
        if thisTier != defaultTier and thisTier not in tier["variance"]:
            invalid.append(
                f"{cardKey}: kind={kind} layout={thisTier} not in variance {tier['variance']} (default={defaultTier})"
            )
    assert not invalid, "KIND_DEFAULT_TIER variance 위반:\n" + "\n".join(invalid)


def test_quantCardCount() -> None:
    """quant 탭 카드 수 최소 15 이상 — KPI summary 단일 보고 회귀 차단.

    옛 v1 = 7 카드 (캔들 1 + KPI summary 5 + placeholder 1). 사용자 격분 후
    v3 = 17+ 카드 (5 section bento). 카드 수 회귀 = quant 정체성 회귀.
    """
    placed = planTabLayout("quant")
    assert len(placed) >= 15, (
        f"quant 탭 카드 {len(placed)} 개 — 15 미만 회귀 (v1 KPI summary 패턴 복귀). "
        f"feedback_dashboard_world_class_assets 룰 위반."
    )


def test_quantNoPlaceholder() -> None:
    """quant 카드에 `comingSoon` / placeholder adapter 잔존 없음."""
    leftover: list[str] = []
    for cardKey in TAB_KEYS.get("quant", []):
        entry = CATALOG.get(cardKey)
        if entry is None:
            continue
        spec = entry.get("dataSpec") or {}
        adapter = spec.get("adapter", "")
        if "comingSoon" in adapter or "ComingSoon" in cardKey:
            leftover.append(f"{cardKey}: adapter={adapter}")
    assert not leftover, "placeholder 카드 잔존 — 사용자 1 순위 (백테스팅) placeholder 회귀:\n" + "\n".join(leftover)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
