"""Company LRU(8) + prefetch (rawFinance/rawDocs/rawReport)."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


_CACHE: "OrderedDict[str, Company]" = OrderedDict()
_LIMIT = 8


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
    for name in ("rawFinance", "rawDocs", "rawReport"):
        try:
            df = getattr(c, name)
            accessors[name] = int(df.height) if df is not None else 0
        except (AttributeError, OSError, RuntimeError, ValueError):
            accessors[name] = -1
    elapsedMs = int((time.perf_counter() - started) * 1000)
    return {"ok": True, "stockCode": str(stockCode), "accessors": accessors, "elapsedMs": elapsedMs}
