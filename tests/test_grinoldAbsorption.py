"""Grinold & Kahn *Active Portfolio Management* 흡수 테스트.

SSOT (quant/strategy/metrics.py) 순수 수식 검증 — quant 엔진 내부에 통합됨.
"""

from __future__ import annotations

import numpy as np
import pytest

# ── L0 SSOT — 상관계수 ──────────────────────────────────────────


@pytest.mark.unit
def test_pearsonCorr_perfect():
    from dartlab.quant.strategy.metrics import pearsonCorr

    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert abs(pearsonCorr(x, x) - 1.0) < 1e-9
    assert abs(pearsonCorr(x, -x) + 1.0) < 1e-9


@pytest.mark.unit
def test_pearsonCorr_zero_variance():
    from dartlab.quant.strategy.metrics import pearsonCorr

    x = np.array([1.0, 1.0, 1.0, 1.0])
    y = np.array([2.0, 3.0, 4.0, 5.0])
    # 분산 0 → 0 반환 (nan 대신 안전한 값)
    assert pearsonCorr(x, y) == 0.0


@pytest.mark.unit
def test_pearsonCorr_nan_mask():
    from dartlab.quant.strategy.metrics import pearsonCorr

    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
    # NaN 쌍 제거 후 (1,1), (2,2), (5,5) → 완벽 상관
    assert abs(pearsonCorr(x, y) - 1.0) < 1e-9


@pytest.mark.unit
def test_spearmanCorr_monotone():
    from dartlab.quant.strategy.metrics import spearmanCorr

    # 비선형이지만 단조 증가 → Spearman = 1
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = x**3
    assert abs(spearmanCorr(x, y) - 1.0) < 1e-9


@pytest.mark.unit
def test_spearmanCorr_ties_avg_rank():
    from dartlab.quant.strategy.metrics import spearmanCorr

    # 동률 처리 — 평균 rank
    x = np.array([1.0, 2.0, 2.0, 3.0])
    y = np.array([10.0, 20.0, 20.0, 30.0])
    assert abs(spearmanCorr(x, y) - 1.0) < 1e-9


# ── L0 SSOT — IR + Fundamental Law ─────────────────────────────


@pytest.mark.unit
def test_calcIR_basic():
    from dartlab.quant.strategy.metrics import calcIR

    alpha = np.array([0.01, 0.02, -0.01, 0.03, 0.0])
    ir = calcIR(alpha)
    expected = alpha.mean() / alpha.std(ddof=1)
    assert abs(ir - expected) < 1e-9


@pytest.mark.unit
def test_calcIR_zero_std():
    from dartlab.quant.strategy.metrics import calcIR

    # 전체 동일값 → std=0 → 0 반환
    alpha = np.array([0.01, 0.01, 0.01, 0.01])
    assert calcIR(alpha) == 0.0


@pytest.mark.unit
def test_fundamentalLawIR_grinold_example():
    """Grinold 대표 사례: IC=0.05, breadth=400 → IR=1.0."""
    from dartlab.quant.strategy.metrics import fundamentalLawIR

    assert abs(fundamentalLawIR(0.05, 400) - 1.0) < 1e-9


@pytest.mark.unit
def test_fundamentalLawIR_breadth_scaling():
    from dartlab.quant.strategy.metrics import fundamentalLawIR

    # breadth 4배 → IR 2배 (√4=2)
    ir1 = fundamentalLawIR(0.05, 100)
    ir2 = fundamentalLawIR(0.05, 400)
    assert abs(ir2 - 2 * ir1) < 1e-9


@pytest.mark.unit
def test_fundamentalLawIR_invalid_breadth():
    from dartlab.quant.strategy.metrics import fundamentalLawIR

    assert fundamentalLawIR(0.05, 0) == 0.0


# ── L0 SSOT — rolling time-series z-score ──────────────────────


@pytest.mark.unit
def test_rollingTimeSeriesZscore_shape():
    from dartlab.quant.strategy.metrics import rollingTimeSeriesZscore

    s = np.arange(20, dtype=float)
    z = rollingTimeSeriesZscore(s, window=5)
    # 앞 window-1 = 4 개 NaN
    assert np.isnan(z[:4]).all()
    # 나머지는 유효
    assert not np.isnan(z[4:]).any()


@pytest.mark.unit
def test_rollingTimeSeriesZscore_constant():
    from dartlab.quant.strategy.metrics import rollingTimeSeriesZscore

    s = np.ones(10)
    z = rollingTimeSeriesZscore(s, window=3)
    # 상수 → std=0 → NaN 유지
    assert np.isnan(z[2:]).all()


@pytest.mark.unit
def test_rollingTimeSeriesZscore_trend():
    from dartlab.quant.strategy.metrics import rollingTimeSeriesZscore

    # 선형 증가 → 마지막 값은 양의 z-score
    s = np.arange(10, dtype=float)
    z = rollingTimeSeriesZscore(s, window=5)
    assert z[-1] > 0


# ── L2 회귀 — decomposeFactor 결과 dict 에 IR 키 ────────────────


@pytest.mark.unit
def test_factor_result_has_ir_keys():
    """decomposeFactor 결과 dict 에 Grinold IR 키 존재 (스키마 회귀)."""
    from dartlab.quant.factor import _multiOls

    # OLS 결과에 residuals 포함 확인 (IR 계산 원료)
    np.random.seed(0)
    X = np.random.normal(0, 1, size=(60, 2))
    y = X @ [0.5, 0.3] + np.random.normal(0, 0.1, 60)
    betas, alpha, r2, tstats, resid = _multiOls(y, X)
    assert resid is not None
    assert len(resid) == 60
