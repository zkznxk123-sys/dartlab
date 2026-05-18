"""Dashboard Layout Engine — 카드 카탈로그 query + tier resolve + bento packing.

설계: catalog 의 카드 entry 가 SSOT. 본 모듈은 entry 의 (kind, layout, seriesPlan)
을 보고 12-col gridstack 식 bento grid 의 (colSpan, rowSpan, x, y) 좌표 자동
산출. cellHeight = columnWidth sync 라 colSpan==rowSpan 이면 자동 1:1 정사각.

매커니즘 5 요소:
1. queryCards(tab, sub, kinds) — 카탈로그 다중 필터 검색.
2. listBlocks(blockKey) — Looker-style semantic 묶음 호출.
3. KIND_DEFAULT_TIER — kind 별 default (colSpan, rowSpan) + variance 한도.
4. resolveLayout(entry) — entry.layout 명시 또는 kind default → (cs, rs).
5. packSkyline(cards) — 순서 보존 빈 공간 0 packing (CSS dense 의 fallback).

원칙:
- 1 entry → 1 tier (default). 변형은 catalog 의 layout 필드 명시.
- kpiTile = 3×3 (KPI 정사각, 4 카드/한행). 차트·테이블 = 4×4 (3 카드/한행).
  Hero = 6×6 (radar 등). Wide = 12×3 (한 행 전체).
- trend 시리즈 수 자동 보정 (3 이하 = 4×4, 4+ = 6×6 hero).
- 변형 한도 위반 = ValueError (lintDashboardLayout 가 PR gate).

12-col 메커니즘 (운영자 요구 "그래프·테이블 1:1 정사각 3 카드/한행" 강제):
- frontend BentoGrid: gridTemplateColumns=repeat(12, cellSize) + gridAutoRows=cellSize.
- 차트 카드 colSpan=rowSpan=4 → 12-col 기준 3 개/한행, 자동 1:1 정사각.
- KPI 카드 colSpan=rowSpan=3 → 12-col 기준 4 개/한행, 자동 1:1 정사각.
"""

from __future__ import annotations

from typing import Any

from dartlab.viz.catalog import CATALOG
from dartlab.viz.schema import CatalogEntry

# 24-col gridstack fine grid (v3): cellSize ≈ 56px (viewport 1700, sidebar 240).
# cellHeight = columnWidth sync → cs==rs 면 시각 정사각.
# kind 별 본질 비율 (정사각 강박 폐기):
# - KPI/diffView = 5×2 가로 (값+추세 단일 metric)
# - gauge/topList = 5×3 / 5×4 세로 (단일 score / 리스트)
# - trend/breakdown/scatter/matrix/waterfall = 8×8 정사각 (시계열 + 다중 series)
# - radar/comparisonTable = 12×12 / 12×8 hero (다차원/peer)
# - phaseIndicator = 24×2 strip (한 행 전체 얇음)
# - narrativeBridge/scoreBadge = 24×4 / 24×3 wide (서사/평점)
# v3-r7 — bento 2026 정통 12-col grid + Anthropic data-viz skill 룰.
# Hero 12×N (assetComposition full row) / Feature 4×3 (chart+table 1/3 폭) /
# Metric 3×1 (KPI 핵심) / Accent 2×1 (KPI 확장 / 6 개 한 줄) / Strip 4×3.
# 모든 size 12 약수 (1,2,3,4,6,12).
KIND_DEFAULT_TIER: dict[str, dict[str, Any]] = {
    "kpiTile": {"cs": 3, "rs": 1, "variance": ["2x1", "4x1", "6x1", "12x1"]},
    "diffView": {"cs": 4, "rs": 2, "variance": ["3x2", "6x2", "12x2"]},
    "gauge": {"cs": 3, "rs": 3, "variance": ["4x3", "6x3"]},
    "topList": {"cs": 4, "rs": 3, "variance": ["3x3", "6x3", "12x3"]},
    # trend chart+table 4×3 default — 한 행 3 카드 (bento 2026 §1 Feature).
    "trend": {"cs": 4, "rs": 3, "variance": ["3x3", "6x3", "6x4", "12x3", "12x4", "12x6"]},
    "breakdown": {"cs": 4, "rs": 3, "variance": ["6x3", "12x4"]},
    "scatter": {"cs": 4, "rs": 3, "variance": ["6x3", "6x4"]},
    "matrix": {"cs": 4, "rs": 3, "variance": ["6x3", "12x4"]},
    "waterfall": {"cs": 4, "rs": 3, "variance": ["6x3", "12x4"]},
    "radar": {"cs": 4, "rs": 4, "variance": ["6x4", "6x6"]},
    "comparisonTable": {"cs": 6, "rs": 4, "variance": ["12x3", "12x4"]},
    "phaseIndicator": {"cs": 12, "rs": 1, "variance": ["12x2"]},
    "narrativeBridge": {"cs": 12, "rs": 3, "variance": ["12x4"]},
    "scoreBadge": {"cs": 6, "rs": 3, "variance": ["12x3"]},
}


