"""regimeSwitching 의 LEI 모듈 — Cleveland Fed probit + Conference Board LEI + SahmRule."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

# ══════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════


@dataclass(frozen=True)
class RecessionProb:
    """침체 확률 (Cleveland Fed 프로빗)."""

    probability: float  # 0.0~1.0
    zone: str  # "low" | "moderate" | "elevated" | "high"
    zoneLabel: str  # "낮음" | "보통" | "경계" | "높음"
    spread: float  # 입력 스프레드 값
    description: str


@dataclass(frozen=True)
class LEIResult:
    """Conference Board LEI 결과."""

    level: float  # LEI 합성 지수 값
    mom: float  # 전월 대비 변화
    mom6m: float | None  # 6개월 연율 변화
    signal: str  # "expansion" | "caution" | "recession_warning"
    signalLabel: str  # "확장" | "경계" | "침체경고"
    components: dict[str, float | None]  # 10개 구성요소
    description: str


# ══════════════════════════════════════
# Cleveland Fed 프로빗 모델
# ══════════════════════════════════════


def _normalCdf(x: float) -> float:
    """표준정규분포 누적분포함수 (scipy 없이 구현)."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def clevelandProbit(spread10y3m: float) -> RecessionProb:
    """Cleveland Fed 프로빗: 10Y-3M 스프레드 → 12개월 내 침체 확률.

    Capabilities:
        Estrella-Mishkin (1996) 기반 Cleveland Fed 공표 probit 모델 — α=-0.5333,
        β=-0.6330. P(recession) = Φ(α + β × spread). 12 개월 내 침체 확률을
        4 zone (low/moderate/elevated/high) 으로 매핑.

    Args:
        spread10y3m: 10Y - 3M 스프레드 (%p). 음수 = 역전.

    Returns:
        RecessionProb — probability(0~1)/zone/zoneLabel/spread/description.

    Example:
        >>> r = clevelandProbit(-0.5)
        >>> r.zone, round(r.probability, 2)
        ('elevated', 0.42)

    Guide:
        zone "elevated" (≥ 30%) = 12 개월 침체 경계. "high" (≥ 50%) = 침체 강한
        신호. 역전 (spread < 0) 4 개월 지속 시 추가 매크로 검증 권장.

    When:
        ``analyzeForecast`` 내부 + AI 침체 확률 답변 1 차.

    How:
        z = α + β × spread → Φ (normal CDF erf 구현) → probability → zone 라벨.

    Requires:
        FRED T10Y3M (또는 DGS10 - DGS3MO).

    Raises:
        없음.

    See Also:
        - sahmRule : 실업률 단순 룰
        - hamiltonRegime : Markov regime
        - conferenceBoardLEI : LEI 합성

    AIContext:
        probability × 100 + zoneLabel 인용으로 "침체 확률 42% (경계)" 답변.

    LLM Specifications:
        AntiPatterns:
            - spread 부호만 단정 (probability 계산 필요)
            - T10Y2Y 대체 사용 (계수 다름)
        OutputSchema:
            RecessionProb ``(probability, zone, zoneLabel, spread, description)``.
        Prerequisites: T10Y3M latest.
        Freshness: 일간.
        Dataflow: spread → probit → probability → zone.
        TargetMarkets: US 한정 (계수). KR 미지원.
    """
    alpha = -0.5333
    beta = -0.6330
    z = alpha + beta * spread10y3m
    prob = _normalCdf(z)

    if prob < 0.15:
        zone, zone_label = "low", "낮음"
    elif prob < 0.30:
        zone, zone_label = "moderate", "보통"
    elif prob < 0.50:
        zone, zone_label = "elevated", "경계"
    else:
        zone, zone_label = "high", "높음"

    desc = f"12개월 내 침체 확률 {prob * 100:.1f}% (10Y-3M 스프레드 {spread10y3m:+.2f}%p)"

    return RecessionProb(
        probability=round(prob, 4),
        zone=zone,
        zoneLabel=zone_label,
        spread=round(spread10y3m, 3),
        description=desc,
    )


# ══════════════════════════════════════
# Conference Board LEI
# ══════════════════════════════════════

