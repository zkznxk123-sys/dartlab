"""Grinold/Kahn 흡수 Phase 2 — crossSectionIC + residualRisk + informationAnalysis
+ holdingsDecomposition + constrainedOpt 회귀 보호.
"""

from __future__ import annotations

import numpy as np
import pytest


# ── B2: crossSectionIC ──────────────────────────────────────


@pytest.mark.unit
def test_calcCrossSectionIC_perfect():
    from dartlab.quant.ranking import calcCrossSectionIC

    scores = {f"S{i}": float(i) for i in range(20)}
    rets = {f"S{i}": float(i) * 2 for i in range(20)}
    r = calcCrossSectionIC(scores, rets)
    assert abs(r["ic_pearson"] - 1.0) < 1e-9
    assert abs(r["ic_spearman"] - 1.0) < 1e-9
    assert r["n_stocks"] == 20
    assert r["is_significant"]


@pytest.mark.unit
def test_calcCrossSectionIC_small_sample_nan():
    from dartlab.quant.ranking import calcCrossSectionIC

    scores = {"A": 1.0, "B": 2.0}
    rets = {"A": 1.0, "B": 2.0}
    r = calcCrossSectionIC(scores, rets)
    assert np.isnan(r["ic_pearson"])
    assert r["is_significant"] is False


@pytest.mark.unit
def test_calcCrossSectionIC_disjoint_keys():
    from dartlab.quant.ranking import calcCrossSectionIC

    r = calcCrossSectionIC({"A": 1.0}, {"B": 2.0})
    assert r["n_stocks"] == 0


@pytest.mark.unit
def test_icTimeSeries_icir():
    from dartlab.quant.ranking import icTimeSeries

    rng = np.random.default_rng(0)
    fss, frs = [], []
    for _ in range(12):
        s = {f"S{i}": float(rng.normal()) for i in range(30)}
        r = {k: v * 0.3 + float(rng.normal(0, 0.5)) for k, v in s.items()}
        fss.append(s)
        frs.append(r)
    t = icTimeSeries(fss, frs)
    assert t["n_periods"] == 12
    assert not np.isnan(t["icir"])


# ── B3: residualRisk ────────────────────────────────────────


@pytest.mark.unit
def test_decomposeRisk_pure_systematic():
    from dartlab.quant.factor import decomposeRisk

    rng = np.random.default_rng(1)
    T = 252
    F = rng.normal(0, 0.01, (T, 2))
    beta = np.array([1.0, 0.5])
    y = F @ beta  # 순수 systematic
    r = decomposeRisk(returns=y, factorExposures=beta, factorReturns=F)
    assert r["residualShare"] < 0.01
    assert r["systematicShare"] > 0.99


@pytest.mark.unit
def test_decomposeRisk_trackingError_is_residual():
    from dartlab.quant.factor import decomposeRisk

    rng = np.random.default_rng(2)
    T = 100
    F = rng.normal(0, 0.01, (T, 1))
    beta = np.array([0.5])
    eps = rng.normal(0, 0.02, T)
    y = F @ beta + eps
    r = decomposeRisk(returns=y, factorExposures=beta, factorReturns=F)
    assert r["trackingError"] == r["residualRisk"]


@pytest.mark.unit
def test_residualAlphaIR_zero_mean():
    from dartlab.quant.factor import residualAlphaIR

    rng = np.random.default_rng(3)
    eps = rng.normal(0, 0.02, 252)
    r = residualAlphaIR(eps)
    assert abs(r["rawIR"]) < 0.3  # 평균 ≈ 0


@pytest.mark.unit
def test_residualRiskForecast_basic():
    from dartlab.quant.factor import residualRiskForecast

    rng = np.random.default_rng(4)
    eps = rng.normal(0, 0.02, 200)
    f = residualRiskForecast(eps, horizonDays=252, halfLifeDays=60)
    # 대략 0.02 × √252 ≈ 0.32
    assert 0.15 < f < 0.50


# ── B4: informationAnalysis ────────────────────────────────


@pytest.mark.unit
def test_icSignificance_high_t():
    from dartlab.quant.strategy.metrics import icSignificance

    # 평균 0.05 ± 0.02, T=36 → t ≈ 15
    rng = np.random.default_rng(5)
    ic = rng.normal(0.05, 0.02, 36)
    r = icSignificance(ic)
    assert r["tStat"] > 5.0
    assert r["isSignificant"]
    assert r["hitRate"] > 0.8


@pytest.mark.unit
def test_factorDecayRate_white_noise():
    from dartlab.quant.strategy.metrics import factorDecayRate

    rng = np.random.default_rng(6)
    ic = rng.normal(0, 1, 50)
    d = factorDecayRate(ic)
    # 백색잡음 → 자기상관 ≈ 0
    assert abs(d["autocorr"]) < 0.3


