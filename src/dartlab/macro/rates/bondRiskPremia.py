"""Cochrane-Piazzesi (2005) Bond Risk Premia Factor.

선도금리의 tent-shaped 선형 결합 → 단일 팩터.
이 팩터로 2-5년 만기 채권의 초과수익률을 R²=0.44로 예측.
경기역행적: 불황기에 팩터 상승 → 기대 초과수익 상승 → 채권 매수 기회.

Cochrane & Piazzesi (2005) "Bond Risk Premia", AER.
계수: Table 2 (1964-2003, annual data).
"""

from __future__ import annotations

import math

# CP (2005) Table 2 계수 — 1Y~5Y 선도금리에 대한 가중치
# tent-shaped: 중간 만기(3Y)에서 최대, 양쪽으로 하락
_CP_GAMMA = [-2.14, 0.81, 3.00, 0.80, -2.08]
_CP_INTERCEPT = -3.38  # 상수항


def forwardRatesFromSpot(spotRates: dict[int, float]) -> list[float]:
    """현물 수익률 → 1Y~5Y 선도금리 계산.

    Capabilities:
        무이표채 현물 수익률 (1Y~5Y) → 1Y forward rate 시리즈 [f(0,1) ~ f(4,5)].
        Cochrane-Piazzesi (2005) factor 입력 사전 단계. 단순 산식 f(n-1,n) =
        n×y(n) - (n-1)×y(n-1).

    Args:
        spotRates: 만기 → 수익률 (%) dict (최소 {1, 2, 3, 4, 5}).

    Returns:
        list[float] — [f(0,1), f(1,2), f(2,3), f(3,4), f(4,5)] 5 개 forward (%).

    Example:
        >>> forwardRatesFromSpot({1: 4.5, 2: 4.3, 3: 4.1, 4: 4.0, 5: 3.95})
        [4.5, 4.1, 3.7, 3.7, 3.75]

    Guide:
        forward 시리즈 tent-shaped (중간 만기 peak) 일 때 CP factor 활성.
        spotRates 5 개 모두 필요 — 결측은 보간 후 호출.

    When:
        ``cochranePiazzesiFactor`` 사전 단계 + AI yield curve 분해 답변.

    How:
        n=1: f = spot[1]. n>1: f(n-1,n) = n*spot[n] - (n-1)*spot[n-1].

    Requires:
        spotRates dict — 1~5 년 yield (FRED DGS1~DGS5).

    Raises:
        KeyError — 1~5 년 키 누락.

    See Also:
        - cochranePiazzesiFactor : CP factor 본체
        - nelsonSiegel : 곡선 분해 (대안)

    AIContext:
        forward[2] (1Y~2Y) - spot[1] = 1Y 후 1Y 시장 예상 인용.

    LLM Specifications:
        AntiPatterns:
            - spot 5 개 미만 입력 (KeyError)
            - bp 단위 입력 (％ 가 정상)
        OutputSchema:
            list[float] length 5.
        Prerequisites: 1~5 년 spot yield.
        Freshness: 일간 (FRED DGS).
        Dataflow: spot → 산식 → forward list.
        TargetMarkets: US (FRED DGS 풀세트). KR/JP 가능.
    """
    forwards = []
    for n in range(1, 6):
        if n == 1:
            forwards.append(spotRates[1])
        else:
            y_n = spotRates[n]
            y_n1 = spotRates[n - 1]
            # f(n-1, n) = n*y(n) - (n-1)*y(n-1)
            fwd = n * y_n - (n - 1) * y_n1
            forwards.append(fwd)
    return forwards


def cochranePiazzesiFactor(forwardRates: list[float]) -> dict:
    """CP 단일 팩터 계산 + 해석.

    Capabilities:
        Cochrane-Piazzesi (2005 AER) Bond Risk Premia 단일 팩터 — 5 개 forward
        rate 의 tent-shaped (γ = -2.14, 0.81, 3.00, 0.80, -2.08) 선형 결합 →
        2-5Y 채권 초과수익률 R²=0.44 예측. 4 zone (high/normal/low/negative).

    Args:
        forwardRates: 1Y~5Y forward 리스트 (forwardRatesFromSpot 출력).

    Returns:
        dict — cpFactor/expectedExcessReturn(%p, 연율)/zone(high/normal/low/
        negative)/zoneLabel/description.

    Example:
        >>> r = cochranePiazzesiFactor([4.5, 4.1, 3.7, 3.7, 3.75])
        >>> r["zone"]
        'normal'

    Guide:
        cpFactor > 2.0 = 채권 초과수익 강한 신호 (장기채 매수 유리, 경기 우려
        반영). 경기역행적 — 불황기에 상승.

    When:
        ``analyzeRates`` 내부 (US 만) + AI 채권 답변.

    How:
        cp = intercept + Σ γ_i × forward_i (i=1..5). 임계 매핑.

    Requires:
        forwardRatesFromSpot 5 개 출력. None/NaN 포함 시 빈 dict.

    Raises:
        없음 — 5 개 미만이면 빈 dict.

    See Also:
        - forwardRatesFromSpot : forward 사전 계산
        - decomposeLongRate : DKW 분해
        - termPremium (ACM) : 대안 텀프리미엄

    AIContext:
        zoneLabel + expectedExcessReturn 인용으로 "CP factor +2.3%p (높음) —
        채권 매수 유리" 답변.

    LLM Specifications:
        AntiPatterns:
            - cp 절대값 단정 + zone 미노출
            - 5 개 미만 forward 입력
            - 계수 임의 변경 (Table 2 표준)
        OutputSchema:
            ``{cpFactor, expectedExcessReturn, zone, zoneLabel, description}``.
        Prerequisites: 5 forward rates (DGS 5 년).
        Freshness: 일간.
        Dataflow: forward → 선형 결합 → 임계 → zone.
        TargetMarkets: US 한정 (계수). KR/JP 데이터로 재추정 필요.
    """
    if len(forwardRates) < 5:
        return {}

    # CP factor = intercept + γ₁f₁ + γ₂f₂ + γ₃f₃ + γ₄f₄ + γ₅f₅
    cp = _CP_INTERCEPT
    for gamma, fwd in zip(_CP_GAMMA, forwardRates[:5]):
        if fwd is None or math.isnan(fwd):
            return {}
        cp += gamma * fwd

    # CP factor ≈ 기대 초과수익률 (%p, 연율)
    # 양수 = 채권 초과수익 기대, 음수 = 채권 불리
    if cp > 2.0:
        zone, zone_label = "high", "높음"
        desc = "채권 기대초과수익 높음 — 장기채 매수 유리 (경기 우려 반영)"
    elif cp > 0.5:
        zone, zone_label = "normal", "보통"
        desc = "채권 기대초과수익 정상 범위"
    elif cp > -0.5:
        zone, zone_label = "low", "낮음"
        desc = "채권 기대초과수익 낮음 — 장기채 초과수익 제한적"
    else:
        zone, zone_label = "negative", "음수"
        desc = "채권 기대초과수익 음수 — 장기채 underweight"

    return {
        "cpFactor": round(cp, 3),
        "expectedExcessReturn": round(cp, 2),
        "zone": zone,
        "zoneLabel": zone_label,
        "description": desc,
    }
