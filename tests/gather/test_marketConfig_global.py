"""marketConfig 15 시장 정합성 회귀 가드.

Sprint 3 PR2 — 8→15 시장 확장 후 모든 시장의 7 필드 유효성 자동 강제.
"""

from __future__ import annotations

import pytest

from dartlab.gather.marketConfig import MARKETS, getMarketConfig, resolveTicker

pytestmark = pytest.mark.unit

EXPECTED_MARKETS = {
    "KR",
    "US",
    "JP",
    "HK",
    "UK",
    "DE",
    "CN",
    "IN",
    # 신규 7
    "CA",
    "AU",
    "BR",
    "ZA",
    "MX",
    "SG",
    "TH",
}


def test_15_markets_registered() -> None:
    """15 시장 모두 MARKETS dict 에 등록."""
    missing = EXPECTED_MARKETS - set(MARKETS)
    assert not missing, f"누락 시장: {missing}"


def test_all_markets_have_required_fields() -> None:
    """모든 MarketConfig 7 필드 not null/not empty."""
    for code, cfg in MARKETS.items():
        assert cfg.code == code, f"{code} code 불일치"
        assert cfg.name, f"{code} name 누락"
        assert cfg.currency, f"{code} currency 누락"
        # US 만 exchange_suffix 가 빈 문자열 허용 (yahoo native)
        if code != "US":
            assert cfg.exchange_suffix, f"{code} exchange_suffix 누락"
        assert cfg.benchmark_ticker, f"{code} benchmark_ticker 누락"
        assert len(cfg.fallback_chain) >= 1, f"{code} fallback_chain 비어있음"
        assert isinstance(cfg.trading_hours_utc, tuple) and len(cfg.trading_hours_utc) == 2


def test_new_markets_have_yahoo_chart_in_chain() -> None:
    """Sprint 3 신규 7 시장은 모두 yahoo_chart 가 fallback chain 첫 번째."""
    new_markets = {"CA", "AU", "BR", "ZA", "MX", "SG", "TH"}
    for code in new_markets:
        cfg = MARKETS[code]
        assert cfg.fallback_chain[0] == "yahoo_chart", f"{code} yahoo_chart 우선 아님"


def test_resolveTicker_new_markets_applies_suffix() -> None:
    """7 신규 시장 모두 yahoo_chart 호출 시 suffix 자동 부착."""
    assert resolveTicker("RY", "CA", "yahoo_chart") == "RY.TO"
    assert resolveTicker("BHP", "AU", "yahoo_chart") == "BHP.AX"
    assert resolveTicker("PETR4", "BR", "yahoo_chart") == "PETR4.SA"
    assert resolveTicker("AGL", "ZA", "yahoo_chart") == "AGL.JO"
    assert resolveTicker("WALMEX", "MX", "yahoo_chart") == "WALMEX.MX"
    assert resolveTicker("D05", "SG", "yahoo_chart") == "D05.SI"
    assert resolveTicker("PTT", "TH", "yahoo_chart") == "PTT.BK"


def test_getMarketConfig_lookup_all_15() -> None:
    """15 시장 모두 getMarketConfig 정상 lookup."""
    for code in EXPECTED_MARKETS:
        cfg = getMarketConfig(code)
        assert cfg.code == code


def test_unknown_market_raises() -> None:
    """미등록 시장 ValueError."""
    with pytest.raises(ValueError, match="알 수 없는 시장"):
        getMarketConfig("XX")
