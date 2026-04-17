"""Damodaran 흡수 완결 테스트.

L0 SSOT (순수 함수) + L2 통합 + Company method 회귀 검증.
"""

from __future__ import annotations

import pytest

# ── L0 SSOT ─────────────────────────────────────────────


@pytest.mark.requires_data
def test_decomposeRoic_identity():
    """ROIC = margin × turnover × (1-tax) — 재구성 일치."""
    from dartlab.core.finance.calc import decomposeRoic

    r = decomposeRoic(
        operatingIncome=10_000_000_000,
        revenue=100_000_000_000,
        investedCapital=50_000_000_000,
        effectiveTaxRate=0.20,
        wacc=10.0,
    )
    assert r is not None
    # margin=10%, turnover=2x, retention=0.8 → ROIC=16%
    assert abs(r["operatingMargin"] - 10.0) < 0.01
    assert abs(r["assetTurnover"] - 2.0) < 0.01
    assert abs(r["roicReconstructed"] - 16.0) < 0.01
    # excessReturn = (16 - 10) × IC = 3B
    assert abs(r["excessReturnAbs"] - 3_000_000_000) < 1.0


@pytest.mark.requires_data
def test_decomposeRoic_rejects_bad_input():
    from dartlab.core.finance.calc import decomposeRoic

    assert decomposeRoic(None, 100, 50, 0.2, 10) is None
    assert decomposeRoic(10, 0, 50, 0.2, 10) is None
    assert decomposeRoic(10, 100, -1, 0.2, 10) is None


@pytest.mark.requires_data
def test_reinvestmentIdentity():
    from dartlab.core.finance.calc import reinvestmentIdentity

    # g=6%, ROIC=12% → reinvestRate=0.5
    r = reinvestmentIdentity(6.0, 12.0)
    assert abs(r["impliedReinvestRate"] - 0.5) < 0.001


@pytest.mark.requires_data
def test_riskPremiums_fallback():
    from dartlab.core.finance.riskPremiums import listSupportedCountries, loadDamodaranERP

    countries = listSupportedCountries()
    assert "KR" in countries
    assert "US" in countries
    assert "JP" in countries

    kr = loadDamodaranERP(currency="KRW")
    assert kr["countryCode"] == "KR"
    assert kr["totalERP"] > kr["matureMarketERP"]  # KR 은 CRP 추가
    assert kr["source"] == "fallback_default"

    us = loadDamodaranERP(currency="USD")
    assert us["countryCode"] == "US"
    assert us["countryRiskPremium"] == 0.0  # AAA 국가


@pytest.mark.requires_data
def test_riskPremiums_currency_to_country():
    from dartlab.core.finance.riskPremiums import resolveCountryCode

    assert resolveCountryCode(currency="KRW") == "KR"
    assert resolveCountryCode(currency="USD") == "US"
    assert resolveCountryCode(country="JP") == "JP"
    # 명시 country 가 currency 보다 우선
    assert resolveCountryCode(currency="KRW", country="US") == "US"


@pytest.mark.requires_data
def test_survivalWeight_safe_zone():
    from dartlab.core.finance.survival import applySurvivalWeight, calcSurvivalWeight

    s = calcSurvivalWeight(zone="safe")
    assert s["pSurvival"] > 0.9  # safe zone 은 장기 생존확률 높음

    # Mature Stable 기업 회귀 불변 확인 — adjusted ≈ primary
    w = applySurvivalWeight(100_000, 50_000, s)
    assert abs(w["adjustedValue"] - 100_000) < 5000


@pytest.mark.requires_data
def test_survivalWeight_distress_zone():
    from dartlab.core.finance.survival import applySurvivalWeight, calcSurvivalWeight

    s = calcSurvivalWeight(zone="distress")
    assert s["pSurvival"] < 0.5
    # distress 기업은 liquidation 가중 비중 커짐
    w = applySurvivalWeight(100_000, 30_000, s)
    assert w["adjustedValue"] < 100_000


