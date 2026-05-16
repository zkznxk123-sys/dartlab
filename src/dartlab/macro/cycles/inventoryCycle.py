"""재고순환 판정 + ISM 자산배분 바로미터.

순수 데이터 + 판정 함수. 외부 의존성 없음.
core/ 계층 소속 — macro(시장 해석) 엔진에서 소비.

Kitchin 순환(3~4년)은 재고 축적-소진 주기에 의해 구동된다.
ISM 신규수주/재고 비율이 이 순환의 핵심 지표다.

학술 근거:
- Kitchin (1923): Short cycles in business
- ISM Manufacturing Report methodology
- Conference Board LEI: ISM New Orders is a component
"""

from __future__ import annotations

from dataclasses import dataclass

# ══════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════


@dataclass(frozen=True)
class InventoryPhase:
    """재고순환 4국면 판정 결과."""

    phase: str  # "active_restock" | "passive_restock" | "active_destock" | "passive_destock"
    phaseLabel: str  # "적극보충" | "수동보충" | "적극감축" | "수동감축"
    ratio: float  # 신규수주/재고 비율
    ratioMom: float | None  # 비율 모멘텀 (전기 대비 변화)
    equityImplication: str  # "bullish" | "neutral" | "bearish"
    equityLabel: str  # "긍정" | "중립" | "부정"
    description: str  # 해석 문장


@dataclass(frozen=True)
class ISMSignal:
    """ISM PMI 기반 자산배분 신호."""

    level: float  # ISM PMI 수치
    zone: str  # "deep_contraction" | "contraction" | "neutral" | "expansion" | "strong_expansion"
    zoneLabel: str  # "심각수축" | "수축" | "중립" | "확장" | "강한확장"
    equityStance: str  # "underweight" | "neutral" | "overweight"
    equityLabel: str  # "비중축소" | "중립" | "비중확대"
    rateImplication: str | None  # "hike_end" 또는 None (ISM<55 하락 시)
    rateLabel: str | None  # "인상종결 가능" 또는 None
    description: str


# ══════════════════════════════════════
# 판정 함수
# ══════════════════════════════════════


def classifyInventoryPhase(
    newOrders: float,
    inventories: float,
    prevRatio: float | None = None,
) -> InventoryPhase:
    """재고순환 4국면 판별.

    Capabilities:
        ISM 신규수주/재고 비율 + 전기 대비 MoM → 재고순환 4 국면
        (active_restock/passive_restock/passive_destock/active_destock) +
        equityImplication (bullish/neutral/bearish). Howard Marks / Damodaran
        cycle positioning 표준 입력.

    Args:
        newOrders: ISM 신규수주 지수 (또는 제조업 신규수주 증가율).
        inventories: ISM 재고 지수 (≤ 0 면 판별 불가).
        prevRatio: 이전 기간 신규수주/재고 비율 (모멘텀 계산용).

    Returns:
        InventoryPhase — phase/phaseLabel/ratio/ratioMom/equityImplication/
        equityLabel/description.

    Example:
        >>> r = classifyInventoryPhase(52, 48, prevRatio=1.0)
        >>> r.phase, r.equityImplication
        ('active_restock', 'bullish')

    Guide:
        active_restock (수요 > 재고 + 비율 ↑) = 회복 초기 강세 신호.
        passive_destock (수요 < 재고 + 비율 ↑) = 수축 후기 반등 임박.

    When:
        ``analyzeInventory`` 내부 + AI 재고순환 답변.

    How:
        ratio = newOrders / inventories → ratio_mom = ratio - prevRatio →
        ratio ≥ 1 + rising/falling × 2 = 4 phase.

    Requires:
        ISM 신규수주 + 재고 (KR 제조업 신규수주/재고 fallback).

    Raises:
        없음 — inventories ≤ 0 면 unknown phase 반환.

    See Also:
        - ismBarometer : ISM PMI 수준
        - analyzeInventory : 본 함수 호출 진입점

    AIContext:
        phaseLabel + equityLabel 인용으로 "적극보충 단계 — 주식 긍정" 답변.

    LLM Specifications:
        AntiPatterns:
            - prevRatio 누락한 채 적극/수동 단정 (MoM 정보 손실)
            - ratio 만 인용 + ratioMom 미노출
        OutputSchema:
            InventoryPhase (7 필드).
        Prerequisites: ISM 또는 제조업 신규수주/재고.
        Freshness: 월간 (ISM 첫 영업일).
        Dataflow: orders/inv → ratio → MoM → 4 phase.
        TargetMarkets: US (ISM), KR (BOK 제조업 fallback).
    """
    if inventories <= 0:
        return InventoryPhase(
            phase="unknown",
            phaseLabel="판별불가",
            ratio=0.0,
            ratioMom=None,
            equityImplication="neutral",
            equityLabel="중립",
            description="재고 데이터 부재",
        )

    ratio = newOrders / inventories
    ratio_mom = ratio - prevRatio if prevRatio is not None else None
    rising = ratio_mom is not None and ratio_mom > 0

    if ratio >= 1.0:
        if rising or ratio_mom is None:
            # 적극보충: 수요 > 재고이고 비율 상승 → 생산 확대
            return InventoryPhase(
                phase="active_restock",
                phaseLabel="적극보충",
                ratio=round(ratio, 3),
                ratioMom=round(ratio_mom, 3) if ratio_mom is not None else None,
                equityImplication="bullish",
                equityLabel="긍정",
                description="수요가 재고를 초과하며 격차 확대 — 생산 확대, 이익 증가 예상",
            )
        else:
            # 수동보충: 수요 > 재고지만 비율 하락 → 확장 둔화
            return InventoryPhase(
                phase="passive_restock",
                phaseLabel="수동보충",
                ratio=round(ratio, 3),
                ratioMom=round(ratio_mom, 3) if ratio_mom is not None else None,
                equityImplication="neutral",
                equityLabel="중립",
                description="수요가 아직 재고를 넘지만 격차 축소 — 확장 후반, 경계 필요",
            )
    else:
        if rising:
            # 수동감축: 수요 < 재고지만 비율 개선 → 바닥 통과 중
            return InventoryPhase(
                phase="passive_destock",
                phaseLabel="수동감축",
                ratio=round(ratio, 3),
                ratioMom=round(ratio_mom, 3) if ratio_mom is not None else None,
                equityImplication="bullish",
                equityLabel="긍정",
                description="재고 과잉이나 비율 개선 중 — 수축 후기, 반등 임박",
            )
        else:
            # 적극감축: 수요 < 재고이고 비율 하락 → 수축
            return InventoryPhase(
                phase="active_destock",
                phaseLabel="적극감축",
                ratio=round(ratio, 3),
                ratioMom=round(ratio_mom, 3) if ratio_mom is not None else None,
                equityImplication="bearish",
                equityLabel="부정",
                description="수요 부족에 재고 과잉 심화 — 생산 감축, 이익 감소 예상",
            )


