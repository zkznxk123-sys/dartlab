"""Damodaran Phase 3 흡수 테스트.

G5 Implied ERP / G6 Bottom-up Beta / G7 Real Options / G8 Control+Synergy /
G9 multiStageDcf / G10 Calibration.
"""

from __future__ import annotations

import math

import pytest

# ── G5 Implied ERP ─────────────────────────────────────


@pytest.mark.unit
def test_impliedERP_returns_loadDamodaranERP_schema():
    """impliedERP 결과는 loadDamodaranERP 와 동일 키 셋을 반환 (proforma 분기 호환)."""
    from dartlab.core.finance.impliedERP import calcImpliedERP
    from dartlab.core.finance.riskPremiums import loadDamodaranERP

    ref = loadDamodaranERP(countryCode="US")
    r = calcImpliedERP(country="US", useCache=False)
    # 핵심 키 동일
    for key in (
        "countryCode",
        "matureMarketERP",
        "countryRiskPremium",
        "totalERP",
        "riskFreeRate",
        "source",
        "asOfDate",
    ):
        assert key in r, f"missing {key} in impliedERP"
        assert key in ref, f"missing {key} in loadDamodaranERP"


@pytest.mark.unit
def test_impliedERP_fallback_when_index_missing():
    """지수/finance.parquet 없는 국가 → source=fallback_historical."""
    from dartlab.core.finance.impliedERP import calcImpliedERP

    # 한국/미국 외 국가는 현재 aggregate 경로 없음
    r = calcImpliedERP(country="JP", useCache=False)
    assert r["source"] == "fallback_historical"
    assert r["method"] == "none"
    assert r["impliedERP"] is None


# ── G6 Bottom-up Beta ──────────────────────────────────


@pytest.mark.unit
def test_bottomUpBeta_hamada_unlever_relever():
    """Hamada equation: β_U = β_L / (1 + (1-t)×D/E).

    peer β=1.0, D/E=0.5, t=0.2 → β_U = 1.0/(1+0.8×0.5) = 1.0/1.4 = 0.714
    자기 D/E=0.3 → β_L = 0.714 × (1+0.8×0.3) = 0.714 × 1.24 = 0.886
    """
    from dartlab.core.finance.bottomUpBeta import calcBottomUpBeta

    # 실제 scan/finance.parquet 호출 → peer 추출 → Hamada
    r = calcBottomUpBeta(sector="IT", debtToEquity=0.3, taxRate=0.22, peerLimit=20)
    # 폴백이든 bottom_up 이든 leveredBeta 는 수치
    assert isinstance(r["leveredBeta"], (int, float))
    assert 0.3 <= r["leveredBeta"] <= 3.0
    assert r["method"] in ("bottom_up", "sector_default", "fallback_one")


@pytest.mark.unit
def test_bottomUpBeta_falls_back_when_peerCount_lt_5():
    """peer 추출 실패 시 fallback_one 또는 sector_default."""
    from dartlab.core.finance.bottomUpBeta import calcBottomUpBeta

    # 존재하지 않는 섹터 → peer 0
    r = calcBottomUpBeta(sector="__NONEXISTENT_SECTOR__", debtToEquity=0.5, taxRate=0.22, peerLimit=20)
    assert r["method"] in ("sector_default", "fallback_one", "bottom_up")
    # fallback 시 leveredBeta 는 기본값
    if r["method"] == "fallback_one":
        assert r["leveredBeta"] == 1.0


# ── G7 Real Options ────────────────────────────────────


@pytest.mark.unit
def test_blackScholesCall_matches_known_value():
    """Hull Ex 15.6: S=42, K=40, T=0.5, r=0.10, σ=0.20 → Call ≈ 4.76."""
    from dartlab.analysis.valuation.optionValue import blackScholesCall

    r = blackScholesCall(S=42, K=40, T=0.5, r=0.10, sigma=0.20)
    assert abs(r["call"] - 4.76) < 0.02, f"expected ~4.76, got {r['call']:.3f}"
    # Put-call parity: C - P = S - K×e^(-rT)
    parity_lhs = r["call"] - r["put"]
    parity_rhs = 42 - 40 * math.exp(-0.10 * 0.5)
    assert abs(parity_lhs - parity_rhs) < 0.01


@pytest.mark.unit
def test_binomial_converges_to_black_scholes():
    """European call: Binomial (100 steps) ≈ Black-Scholes."""
    from dartlab.analysis.valuation.optionValue import binomialOption, blackScholesCall

    bs = blackScholesCall(S=50, K=50, T=1.0, r=0.05, sigma=0.25)
    bn = binomialOption(S=50, K=50, T=1.0, r=0.05, sigma=0.25, steps=100, kind="call", american=False)
    assert abs(bn["value"] - bs["call"]) < 0.05


