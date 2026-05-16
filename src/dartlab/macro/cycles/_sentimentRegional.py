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

    Args:
        unrate: 실업률 (%)
        payrolls_3m_avg: 비농업고용 3개월 평균 변화 (천명)

    Returns:
        EmploymentSignal
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

    Args:
        cpi_yoy: CPI YoY (%)
        core_cpi_yoy: Core CPI YoY (%)
        bei_5y: 5년 BEI (%) — 기대인플레이션
        bei_10y: 10년 BEI (%) — 기대인플레이션

    Returns:
        InflationSignal
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

    투자전략 18: 우리나라 물가 흐름은 환율과 유가에 좌우된다.
    원/달러 상승(원화약세) → 수입물가 상승 → CPI 상승.
    유가 상승 → 에너지/운송비 상승 → CPI 상승.

    Args:
        fxYoy: USDKRW 전년대비 변화율 (%)
        oilYoy: WTI 유가 전년대비 변화율 (%)

    Returns:
        KRInflationEstimate: 물가 방향
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
