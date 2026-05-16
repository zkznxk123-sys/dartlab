"""Dalio/R&R 흡수 Phase 2 — subPhase, regimeVariant, caseMatch, 48Match, rrCrisisDB 회귀."""

from __future__ import annotations

import pytest

# ── C3: dalioSubPhase ───────────────────────────────────────


@pytest.mark.requires_data
def test_beautifulDeleveragingSubPhase_moneyPrinting():
    from dartlab.credit.monitoring.crisisDetector import _beautifulDeleveragingSubPhase as beautifulDeleveragingSubPhase

    # m2 YoY 12% + 실질금리 -1% → moneyPrinting
    sp = beautifulDeleveragingSubPhase(realRate=-1.0, m2GrowthYoy=12.0, debtServiceYoY=-1.0, npl=2.0, hySpread=400)
    assert sp == "moneyPrinting"


@pytest.mark.requires_data
def test_beautifulDeleveragingSubPhase_defaultRestructuring():
    from dartlab.credit.monitoring.crisisDetector import _beautifulDeleveragingSubPhase as beautifulDeleveragingSubPhase

    sp = beautifulDeleveragingSubPhase(realRate=1.0, m2GrowthYoy=5.0, debtServiceYoY=0.0, npl=8.0, hySpread=900)
    assert sp == "defaultRestructuring"


@pytest.mark.requires_data
def test_beautifulDeleveragingSubPhase_wealthTransfer():
    from dartlab.credit.monitoring.crisisDetector import _beautifulDeleveragingSubPhase as beautifulDeleveragingSubPhase

    sp = beautifulDeleveragingSubPhase(
        realRate=0.5,
        m2GrowthYoy=5.0,
        debtServiceYoY=-0.5,
        npl=2.0,
        hySpread=300,
        fiscalDeficitPctGdp=8.0,
    )
    assert sp == "wealthTransfer"


@pytest.mark.requires_data
def test_beautifulDeleveragingSubPhase_austerity():
    from dartlab.credit.monitoring.crisisDetector import _beautifulDeleveragingSubPhase as beautifulDeleveragingSubPhase

    sp = beautifulDeleveragingSubPhase(
        realRate=2.5,
        m2GrowthYoy=3.0,
        debtServiceYoY=1.0,
        npl=1.5,
        hySpread=300,
        fiscalDeficitPctGdp=3.0,
    )
    assert sp == "austerity"


@pytest.mark.requires_data
def test_beautifulDeleveragingSubPhase_insufficient_signals():
    from dartlab.credit.monitoring.crisisDetector import _beautifulDeleveragingSubPhase as beautifulDeleveragingSubPhase

    sp = beautifulDeleveragingSubPhase(realRate=1.0)  # 하나만
    assert sp is None


@pytest.mark.requires_data
def test_dalioRegimeVariant_deflationary_foreign_debt():
    from dartlab.credit.monitoring.crisisDetector import _dalioRegimeVariant as dalioRegimeVariant

    v = dalioRegimeVariant(fxFlexibility="pegged", reserveCurrency=False, realRate=3.0, foreignDebtPct=40)
    assert v == "deflationary"


@pytest.mark.requires_data
def test_dalioRegimeVariant_inflationary_reserve_currency():
    from dartlab.credit.monitoring.crisisDetector import _dalioRegimeVariant as dalioRegimeVariant

    v = dalioRegimeVariant(fxFlexibility="flexible", reserveCurrency=True, realRate=-3.0)
    assert v == "inflationary"


@pytest.mark.requires_data
def test_dalioDebtCyclePhase_emits_subPhase():
    """beautifulDeleveraging 진단 시 subPhase 활성."""
    from dartlab.credit.monitoring.crisisDetector import dalioDebtCyclePhase

    r = dalioDebtCyclePhase(
        totalDebtToGdp=240,
        debtServiceYoY=-2.0,
        creditGap=2.0,
        realRate=-1.0,
        gdpGrowth=2.0,
        m2GrowthYoy=12.0,
    )
    assert r.phase == "beautifulDeleveraging"
    assert r.subPhase == "moneyPrinting"
    assert r.subPhaseLabel == "화폐발행"


@pytest.mark.requires_data
def test_dalioDebtCyclePhase_no_subphase_outside_deleveraging():
    from dartlab.credit.monitoring.crisisDetector import dalioDebtCyclePhase

    r = dalioDebtCyclePhase(
        totalDebtToGdp=150,
        debtServiceYoY=4,
        creditGap=-3,
        realRate=6,
        gdpGrowth=-2,
        m2GrowthYoy=3.0,  # subPhase 활성 조건 아님
    )
    assert r.phase == "deflationaryDepression"
    assert r.subPhase is None


# ── C4: dalioCaseMatch ─────────────────────────────────────


