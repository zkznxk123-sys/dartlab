"""금융환경지수(Financial Conditions Index) — GS 방식 5변수 z-score.

순수 데이터 + 판정 함수. numpy만 사용.
core/ 계층 소속 — macro/liquidity에서 소비.

학술 근거:
- Hatzius et al. (2010): "Financial Conditions Indexes: A Fresh Look"
- Goldman Sachs FCI: 5변수 GDP 임팩트 가중치
- Chicago Fed NFCI: 105변수 DFM (FRED에서 직접 소비 가능)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FCIResult:
    """금융환경지수 결과."""

    value: float  # FCI 값 (양수=긴축, 음수=완화. NFCI와 동일 부호)
    regime: str  # "tight" | "neutral" | "loose"
    regimeLabel: str  # "긴축" | "중립" | "완화"
    components: dict[str, float]  # 개별 변수 z-score
    description: str


# GS FCI 방식 가중치 — GDP impulse response 기반
# Hatzius et al. (2010) Table 3: 1-year GDP impact per 100bp shock
# 원본 GS 추정: short_rate 0.25, long_rate 0.20, credit 0.30, equity 0.15, fx 0.10
# 합계 1.0으로 정규화. GS 논문은 impulse response 크기로 가중치 결정.
# 이전 값 [0.35, 0.15, 0.25, 0.15, 0.10]에서 논문 기반으로 교정.
_WEIGHTS_US = {
    "policy_rate": 0.25,  # Hatzius: 정책금리 100bp → GDP -0.5%p
    "long_rate": 0.20,  # Hatzius: 장기금리 100bp → GDP -0.4%p
    "credit_spread": 0.30,  # Hatzius: 스프레드 100bp → GDP -0.6%p (가장 큰 영향)
    "equity": 0.15,  # Hatzius: S&P -10% → GDP -0.3%p
    "fx": 0.10,  # Hatzius: USD +10% → GDP -0.2%p
}

# 한국 FCI — 개방경제 특성 반영 (수출 비중 50%+ → 환율 영향 확대)
_WEIGHTS_KR = {
    "policy_rate": 0.25,
    "long_rate": 0.20,
    "credit_spread": 0.25,
    "equity": 0.15,
    "fx": 0.15,  # 한국은 환율 영향 더 큼 (수출 의존)
}


def calcFCI(
    variables: dict[str, list[float]],
    *,
    market: str = "US",
) -> FCIResult:
    """금융환경지수 계산 — 5변수 z-score 가중 합산.

    Capabilities:
        5 변수 (정책금리/장기금리/신용스프레드/주가/환율) 시계열을 24+ 개월
        z-score 표준화 → 시장별 (US/KR) 가중치 합산 → FCI 값 + 3 zone
        (tight/neutral/loose). Chicago Fed NFCI 의 단순 자체 구현.

    Args:
        variables: 변수별 시계열 list (최근 24+ 개월). 키: policy_rate/long_rate/
            credit_spread/equity (YoY%)/fx.
        market: ``"US"`` | ``"KR"``.

    Returns:
        FCIResult — value/regime(tight/neutral/loose)/regimeLabel/components
        (z-score per 변수)/description.

    Example:
        >>> r = calcFCI({"policy_rate": [...], "credit_spread": [...]})
        >>> r.regime, r.value
        ('tight', 0.85)

    Guide:
        |value| > 0.5 = 의미 있는 편차. components 의 가장 큰 양수 z 가 dominant
        긴축 요인. NFCI 와 동시 인용 시 정합성 검증.

    When:
        ``analyzeCrisis`` 내부 + AI 금융 환경 답변.

    How:
        각 변수 시계열 → z-score 표준화 → equity 부호 반전 → 시장별 가중 평균.

    Requires:
        24+ 개월 시계열 (5 변수 모두). 부분 입력도 동작 (가중치 정규화).

    Raises:
        없음 — 데이터 부족 시 "데이터부족" regime 반환.

    See Also:
        - calcLiquidity : NFCI + FCI 동시 노출
        - classifyLiquidityRegime : 표준 라벨

    AIContext:
        regime + value + dominant component 인용으로 "FCI +0.85 (긴축),
        신용스프레드가 주도" 답변.

    LLM Specifications:
        AntiPatterns:
            - 시계열 6 개월 미만 입력 (24+ 권장)
            - market="US" 변수에 KR 가중치 적용
            - components 미노출 (dominant 인용 불가)
        OutputSchema:
            FCIResult ``(value, regime, regimeLabel, components, description)``.
        Prerequisites: 5 변수 월별 시계열.
        Freshness: 일간 (yield/spread/equity/fx) ~ 월간 (policy rate).
        Dataflow: variables → z-score → 가중 합 → regime.
        TargetMarkets: US, KR (가중치 다름).
    """
    weights = _WEIGHTS_US if market.upper() == "US" else _WEIGHTS_KR
    components: dict[str, float] = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for key, weight in weights.items():
        series = variables.get(key)
        if series is None or len(series) < 6:
            continue

        arr = np.array(series, dtype=np.float64)
        arr = arr[~np.isnan(arr)]
        if len(arr) < 6:
            continue

        mean = float(np.mean(arr))
        std = float(np.std(arr))
        if std < 1e-10:
            continue

        current = float(arr[-1])
        z = (current - mean) / std

        # 주가는 역수: 주가 하락 = 긴축(양수)
        if key == "equity":
            z = -z

        components[key] = round(z, 3)
        weighted_sum += z * weight
        total_weight += weight

    if total_weight == 0:
        return FCIResult(0.0, "neutral", "데이터부족", {}, "FCI 계산 불가")

    fci = weighted_sum / total_weight

    if fci > 0.5:
        regime, label = "tight", "긴축"
        desc = f"FCI {fci:+.2f} — 금융환경 긴축"
    elif fci < -0.5:
        regime, label = "loose", "완화"
        desc = f"FCI {fci:+.2f} — 금융환경 완화"
    else:
        regime, label = "neutral", "중립"
        desc = f"FCI {fci:+.2f} — 금융환경 중립"

    return FCIResult(
        value=round(fci, 3),
        regime=regime,
        regimeLabel=label,
        components=components,
        description=desc,
    )
