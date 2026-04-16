"""Phase 5-lite — Audit 오탐 수정 테스트.

G16 Normalized Earnings / G17 highGrowth 10년 / G18 narrate rationale.
"""

from __future__ import annotations

import pytest


# ── G16 Normalized Earnings ────────────────────────────


@pytest.mark.unit
def test_normalizedFcf_cyclical_recovery():
    """적자 시계열에서 양수 마진 중앙값 사용."""
    from dartlab.core.finance.normalized import calcNormalizedFcf

    r = calcNormalizedFcf(
        revenueHistory=[110, 95, 85, 90, 100],
        marginHistory=[0.08, 0.03, 0.01, -0.02, -0.05],
    )
    assert r["method"] == "median_positive_margin"
    assert r["normalizedMargin"] > 0
    assert r["normalizedFcf"] > 0


@pytest.mark.unit
def test_normalizedFcf_skip_when_no_positive_margin():
    """양수 마진 0건 → skip."""
    from dartlab.core.finance.normalized import calcNormalizedFcf

    r = calcNormalizedFcf(
        revenueHistory=[100, 90, 80],
        marginHistory=[-0.10, -0.15, -0.20],
    )
    # 양수 마진 0건 + 평균도 음수 → skip 또는 0 이하 fallback
    assert r["method"] == "skip" or r["normalizedFcf"] is None or r["normalizedFcf"] <= 0


@pytest.mark.unit
def test_needsNormalized_decline_phase():
    """decline / turnaround phase → True."""
    from dartlab.core.finance.normalized import needsNormalized

    assert needsNormalized("decline", []) is True
    assert needsNormalized("turnaround", []) is True


@pytest.mark.unit
def test_needsNormalized_roic_loss_history():
    """ROIC 적자 이력 1회 이상 → True (matureStable 도)."""
    from dartlab.core.finance.normalized import needsNormalized

    history = [
        {"period": "2025", "roic": 21.43},
        {"period": "2024", "roic": 16.09},
        {"period": "2022", "roic": -84.24},  # 적자
    ]
    assert needsNormalized("matureStable", history) is True

    # 적자 이력 없음 → False
    healthy = [{"roic": 10}, {"roic": 12}, {"roic": 9}]
    assert needsNormalized("matureStable", healthy) is False


# ── G17 highGrowth 10년 확장 ────────────────────────────


@pytest.mark.integration
@pytest.mark.requires_data
def test_yangyang_dFV_highGrowth_realistic():
    """삼양식품 dFV 1,150K~1,550K (현재가 1,281K 근처)."""
    import dartlab
    from dartlab.analysis.valuation.dFV import calcDFV

    c = dartlab.Company("003230")
    r = calcDFV(c)
    assert 1_150_000 < r["dFV"] < 1_550_000, f"삼양 dFV={r['dFV']:,}"
    # primary=dcf2stage 유지
    assert r["primaryModel"] == "dcf2stage"
    # twoStage phase 가 3개 (10년 확장)
    ts = r.get("twoStage", {})
    assert len(ts.get("growthYears", [])) == 3


# ── G16 dFV 통합 — 한전 ─────────────────────────────────


@pytest.mark.integration
@pytest.mark.requires_data
def test_kepco_dFV_no_overshoot():
    """한전 dFV 가 현재가 ±150% 내 (이전 +233% 오탐 해결)."""
    import dartlab
    from dartlab.analysis.valuation.dFV import calcDFV

    c = dartlab.Company("015760")
    r = calcDFV(c)
    current = 44_350
    # 현재가 18K~110K (±150% 범위, ±233% 오탐 해결 검증)
    assert current * 0.4 < r["dFV"] < current * 2.5, f"한전 dFV={r['dFV']:,}"


# ── G18 valuationSins narrate rationale ─────────────────


@pytest.mark.unit
def test_valuationSins_narrate_includes_rationale():
    """narrate 에 Damodaran rationale + override 힌트 포함."""
    from dartlab.review.narrate import narrateValuationSins

    result = narrateValuationSins({
        "flags": [{"key": "roic_wacc_persist", "severity": "warn", "reason": "ROIC/WACC 4.5x"}],
        "severity": "warn",
    })
    assert "Damodaran" in result
    assert "overrides" in result.lower()


@pytest.mark.unit
def test_valuationSins_narrate_g_vs_rf():
    """g_vs_rf 위반 시 'Damodaran 상한 권고' 포함."""
    from dartlab.review.narrate import narrateValuationSins

    result = narrateValuationSins({
        "flags": [{"key": "g_vs_rf", "severity": "warn", "reason": "tg 5% > rf 3.4%"}],
        "severity": "warn",
    })
    assert "rf" in result.lower() or "무위험" in result
