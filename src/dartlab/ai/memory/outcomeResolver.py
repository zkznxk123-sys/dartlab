"""pending entry 자동 resolution — SSOT §6 deferred resolution 계약 이행.

흐름:
1. pending entry 의 entry_date 와 today 사이 가격 변화 계산
2. 벤치마크 (KOSPI / S&P500) 가 함께 주어지면 alpha 산출
3. minHoldingDays 미달 시 pending 유지 (intraday noise 차단)
4. 가격 lookup 실패 시 pending 유지 (다음 호출까지 굴림)
5. batchUpdateWithOutcomes 로 atomic 갱신

`Company.price` 직접 import 금지 — caller 가 callable 주입 (SSOT §1 ai/ 정적
import 가드 정신). wiring.py 의 default lookup 이 lazy import 로 providers 호출.

reflection 자동 생성은 사실 진술만 (alpha 인용 + holding 기간). thesis 평가
2/3 항목 (SSOT §6) 은 다음 분석 LLM 이 past_context 주입 받아 보강.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from dartlab.ai.memory.outcomeLog import (
    Entry,
    Update,
    _decisionsRoot,
    _loadEntries,
    _logPath,
    _normalizeMarket,
    batchUpdateWithOutcomes,
    safeStockcode,
)

PriceLookup = Callable[[str, str], float | None]
"""(symbol, asOf) -> close price or None. asOf 'YYYY-MM-DD'."""

_DEFAULT_BENCHMARK_BY_MARKET = {"KR": "KOSPI", "US": "SPX"}


@dataclass
class ResolveReport:
    """resolvePending 결과 — 운영 측정용."""

    stockCode: str
    market: str
    pendingExamined: int
    resolvedCount: int
    skippedShortHolding: int
    skippedMissingPrice: int


def resolvePending(
    stockCode: str,
    *,
    market: str = "KR",
    pricer: PriceLookup,
    benchmarkPricer: PriceLookup | None = None,
    benchmarkSymbol: str | None = None,
    today: str | None = None,
    minHoldingDays: int = 30,
) -> ResolveReport:
    """단일 종목 pending entry 들을 가격 lookup 으로 resolved 변환.

    Args:
        stockCode: 단일 종목 (safeStockcode 가드 통과 필수).
        market: "KR" or "US".
        pricer: (symbol, asOf) -> close price or None. SSOT §6 의
            `Company.price(asOf=...)` look-ahead 가드 결합.
        benchmarkPricer: 벤치마크용 callable. None 이면 alpha 빈 값.
        benchmarkSymbol: 벤치마크 심볼 (KR=KOSPI, US=SPX 기본).
        today: 'YYYY-MM-DD' (기본 today.isoformat()).
        minHoldingDays: 이 미만 holding 은 resolve skip (pending 유지).

    Returns:
        ResolveReport — pending 검사 수, resolved 수, skip 사유별 분포.
    """
    safe_code = safeStockcode(stockCode)
    safe_market = _normalizeMarket(market)
    todayStr = today or date.today().isoformat()
    today_dt = _parseDate(todayStr)
    if today_dt is None:
        return ResolveReport(safe_code, safe_market, 0, 0, 0, 0)

    target = _logPath(safe_market, safe_code)
    pending = [e for e in _loadEntries(target) if e.isPending() and e.stockCode == safe_code]
    if not pending:
        return ResolveReport(safe_code, safe_market, 0, 0, 0, 0)

    benchmark = benchmarkSymbol or _DEFAULT_BENCHMARK_BY_MARKET.get(safe_market, "")
    updates: list[Update] = []
    skip_short = 0
    skip_missing = 0

    for entry in pending:
        entry_dt = _parseDate(entry.date)
        if entry_dt is None:
            skip_missing += 1
            continue
        holdingDays = (today_dt - entry_dt).days
        if holdingDays < minHoldingDays:
            skip_short += 1
            continue
        entry_price = pricer(safe_code, entry.date)
        exit_price = pricer(safe_code, todayStr)
        if entry_price is None or exit_price is None or entry_price <= 0:
            skip_missing += 1
            continue
        rawReturnPct = (exit_price / entry_price - 1.0) * 100.0
        alphaPct: float | None = None
        if benchmarkPricer is not None and benchmark:
            b_entry = benchmarkPricer(benchmark, entry.date)
            b_exit = benchmarkPricer(benchmark, todayStr)
            if b_entry is not None and b_exit is not None and b_entry > 0:
                b_return = (b_exit / b_entry - 1.0) * 100.0
                alphaPct = rawReturnPct - b_return
        updates.append(
            Update(
                stockCode=safe_code,
                market=safe_market,
                date=entry.date,
                raw_return=_formatPct(rawReturnPct),
                alpha=_formatAlpha(alphaPct, benchmark) if alphaPct is not None else "",
                holding=f"{holdingDays}d",
                reflection=_buildReflection(
                    entry=entry,
                    rawReturnPct=rawReturnPct,
                    alphaPct=alphaPct,
                    benchmark=benchmark,
                    holdingDays=holdingDays,
                    todayStr=todayStr,
                ),
            )
        )

    resolved_count = batchUpdateWithOutcomes(updates) if updates else 0
    return ResolveReport(
        stockCode=safe_code,
        market=safe_market,
        pendingExamined=len(pending),
        resolvedCount=resolved_count,
        skippedShortHolding=skip_short,
        skippedMissingPrice=skip_missing,
    )


def resolvePendingMarket(
    market: str = "KR",
    *,
    pricer: PriceLookup,
    benchmarkPricer: PriceLookup | None = None,
    benchmarkSymbol: str | None = None,
    today: str | None = None,
    minHoldingDays: int = 30,
) -> list[ResolveReport]:
    """시장 전체 종목 일괄 resolve. 운영 cron 경로 또는 수동 sweep.

    Returns:
        per-stockCode ResolveReport list (resolved 0 인 종목 포함, 빈 디렉토리만 제외).
    """
    safe_market = _normalizeMarket(market)
    base = _decisionsRoot() / safe_market
    if not base.is_dir():
        return []
    reports: list[ResolveReport] = []
    for path in sorted(base.glob("*.md")):
        code = path.stem
        try:
            safe_code = safeStockcode(code)
        except ValueError:
            continue
        report = resolvePending(
            safe_code,
            market=safe_market,
            pricer=pricer,
            benchmarkPricer=benchmarkPricer,
            benchmarkSymbol=benchmarkSymbol,
            today=today,
            minHoldingDays=minHoldingDays,
        )
        reports.append(report)
    return reports


# ── 내부 helper ──


def _parseDate(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _formatPct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def _formatAlpha(value: float, benchmark: str) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%vs_{benchmark}"


def _buildReflection(
    *,
    entry: Entry,
    rawReturnPct: float,
    alphaPct: float | None,
    benchmark: str,
    holdingDays: int,
    todayStr: str,
) -> str:
    """SSOT §6 reflection — 사실 진술만. thesis 평가 2/3 항목은 다음 LLM 보강."""
    direction = "유지" if rawReturnPct >= 0 else "반대"
    raw_str = _formatPct(rawReturnPct)
    if alphaPct is None:
        alpha_clause = "벤치마크 미주입"
    else:
        alpha_clause = f"alpha {_formatAlpha(alphaPct, benchmark)} ({'적중' if alphaPct > 0 else '회귀'})"
    return (
        f"Resolved {todayStr} ({holdingDays}d hold). Raw return {raw_str}, {alpha_clause}. "
        f"Theme={entry.theme}, decision direction {direction}. "
        f"Thesis 어느 부분 유지/실패 + 다음 lesson 은 후속 분석 past_context 주입 시 LLM 이 보강."
    )


__all__ = [
    "PriceLookup",
    "ResolveReport",
    "resolvePending",
    "resolvePendingMarket",
]