def ismBarometer(ism: float, ismPrev: float | None = None) -> ISMSignal:
    """ISM PMI 기반 자산배분 바로미터.

    Capabilities:
        ISM 제조업 PMI 수준 → 4 zone (strong_expansion/expansion/contraction/
        deep_contraction) + 자산배분 (overweight/neutral/underweight) +
        rateImplication (ISM < 55 + 하락 → 인상 종결 신호). 투자전략 13 + 34.

    Args:
        ism: ISM 제조업 PMI (0-100).
        ismPrev: 이전 기간 ISM PMI (방향 판단용).

    Returns:
        ISMSignal — level/zone/zoneLabel/equityStance/equityLabel/
        rateImplication/rateLabel/description.

    Example:
        >>> r = ismBarometer(48, ismPrev=52)
        >>> r.zone, r.rateImplication
        ('contraction', 'hike_end')

    Guide:
        ISM 55 = 자산배분 분기점. < 55 + 하락 추세 = Fed 인상 종결 신호 (전략 34).
        < 45 = 심각 수축 → 채권/안전자산 강하게 선호.

    When:
        ``analyzeInventory`` 내부 + AI 글로벌 자산배분 답변.

    How:
        ism 4 구간 (55/50/45) × declining 매핑 → zone + equityStance +
        rateImplication.

    Requires:
        ISM PMI (FRED NAPM 또는 ISMPMI).

    Raises:
        없음.

    See Also:
        - classifyInventoryPhase : 4 phase 단독
        - ismAssetAllocation : risk_on/off 단순화

    AIContext:
        zoneLabel + equityLabel + rateLabel 3 필드 인용으로 "ISM 수축, 비중축소,
        인상 종결" 답변.

    LLM Specifications:
        AntiPatterns:
            - ism 수준만 인용 + ismPrev 누락 (방향 무시)
            - rate implication 자동 단정 (ISM<55 + 하락 조건)
        OutputSchema:
            ISMSignal (8 필드).
        Prerequisites: ISM PMI level (+ 이전).
        Freshness: 월간.
        Dataflow: ism + prev → zone + 자산배분 + rate.
        TargetMarkets: US (ISM). KR BOK PMI 가능.
    """
    declining = ismPrev is not None and ism < ismPrev

    # ISM < 55 + 하락 추세 → 금리인상 종결 신호 (전략 34)
    rate_implication: str | None = None
    rate_label: str | None = None
    if ism < 55 and declining:
        rate_implication = "hike_end"
        rate_label = "인상종결 가능"

    if ism >= 55:
        return ISMSignal(
            level=round(ism, 1),
            zone="strong_expansion",
            zoneLabel="강한확장",
            equityStance="overweight",
            equityLabel="비중확대",
            rateImplication=rate_implication,
            rateLabel=rate_label,
            description=f"ISM {ism:.1f} — 제조업 강한 확장, 위험자산 비중확대 유리",
        )
    elif ism >= 50:
        return ISMSignal(
            level=round(ism, 1),
            zone="expansion",
            zoneLabel="확장",
            equityStance="overweight" if not declining else "neutral",
            equityLabel="비중확대" if not declining else "중립",
            rateImplication=rate_implication,
            rateLabel=rate_label,
            description=f"ISM {ism:.1f} — 제조업 확장{'(둔화 중)' if declining else ''}, {'방향 전환 주시' if declining else '위험자산 유지'}",
        )
    elif ism >= 45:
        return ISMSignal(
            level=round(ism, 1),
            zone="contraction",
            zoneLabel="수축",
            equityStance="neutral" if not declining else "underweight",
            equityLabel="중립" if not declining else "비중축소",
            rateImplication=rate_implication,
            rateLabel=rate_label,
            description=f"ISM {ism:.1f} — 제조업 수축, 방어적 포지션 권장",
        )
    else:
        return ISMSignal(
            level=round(ism, 1),
            zone="deep_contraction",
            zoneLabel="심각수축",
            equityStance="underweight",
            equityLabel="비중축소",
            rateImplication=rate_implication,
            rateLabel=rate_label,
            description=f"ISM {ism:.1f} — 제조업 심각 수축, 채권/안전자산 선호",
        )
