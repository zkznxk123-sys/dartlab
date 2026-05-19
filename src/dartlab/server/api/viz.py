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
import time
from collections import OrderedDict
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


# ── 카드 spec TTL 캐시 ──
# (cardKey, code, periodKind, nPeriods) → (ts, spec). 같은 회사·기간 spec 이
# 여러 endpoint·동시 호출에서 중복 build 되던 비용 차단. error spec 은 캐시 X.
# 5 분 TTL — 동일 세션 안 회사 전환·재진입·hover prefetch race 모두 보호.
_SPEC_CACHE: "OrderedDict[tuple[str, str, str, int], tuple[float, dict[str, Any]]]" = OrderedDict()
_SPEC_CACHE_TTL_SEC = 300.0
_SPEC_CACHE_MAX = 512


def _specCacheGet(key: tuple[str, str, str, int]) -> dict[str, Any] | None:
    item = _SPEC_CACHE.get(key)
    if item is None:
        return None
    ts, spec = item
    if time.monotonic() - ts > _SPEC_CACHE_TTL_SEC:
        _SPEC_CACHE.pop(key, None)
        return None
    _SPEC_CACHE.move_to_end(key)
    return spec


def _specCacheSet(key: tuple[str, str, str, int], spec: dict[str, Any]) -> None:
    if spec.get("error"):
        return
    _SPEC_CACHE[key] = (time.monotonic(), spec)
    while len(_SPEC_CACHE) > _SPEC_CACHE_MAX:
        _SPEC_CACHE.popitem(last=False)


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
    """buildView + toRechartsSpec — 예외는 카드 단위 error envelope. TTL 캐시 적용."""
    cacheKey = (cardKey, str(code).zfill(6), periodKind, int(nPeriods))
    hit = _specCacheGet(cacheKey)
    if hit is not None:
        return hit
    try:
        view = buildView(cardKey, code, periodKind=periodKind, nPeriods=nPeriods)  # type: ignore[arg-type]
        spec = toRechartsSpec(view)
    except Exception as exc:  # noqa: BLE001
        return {
            "cardKey": cardKey,
            "error": str(exc),
            "componentType": "Error",
            "kind": "error",
            "title": CATALOG.get(cardKey, {}).get("title", cardKey),
        }
    _specCacheSet(cacheKey, spec)
    return spec


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
        return all((t.get("value") in (None,) or (t.get("value") == 0 and not scoreMode)) for t in tiles)
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


# ── prefetch in-flight dedup ──
# 회사 페이지 진입 시 여러 endpoint (layout · spec · 미래 추가) 가 동시에
# _prefetchCompany 호출 → 각자 rawFinance LazyFrame collect (200~500MB) trigger →
# race + 메모리·CPU 낭비. 같은 stockCode 동시 호출은 첫 번째 Task 1 회만 실행하고
# 나머지는 그 결과 await.
_PREFETCH_INFLIGHT: dict[str, asyncio.Task[None]] = {}
_PREFETCH_LOCK = asyncio.Lock()


async def _prefetchCompany(stockCode: str) -> None:
    """Company rawFinance 1 회 collect → LRU 안착. 동시 호출은 dedup."""
    code = str(stockCode).strip()

    async def _warmOnce() -> None:
        from dartlab.viz.display.finance._cache import getCompany

        def _warm() -> None:
            c = getCompany(code)
            _ = c.rawFinance  # lazy frame collect 강제

        await asyncio.to_thread(_warm)

    async with _PREFETCH_LOCK:
        task = _PREFETCH_INFLIGHT.get(code)
        if task is None or task.done():
            task = asyncio.create_task(_warmOnce())
            _PREFETCH_INFLIGHT[code] = task
    try:
        await task
    finally:
        async with _PREFETCH_LOCK:
            if _PREFETCH_INFLIGHT.get(code) is task and task.done():
                _PREFETCH_INFLIGHT.pop(code, None)


