"""회귀 가드 — outcome_stats per-stockCode/market 집계 + outcome_resolver auto pending→resolved.

다종목 시뮬레이션:
- 3 종목 × 5 결정 × 30 일 holding mock 가격 시나리오
- alpha 분포 (positive/negative) 와 stats 집계 일치 확인
- pricer None 반환 시 pending 유지 (look-ahead 가드 통합)
- minHoldingDays 미달 시 skip
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_dartlab_home(tmp_path, monkeypatch):
    monkeypatch.setenv("DARTLAB_HOME", str(tmp_path))
    return tmp_path


# ── outcome_stats.py ──


@pytest.mark.unit
def test_get_stats_empty_returns_zero_counts(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeStats import getStats

    stats = getStats("KR")
    assert stats["pendingCount"] == 0
    assert stats["resolvedCount"] == 0
    assert stats["resolvedAlphaPositiveRatio"] is None
    assert stats["avgAlpha"] is None
    assert stats["holdingDistribution"] == {}


@pytest.mark.unit
def test_get_stats_per_ticker_aggregates_pending_and_resolved(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import (
        Update,
        batch_update_with_outcomes,
        store_decision,
    )
    from dartlab.ai.memory.outcomeStats import getStats

    # pending 1
    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis A",
    )
    # resolved positive
    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-03-01",
        theme="Buy",
        decision_text="thesis B",
    )
    batch_update_with_outcomes(
        [
            Update(
                stockCode="005930",
                market="KR",
                date="2026-03-01",
                raw_return="+5.4%",
                alpha="+1.8%vs_KOSPI",
                holding="30d",
                reflection="positive case",
            )
        ]
    )
    # resolved negative
    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-02-01",
        theme="Buy",
        decision_text="thesis C",
    )
    batch_update_with_outcomes(
        [
            Update(
                stockCode="005930",
                market="KR",
                date="2026-02-01",
                raw_return="-2.0%",
                alpha="-3.5%vs_KOSPI",
                holding="30d",
                reflection="negative case",
            )
        ]
    )

    stats = getStats("KR", stockCode="005930")
    assert stats["pendingCount"] == 1
    assert stats["resolvedCount"] == 2
    assert stats["resolvedAlphaPositiveRatio"] == 0.5
    assert stats["resolvedAlphaNegativeRatio"] == 0.5
    assert stats["avgAlpha"] == pytest.approx((1.8 + -3.5) / 2)
    assert stats["holdingDistribution"] == {"30d": 2}
    assert stats["themeDistribution"] == {"Buy": 3}


@pytest.mark.unit
def test_get_regression_rate_returns_none_when_no_resolved(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import store_decision
    from dartlab.ai.memory.outcomeStats import getRegressionRate

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="pending only",
    )
    assert getRegressionRate("005930", market="KR") is None


@pytest.mark.unit
def test_get_market_summary_aggregates_multiple_tickers(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import (
        Update,
        batch_update_with_outcomes,
        store_decision,
    )
    from dartlab.ai.memory.outcomeStats import getMarketSummary

    for code, alpha in [("005930", "+2.0%vs_KOSPI"), ("000660", "-1.5%vs_KOSPI"), ("035720", "+0.5%vs_KOSPI")]:
        store_decision(stockCode=code, market="KR", date="2026-03-01", theme="Buy", decision_text=f"thesis {code}")
        batch_update_with_outcomes(
            [
                Update(
                    stockCode=code,
                    market="KR",
                    date="2026-03-01",
                    raw_return="+1.0%",
                    alpha=alpha,
                    holding="30d",
                    reflection="auto reflection",
                )
            ]
        )

    summary = getMarketSummary("KR")
    assert summary["market"] == "KR"
    assert summary["tickerCount"] == 3
    assert set(summary["perTicker"].keys()) == {"005930", "000660", "035720"}
    market_stats = summary["marketStats"]
    assert market_stats["resolvedCount"] == 3
    assert market_stats["resolvedAlphaPositiveRatio"] == pytest.approx(2 / 3)


@pytest.mark.unit
def test_get_stats_date_range_filter(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import store_decision
    from dartlab.ai.memory.outcomeStats import getStats

    for d in ["2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15"]:
        store_decision(stockCode="005930", market="KR", date=d, theme="Hold", decision_text=f"d {d}")

    full = getStats("KR", stockCode="005930")
    assert full["pendingCount"] == 4

    windowed = getStats("KR", stockCode="005930", startDate="2026-02-01", endDate="2026-03-31")
    assert windowed["pendingCount"] == 2


# ── outcome_resolver.py ──


@pytest.mark.unit
def test_resolve_pending_skips_when_holding_short(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import get_pending_entries, store_decision
    from dartlab.ai.memory.outcomeResolver import resolvePending

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-05-01",
        theme="Buy",
        decision_text="recent decision",
    )

    def mock_pricer(symbol: str, asOf: str) -> float | None:
        return 70000.0

    report = resolvePending(
        "005930",
        market="KR",
        pricer=mock_pricer,
        today="2026-05-08",  # 7d hold < 30d
        minHoldingDays=30,
    )
    assert report.pendingExamined == 1
    assert report.resolvedCount == 0
    assert report.skippedShortHolding == 1
    assert len(get_pending_entries("005930")) == 1  # 여전히 pending


@pytest.mark.unit
def test_resolve_pending_keeps_pending_when_pricer_returns_none(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import get_pending_entries, store_decision
    from dartlab.ai.memory.outcomeResolver import resolvePending

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis",
    )

    def missing_pricer(symbol: str, asOf: str) -> float | None:
        return None  # 모든 lookup 실패

    report = resolvePending(
        "005930",
        market="KR",
        pricer=missing_pricer,
        today="2026-05-08",  # 37d hold > 30d
        minHoldingDays=30,
    )
    assert report.pendingExamined == 1
    assert report.resolvedCount == 0
    assert report.skippedMissingPrice == 1
    assert len(get_pending_entries("005930")) == 1


@pytest.mark.unit
def test_resolve_pending_writes_alpha_when_benchmark_provided(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import (
        get_pending_entries,
        store_decision,
    )
    from dartlab.ai.memory.outcomeResolver import resolvePending
    from dartlab.ai.memory.outcomeStats import getStats

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis",
    )

    # 종목 +10%, KOSPI +3% → alpha +7%
    def stock_pricer(symbol: str, asOf: str) -> float | None:
        return {"2026-04-01": 70000.0, "2026-05-08": 77000.0}.get(asOf)

    def benchmark_pricer(symbol: str, asOf: str) -> float | None:
        return {"2026-04-01": 2700.0, "2026-05-08": 2781.0}.get(asOf)

    report = resolvePending(
        "005930",
        market="KR",
        pricer=stock_pricer,
        benchmarkPricer=benchmark_pricer,
        today="2026-05-08",  # 37d hold
        minHoldingDays=30,
    )
    assert report.resolvedCount == 1
    assert len(get_pending_entries("005930")) == 0

    stats = getStats("KR", stockCode="005930")
    assert stats["resolvedCount"] == 1
    assert stats["avgRawReturn"] == pytest.approx(10.0, abs=0.1)
    assert stats["avgAlpha"] == pytest.approx(7.0, abs=0.1)


@pytest.mark.unit
def test_resolve_pending_no_benchmark_writes_raw_return_only(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import get_pending_entries, store_decision
    from dartlab.ai.memory.outcomeResolver import resolvePending
    from dartlab.ai.memory.outcomeStats import getEntries

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis",
    )

    def pricer(symbol: str, asOf: str) -> float | None:
        return {"2026-04-01": 100.0, "2026-05-08": 110.0}.get(asOf)

    report = resolvePending(
        "005930",
        market="KR",
        pricer=pricer,
        today="2026-05-08",
        minHoldingDays=30,
    )
    assert report.resolvedCount == 1
    assert len(get_pending_entries("005930")) == 0

    resolved = [e for e in getEntries("KR", "005930") if not e.is_pending()]
    assert len(resolved) == 1
    assert resolved[0].raw_return == "+10.0%"
    assert resolved[0].alpha == ""  # 벤치마크 미주입
    assert resolved[0].holding == "37d"


@pytest.mark.unit
def test_resolve_pending_market_iterates_all_tickers(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import store_decision
    from dartlab.ai.memory.outcomeResolver import resolvePendingMarket

    for code in ["005930", "000660", "035720"]:
        store_decision(
            stockCode=code,
            market="KR",
            date="2026-04-01",
            theme="Buy",
            decision_text=f"thesis {code}",
        )

    def pricer(symbol: str, asOf: str) -> float | None:
        # 005930 만 lookup 성공, 다른 종목은 None
        if symbol != "005930":
            return None
        return {"2026-04-01": 100.0, "2026-05-08": 105.0}.get(asOf)

    reports = resolvePendingMarket(
        "KR",
        pricer=pricer,
        today="2026-05-08",
        minHoldingDays=30,
    )
    assert len(reports) == 3
    by_code = {r.stockCode: r for r in reports}
    assert by_code["005930"].resolvedCount == 1
    assert by_code["000660"].resolvedCount == 0
    assert by_code["000660"].skippedMissingPrice == 1
    assert by_code["035720"].resolvedCount == 0


# ── wiring.py helper ──


@pytest.mark.unit
def test_try_resolve_pending_noop_without_pricer(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import get_pending_entries, store_decision
    from dartlab.ai.memory.wiring import tryResolvePending

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis",
    )

    # pricer 미주입 → 0 반환, pending 유지
    assert tryResolvePending("005930", "KR", today="2026-05-08") == 0
    assert len(get_pending_entries("005930")) == 1


@pytest.mark.unit
def test_try_resolve_pending_with_callable_pricer(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.outcomeLog import get_pending_entries, store_decision
    from dartlab.ai.memory.wiring import tryResolvePending

    store_decision(
        stockCode="005930",
        market="KR",
        date="2026-04-01",
        theme="Buy",
        decision_text="thesis",
    )

    def pricer(symbol: str, asOf: str) -> float | None:
        return {"2026-04-01": 100.0, "2026-05-08": 108.0}.get(asOf)

    resolved = tryResolvePending(
        "005930",
        "KR",
        pricer=pricer,
        today="2026-05-08",
        minHoldingDays=30,
    )
    assert resolved == 1
    assert len(get_pending_entries("005930")) == 0


@pytest.mark.unit
def test_try_resolve_pending_safe_on_invalid_stockcode(tmp_dartlab_home) -> None:
    from dartlab.ai.memory.wiring import tryResolvePending

    def pricer(symbol: str, asOf: str) -> float | None:
        return 100.0

    # path traversal 시도 → safe_stockcode 가 ValueError → wrapper 가 0 반환
    assert tryResolvePending("../etc", "KR", pricer=pricer) == 0
    assert tryResolvePending(None, "KR", pricer=pricer) == 0