@pytest.mark.requires_data
def test_twoStageDcf_explicit_plus_terminal():
    from dartlab.core.finance.dcf import twoStageDcf

    r = twoStageDcf(
        baseFcf=100_000_000_000,
        growthYears=5,
        highGrowthRate=10.0,
        terminalGrowthRate=3.0,
        wacc=10.0,
        netDebt=0,
        shares=1_000_000,
    )
    assert r["pvExplicit"] > 0
    assert r["pvTerminal"] > 0
    assert r["enterpriseValue"] == r["pvExplicit"] + r["pvTerminal"]
    assert 0.0 < r["tvShare"] < 1.0
    assert r["perShare"] is not None


@pytest.mark.requires_data
def test_twoStageDcf_enforces_tg_lt_wacc():
    """영구성장률이 WACC 이상이면 자동 보정."""
    from dartlab.core.finance.dcf import twoStageDcf

    r = twoStageDcf(
        baseFcf=100_000_000_000,
        growthYears=5,
        highGrowthRate=10.0,
        terminalGrowthRate=12.0,  # WACC(10%) 초과 — 보정 기대
        wacc=10.0,
    )
    assert r["terminalGrowthRate"] < r["wacc"]
    assert any("보정" in w or "영구성장" in w for w in r["warnings"])


@pytest.mark.requires_data
def test_liquidationValuation_recovery_rates():
    from dartlab.core.finance.dcf import liquidationValuation

    r = liquidationValuation(
        cash=100_000_000_000,
        receivables=50_000_000_000,
        inventory=40_000_000_000,
        tangibleAssets=200_000_000_000,
        intangibleAssets=30_000_000_000,
        otherAssets=20_000_000_000,
        totalLiabilities=100_000_000_000,
        shares=1_000_000,
    )
    # 현금 100% 회수
    assert r["recoveries"]["cash"] == 100_000_000_000
    # 무형자산 10% 회수
    assert abs(r["recoveries"]["intangible"] - 3_000_000_000) < 1.0
    assert r["grossRecovery"] > 0
    assert r["netToEquity"] > 0


# ── L0 overrides ─────────────────────────────────────────


@pytest.mark.requires_data
def test_overrides_validation():
    from dartlab.core.overrides import VALUATION_KEYS

    # 신규 Damodaran 키들
    assert "lifeCyclePhase" in VALUATION_KEYS
    assert "pSurvival" in VALUATION_KEYS
    assert "countryCode" in VALUATION_KEYS
    assert "liquidationDiscount" in VALUATION_KEYS


@pytest.mark.requires_data
def test_detectExtremeFlags_lifecycle_conflict():
    """생애주기 decline 인데 CAGR > 15% 면 lifecycle_conflict flag."""
    from dartlab.core.overrides import detectExtremeFlags

    flags = detectExtremeFlags(
        {
            "lifeCyclePhase": "decline",
            "revenueCAGR": 20.0,
        }
    )
    keys = [f["flag"] for f in flags]
    assert "lifecycle_conflict" in keys


@pytest.mark.requires_data
def test_detectExtremeFlags_survival_extreme_low():
    from dartlab.core.overrides import detectExtremeFlags

    flags = detectExtremeFlags({"pSurvival": 0.10})
    keys = [f["flag"] for f in flags]
    assert "survival_extreme_low" in keys


# ── L2 consistency ───────────────────────────────────────


@pytest.mark.requires_data
def test_consistency_tg_vs_rf():
    """영구성장률 > 무위험수익률 → g_vs_rf 경고."""
    from dartlab.analysis.valuation.consistency import calcCashFlowConsistency

    r = calcCashFlowConsistency(
        terminalGrowthPct=8.0,  # KR Rf 3.4% 초과
        country="KR",
    )
    rules = [f["rule"] for f in r["flags"]]
    assert "g_vs_rf" in rules


@pytest.mark.requires_data
def test_consistency_tv_weight():
    from dartlab.analysis.valuation.consistency import calcCashFlowConsistency

    r = calcCashFlowConsistency(terminalValueShare=0.85)
    rules = [f["rule"] for f in r["flags"]]
    assert "tv_weight" in rules


@pytest.mark.requires_data
def test_consistency_single_model():
    from dartlab.analysis.valuation.consistency import calcCashFlowConsistency

    r = calcCashFlowConsistency(modelsUsed=1)
    rules = [f["rule"] for f in r["flags"]]
    assert "single_model" in rules
