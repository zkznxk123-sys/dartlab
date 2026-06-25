"""거시 시뮬레이션 엔진 단위 테스트 — 합성 VAR 데이터(DI·parquet 비의존·CI-safe).

코어 순수 함수(BVAR·fan·IRF·regimePath) 검증. 개념검증 졸업 후 본진 회귀 가드.
실행: bash tests/test-lock.sh tests/macro/test_macro_simulate.py -m unit -v
"""

from __future__ import annotations

import numpy as np
import pytest

from dartlab.macro.simulate import (
    VarSpec,
    estimateBvar,
    forwardFan,
    impulseResponse,
    maxCompanionModulus,
    simulateRegimePath,
)

pytestmark = pytest.mark.unit

SPECS = (
    VarSpec("A", "성장", "logdiff100"),
    VarSpec("B", "물가", "logdiff100"),
    VarSpec("C", "금리", "level"),
)


def _synthPanel(t: int = 240, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = np.array([[0.5, 0.0, -0.1], [0.1, 0.4, -0.05], [0.0, 0.1, 0.85]])
    y = np.zeros((t, 3))
    for i in range(1, t):
        y[i] = a @ y[i - 1] + rng.standard_normal(3) * np.array([0.6, 0.4, 0.3])
    return y


@pytest.fixture(scope="module")
def fit():
    panel = _synthPanel()
    return estimateBvar(panel, SPECS, p=4, lam=0.3, lastLevels=np.array([100.0, 100.0, 3.0]), endYm="2026-05")


def test_estimateShapes(fit):
    k = 3 * 4 + 1
    assert fit.bPost.shape == (k, 3)
    assert fit.sPost.shape == (3, 3)
    assert fit.nuPost > 3
    assert fit.nObs == 240


def test_companionStable(fit):
    assert maxCompanionModulus(fit) < 1.0


def test_fanDeterminism(fit):
    panel = _synthPanel()
    a = forwardFan(fit, panel, horizon=12, draws=300, seed=20260624)
    b = forwardFan(fit, panel, horizon=12, draws=300, seed=20260624)
    for s in SPECS:
        assert a[s.label]["q50"] == b[s.label]["q50"]
        assert a[s.label]["q5"] == b[s.label]["q5"]


def test_fanQuantileMonotone(fit):
    panel = _synthPanel()
    fan = forwardFan(fit, panel, horizon=12, draws=500, seed=7)
    for s in SPECS:
        r = fan[s.label]
        for h in range(12):
            assert r["q5"][h] <= r["q25"][h] <= r["q50"][h] <= r["q75"][h] <= r["q95"][h]


def test_fanLevelCumulation(fit):
    panel = _synthPanel()
    fan = forwardFan(fit, panel, horizon=6, draws=200, seed=3, histMonths=18)
    assert "level_q50" in fan["성장"]
    assert len(fan["성장"]["level_q50"]) == 6
    assert all(np.isfinite(fan["성장"]["level_q50"]))
    assert "level_q50" not in fan["금리"]  # level 변수는 누적 환산 없음
    # 차트 연결용 과거 실적(변환 단위) 동봉
    assert len(fan["성장"]["history"]) == 18
    assert fan["성장"]["history"] == panel[-18:, 0].tolist()


def test_irfShape(fit):
    irf = impulseResponse(fit, horizon=24, shockVar=2, shockSize=1.0)
    assert len(irf["금리"]) == 25
    assert abs(irf["금리"][0] - 1.0) < 1e-9
    assert irf["caveat"] == "recursive-identification·illustrative"
    assert all(np.all(np.isfinite(irf[k])) for k in irf if k != "caveat")


def test_regimePathMarkov():
    """π_h = π_0 · P^h. 자기지속 0.95·0.90 → P(수축) 가 ergodic 으로 수렴."""
    rp = simulateRegimePath(0.95, 0.90, [0.9, 0.1], horizon=24)
    fwd = [d["pContraction"] for d in rp["forward"]]
    assert len(fwd) == 24
    assert all(0.0 <= v <= 1.0 for v in fwd)
    assert rp["current"] == 0.1
    # ergodic = (1-p00)/(2-p00-p11) = 0.05/0.15 ≈ 0.333
    assert abs(rp["ergodic"] - 1 / 3) < 0.02
    assert abs(fwd[-1] - rp["ergodic"]) < 0.05  # 24기 뒤 수렴


def test_regimePathAbsorbingLimit():
    """완전 지속(1,1)이면 현재 분포 유지."""
    rp = simulateRegimePath(1.0, 1.0, [0.3, 0.7], horizon=6)
    assert abs(rp["forward"][-1]["pContraction"] - 0.7) < 1e-9