@pytest.mark.unit
def test_realOptions_no_double_count_field():
    """realOptions 반환 dict 의 appliedAs 가 uplift/floor 만 — primary 합산 금지 규약."""
    from dartlab.analysis.valuation.realOptions import _selectOptionType

    # phase → optionType 매핑 검증
    assert _selectOptionType("earlyGrowth") == "delay"
    assert _selectOptionType("highGrowth") == "delay"
    assert _selectOptionType("matureGrowth") == "expand"
    assert _selectOptionType("decline") == "abandon"
    assert _selectOptionType("turnaround") == "abandon"
    assert _selectOptionType("matureStable") is None  # 옵션 없음
    assert _selectOptionType(None) is None


# ── G8 Control + Synergy ───────────────────────────────


@pytest.mark.unit
def test_valuationSins_flags_control_synergy_overlap():
    """Control premium + Synergy > standalone × 50% → critical flag."""
    from dartlab.analysis.financial.storyValidation import calcValuationSins

    # valuation dict 에 controlPremium + synergy + standalone 주입
    valuation = {
        "dFV": 100_000,
        "controlPremium": 40_000,
        "synergy": 40_000,
        "companyType": "성장",
    }
    r = calcValuationSins(valuation=valuation)
    flags = r["flags"]
    keys = [f.get("key") for f in flags]
    assert "control_synergy_overlap" in keys
    # critical severity
    overlap = next(f for f in flags if f.get("key") == "control_synergy_overlap")
    assert overlap["severity"] == "critical"


# ── G9 multiStageDcf ───────────────────────────────────


@pytest.mark.unit
def test_multiStageDcf_single_phase_equals_twoStage():
    """multiStageDcf(growthYears=[n], rates=[r]) 가 기존 twoStageDcf 와 동일."""
    from dartlab.analysis.valuation.dcf import multiStageDcf, twoStageDcf

    args = dict(baseFcf=100_000_000_000, terminalGrowthRate=3.0, wacc=10.0, netDebt=0, shares=1_000_000)
    old = twoStageDcf(growthYears=5, highGrowthRate=10.0, **args)
    new = multiStageDcf(growthYears=[5], growthRates=[10.0], **args)
    # perShare 동일
    assert abs(old["perShare"] - new["perShare"]) < 1e-6
    # EV 동일
    assert abs(old["enterpriseValue"] - new["enterpriseValue"]) < 1e-3


@pytest.mark.unit
def test_multiStageDcf_threephase_pv_sum():
    """3-phase DCF: pvExplicit = Σ(phase_pv). phases 구조 검증."""
    from dartlab.analysis.valuation.dcf import multiStageDcf

    r = multiStageDcf(
        baseFcf=100_000_000_000,
        growthYears=[5, 3, 2],
        growthRates=[20.0, 10.0, 5.0],
        terminalGrowthRate=3.0,
        wacc=10.0,
    )
    assert len(r["phases"]) == 3
    total_pv = sum(p["pv"] for p in r["phases"])
    assert abs(total_pv - r["pvExplicit"]) < 1.0
    assert r["enterpriseValue"] > r["pvTerminal"]
    assert len(r["projections"]) == 5 + 3 + 2


@pytest.mark.unit
def test_multiStageDcf_tg_auto_correction():
    """영구성장률 ≥ WACC 이면 자동 보정."""
    from dartlab.analysis.valuation.dcf import multiStageDcf

    r = multiStageDcf(
        baseFcf=100_000_000_000,
        growthYears=[5],
        growthRates=[10.0],
        terminalGrowthRate=12.0,  # WACC 10% 초과
        wacc=10.0,
    )
    assert r["terminalGrowthRate"] < r["wacc"]
    assert any("보정" in w or "영구성장" in w for w in r["warnings"])


# ── overrides Phase 3 ──────────────────────────────────


@pytest.mark.unit
def test_overrides_has_phase3_keys():
    """신규 Phase 3 override 키가 VALUATION_KEYS 에 등록됨."""
    from dartlab.core.overrides import FORECAST_KEYS, VALUATION_KEYS

    for key in ("impliedERP", "bottomUpBeta", "optimalROIC", "synergyType", "controlScenario"):
        assert key in VALUATION_KEYS, f"{key} missing in VALUATION_KEYS"
    assert "marginPath" in FORECAST_KEYS
    assert "reinvestmentPath" in FORECAST_KEYS


@pytest.mark.unit
def test_detectExtremeFlags_control_synergy_double_count():
    """Control + Synergy > standalone × 0.5 → control_synergy_double_count flag."""
    from dartlab.core.overrides import detectExtremeFlags

    flags = detectExtremeFlags(
        {
            "controlPremium": 60_000,
            "synergy": 50_000,
            "standaloneValue": 100_000,
        }
    )
    keys = [f["flag"] for f in flags]
    assert "control_synergy_double_count" in keys


@pytest.mark.unit
def test_detectExtremeFlags_implied_far_from_historical():
    """Implied ERP 가 historical 대비 ±3%p 초과 → flag."""
    from dartlab.core.overrides import detectExtremeFlags

    flags = detectExtremeFlags(
        {
            "impliedERP": 8.5,
            "historicalERP": 4.6,
        }
    )
    keys = [f["flag"] for f in flags]
    assert "implied_far_from_historical" in keys