# Looker-style semantic Block library — 카드 묶음 의미 단위.
# AI 또는 frontend 가 "수익성 분석" 한 호출로 카드 5 묶음 받음.
BLOCKS: dict[str, list[str]] = {
    "performanceCore": [
        "kpiOpMarginPerf",
        "kpiNetMarginPerf",
        "kpiRoePerf",
        "kpiRoicPerf",
        "marginTrend",
        "returnTrend",
        "growthYoy",
    ],
    "capitalStructureCore": [
        "kpiDebtRatio",
        "kpiCurrentRatio",
        "kpiCashAssets",
        "kpiInterestCoverage",
        "assetComposition",
        "liabilityDetail",
        "equityDetail",
        "liquidityTrend",
        "leverageTrend",
    ],
    "cashflowCore": [
        "kpiCashOp",
        "kpiCashFcf",
        "kpiCashFcfMargin",
        "kpiCashPayout",
        "cashflowSigned",
        "fcfTrend",
        "capitalAllocationBars",
        "capitalAllocationWaterfall",
    ],
    "riskCore": [
        "altmanZGauge",
        "beneishGauge",
        "interestCoverageGauge",
        "debtEbitdaGauge",
        "scenarioSensitivityHeatmap",
        "anomalyTopList",
        "lifeCyclePhase",
    ],
}


def queryCards(
    *,
    tab: str | None = None,
    sub: str | None = None,
    kinds: list[str] | None = None,
    topic: str | None = None,
) -> list[tuple[str, CatalogEntry]]:
    """카탈로그 다중 필터 검색.

    Args:
        tab: 'financial' 또는 'viewer' (옛 8 탭 → financial 안의 7 방법론
            view 로 흡수됨).
        sub: 재무제표 7 분석 방법론 — story/dupont/value/growth/credit/
            quality/snowflake. None = 전체 (sub 무관).
        kinds: ['trend','kpiTile',...] 중 하나라도 매치.
        topic: 'IS'/'BS'/'CF'/'ratios'.

    Returns:
        list[(cardKey, entry)] — catalog 순서 보존.

    Example:
        >>> queryCards(tab='financial', sub='dupont')
        [('kpiRoe', {...}), ('marginTrend', {...}), ...]
    """
    out: list[tuple[str, CatalogEntry]] = []
    for k, e in CATALOG.items():
        if tab is not None and e.get("tab") != tab:
            continue
        if sub is not None and e.get("subCategory") != sub:
            continue
        if kinds and e.get("kind") not in kinds:
            continue
        if topic is not None and e.get("topic") != topic:
            continue
        out.append((k, e))
    return out


def listBlocks(blockKey: str) -> list[str]:
    """Semantic block — 의미 단위 카드 묶음 (Looker Block library 흡수).

    Args:
        blockKey: 'performanceCore'/'capitalStructureCore'/'cashflowCore'/'riskCore'.

    Returns:
        cardKey list (catalog 존재 보장 안 함 — caller 가 query 로 검증).
    """
    return list(BLOCKS.get(blockKey, []))