@pytest.mark.requires_data
def test_matchDalioDetailCase_2008_matches_subprime():
    from dartlab.synth.dalioCaseMatch import matchDalioDetailCase

    r = matchDalioDetailCase(
        {
            "totalDebtToGdp": 370,
            "creditGap": -2,
            "realRate": 1.0,
            "gdpGrowth": -0.3,
            "debtServiceYoY": 3.0,
        }
    )
    assert r["matches"]
    assert "Subprime" in r["matches"][0]["caseLabel"]


@pytest.mark.requires_data
def test_matchDalioDetailCase_empty_state():
    from dartlab.synth.dalioCaseMatch import matchDalioDetailCase

    r = matchDalioDetailCase({})
    # 공통 축 < 2 → 모든 유사도 0. 여전히 matches 반환.
    assert isinstance(r["matches"], list)


@pytest.mark.requires_data
def test_matchDalioDetailCase_returns_nextStage():
    from dartlab.synth.dalioCaseMatch import matchDalioDetailCase

    r = matchDalioDetailCase(
        {
            "totalDebtToGdp": 340,
            "creditGap": 10,
            "realRate": 2.5,
            "gdpGrowth": 2.0,
            "debtServiceYoY": 0.5,
        }
    )
    top = r["matches"][0]
    # 2007 topBubble → nextStage = 2008 deflationaryDepression
    assert top["nextStage"] is not None


# ── C5: dalio48Match ───────────────────────────────────────


@pytest.mark.requires_data
def test_match48Cases_dominant_deflationary():
    from dartlab.synth.dalio48Match import match48Cases

    r = match48Cases(
        {
            "peakDebtToGdp": 350,
            "peakCreditGap": 12,
            "troughRealRate": 0.5,
            "troughGdpGrowth": -2.8,
        }
    )
    assert r["dominantArchetype"] == "deflationary"
    assert r["matches"]


@pytest.mark.requires_data
def test_match48Cases_hyperinflation_recognized():
    from dartlab.synth.dalio48Match import match48Cases

    r = match48Cases(
        {
            "peakDebtToGdp": 280,
            "peakCreditGap": 25,
            "troughRealRate": -80,
            "troughGdpGrowth": -15,
        }
    )
    # Weimar / Zimbabwe / Venezuela 중 하나 상위
    assert r["matches"][0]["archetype"] == "inflationary"


# ── C6: rrCrisisDB ─────────────────────────────────────────


@pytest.mark.requires_data
def test_classifyCrisisType_triple_kr_1997():
    from dartlab.macro.crisis.rrCrisisDB import classifyCrisisType

    r = classifyCrisisType(
        hySpread=1200,
        npl=8,
        fxDepreciationYoy=45,
        inflationYoy=7,
        sovereignSpread=600,
        gdpGrowth=-5,
    )
    assert "banking" in r["activeTypes"]
    assert "currency" in r["activeTypes"]
    assert "sovereign_debt" in r["activeTypes"]
    assert r["isTripleCrisis"]


@pytest.mark.requires_data
def test_classifyCrisisType_stagflation():
    from dartlab.macro.crisis.rrCrisisDB import classifyCrisisType

    r = classifyCrisisType(inflationYoy=8, gdpGrowth=0.5)
    assert "stagflation" in r["activeTypes"]


@pytest.mark.requires_data
def test_classifyCrisisType_empty_normal():
    from dartlab.macro.crisis.rrCrisisDB import classifyCrisisType

    r = classifyCrisisType(hySpread=300, npl=1, fxDepreciationYoy=2, inflationYoy=2)
    assert r["activeTypes"] == []
    assert r["dominantType"] is None


@pytest.mark.requires_data
def test_matchRrHistorical_kr_1997_bonus():
    from dartlab.macro.crisis.rrCrisisDB import matchRrHistorical

    r = matchRrHistorical(["banking", "currency", "sovereign_debt"], country="KR")
    assert r["matches"]
    top = r["matches"][0]
    # KR + triple 일치로 가장 높은 score
    assert top["id"] == "kr_1997"
    assert top["score"] >= 4


@pytest.mark.requires_data
def test_matchRrHistorical_no_types():
    from dartlab.macro.crisis.rrCrisisDB import matchRrHistorical

    r = matchRrHistorical([])
    assert r["matches"] == []


# ── macro/crisis.py — analyze_crisis 결과 dict 회귀 (kwargs 없이도 Dalio 블록 존재) ──


@pytest.mark.requires_data
def test_analyze_crisis_emits_dalio_keys(monkeypatch):
    """analyze_crisis 가 데이터 없어도 dict 구조 반환 (키 존재)."""
    import dartlab.macro.crisis.crisis as crisis_mod

    monkeypatch.setattr(crisis_mod, "_fetchCrisisData", lambda market, asOf=None: {})
    r = crisis_mod.analyzeCrisis(market="US")
    assert "debtCyclePhase" in r
    assert "policyLeverStatus" in r
