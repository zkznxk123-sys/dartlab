"""quant/screen/extended OHLCV 캐싱 헬퍼.

quant/screen/extended.py 가 818 줄 god module 이라 캐싱 헬퍼 5개를 분리.
identity 보존을 위해 extended.py 가 본 모듈에서 re-export 한다.

함수:
- _fetchOhlcv — gather("price") → Company._cache 저장
- _fetchBenchmarkForCompany — KRX 지수 OHLCV
- _benchmarkMetaForCompany — benchmark meta 조회
- _detectMarket — company.currency → "US"|"KR"
- _isUSD — USD 통화 여부
"""

from __future__ import annotations

from typing import Any

import polars as pl


def _fetchOhlcv(company: Any) -> pl.DataFrame | None:
    """gather("price")로 OHLCV 수집 — Company._cache에 저장.

    모든 함수가 이 캐시를 공유하므로 네트워크 호출은 1회만 발생.
    """
    cache = getattr(company, "_cache", None)
    _KEY = "_quant_ohlcv"
    if cache is not None and _KEY in cache:
        return cache[_KEY]

    stockCode = getattr(company, "stockCode", None)
    if not stockCode:
        return None

    result = None
    try:
        from dartlab.gather.infra.http import runAsync
        from dartlab.gather.sources.price import fetch as fetchPrice

        snapshot = runAsync(fetchPrice(stockCode, market=_detectMarket(company)))
        if snapshot is not None and hasattr(snapshot, "ohlcv"):
            result = snapshot.ohlcv
        elif isinstance(snapshot, pl.DataFrame) and "close" in snapshot.columns:
            result = snapshot
    except (ImportError, AttributeError, ValueError, TypeError, RuntimeError):
        pass

    if result is None:
        try:
            from dartlab.gather.entry import GatherEntry

            raw = GatherEntry()("price", stockCode)
            if isinstance(raw, pl.DataFrame) and "close" in raw.columns:
                result = raw
        except (ImportError, ValueError, TypeError, RuntimeError):
            pass

    if cache is not None:
        cache[_KEY] = result
    return result


def _fetchBenchmarkForCompany(company: Any) -> pl.DataFrame | None:
    """시장 벤치마크 OHLCV — KRX 지수 SSOT."""
    cache = getattr(company, "_cache", None)
    stockCode = getattr(company, "stockCode", None)
    benchmark = getattr(company, "benchmark", None)
    benchmarkMode = getattr(company, "benchmarkMode", "market")
    cacheKey = f"_quant_benchmark:{benchmark or ''}:{benchmarkMode}"
    metaKey = f"{cacheKey}:meta"
    if cache is not None and cacheKey in cache:
        return cache[cacheKey]

    result = None
    meta = None
    try:
        from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

        result, meta = fetchBenchmarkOhlcv(
            stockCode,
            market=_detectMarket(company),
            benchmark=benchmark,
            benchmarkMode=benchmarkMode,
            returnMeta=True,
        )
    except (ImportError, ValueError, TypeError, RuntimeError):
        pass

    if cache is not None:
        cache[cacheKey] = result
        cache[metaKey] = meta
        cache["_quant_benchmark_meta"] = meta
    return result


def _benchmarkMetaForCompany(company: Any) -> dict | None:
    cache = getattr(company, "_cache", None)
    if cache is not None:
        return cache.get("_quant_benchmark_meta")
    return None


def _detectMarket(company: Any) -> str:
    """company.currency로 시장 감지."""
    return "US" if _isUSD(company) else "KR"


def _isUSD(company: Any) -> bool:
    return getattr(company, "currency", "KRW") == "USD"


__all__ = [
    "_benchmarkMetaForCompany",
    "_detectMarket",
    "_fetchBenchmarkForCompany",
    "_fetchOhlcv",
    "_isUSD",
]