def resolveLayout(entry: CatalogEntry) -> tuple[int, int]:
    """카드 entry → (colSpan, rowSpan) 산출 + 변형 한도 검증.

    우선순위:
    1. entry.layout 명시 → 변형 한도 안인지 확인.
    2. kind=trend 미명시 → seriesPlan 길이로 자동 보정 (1~3=M, 4~5=L, 6+=XL).
    3. 그 외 미명시 → KIND_DEFAULT_TIER.

    Args:
        entry: catalog 의 단일 entry.

    Returns:
        (colSpan, rowSpan) tuple.

    Raises:
        ValueError: 변형 한도 위반 또는 kind 미지원.
    """
    kind = entry.get("kind", "trend")
    if kind not in KIND_DEFAULT_TIER:
        raise ValueError(f"viz.layout.resolveLayout: unknown kind '{kind}'")
    default = KIND_DEFAULT_TIER[kind]
    hint = entry.get("layout") or {}

    if hint:
        cs = hint.get("colSpan", default["cs"])
        rs = hint.get("rowSpan", default["rs"])
        tier = f"{cs}x{rs}"
        defaultTier = f"{default['cs']}x{default['rs']}"
        if tier != defaultTier and tier not in default["variance"]:
            cardKey = entry.get("title", "<unknown>")
            raise ValueError(
                f"viz.layout: card '{cardKey}' layout {tier} not in variance "
                f"{default['variance']} (kind={kind}, default={defaultTier})"
            )
        return cs, rs

    # v3-r7 — kind=trend 자동 보정 (bento 2026 12-col).
    # 8+ 시리즈 (assetComposition 9 dual-stack 등) = 12×4 hero full row.
    # 1~7 = 4×3 feature (1/3 폭).
    if kind == "trend":
        nSeries = len(entry.get("seriesPlan") or [])
        if nSeries >= 8:
            return 12, 4
        return 4, 3

    return default["cs"], default["rs"]


