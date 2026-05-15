"""Company LRU(8) + prefetch (rawFinance/rawDocs/rawReport 강제 collect)."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


_CACHE: OrderedDict[str, "Company"] = OrderedDict()
_LIMIT = 8


def getCompany(stockCode: str) -> "Company":
    """stockCode 로 Company 1 개 반환. LRU 최대 8 개 유지."""
    import dartlab

    sc = str(stockCode).strip()
    if sc in _CACHE:
        _CACHE.move_to_end(sc)
        return _CACHE[sc]
    company = dartlab.Company(sc)
    _CACHE[sc] = company
    if len(_CACHE) > _LIMIT:
        _CACHE.popitem(last=False)
    return company


def prefetch(stockCode: str) -> dict:
    """rawFinance + rawDocs + rawReport 강제 collect → Company _cache 안착.

    Returns:
        {ok, stockCode, accessors: {finance, docs, report}, elapsedMs}
    """
    started = time.perf_counter()
    c = getCompany(stockCode)
    accessors: dict[str, int] = {}
    try:
        rf = c.rawFinance
        accessors["finance"] = int(getattr(rf, "height", 0)) if rf is not None else 0
    except Exception:  # noqa: BLE001
        accessors["finance"] = 0
    try:
        rd = c.rawDocs
        accessors["docs"] = int(getattr(rd, "height", 0)) if rd is not None else 0
    except Exception:  # noqa: BLE001
        accessors["docs"] = 0
    try:
        rr = c.rawReport
        accessors["report"] = int(getattr(rr, "height", 0)) if rr is not None else 0
    except Exception:  # noqa: BLE001
        accessors["report"] = 0
    return {
        "ok": True,
        "stockCode": stockCode,
        "accessors": accessors,
        "elapsedMs": round((time.perf_counter() - started) * 1000.0, 1),
    }


def evict(stockCode: str | None = None) -> int:
    """캐시 비우기. stockCode None 이면 전체."""
    if stockCode is None:
        n = len(_CACHE)
        _CACHE.clear()
        return n
    sc = str(stockCode).strip()
    if sc in _CACHE:
        del _CACHE[sc]
        return 1
    return 0