async def _prefetchQuantPrice(stockCode: str) -> None:
    """quant 탭 전용 — 가격 OHLCV 1 회 fetch → 동시 카드 build 시 race 회피.

    7 카드 (verdict/momentum/volatility/beta/forecast/priceTrend/comingSoon) 가
    asyncio.gather 동시 build 시 각각 fetchOhlcv 호출하면 첫 cold 호출에서 race.
    1 회 prefetch 후 fetchOhlcv 내부 캐시 hit → 나머지 6 호출은 즉시 반환.
    """

    def _warm() -> None:
        try:
            from datetime import date, timedelta

            from dartlab.quant.signal.momentum import fetchOhlcv

            start = (date.today() - timedelta(days=400)).isoformat()
            fetchOhlcv(stockCode, start=start)
        except Exception:  # noqa: BLE001
            pass

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
    layoutOnly: bool = Query(
        False, description="True → layout 만 반환, cards 는 빈 dict. frontend 가 카드별 progressive load."
    ),
    eagerN: int = Query(
        6,
        ge=0,
        le=80,
        description="첫 페인트 즉시 build 할 카드 수. 나머지는 frontend 가 IntersectionObserver hit 시 /api/viz/spec/{cardKey}/{code} 호출 (TTL 캐시로 중복 build 0). 0=전체 lazy, 큰 값=전체 eager.",
    ),
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

    # v3-r6 — planTabLayout 단일 호출 (view=null + tab=financial → OVERVIEW_KEYS 8 카드).
    # _isCardEmpty 2 단 packing 일시 폐기 (backend hang 회피). 후속 PR 에서 cost 낮춰 재도입.
    placed = planTabLayout(tab, sub=effectiveView)
    if not placed:
        return {
            "stockCode": stockCode,
            "tab": tab,
            "view": effectiveView,
            "periodKind": periodKind,
            "colCount": 24,
            "layout": [],
            "cards": {},
        }

    cardKeys = [p["cardKey"] for p in placed]

    # hero 카드 — layout 의 BentoGrid 에는 안 들어가지만 frontend 가 헤더 영역에서
    # 별도 render 하는 spec. 같은 prefetch + gather 안에서 빌드해 round-trip + cold
    # prefetch 1 회 절약. financial 탭의 snowflakeRadar 가 대표 사례.
    heroKeys: list[str] = []
    if tab == "financial":
        heroKeys.append("snowflakeRadar")

    # eager set — 첫 페인트에 spec 동행할 카드. 카드 순서대로 첫 eagerN + heroKeys.
    # 나머지 (lazyKeys) 는 frontend 가 viewport 진입 시 /api/viz/spec/{cardKey}/{code}
    # 호출. backend TTL 캐시 (Task 2) 가 중복 build 0 보장 → 사용자가 끝까지 스크롤
    # 해도 같은 카드 두 번 build 안 함. cold layout 5s → 1~2s 목표.
    eagerCardKeys = cardKeys[: max(0, eagerN)]
    lazyCardKeys = cardKeys[max(0, eagerN) :]
    buildKeys = eagerCardKeys + [k for k in heroKeys if k not in eagerCardKeys]

    if layoutOnly:
        # progressive load mode — frontend 가 /api/viz/spec/{cardKey}/{stockCode} 로 카드별 fetch.
        return {
            "stockCode": stockCode,
            "tab": tab,
            "view": effectiveView,
            "periodKind": periodKind,
            "colCount": 24,
            "layout": placed,
            "cards": {},
            "lazyKeys": cardKeys,
        }

    async def _one(k: str) -> dict[str, Any]:
        return await asyncio.to_thread(_safeBuildAndRender, k, stockCode, periodKind, nPeriods)

    if tab == "quant":
        # 가격 데이터 fetcher (gather provider) 가 동시 진입에 안전하지 않음 —
        # asyncio.gather 시 coroutine race 로 fetchOhlcv 다중 실패. 순차 build 강행.
        # 첫 카드 (priceTrend) 가 가격 데이터 안착시키면 후속 카드는 빠르게 진행.
        await _prefetchQuantPrice(stockCode)
        specs: list[dict[str, Any]] = []
        for k in buildKeys:
            specs.append(await _one(k))
    else:
        await _prefetchCompany(stockCode)
        specs = list(await asyncio.gather(*[_one(k) for k in buildKeys]))

    return {
        "stockCode": stockCode,
        "tab": tab,
        "view": effectiveView,
        "periodKind": periodKind,
        "colCount": 24,
        "layout": placed,
        "cards": dict(zip(buildKeys, specs)),
        # frontend 가 viewport 진입 시 fetchCard 할 카드 목록 (eager 외).
        "lazyKeys": lazyCardKeys,
    }