def packSkyline(
    cards: list[tuple[str, CatalogEntry]],
    colCount: int = 12,
) -> list[dict[str, Any]]:
    """First-Fit-Decreasing skyline packing — 순서 보존 + 빈 공간 0.

    catalog 순서가 의미 흐름 (narrative) 이므로 보존. 카드가 현재 row 에
    안 들어가면 다음 row 로. backfill: 다음 카드가 작으면 현재 row 빈 곳 채움.

    Args:
        cards: queryCards 결과.
        colCount: grid column 수 (12 = gridstack 표준 default).

    Returns:
        [{cardKey, kind, title, x, y, w, h}, ...] — frontend dispatch.

    Algorithm:
        skyline[c] = 각 col 의 다음 빈 row index (위→아래).
        매 반복: 가장 낮은 row 의 가장 좌측 col 부터 가능한 width 측정 →
        catalog 큐에서 width 안 맞는 첫 카드 선택 → 배치 → skyline 갱신.
    """
    skyline = [0] * colCount
    placed: list[dict[str, Any]] = []
    queue = list(cards)

    while queue:
        # 다음 빈 slot 찾기 — 가장 낮은 row, 가장 좌측 col.
        minY = min(skyline)
        startCol = skyline.index(minY)
        # 이 row 의 연속 빈 width.
        availWidth = 0
        for c in range(startCol, colCount):
            if skyline[c] == minY:
                availWidth += 1
            else:
                break

        # 큐에서 width <= availWidth 인 첫 카드.
        chosenIdx = None
        for i, (_, e) in enumerate(queue):
            try:
                w, _ = resolveLayout(e)
            except ValueError:
                continue
            if w <= availWidth:
                chosenIdx = i
                break

        if chosenIdx is None:
            # 큐 모든 카드가 availWidth 초과 — 다음 row 로 진입 (skyline 의
            # 가장 낮은 col 을 그 다음 높이로 올림).
            nextRow = min(s for s in skyline if s > minY) if any(s > minY for s in skyline) else minY + 1
            for c in range(startCol, startCol + availWidth):
                skyline[c] = nextRow
            continue

        cardKey, entry = queue.pop(chosenIdx)
        w, h = resolveLayout(entry)
        x, y = startCol, minY
        for c in range(x, x + w):
            skyline[c] = y + h
        placed.append(
            {
                "cardKey": cardKey,
                "kind": entry.get("kind", "trend"),
                "title": entry.get("title", cardKey),
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )

    return placed


# v3-r5 §9 — F-pattern 시선 흐름. Hero (narrativeBridge/radar/scoreBadge/wide gauge/phaseIndicator)
# 가 *좌상단* y=0 박히게 priority 0. KPI strip 그 다음, 본문 trend, 끝에 signals.
# 추가 규칙: layout.colSpan >= 24 인 카드는 priority 강제 0 (wide hero 우선) — resolveKindOrder 참조.
_NARRATIVE_KIND_ORDER: dict[str, int] = {
    "narrativeBridge": 0,  # Tier 1 — conclusion / hero text
    "scoreBadge": 0,
    "radar": 0,  # Tier 1 — hero polygon
    "phaseIndicator": 0,  # Tier 1 — strip
    "kpiTile": 1,  # Tier 2 — result
    "diffView": 1,
    "topList": 2,  # Tier 3 — decomp
    "gauge": 2,  # 일반 gauge (wide 는 entry cs 로 priority 0 강제)
    "trend": 3,  # Tier 3 — trend body
    "breakdown": 4,
    "scatter": 5,
    "matrix": 6,
    "waterfall": 7,
    "comparisonTable": 8,  # Tier 4 — peer
    "percentileRank": 8,
}


def _kindOrderKey(entry: CatalogEntry) -> int:
    """카드 정렬 우선순위 — kind + layout 폭 결합. wide hero (cs >= 24) 강제 priority 0."""
    kind = entry.get("kind", "trend")
    layout = entry.get("layout") or {}
    cs = layout.get("colSpan", 0)
    if cs >= 24:
        return 0
    return _NARRATIVE_KIND_ORDER.get(kind, 99)


def planTabLayout(
    tab: str,
    *,
    sub: str | None = None,
    colCount: int = 12,
) -> list[dict[str, Any]]:
    """탭 + sub view → packed layout grid.

    Args:
        tab: 'financial'/'portfolio'/.../'macro'.
        sub: 재무제표 sub view ('performance' 등). None = 전체.
            tab='financial' + sub=None 일 때는 OVERVIEW_KEYS 의 curated 12 카드
            (한눈에 진단 narrative) 만. 38 카드 dump 가 아닌 흐름 view.
        colCount: grid column 수.

    Returns:
        [{cardKey, kind, title, x, y, w, h}, ...] — frontend dispatch.

    Example:
        >>> planTabLayout('financial', sub='performance')
        [{'cardKey': 'kpiOpMarginPerf', 'x': 0, 'y': 0, 'w': 1, 'h': 1, ...}, ...]
    """
    if tab == "financial" and sub is None:
        from dartlab.viz.catalog.finance import OVERVIEW_KEYS

        ordered: list[tuple[str, CatalogEntry]] = []
        for k in OVERVIEW_KEYS:
            entry = CATALOG.get(k)
            if entry is not None:
                ordered.append((k, entry))
        return packSkyline(ordered, colCount=colCount)

    cards = queryCards(tab=tab, sub=sub)
    if sub is not None:
        # sub view: Hero (narrativeBridge/radar/scoreBadge/wide) → KPI → trend → signals.
        # stable sort 라 동일 priority 끼리는 catalog 순서. wide hero (cs >= 24) 강제 priority 0.
        cards.sort(key=lambda kc: _kindOrderKey(kc[1]))
    return packSkyline(cards, colCount=colCount)


__all__ = [
    "BLOCKS",
    "KIND_DEFAULT_TIER",
    "listBlocks",
    "packSkyline",
    "planTabLayout",
    "queryCards",
    "resolveLayout",
]
