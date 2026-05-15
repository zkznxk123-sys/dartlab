"""predictionSignals 작은 헬퍼 — clamp · 방향 스코어 매핑 · 베이즈 보정/업데이트.

analysis/financial/predictionSignals.py 가 2650 줄 god module 이라 단계적 분리.
identity 보존을 위해 predictionSignals.py 가 본 모듈에서 re-export.

상수:
- DIRECTION_SCORES — 방향 라벨 → 점수 (-1.0 ~ 1.0)

함수:
- clamp(v, lo, hi) — 범위 클램핑
- calibrate(rawPosterior) — 베이즈 사후확률 실측 캘리브레이션
- bayesUpdate(prior, evidence, damping) — 감쇠 적용 사후확률 갱신
"""

from __future__ import annotations

DIRECTION_SCORES = {
    "up": 1.0,
    "accelerating": 1.0,
    "bullish": 1.0,
    "positive": 0.5,
    "flat": 0.0,
    "stable": 0.0,
    "neutral": 0.0,
    "down": -1.0,
    "decelerating": -0.5,
    "bearish": -1.0,
    "negative": -0.5,
    "reversing": 0.0,
    "transitioning": -0.2,
    "volatile": -0.5,
}


def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """값을 [lo, hi] 범위로 클램핑."""
    return max(lo, min(hi, v))


def calibrate(rawPosterior: float) -> float:
    """원시 베이즈 확률을 실측 기반으로 재보정.

    walk-forward 564건 캘리브레이션 결과:
    - 원시 78% → 실측 62%
    - 원시 83% → 실측 73%
    - 원시 86% → 실측 88%

    선형 보간으로 과신 제거. 원시 확률이 높을수록 실측에 가깝게 보정.
    """
    base = 0.72  # 모멘텀 기저 정확도
    shrinkage = 0.6  # 60%만 반영
    calibrated = base + (rawPosterior - base) * shrinkage
    return max(0.50, min(0.95, calibrated))


def bayesUpdate(prior: float, evidence: float, damping: float = 0.3) -> float:
    """베이즈 사후확률 갱신 (감쇠 적용).

    Args:
        prior: 현재 P(매출↑)
        evidence: P(매출↑ | 이 신호)
        damping: 갱신 강도 감쇠 (0~1). 1.0 = 완전 갱신, 0.3 = 30% 갱신.
            신호 간 독립성 가정 위반을 보정. 0.3이 과신 방지 + 변별력 유지의 균형.

    나이브 베이즈 + 감쇠: lr^damping
    """
    if evidence <= 0 or evidence >= 1:
        return prior
    lr = evidence / (1 - evidence)
    lr_damped = lr**damping
    prior_odds = prior / (1 - prior)
    posterior_odds = prior_odds * lr_damped
    return posterior_odds / (1 + posterior_odds)


# 옛 이름 (private prefix) — BC 보존용
_DIRECTION_SCORES = DIRECTION_SCORES
_clamp = clamp
_calibrate = calibrate
_bayesUpdate = bayesUpdate


__all__ = [
    "DIRECTION_SCORES",
    "bayesUpdate",
    "calibrate",
    "clamp",
]