# Conference Board 공표 가중치 (2023 기준)
_LEI_WEIGHTS: dict[str, float] = {
    "avg_weekly_hours": 0.2772,
    "initial_claims": 0.0314,  # 역수 사용
    "new_orders_consumer": 0.0505,
    "ism_new_orders": 0.0948,
    "new_orders_nondefense_cap": 0.0139,
    "building_permits": 0.0207,
    "sp500": 0.0381,
    "leading_credit": 0.3585,
    "term_spread": 0.1068,
    "consumer_expectations": 0.0081,
}


def conferenceBoardLEI(
    components: dict[str, float | None],
    prevLevel: float | None = None,
    prevLevel6m: float | None = None,
) -> LEIResult:
    """Conference Board LEI 복제.

    Capabilities:
        Conference Board 10 구성요소 (가중치 2023 공표값) 가중 합산 → LEI level
        + MoM + 6 개월 연율 변화 + 신호 (expansion/caution/recession_warning).
        침체 룰: 6 개월 연율 < -4.4% AND 5+ 구성요소 하락.

    Args:
        components: 10 구성요소 dict (avg_weekly_hours/initial_claims(역수)/
            new_orders_consumer/ism_new_orders/new_orders_nondefense_cap/
            building_permits/sp500/leading_credit/term_spread/
            consumer_expectations). None 허용 (부분 weight 정규화).
        prevLevel: 이전 LEI level.
        prevLevel6m: 6 개월 전 LEI level.

    Returns:
        LEIResult — level/mom/mom6m/signal/signalLabel/components/description.

    Example:
        >>> r = conferenceBoardLEI({"sp500": 0.5, ...}, prevLevel=100)
        >>> r.signal
        'expansion'

    Guide:
        signal "recession_warning" = Conference Board 공식 침체 룰 (6 개월 연율
        < -4.4% + 5 개+ 하락) 동시 충족 시.

    When:
        ``analyzeForecast`` 내부 + AI 경기선행 답변.

    How:
        가중 합산 (부분 데이터 정규화) → level → MoM + 6M 연율 → 룰 매칭.

    Requires:
        FRED 10 시리즈 (AWHMAN/ICSA/UMCSENT/NAPM/NEWORDER/PERMIT/SP500/
        T10Y3M 등) 중 1+.

    Raises:
        없음 — 데이터 부족 시 "데이터부족" 신호.

    See Also:
        - clevelandProbit : 단변량 yield curve
        - sahmRule : 실업률 단순 룰
        - hamiltonRegime : Markov

    AIContext:
        signalLabel + mom6m + declining 카운트 인용으로 한 단락 답변.

    LLM Specifications:
        AntiPatterns:
            - components 부분 입력 후 level 절대값 단정
            - signal 만 인용 + mom6m 미노출
        OutputSchema:
            LEIResult (7 필드).
        Prerequisites: 10 구성요소 시리즈 중 일부.
        Freshness: 월간 (Conference Board 발표).
        Dataflow: components → 가중합 → MoM + 6M 연율 → 신호.
        TargetMarkets: US 한정. KR 미지원.
    """
    weighted_sum = 0.0
    available = 0

    for key, weight in _LEI_WEIGHTS.items():
        val = components.get(key)
        if val is not None:
            weighted_sum += val * weight
            available += 1

    if available == 0:
        return LEIResult(
            level=0.0,
            mom=0.0,
            mom6m=None,
            signal="caution",
            signalLabel="데이터부족",
            components=components,
            description="LEI 구성요소 데이터 부족",
        )

    # 부분 구성요소일 때 비례 조정
    total_weight = sum(w for k, w in _LEI_WEIGHTS.items() if components.get(k) is not None)
    if total_weight > 0:
        level = weighted_sum / total_weight * 100  # 정규화
    else:
        level = weighted_sum * 100

    mom = level - prevLevel if prevLevel is not None else 0.0
    mom6m = None
    if prevLevel6m is not None and prevLevel6m != 0:
        mom6m = ((level / prevLevel6m) ** 2 - 1) * 100  # 6개월 연율

    # 신호 판별 (Conference Board 기준)
    # 6개월 연율 < -4.4% AND 5개 이상 구성요소 하락 → 침체경고
    declining = sum(1 for v in components.values() if v is not None and v < 0)
    if mom6m is not None and mom6m < -4.4 and declining >= 5:
        signal, signal_label = "recession_warning", "침체경고"
        desc = f"LEI 6개월 연율 {mom6m:.1f}% + {declining}개 구성요소 하락 → 침체 경고"
    elif mom < -0.1 or (mom6m is not None and mom6m < 0):
        signal, signal_label = "caution", "경계"
        desc = f"LEI 전월비 {mom:+.2f}, 경기 둔화 징후"
    else:
        signal, signal_label = "expansion", "확장"
        desc = f"LEI 전월비 {mom:+.2f}, 경기 확장 지속"

    return LEIResult(
        level=round(level, 2),
        mom=round(mom, 3),
        mom6m=round(mom6m, 2) if mom6m is not None else None,
        signal=signal,
        signalLabel=signal_label,
        components=components,
        description=desc,
    )


