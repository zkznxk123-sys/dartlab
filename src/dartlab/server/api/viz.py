"""viz dashboard 엔드포인트 — catalog + builder + render 의 HTTP 진입점.

3 엔드포인트:
- ``GET /api/viz/catalog``  — 카드 메타 (cardKey · title · xlSpan · kind).
                              web 그리드 구성용.
- ``GET /api/viz/dashboard/{stockCode}``  — Phase 1 8 카드 일괄 View list.
                              web 진입 시 단일 호출.
- ``GET /api/viz/spec/{cardKey}/{stockCode}``  — 단일 카드 lazy/refresh.

View 출력은 `toRechartsSpec` 결과 — recharts 호환 JSON. paletteOverride 는
web 측이 dark/light 토글에 맞춰 자체 적용 (서버는 catalog 기본 hex 그대로).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from dartlab.viz import (
    CATALOG,
    FINANCE_DASHBOARD_KEYS,
    OVERVIEW_KEYS,
    TAB_KEYS,
    buildView,
    planTabLayout,
    toRechartsSpec,
)
from dartlab.viz.layout import packSkyline

router = APIRouter()


def _catalogMeta() -> list[dict[str, Any]]:
    """catalog dict → 메타 리스트 (web 그리드 구성용)."""
    return [
        {
            "cardKey": k,
            "title": entry.get("title", ""),
            "kind": entry.get("kind", ""),
            "topic": entry.get("topic", ""),
            "tab": entry.get("tab", "financial"),
            "subCategory": entry.get("subCategory", ""),
            "xlSpan": entry.get("xlSpan", 1),
            "seriesCount": len(entry.get("seriesPlan") or []),
            "help": entry.get("help", ""),
        }
        for k, entry in CATALOG.items()
    ]


@router.get("/api/viz/catalog")
async def apiVizCatalog() -> dict[str, Any]:
    """등록된 카드 카탈로그 메타."""
    return {
        "cards": _catalogMeta(),
        "dashboardKeys": list(FINANCE_DASHBOARD_KEYS),
    }


def _safeBuildAndRender(cardKey: str, code: str, periodKind: str, nPeriods: int) -> dict[str, Any]:
    """buildView + toRechartsSpec — 예외는 카드 단위 error envelope."""
    try:
        view = buildView(cardKey, code, periodKind=periodKind, nPeriods=nPeriods)  # type: ignore[arg-type]
        return toRechartsSpec(view)
    except Exception as exc:  # noqa: BLE001
        return {
            "cardKey": cardKey,
            "error": str(exc),
            "componentType": "Error",
            "kind": "error",
            "title": CATALOG.get(cardKey, {}).get("title", cardKey),
        }


def _isCardEmpty(spec: dict[str, Any]) -> bool:
    """v3-r5 §3.1 — spec 의 데이터 의미 무효 판정. True 면 packSkyline 큐에서 omit.

    의미 무효 표면 (운영자 원칙 4 위반):
    - spec error / kind error
    - kpiTile 의 모든 tile value None 또는 (0 + non-scoreMode)
    - topList items 0
    - trend 모든 series data 가 None 도배
    - gauge value None + bands 빈
    - radar 모든 dimension 0 (Snowflake 5 차원 0 점 도배 회피)
    - scoreBadge dimensions 0 + overallScore None
    - narrativeBridge transitions 0
    """
    if spec is None or spec.get("error"):
        return True
    kind = spec.get("kind")
    if kind == "kpiTile":
        tiles = spec.get("tiles") or []
        if not tiles:
            return True
        scoreMode = (spec.get("options") or {}).get("scoreMode") is True
        return all(
            (t.get("value") in (None,) or (t.get("value") == 0 and not scoreMode)) for t in tiles
        )
    if kind in ("topList",):
        return not (spec.get("items") or [])
    if kind in ("comparisonTable",):
        return not (spec.get("rows") or [])
    if kind == "trend":
        series = spec.get("series") or []
        if not series:
            return True
        return all(all(v is None for v in (s.get("data") or [])) for s in series)
    if kind == "gauge":
        return spec.get("value") is None
    if kind == "scoreBadge":
        return not (spec.get("dimensions") or []) and spec.get("overallScore") is None
    if kind == "narrativeBridge":
        return not (spec.get("transitions") or [])
    if kind == "phaseIndicator":
        return not (spec.get("phases") or [])
    if kind == "radar":
        series = spec.get("series") or []
        if not series:
            return True
        return all(all((v is None or v == 0) for v in (s.get("data") or [])) for s in series)
    if kind in ("matrix", "scatter", "breakdown", "waterfall"):
        # 기본: series + categories 둘 다 비면 omit.
        return not (spec.get("series") or spec.get("cells") or spec.get("points") or [])
    return False


async def _prefetchCompany(stockCode: str) -> None:
    """Company rawFinance 를 한 번 collect → LRU 안착. 동시 빌드 race 방지."""
    from dartlab.viz.display.finance._cache import getCompany

    def _warm() -> None:
        c = getCompany(stockCode)
        _ = c.rawFinance  # lazy frame collect 강제

    await asyncio.to_thread(_warm)


@router.get("/api/viz/dashboard/{stockCode}")
async def apiVizDashboard(
    stockCode: str,
    periodKind: str = Query("annual", pattern="^(annual|quarterly)$"),
    nPeriods: int = Query(40, ge=2, le=80),
) -> dict[str, Any]:
    """대시보드 카드 일괄 빌드 → recharts spec list.

    Company rawFinance 를 먼저 한 번 collect 해서 LRU 안착시킨 뒤
    각 카드를 동시 빌드 (cold-start race 방지).
    """
    await _prefetchCompany(stockCode)
    keys = list(FINANCE_DASHBOARD_KEYS)

    async def _one(k: str) -> dict[str, Any]:
        return await asyncio.to_thread(_safeBuildAndRender, k, stockCode, periodKind, nPeriods)

    specs = await asyncio.gather(*[_one(k) for k in keys])
    return {
        "stockCode": stockCode,
        "periodKind": periodKind,
        "cards": dict(zip(keys, specs)),
        "order": keys,
    }


@router.get("/api/viz/tab/{tab}/{stockCode}")
async def apiVizTabDashboard(
    tab: str,
    stockCode: str,
    periodKind: str = Query("annual", pattern="^(annual|quarterly)$"),
    nPeriods: int = Query(40, ge=2, le=80),
) -> dict[str, Any]:
    """탭별 카드 일괄 빌드. financial 외 7 탭은 placeholder 또는 시계열 proxy."""
    keys = TAB_KEYS.get(tab)
    if keys is None:
        raise HTTPException(status_code=404, detail=f"unknown tab: {tab}")
    if not keys:
        return {
            "stockCode": stockCode,
            "tab": tab,
            "periodKind": periodKind,
            "cards": {},
            "order": [],
        }
    await _prefetchCompany(stockCode)

    async def _one(k: str) -> dict[str, Any]:
        return await asyncio.to_thread(_safeBuildAndRender, k, stockCode, periodKind, nPeriods)

    specs = await asyncio.gather(*[_one(k) for k in keys])
    return {
        "stockCode": stockCode,
        "tab": tab,
        "periodKind": periodKind,
        "cards": dict(zip(keys, specs)),
        "order": keys,
    }


@router.get("/api/viz/spec/{cardKey}/{stockCode}")
async def apiVizSpec(
    cardKey: str,
    stockCode: str,
    periodKind: str = Query("annual", pattern="^(annual|quarterly)$"),
    nPeriods: int = Query(40, ge=2, le=80),
) -> dict[str, Any]:
    """단일 카드 lazy 호출 — 회사 전환 시 일부 카드 refresh 용."""
    if cardKey not in CATALOG:
        raise HTTPException(status_code=404, detail=f"unknown cardKey: {cardKey}")
    spec = await asyncio.to_thread(_safeBuildAndRender, cardKey, stockCode, periodKind, nPeriods)
    return spec


# 옛 4 view sub → 7 방법론 redirect (URL bookmark 호환).
_LEGACY_VIEW_REDIRECT: dict[str, str] = {
    "overview": "snowflake",
    "performance": "dupont",
    "capitalStructure": "credit",
    "cashflow": "quality",
    "risk": "credit",
    "profitability": "dupont",
}


@router.get("/api/viz/layout/{tab}/{stockCode}")
async def apiVizLayout(
    tab: str,
    stockCode: str,
    view: str | None = Query(
        None, description="7 방법론 sub view (story/dupont/value/growth/credit/quality/snowflake)"
    ),
    periodKind: str = Query("annual", pattern="^(annual|quarterly)$"),
    nPeriods: int = Query(40, ge=2, le=80),
) -> dict[str, Any]:
    """탭 + 7 방법론 view → 12-col bento packed grid + 각 카드 spec.

    Layout Engine (`dartlab.viz.layout`) 가 카드 카탈로그를 query 하고 12-col
    gridstack 식 packing 산출. frontend 는 (x, y, w, h) + colCount 받아
    cellHeight=columnWidth sync 로 자동 1:1 정사각 렌더.

    Returns:
        {
            tab, view, periodKind, colCount: 12,
            layout: [{cardKey, kind, title, x, y, w, h}, ...],
            cards: {cardKey: RechartsSpec},
        }
    """
    effectiveView = _LEGACY_VIEW_REDIRECT.get(view or "", view)

    # v3-r5 §3 — 2 단 packing. 1) spec build → 2) _isCardEmpty 통과 카드만 packSkyline.
    from dartlab.viz.catalog import CATALOG
    from dartlab.viz.layout import packSkyline, queryCards

    cards = queryCards(tab=tab, sub=effectiveView) if effectiveView else queryCards(tab=tab)
    if not cards:
        return {
            "stockCode": stockCode,
            "tab": tab,
            "view": effectiveView,
            "periodKind": periodKind,
            "colCount": 24,
            "layout": [],
            "cards": {},
        }

    await _prefetchCompany(stockCode)
    cardKeys = [k for k, _ in cards]

    async def _one(k: str) -> dict[str, Any]:
        return await asyncio.to_thread(_safeBuildAndRender, k, stockCode, periodKind, nPeriods)

    specs = await asyncio.gather(*[_one(k) for k in cardKeys])
    specMap = dict(zip(cardKeys, specs))

    # 의미 무효 카드 omit — 운영자 원칙 4. _isCardEmpty 통과 카드만 packing.
    nonEmptyCards = [(k, e) for k, e in cards if not _isCardEmpty(specMap[k])]
    placed = packSkyline(nonEmptyCards, colCount=24)

    return {
        "stockCode": stockCode,
        "tab": tab,
        "view": effectiveView,
        "periodKind": periodKind,
        "colCount": 24,
        "layout": placed,
        "cards": {k: specMap[k] for k, _ in nonEmptyCards},
    }
