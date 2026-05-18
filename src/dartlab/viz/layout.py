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
KIND_DEFAULT_TIER: dict[str, dict[str, Any]] = {
    "kpiTile": {"cs": 4, "rs": 2, "variance": ["4x3", "6x2", "8x2"]},  # 작게 — 한 행 6 카드 = 24col 정확
    "diffView": {"cs": 4, "rs": 2, "variance": ["8x4", "12x4"]},
    "gauge": {"cs": 4, "rs": 3, "variance": ["8x4"]},  # 한 행 6 카드
    "topList": {"cs": 4, "rs": 4, "variance": ["8x4"]},  # 한 행 6 카드
    "trend": {"cs": 8, "rs": 8, "variance": ["12x8", "24x6", "6x6", "12x12"]},
    "breakdown": {"cs": 8, "rs": 8, "variance": ["12x6"]},
    "scatter": {"cs": 8, "rs": 8, "variance": ["12x8"]},
    "matrix": {"cs": 8, "rs": 8, "variance": ["12x8"]},
    "waterfall": {"cs": 8, "rs": 8, "variance": ["12x6"]},
    "radar": {"cs": 12, "rs": 12, "variance": ["8x8"]},
    "comparisonTable": {"cs": 12, "rs": 8, "variance": ["24x6"]},
    "phaseIndicator": {"cs": 24, "rs": 2, "variance": ["12x3", "24x3"]},
    "narrativeBridge": {"cs": 24, "rs": 4, "variance": []},
    "scoreBadge": {"cs": 24, "rs": 3, "variance": ["12x3"]},
    "sankey": {"cs": 12, "rs": 8, "variance": ["8x8"]},  # legacy
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

    # kind=trend 자동 보정 (24-col 기준):
    # 1~3 시리즈 = 8×8 (default 정사각, 3 카드/한행)
    # 4~5 시리즈 = 12×12 (hero, 2 카드/한행)
    # 6+ 시리즈 = 24×6 (wide, 한 행 전체)
    if kind == "trend":
        nSeries = len(entry.get("seriesPlan") or [])
        if nSeries >= 6:
            return 24, 6
        if 4 <= nSeries <= 5:
            return 12, 12
        # 1~3 시리즈 = 8×8 (default)

    return default["cs"], default["rs"]


def packSkyline(
    cards: list[tuple[str, CatalogEntry]],
    colCount: int = 24,
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


# sub 별 카드 narrative 정렬 우선순위 — KPI 가 hero, 추세는 본문, 분해/위험은 끝.
# 사용자 1 지시: 카드 순서 = 의미 흐름 (위→아래 / 좌→우 = 종합 → 분해).
_NARRATIVE_KIND_ORDER: dict[str, int] = {
    "kpiTile": 0,
    "diffView": 1,
    "scoreBadge": 2,
    "narrativeBridge": 3,
    "trend": 4,
    "breakdown": 5,
    "waterfall": 6,
    "comparisonTable": 7,
    "radar": 8,
    "scatter": 9,
    "matrix": 10,
    "gauge": 11,
    "topList": 12,
    "percentileRank": 13,
    "phaseIndicator": 14,
    "sankey": 15,
}


def planTabLayout(
    tab: str,
    *,
    sub: str | None = None,
    colCount: int = 24,
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
        # sub view: KPI hero → trend → radar/gauge → topList/phase. catalog dict
        # 순서가 narrative 와 어긋난 경우 보정. stable sort 라 동일 kind 끼리는 catalog 순서.
        cards.sort(key=lambda kc: _NARRATIVE_KIND_ORDER.get(kc[1].get("kind", "trend"), 99))
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