# ══════════════════════════════════════
# Sahm Rule (2019)
# ══════════════════════════════════════


@dataclass(frozen=True)
class SahmResult:
    """Sahm Rule 침체 지표."""

    value: float  # Sahm 지표 값 (%p)
    triggered: bool  # >= 0.5이면 침체 신호
    zone: str  # "normal" | "warning" | "recession"
    zoneLabel: str  # "정상" | "경고" | "침체"
    description: str


def sahmRule(unemploymentSeries: list[float]) -> SahmResult:
    """Sahm Rule: 실업률 3개월 MA - 12개월 최저 3개월 MA.

    Capabilities:
        Sahm Rule (2019) 침체 시작 룰 — 실업률 3 개월 평균 - 직전 12 개월 내
        3 개월 평균 최저값 ≥ 0.5%p 면 침체 신호 (역사적 100% 정확). 3 zone
        (normal/warning/recession) 매핑.

    Args:
        unemploymentSeries: 월간 실업률 (%) 시계열 (≥ 15 개월).

    Returns:
        SahmResult — value(%p)/triggered(bool)/zone/zoneLabel/description.

    Example:
        >>> r = sahmRule([3.5]*12 + [3.7, 4.0, 4.1])
        >>> r.triggered, r.zone
        (True, 'recession')

    Guide:
        triggered=True 면 침체 강한 신호 (Sahm 본인은 ≥ 0.5 임계 절대 신뢰).
        warning (0.3~0.5) = 침체 접근 중.

    When:
        ``analyzeForecast`` 내부 + AI 침체 시작 답변.

    How:
        최근 3 개월 평균 - 직전 12 개월 중 3 개월 평균 최저값.

    Requires:
        FRED UNRATE 월별 ≥ 15 개월.

    Raises:
        없음 — 데이터 부족 시 0 값 + "데이터부족" 라벨.

    See Also:
        - clevelandProbit : yield curve
        - conferenceBoardLEI : 10 구성요소
        - unemploymentBounceToRecession : 0.3%p 변형

    AIContext:
        value + zoneLabel 인용으로 "Sahm 0.55%p (침체 발동)" 답변.

    LLM Specifications:
        AntiPatterns:
            - 단일 월 실업률 단정 (3 개월 MA 가 표준)
            - 15 개월 미만에 강한 단정
        OutputSchema:
            SahmResult ``(value, triggered, zone, zoneLabel, description)``.
        Prerequisites: UNRATE 월별 ≥ 15.
        Freshness: 월간 (BLS 첫 금요일).
        Dataflow: series → 3M MA → 12M 최저 → 차.
        TargetMarkets: US 한정 (계수 검증). KR 미지원.
    """
    if len(unemploymentSeries) < 15:
        return SahmResult(0.0, False, "normal", "데이터부족", "실업률 시계열 15개월 미만")

    # 3개월 이동평균
    ma3_current = sum(unemploymentSeries[-3:]) / 3
    # 12개월 내 3개월 MA 최저점
    ma3_min = min(
        sum(unemploymentSeries[i : i + 3]) / 3 for i in range(len(unemploymentSeries) - 15, len(unemploymentSeries) - 2)
    )

    sahm = ma3_current - ma3_min

    if sahm >= 0.5:
        return SahmResult(round(sahm, 2), True, "recession", "침체", f"Sahm {sahm:.2f}%p ≥ 0.5 — 침체 신호 발동")
    elif sahm >= 0.3:
        return SahmResult(round(sahm, 2), False, "warning", "경고", f"Sahm {sahm:.2f}%p — 침체 접근 중")
    else:
        return SahmResult(round(sahm, 2), False, "normal", "정상", f"Sahm {sahm:.2f}%p — 정상")


# ══════════════════════════════════════
# Hamilton Regime Switching (1989)
# numpy 직접 구현 — 외부 의존성 없음
# ══════════════════════════════════════