@pytest.mark.unit
def test_factorDecayRate_persistent_ar1():
    from dartlab.quant.strategy.metrics import factorDecayRate

    rng = np.random.default_rng(7)
    n = 200
    ic = np.zeros(n)
    ic[0] = rng.normal()
    for t in range(1, n):
        ic[t] = 0.7 * ic[t - 1] + rng.normal(0, 0.3)
    d = factorDecayRate(ic)
    assert d["autocorr"] > 0.5
    assert d["persistence"] == "high"
    assert d["halfLifePeriods"] is not None


@pytest.mark.unit
def test_breadthFromFrequency_basic():
    from dartlab.quant.strategy.metrics import breadthFromFrequency

    # 월 리밸 × 100 종목 × 독립 0.5 = 600
    assert breadthFromFrequency(rebalancesPerYear=12, nStocks=100, independenceRatio=0.5) == 600


@pytest.mark.unit
def test_breadthFromFrequency_clip_independence():
    from dartlab.quant.strategy.metrics import breadthFromFrequency

    # independence > 1.0 → clip to 1.0
    assert breadthFromFrequency(rebalancesPerYear=12, nStocks=10, independenceRatio=2.0) == 120


@pytest.mark.unit
def test_impliedIR_fundamental_law():
    from dartlab.quant.strategy.metrics import impliedIRFromICDistribution

    rng = np.random.default_rng(8)
    ic = rng.normal(0.05, 0.02, 36)
    r = impliedIRFromICDistribution(ic, breadth=400)
    # theoretical IR = 0.05 × √400 = 1.0 (± 시뮬레이션 노이즈)
    assert 0.7 < r["theoreticalIR"] < 1.3


# ── B7: holdingsDecomposition ──────────────────────────────


@pytest.mark.unit
def test_holdingsToFactorExposure_weighted_sum():
    from dartlab.quant.portfolio import holdingsToFactorExposure

    w = {"A": 0.5, "B": 0.5}
    L = {"A": {"MKT": 1.0, "SMB": -0.5}, "B": {"MKT": 1.2, "SMB": 0.3}}
    exp = holdingsToFactorExposure(w, L)
    assert abs(exp["MKT"] - 1.1) < 1e-9
    assert abs(exp["SMB"] - (-0.1)) < 1e-9


@pytest.mark.unit
def test_activeExposure_zero_when_identical():
    from dartlab.quant.portfolio import activeExposure

    w = {"A": 0.5, "B": 0.5}
    L = {"A": {"MKT": 1.0}, "B": {"MKT": 1.2}}
    ae = activeExposure(w, w, L)
    assert abs(ae.get("MKT", 0.0)) < 1e-9


@pytest.mark.unit
def test_riskBudgetByFactor_shares_sum_to_one():
    from dartlab.quant.portfolio import riskBudgetByFactor

    exp = {"MKT": 1.0, "SMB": 0.2}
    cov = {("MKT", "MKT"): 0.04, ("SMB", "SMB"): 0.01, ("MKT", "SMB"): 0.002}
    r = riskBudgetByFactor(exp, cov, ["MKT", "SMB"])
    total = sum(r["pctContrib"].values())
    assert abs(total - 1.0) < 1e-6


# ── B8: constrainedOpt ──────────────────────────────────────


@pytest.mark.unit
def test_constrainedMinVariance_weights_sum_to_one():
    from dartlab.quant.portfolio import constrainedMinVariance

    S = np.array([[0.04, 0.01], [0.01, 0.03]])
    r = constrainedMinVariance(S, boxMin=0.0, boxMax=1.0)
    assert abs(r["weights"].sum() - 1.0) < 1e-6


@pytest.mark.unit
def test_constrainedMinVariance_box_respected():
    from dartlab.quant.portfolio import constrainedMinVariance

    S = np.array([[0.01, 0.0, 0.0], [0.0, 0.1, 0.0], [0.0, 0.0, 0.5]])
    r = constrainedMinVariance(S, boxMin=0.1, boxMax=0.5)
    w = r["weights"]
    assert (w >= 0.1 - 1e-6).all()
    assert (w <= 0.5 + 1e-6).all()


@pytest.mark.unit
def test_factorExposureConstraint_breach_detection():
    from dartlab.quant.portfolio import factorExposureConstraint

    w = np.array([0.6, 0.4])
    L = np.array([[1.5, 0.2], [1.3, 0.1]])
    r = factorExposureConstraint(w, L, np.array([1.0, 1.0]))
    # MKT 노출 = 0.6*1.5 + 0.4*1.3 = 1.42 > 1.0 → 초과
    assert 0 in r["breaches"]
    assert r["compliant"] is False


@pytest.mark.unit
def test_constrainedMinVariance_empty_cov():
    from dartlab.quant.portfolio import constrainedMinVariance

    r = constrainedMinVariance(np.zeros((0, 0)))
    assert r["weights"].size == 0
    assert r["variance"] == 0.0
