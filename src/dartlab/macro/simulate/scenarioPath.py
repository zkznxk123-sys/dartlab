"""시나리오 조건부 forward — 정책 변수 경로를 고정한 BVAR 조건부 예측(해석적·결정론).

무조건 예측분포 N(μ, Ω)에 "정책 변수가 baseline+δ 경로를 따른다"는 하드 제약을 걸어 나머지
변수의 조건부 평균·밴드를 닫힌형으로 푼다(Gaussian 조건화). 난수 0 → 터미널 TS 와 byte 일치(parity).

    μ̃ = μ + Ω R'(R Ω R')⁻¹ (z − R μ),   Ω̃ = Ω − Ω R'(R Ω R')⁻¹ R Ω

z = 조건 horizon 의 정책 변수 목표값(=baseline μ + δ), R = 해당 (변수,horizon) 셀 선택자.
Ω = Ψ (I_H ⊗ Σ) Ψ' (Ψ = MA 계수 블록 하삼각). baseline 과 같은 fan 출력 형태 → UI overlay 재사용.

근거: Doan-Litterman-Sims(1984) 조건부 예측 · Bańbura-Giannone-Lenza(2015) Conditional forecasts and
scenario analysis with large VARs. 정직: scenario≠forecast — "조건부 가정" 라벨 강제(02 §5).
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.simulate._types import BvarFit
from dartlab.macro.simulate.fan import _Z, _meanPath, companionMA

# 정책금리 충격 프리셋(Python·TS 공유 상수). deltaPath = 정책 변수(level) baseline 대비 편차(%p).
# 조건 horizon = len(deltaPath). 최소 2종(declutter) — 긴축 held + 완화 누적.
SCENARIO_PRESETS: tuple[dict, ...] = (
    {
        "key": "tighten",
        "labelKr": "긴축 +100bp",
        "labelEn": "Tightening +100bp",
        "condLabelKr": "정책금리 +100bp · 6M",
        "condLabelEn": "policy +100bp · 6M",
        "deltaPath": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    },
    {
        "key": "ease",
        "labelKr": "완화 −150bp",
        "labelEn": "Easing −150bp",
        "condLabelKr": "정책금리 −25bp/월 · 6M",
        "condLabelEn": "policy −25bp/mo · 6M",
        "deltaPath": [-0.25, -0.5, -0.75, -1.0, -1.25, -1.5],
    },
)


def _stackedCov(fit: BvarFit, horizon: int) -> np.ndarray:
    """(H·n, H·n) 누적 예측오차 공분산 Ω. 블록(a,b) = Σ_{j=0}^{min(a,b)} Φ_j Σ Φ_{j+|b−a|}'."""
    coefs = companionMA(fit, horizon)
    sigma = fit.sigmaHat
    n = fit.n
    hn = horizon * n
    omega = np.zeros((hn, hn))
    for a in range(horizon):
        for b in range(a, horizon):
            d = b - a
            block = np.zeros((n, n))
            for j in range(a + 1):
                block = block + coefs[j] @ sigma @ coefs[j + d].T
            omega[a * n : (a + 1) * n, b * n : (b + 1) * n] = block
            if a != b:
                omega[b * n : (b + 1) * n, a * n : (a + 1) * n] = block.T
    return omega


def conditionalPath(
    fit: BvarFit,
    history: np.ndarray,
    condIdx: int,
    condDeltas,
    horizon: int = 12,
    quantiles: tuple[int, ...] = (5, 25, 50, 75, 95),
) -> dict:
    """정책 변수(condIdx)를 baseline+condDeltas 경로로 고정한 조건부 forward 분위 경로.

    Args:
        fit: BVAR 적합.
        history: (>=p, n) 정상성 변환 패널 최근값(끝이 최신).
        condIdx: 고정할 변수 인덱스(보통 정책금리).
        condDeltas: 조건 horizon 의 baseline 대비 편차 경로(길이 m ≤ horizon).
        horizon: 예측 개월.
        quantiles: 산출 분위(%). _Z 키 부분집합.

    Returns:
        dict[label → {transform, label, seriesId, mean, q5.., level_q5..(logdiff100)}] — forwardFan 동형.
    """
    n = fit.n
    mean = _meanPath(fit, history, horizon)  # (H, n)
    omega = _stackedCov(fit, horizon)  # (H·n, H·n)
    m = min(len(condDeltas), horizon)
    muStack = mean.reshape(-1)  # (h,i) → h*n+i
    rsel = np.zeros((m, horizon * n))
    for a in range(m):
        rsel[a, a * n + condIdx] = 1.0
    resid = np.asarray(condDeltas[:m], float)  # z − Rμ = (mean[:,condIdx]+δ) − mean[:,condIdx] = δ
    omRt = omega @ rsel.T  # (H·n, m)
    rOmRt = rsel @ omRt  # (m, m)
    gain = omRt @ np.linalg.inv(rOmRt)  # (H·n, m)
    muCond = muStack + gain @ resid
    omCond = omega - gain @ (rsel @ omega)
    condMean = muCond.reshape(horizon, n)
    condSE = np.sqrt(np.maximum(np.diag(omCond).reshape(horizon, n), 0.0))

    out: dict = {}
    for i, spec in enumerate(fit.specs):
        rec: dict = {"transform": spec.transform, "label": spec.label, "seriesId": spec.seriesId}
        rec["mean"] = condMean[:, i].tolist()
        for q in quantiles:
            rec[f"q{q}"] = (condMean[:, i] + _Z[q] * condSE[:, i]).tolist()
        if spec.transform == "logdiff100":
            lvl0 = float(fit.lastLevels[i])
            for q in quantiles:
                g = np.array(rec[f"q{q}"]) / 100.0
                rec[f"level_q{q}"] = (lvl0 * np.exp(np.cumsum(g))).tolist()
        out[spec.label] = rec
    return out


def buildScenarios(fit: BvarFit, history: np.ndarray, condIdx: int, horizon: int = 12) -> list[dict]:
    """SCENARIO_PRESETS 전체를 조건부 경로로 산출 → 리스트(다이얼로그 overlay 소비)."""
    out: list[dict] = []
    for preset in SCENARIO_PRESETS:
        fan = conditionalPath(fit, history, condIdx, preset["deltaPath"], horizon=horizon)
        out.append(
            {
                "key": preset["key"],
                "label": preset["labelKr"],
                "labelEn": preset["labelEn"],
                "condLabel": preset["condLabelKr"],
                "condLabelEn": preset["condLabelEn"],
                "condVar": fit.specs[condIdx].label,
                "fan": fan,
            }
        )
    return out
