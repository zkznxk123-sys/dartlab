"""sentiment.py 고용·인플레·지역 시그널 분리 — Employment/Inflation/ISM/KR.

sentiment.py 655 줄 분할. interpretEmployment (59) + interpretInflation (71) +
ISMAllocationSignal + ismAssetAllocation (40) + KRInflationEstimate + krInflationModel
(42) 약 234 줄. sentiment.py 의 facade (calcFearGreedProxy · estimateRateExpectation
· calcSentiment) 책임 유지.

BC: sentiment 모듈에서 모든 심볼 import 가능 (re-export).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.macro.cycles.sentiment import EmploymentSignal, InflationSignal

# 본 모듈은 sentiment 의 dataclass 두 종을 참조하나, 순환 import 회피로 함수 본문에서
# lazy import 한다. annotation 은 TYPE_CHECKING 블록만으로 충분.


def interpretEmployment(
    unrate: float,
    payrolls3mAvg: float | None = None,
) -> EmploymentSignal:
    """고용 지표 해석.

    Capabilities:
        실업률 + 비농업고용 3 개월 평균을 가중 score 화 → 고용 상태 4 단계
        (strong/moderate/weakening/weak) + 한글 라벨 + reasoning lines. sentiment
        엔진 employment 축이 직접 호출.

    Args:
        unrate: 실업률 (%).
        payrolls3mAvg: 비농업고용 3 개월 평균 변화 (천명). None 가능.

    Returns:
        EmploymentSignal(state, stateLabel, reasoning).

    Example:
        >>> r = interpretEmployment(3.7, 200)
        >>> r.state, r.stateLabel
        ('strong', '강함')

    Guide:
        실업률 < 4% = 완전고용. payrolls 3M 평균 ±100K 가 강세/둔화 경계.

    When:
        ``calcSentiment`` 내부 employment 축. AI 고용 시장 답변.

    How:
        실업률 4 구간 + payrolls 4 구간 별 score (±1~2) 누적 → ≥3=strong,
        ≥1=moderate, ≥-1=weakening, 그 외 weak.

    Requires:
        unrate (%). payrolls 옵션.

    Raises:
        없음.

    See Also:
        - interpretInflation : 인플레 축 (sentiment 의 쌍축)
        - calcSentiment : sentiment 종합

    AIContext:
        stateLabel 인용 + reasoning 1~2 줄 노출 = 한 문장 답변 완성.

    LLM Specifications:
        AntiPatterns:
            - 실업률만 보고 강세 단정 — payrolls 둔화면 weakening 가능
            - payrolls3mAvg 음수 무시
        OutputSchema:
            EmploymentSignal ``(state, stateLabel, reasoning)``.
        Prerequisites: BLS UNRATE + PAYEMS.
        Freshness: 월간 (첫 금요일).
        Dataflow: unrate + payrolls → score → state 매핑.
        TargetMarkets: US (BLS). KR 미지원.
    """
    from dartlab.macro.cycles.sentiment import EmploymentSignal

    reasons: list[str] = []
    score = 0  # 양수=강함, 음수=약함

    if unrate < 4.0:
        score += 2
        reasons.append(f"실업률 {unrate:.1f}% — 완전고용 수준")
    elif unrate < 5.0:
        score += 1
        reasons.append(f"실업률 {unrate:.1f}% — 양호")
    elif unrate < 6.0:
        score -= 1
        reasons.append(f"실업률 {unrate:.1f}% — 약화")
    else:
        score -= 2
        reasons.append(f"실업률 {unrate:.1f}% — 고용 악화")

    if payrolls3mAvg is not None:
        if payrolls3mAvg > 200:
            score += 2
            reasons.append(f"고용 증가 3M평균 +{payrolls3mAvg:.0f}K — 강함")
        elif payrolls3mAvg > 100:
            score += 1
            reasons.append(f"고용 증가 3M평균 +{payrolls3mAvg:.0f}K — 적정")
        elif payrolls3mAvg > 0:
            reasons.append(f"고용 증가 3M평균 +{payrolls3mAvg:.0f}K — 둔화")
        else:
            score -= 2
            reasons.append(f"고용 감소 3M평균 {payrolls3mAvg:.0f}K — 경고")

    if score >= 3:
        state, label = "strong", "강함"
    elif score >= 1:
        state, label = "moderate", "보통"
    elif score >= -1:
        state, label = "weakening", "약화"
    else:
        state, label = "weak", "약함"

    return EmploymentSignal(state=state, stateLabel=label, reasoning=tuple(reasons))


# ══════════════════════════════════════
# 물가 해석
# ══════════════════════════════════════


def interpretInflation(
    cpiYoy: float,
    coreCpiYoy: float | None = None,
    bei5y: float | None = None,
    bei10y: float | None = None,
) -> InflationSignal:
    """물가 지표 해석.

    Capabilities:
        CPI YoY + Core CPI + 5/10Y BEI 를 heat score 로 합산 → 인플레 5 단계
        (hot/warm/target/cool/cold) + 한글 라벨. sentiment 엔진 inflation 축이
        직접 호출.

    Args:
        cpiYoy: CPI YoY (%).
        coreCpiYoy: Core CPI YoY (%). None 가능.
        bei5y: 5 년 BEI (%). None 가능.
        bei10y: 10 년 BEI (%). 현재 미사용 (확장 슬롯).

    Returns:
        InflationSignal(state, stateLabel, reasoning).

    Example:
        >>> r = interpretInflation(3.2, 3.0, 2.5)
        >>> r.state, r.stateLabel
        ('warm', '높음')

    Guide:
        CPI > 4% = 과열, < 0% = 디플레 우려. BEI 5Y > 2.8% = 기대인플레 상승.

    When:
        ``calcSentiment`` 내부 inflation 축. AI 물가 답변 1 차.

    How:
        CPI 5 구간 (heat ±2/±1) + Core CPI ±1 + BEI ±1 누적 → ≥3=hot, ≥1=warm,
        ≥-1=target, ≥-2=cool, 그 외 cold.

    Requires:
        cpiYoy (%). 나머지 옵션.

    Raises:
        없음.

    See Also:
        - interpretEmployment : 고용 축 (sentiment 의 쌍축)
        - rateOutlook : 인플레 + 고용 → 정책금리 방향

    AIContext:
        stateLabel 인용 + reasoning 1~2 줄 = 한 문장 답변.

    LLM Specifications:
        AntiPatterns:
            - CPI 단독 인용 + Core CPI 무시
            - 한국 CPI 에 미국 임계 (2%) 적용
            - BEI 누락한 채 hot 단정
        OutputSchema:
            InflationSignal ``(state, stateLabel, reasoning)``.
        Prerequisites: CPIAUCSL + CPILFESL + T5YIE.
        Freshness: 월간 (CPI 10 일 발표).
        Dataflow: CPI + Core + BEI → heat → state 매핑.
        TargetMarkets: US (BLS + FRED). KR 미지원 (krInflationModel 별도).
    """
    from dartlab.macro.cycles.sentiment import InflationSignal

    reasons: list[str] = []
    heat = 0  # 양수=과열, 음수=냉각

    if cpiYoy > 4.0:
        heat += 3
        reasons.append(f"CPI {cpiYoy:.1f}% — 인플레이션 과열")
    elif cpiYoy > 3.0:
        heat += 2
        reasons.append(f"CPI {cpiYoy:.1f}% — 목표 상회")
    elif cpiYoy > 1.5:
        reasons.append(f"CPI {cpiYoy:.1f}% — 목표 부근")
    elif cpiYoy > 0:
        heat -= 1
        reasons.append(f"CPI {cpiYoy:.1f}% — 둔화")
    else:
        heat -= 2
        reasons.append(f"CPI {cpiYoy:.1f}% — 디플레이션 우려")

    if coreCpiYoy is not None:
        if coreCpiYoy > 3.5:
            heat += 1
            reasons.append(f"Core CPI {coreCpiYoy:.1f}% — 기조적 인플레")
        elif coreCpiYoy < 2.0:
            heat -= 1
            reasons.append(f"Core CPI {coreCpiYoy:.1f}% — 기조 둔화")

    if bei5y is not None:
        if bei5y > 2.8:
            heat += 1
            reasons.append(f"5Y BEI {bei5y:.2f}% — 기대인플레 상승")
        elif bei5y < 1.8:
            heat -= 1
            reasons.append(f"5Y BEI {bei5y:.2f}% — 기대인플레 하락")

    if heat >= 3:
        state, label = "hot", "과열"
    elif heat >= 1:
        state, label = "warm", "높음"
    elif heat >= -1:
        state, label = "target", "목표부근"
    elif heat >= -2:
        state, label = "cool", "둔화"
    else:
        state, label = "cold", "디플레우려"

    return InflationSignal(state=state, stateLabel=label, reasoning=tuple(reasons))


# ══════════════════════════════════════
# ISM 자산배분 (투자전략 13)
# ══════════════════════════════════════


@dataclass(frozen=True)
class ISMAllocationSignal:
    """ISM 기반 글로벌 자산배분 신호."""

    ism: float
    stance: str  # "risk_on" | "neutral" | "risk_off"
    stanceLabel: str  # "위험자산 선호" | "중립" | "안전자산 선호"
    equityWeight: str  # "overweight" | "neutral" | "underweight"
    bondWeight: str  # "underweight" | "neutral" | "overweight"
    description: str


def ismAssetAllocation(ism: float) -> ISMAllocationSignal:
    """ISM PMI → 글로벌 자산배분 신호.

    투자전략 13: ISM지수가 세계 자산배분의 바로미터다.

    Example:
        >>> r = ismAssetAllocation(56)
        >>> r.stance, r.equityWeight
        ('risk_on', 'overweight')

    Requires:
        ISM PMI (FRED NAPM 또는 ISMPMI).

    Raises:
        없음 (실수 입력 시 산술 안전).
    """
    if ism >= 55:
        return ISMAllocationSignal(
            ism=round(ism, 1),
            stance="risk_on",
            stanceLabel="위험자산 선호",
            equityWeight="overweight",
            bondWeight="underweight",
            description=f"ISM {ism:.1f} ≥ 55 — 글로벌 위험자산 비중확대, 채권 축소",
        )
    elif ism >= 50:
        return ISMAllocationSignal(
            ism=round(ism, 1),
            stance="neutral",
            stanceLabel="중립",
            equityWeight="neutral",
            bondWeight="neutral",
            description=f"ISM {ism:.1f} (50-55) — 자산배분 중립, 방향 전환 주시",
        )
    else:
        return ISMAllocationSignal(
            ism=round(ism, 1),
            stance="risk_off",
            stanceLabel="안전자산 선호",
            equityWeight="underweight",
            bondWeight="overweight",
            description=f"ISM {ism:.1f} < 50 — 안전자산 선호, 주식 비중축소",
        )


# ══════════════════════════════════════
# 한국 물가 모델 (투자전략 18)
# ══════════════════════════════════════


@dataclass(frozen=True)
class KRInflationEstimate:
    """한국 물가 방향 추정."""

    fxEffect: float  # 환율 효과 (%)
    oilEffect: float  # 유가 효과 (%)
    combined: float  # 합산 물가 압력
    direction: str  # "upward" | "stable" | "downward"
    directionLabel: str  # "상승" | "안정" | "하락"
    description: str


def krInflationModel(fxYoy: float, oilYoy: float) -> KRInflationEstimate:
    """한국 물가 = 환율 + 유가 모델.

    Capabilities:
        한국은행 pass-through 계수 (환율 0.06, 유가 0.03) 로 USDKRW YoY + WTI
        YoY → 향후 CPI 방향 (upward/stable/downward) 추정. 투자전략 18 — 한국 물가
        흐름은 환율과 유가에 좌우.

    Args:
        fxYoy: USDKRW 전년대비 변화율 (%). 양수=원화 약세.
        oilYoy: WTI 유가 전년대비 변화율 (%).

    Returns:
        KRInflationEstimate(fxEffect, oilEffect, combined, direction,
        directionLabel, description).

    Example:
        >>> r = krInflationModel(8.0, 30.0)
        >>> r.direction, r.directionLabel
        ('upward', '상승')

    Guide:
        combined > 0.5 = 상승 압력, < -0.5 = 하락. 환율 약세 + 유가 상승 동반 시
        CPI 가속.

    When:
        ``calcSentiment`` market="KR" 내부 inflation 축. AI 한국 물가 답변.

    How:
        fxEffect = fxYoy × 0.06 + oilEffect = oilYoy × 0.03 → combined 합산 →
        ±0.5 임계로 direction.

    Requires:
        fxYoy (BOK USDKRW), oilYoy (FRED DCOILWTICO 또는 EIA).

    Raises:
        없음.

    See Also:
        - interpretInflation : 미국 CPI 축
        - calcSentiment : KR sentiment 종합 진입점

    AIContext:
        directionLabel + description 한 줄 인용으로 한국 물가 답변 완성.

    LLM Specifications:
        AntiPatterns:
            - 단일 변수 (FX 만) 로 CPI 단정 — 유가 동반 검토 필수
            - 한국 모델을 미국에 적용 — pass-through 계수 다름
            - bp 단위로 fxYoy 입력 (％ 가 정상)
        OutputSchema:
            KRInflationEstimate ``(fxEffect, oilEffect, combined, direction,
            directionLabel, description)``.
        Prerequisites: USDKRW YoY + WTI YoY.
        Freshness: USDKRW 일간, WTI 일간.
        Dataflow: fx + oil → effect → combined → direction.
        TargetMarkets: KR (한정).
    """
    # 실증적 pass-through 계수 (한국은행 연구: 환율 0.05~0.08, 유가 0.02~0.04)
    fx_effect = fxYoy * 0.06
    oil_effect = oilYoy * 0.03
    combined = fx_effect + oil_effect

    if combined > 0.5:
        direction = "upward"
        direction_label = "상승"
        desc = f"환율({fxYoy:+.1f}%) + 유가({oilYoy:+.1f}%) → 물가 상승 압력 {combined:+.1f}%p"
    elif combined < -0.5:
        direction = "downward"
        direction_label = "하락"
        desc = f"환율({fxYoy:+.1f}%) + 유가({oilYoy:+.1f}%) → 물가 하락 압력 {combined:+.1f}%p"
    else:
        direction = "stable"
        direction_label = "안정"
        desc = f"환율({fxYoy:+.1f}%) + 유가({oilYoy:+.1f}%) → 물가 안정 {combined:+.1f}%p"

    return KRInflationEstimate(
        fxEffect=round(fx_effect, 2),
        oilEffect=round(oil_effect, 2),
        combined=round(combined, 2),
        direction=direction,
        directionLabel=direction_label,
        description=desc,
    )
