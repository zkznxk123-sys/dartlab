"""Company LRU(8) + prefetch (rawFinance/rawDocs/rawReport).

normFinance 메모이제이션도 같이 — Company instance lifecycle 안 1회 계산.
rawFinance 와 동일 lifespan (Company LRU evict 시 함께 GC). storage cache
아님 — Company instance 내부 상태.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


_CACHE: "OrderedDict[str, Company]" = OrderedDict()
_LIMIT = 8
# Company instance id → normalized finance frame. Company LRU evict 시 자동 stale.
_NORM_BY_COMPANY: dict[int, Any] = {}
# Company instance id → TTM-transformed norm. norm 옆에 별도 lifespan.
_TTM_NORM_BY_COMPANY: dict[int, Any] = {}


def getCompany(stockCode: str) -> "Company":
    """stockCode → Company. LRU 최대 8 개 유지."""
    import dartlab

    sc = str(stockCode).strip()
    if sc in _CACHE:
        _CACHE.move_to_end(sc)
        return _CACHE[sc]
    company = dartlab.Company(sc)
    _CACHE[sc] = company
    if len(_CACHE) > _LIMIT:
        evicted = _CACHE.popitem(last=False)[1]
        _NORM_BY_COMPANY.pop(id(evicted), None)
        _TTM_NORM_BY_COMPANY.pop(id(evicted), None)
    return company


def getNormFinance(company: "Company") -> Any:
    """company.rawFinance → normalized long-form. Company instance lifecycle 안 1회.

    동일 Company instance 가 LRU 안 살아있는 동안 정규화 결과 재사용. 카드 34장이
    한 요청 안에서 한 norm 을 공유 → polars collect 34→1.
    """
    from dartlab.viz.display.finance import normalize as _norm

    key = id(company)
    cached = _NORM_BY_COMPANY.get(key)
    if cached is not None:
        return cached
    norm = _norm.normalize(company.rawFinance)
    _NORM_BY_COMPANY[key] = norm
    return norm


def getTtmNorm(company: "Company") -> Any:
    """getNormFinance(company) → TTM 화 norm. 분기 IS/CF row 만 4Q TTM 합산.

    BS row 와 IS/CF annual row 는 pass-through. Company instance lifecycle 안
    1회 변환 + memoize. norm 본체와 lifespan 동일 (LRU evict 시 같이 pop).
    """
    from dartlab.viz.display.finance import _ttm

    key = id(company)
    cached = _TTM_NORM_BY_COMPANY.get(key)
    if cached is not None:
        return cached
    ttm = _ttm.toTtmNorm(getNormFinance(company))
    _TTM_NORM_BY_COMPANY[key] = ttm
    return ttm


def ttmAvailability(company: "Company") -> dict:
    """TTM 가용성 진단. quarterlyTtm 모드 UI badge 결정용.

    Returns:
        {
          annualFyYears: int,       # 보유 FY (annual periodKind) 햇수
          quarterlyPeriods: int,    # 보유 quarterly period 개수 (Q1+HY+Q3 합산)
          ttmFullCount: int,        # TTM 공식 (FY 전년도 보유) 적용 가능한 분기 수
          ttmFallbackCount: int,    # annualize fallback (× 12/months) 으로 처리되는 분기 수
          sufficient: bool,         # ttmFullCount >= 4 ?
        }
    """
    from dartlab.viz.display.finance import _ttm

    norm = getNormFinance(company)
    if norm is None or norm.height == 0:
        return {
            "annualFyYears": 0,
            "quarterlyPeriods": 0,
            "ttmFullCount": 0,
            "ttmFallbackCount": 0,
            "sufficient": False,
        }
    import polars as pl

    flowAnnual = norm.filter(pl.col("sjDiv").is_in(list(_ttm._FLOW_SJ)) & (pl.col("periodKind") == "annual"))
    flowQuarterly = norm.filter(pl.col("sjDiv").is_in(list(_ttm._FLOW_SJ)) & (pl.col("periodKind") == "quarterly"))
    annualYears = flowAnnual["bsnsYear"].unique().to_list() if flowAnnual.height else []
    quarterlyPeriods = flowQuarterly["period"].unique().to_list() if flowQuarterly.height else []
    # 분기 period 가 FY(전년) 보유 시 TTM full, 미보유 시 annualize fallback.
    annualSet = set(annualYears)
    fullCnt = 0
    fbCnt = 0
    for p in quarterlyPeriods:
        try:
            yr = p.split("-", 1)[0]
            prev = str(int(yr) - 1)
        except (ValueError, IndexError):
            continue
        if prev in annualSet:
            fullCnt += 1
        else:
            fbCnt += 1
    return {
        "annualFyYears": len(annualSet),
        "quarterlyPeriods": len(quarterlyPeriods),
        "ttmFullCount": fullCnt,
        "ttmFallbackCount": fbCnt,
        "sufficient": fullCnt >= 4,
    }


def prefetch(stockCode: str) -> dict:
    """rawFinance + rawDocs + rawReport 강제 collect → Company _cache 안착.

    Returns:
        {ok, stockCode, accessors: {finance, docs, report}, elapsedMs}
    """
    started = time.perf_counter()
    c = getCompany(stockCode)
    accessors: dict[str, int] = {}
    for name in ("rawFinance", "rawDocs", "rawReport"):
        try:
            df = getattr(c, name)
            accessors[name] = int(df.height) if df is not None else 0
        except (AttributeError, OSError, RuntimeError, ValueError):
            accessors[name] = -1
    elapsedMs = int((time.perf_counter() - started) * 1000)
    return {"ok": True, "stockCode": str(stockCode), "accessors": accessors, "elapsedMs": elapsedMs}
