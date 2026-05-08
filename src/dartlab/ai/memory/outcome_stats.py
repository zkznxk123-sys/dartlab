"""outcome_log entry 집계 — per-stockCode/market 회귀율·alpha·holding 분포.

raw markdown SSOT (`~/.dartlab/decisions/{market}/{stockCode}.md`) 를 읽어
운영 측정 가능한 dict 로 환산. write 책임 0 — 순수 read + 집계.

회귀 검증 metric:
- pendingCount / resolvedCount — 누적 결정 분포
- resolvedAlphaPositiveRatio — resolved 중 alpha > 0 비율 (높을수록 thesis 적중)
- resolvedAlphaNegativeRatio — alpha < 0 비율 (회귀 여부 raw 신호)
- avgRawReturn / avgAlpha — 평균 수익/알파 (간단 정렬)
- holdingDistribution — holding 기간 분포 (예: {"30d": 5, "90d": 2})

Polars 의존 안 함 (entry 수가 보통 수백 미만 — 표준 dict 충분, 외부 의존 최소).
"""

from __future__ import annotations

import re
from typing import Any

from dartlab.ai.memory.outcome_log import (
    Entry,
    _decisions_root,
    _load_entries,
    _log_path,
    _normalize_market,
    safe_stockcode,
)

_ALPHA_NUM_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_HOLDING_RE = re.compile(r"^\s*(\d+)\s*([a-zA-Z]+)\s*$")


def getEntries(market: str, stockCode: str | None = None) -> list[Entry]:
    """단일 종목 또는 전 종목 entry list. 안전 read 만."""
    safe_market = _normalize_market(market)
    if stockCode:
        safe_code = safe_stockcode(stockCode)
        return _load_entries(_log_path(safe_market, safe_code))
    base = _decisions_root() / safe_market
    if not base.is_dir():
        return []
    out: list[Entry] = []
    for path in sorted(base.glob("*.md")):
        out.extend(_load_entries(path))
    return out


def getStats(
    market: str,
    *,
    stockCode: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
) -> dict[str, Any]:
    """단일 종목 또는 시장 누적 통계.

    Args:
        market: "KR" or "US".
        stockCode: 명시 시 단일 종목, None 이면 시장 전체.
        startDate / endDate: 'YYYY-MM-DD' 포함 범위 필터 (선택).

    Returns:
        {pendingCount, resolvedCount, resolvedAlphaPositiveRatio,
         resolvedAlphaNegativeRatio, avgRawReturn, avgAlpha, holdingDistribution,
         themeDistribution, dateRange}
    """
    entries = getEntries(market, stockCode)
    entries = _filterByDate(entries, startDate, endDate)
    return _summarize(entries)


def getRegressionRate(stockCode: str, *, market: str = "KR") -> float | None:
    """단일 종목 회귀율 = resolved 중 alpha < 0 비율.

    None: resolved entry 0 건 (계산 불가).
    """
    entries = [e for e in getEntries(market, stockCode) if not e.is_pending()]
    if not entries:
        return None
    negatives = sum(1 for e in entries if _parseAlpha(e.alpha) is not None and _parseAlpha(e.alpha) < 0)  # type: ignore[operator]
    return negatives / len(entries)


def getMarketSummary(market: str = "KR") -> dict[str, Any]:
    """시장 전체 종목 요약 — 운영 점검 entry point.

    Returns:
        {market, tickerCount, perTicker: {stockCode: stats}, marketStats}
    """
    safe_market = _normalize_market(market)
    base = _decisions_root() / safe_market
    if not base.is_dir():
        return {"market": safe_market, "tickerCount": 0, "perTicker": {}, "marketStats": _emptyStats()}
    perTicker: dict[str, dict[str, Any]] = {}
    allEntries: list[Entry] = []
    for path in sorted(base.glob("*.md")):
        code = path.stem
        try:
            safe_code = safe_stockcode(code)
        except ValueError:
            continue
        entries = _load_entries(path)
        if not entries:
            continue
        perTicker[safe_code] = _summarize(entries)
        allEntries.extend(entries)
    return {
        "market": safe_market,
        "tickerCount": len(perTicker),
        "perTicker": perTicker,
        "marketStats": _summarize(allEntries),
    }


# ── 내부 helper ──


def _filterByDate(entries: list[Entry], startDate: str | None, endDate: str | None) -> list[Entry]:
    if not startDate and not endDate:
        return entries
    out = []
    for e in entries:
        if startDate and e.date < startDate:
            continue
        if endDate and e.date > endDate:
            continue
        out.append(e)
    return out


def _summarize(entries: list[Entry]) -> dict[str, Any]:
    if not entries:
        return _emptyStats()
    pending = [e for e in entries if e.is_pending()]
    resolved = [e for e in entries if not e.is_pending()]
    alphas = [v for v in (_parseAlpha(e.alpha) for e in resolved) if v is not None]
    rawReturns = [v for v in (_parseAlpha(e.raw_return) for e in resolved) if v is not None]
    positiveAlpha = sum(1 for a in alphas if a > 0)
    negativeAlpha = sum(1 for a in alphas if a < 0)
    holdingDist: dict[str, int] = {}
    for e in resolved:
        h = (e.holding or "").strip()
        if h:
            holdingDist[h] = holdingDist.get(h, 0) + 1
    themeDist: dict[str, int] = {}
    for e in entries:
        t = (e.theme or "").strip() or "Verdict"
        themeDist[t] = themeDist.get(t, 0) + 1
    dates = [e.date for e in entries if e.date]
    dateRange = {"min": min(dates), "max": max(dates)} if dates else {"min": "", "max": ""}
    return {
        "pendingCount": len(pending),
        "resolvedCount": len(resolved),
        "resolvedAlphaPositiveRatio": (positiveAlpha / len(alphas)) if alphas else None,
        "resolvedAlphaNegativeRatio": (negativeAlpha / len(alphas)) if alphas else None,
        "avgRawReturn": (sum(rawReturns) / len(rawReturns)) if rawReturns else None,
        "avgAlpha": (sum(alphas) / len(alphas)) if alphas else None,
        "holdingDistribution": holdingDist,
        "themeDistribution": themeDist,
        "dateRange": dateRange,
    }


def _emptyStats() -> dict[str, Any]:
    return {
        "pendingCount": 0,
        "resolvedCount": 0,
        "resolvedAlphaPositiveRatio": None,
        "resolvedAlphaNegativeRatio": None,
        "avgRawReturn": None,
        "avgAlpha": None,
        "holdingDistribution": {},
        "themeDistribution": {},
        "dateRange": {"min": "", "max": ""},
    }


def _parseAlpha(value: str) -> float | None:
    """`+1.1%vs_KOSPI` / `+3.2%` / `-2.5%vs_S&P500` → 1.1 / 3.2 / -2.5."""
    if not value:
        return None
    match = _ALPHA_NUM_RE.search(value)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


__all__ = [
    "getEntries",
    "getMarketSummary",
    "getRegressionRate",
    "getStats",
]
