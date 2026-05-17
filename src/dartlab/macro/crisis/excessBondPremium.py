"""Excess Bond Premium — Gilchrist & Zakrajšek (2012) AER.

회사채 스프레드 = 예상 부도 프리미엄 + EBP(잔차).
EBP는 신용시장의 투자심리를 반영하며, 경기침체를 HY 스프레드보다 정확히 예측.
EBP > 0: 시장이 부도확률 이상으로 스프레드 요구 → 신용 스트레스.
EBP > 1.0: 역사적으로 12개월 내 침체 강한 신호.

Fed가 CSV로 직접 제공하지만, FRED에 없으므로
HY 스프레드와 기대 부도 프리미엄의 차이로 근사한다.
"""

from __future__ import annotations


def classifyEBP(ebp: float, ebpPrev: float | None = None) -> dict:
    """EBP 수준 + 변화 → 신용 스트레스 판별.

    Capabilities:
        Gilchrist-Zakrajšek (2012 AER) Excess Bond Premium 근사값을 4 zone
        (benign/caution/stress/crisis) 으로 매핑 + 3 개월 변화 방향 (worsening/stable/
        improving) 까지 동시 분류. EBP > 1.0 = 12 개월 내 침체 강한 신호.

    Args:
        ebp: 현재 Excess Bond Premium 근사값 (%p, 예: 0.5 = 50bp).
        ebpPrev: 3 개월 전 EBP. None 이면 direction="stable".

    Returns:
        dict — ebp/ebpChange3m/direction/zone/zoneLabel(한글)/recessionSignal(bool)/
        description.

    Example:
        >>> r = classifyEBP(1.2, 0.8)
        >>> r["zone"], r["recessionSignal"], r["direction"]
        ('crisis', True, 'worsening')

    Guide:
        매크로 위기 신호 1 차 게이트. crisis zone 이면 사이클 분석 (cycle) 결과 무관
        하게 회피 신호 우선.

    When:
        ``analyzeCrisis`` 내부 + AI 신용 스트레스 답변 진입점.

    How:
        4 임계 (0/0.5/1.0) 로 zone → zoneLabel 매핑 + 3 개월 변화 ±0.2 임계로 direction.

    Requires:
        - approximateEBP 로 사전 산출된 ebp 값
        - 3 개월 전 같은 방식 산출된 ebpPrev (변화 방향 신뢰성)

    Raises:
        없음 — None 입력 안전 처리.

    See Also:
        - approximateEBP : HY OAS 기반 EBP 근사
        - dartlab.macro.crisis.fci.calcFCI : 종합 금융컨디션 지수

    AIContext:
        zoneLabel 한 단어 인용 ("위기" · "스트레스") 으로 한 문장 답변 가능.

    LLM Specifications:
        AntiPatterns:
            - ebp 단독 인용 + direction 무시 → 추세 신호 손실
            - benign zone 에서 추가 분석 생략 → improvement 추세 못 잡음
            - bp 단위로 ebp 넘김 (％p 가 정상)
        OutputSchema:
            ``{ebp, ebpChange3m, direction, zone, zoneLabel, recessionSignal, description}``
        Prerequisites: approximateEBP 출력.
        Freshness: HY OAS 일간.
        Dataflow: approximateEBP → classifyEBP → analyzeCrisis.
        TargetMarkets: US (HY OAS 풀세트), KR 미지원.
    """
    if ebp < 0:
        zone, zone_label = "benign", "양호"
        desc = "신용시장 낙관 — 스프레드가 부도확률 이하"
    elif ebp < 0.5:
        zone, zone_label = "caution", "주의"
        desc = "신용 스트레스 소폭 상승"
    elif ebp < 1.0:
        zone, zone_label = "stress", "스트레스"
        desc = "신용시장 긴장 — 위험 회피 확대"
    else:
        zone, zone_label = "crisis", "위기"
        desc = "신용시장 경색 — 12개월 내 침체 강한 신호"

    change_3m = None
    direction = "stable"
    if ebpPrev is not None:
        change_3m = round(ebp - ebpPrev, 3)
        if change_3m > 0.2:
            direction = "worsening"
        elif change_3m < -0.2:
            direction = "improving"

    return {
        "ebp": round(ebp, 3),
        "ebpChange3m": change_3m,
        "direction": direction,
        "zone": zone,
        "zoneLabel": zone_label,
        "recessionSignal": ebp > 1.0,
        "description": desc,
    }


def approximateEBP(
    hySpread: float,
    defaultSpreadProxy: float,
) -> float:
    """EBP 근사: HY OAS - 기대 부도 프리미엄.

    기대 부도 프리미엄 근사:
    - Moody's BAA-AAA spread (순수 신용등급 차이, 부도확률 반영)
    - 또는 역사 평균 HY 스프레드의 일정 비율

    Args:
        hySpread: ICE BofA HY OAS (bp)
        defaultSpreadProxy: 기대 부도 프리미엄 근사 (bp)
            예: BAA-AAA spread × 스케일 팩터, 또는 장기 평균 HY 스프레드의 60%

    Returns:
        EBP 근사값 (%p 단위, 예: 0.5 = 50bp)

    Requires:
        - hySpread: ICE BofA HY OAS daily (FRED BAMLH0A0HYM2)
        - defaultSpreadProxy: BAA-AAA (Moody's) 또는 HY 장기평균 × 비율

    Raises:
        없음 — 단순 산술.
    """
    return round((hySpread - defaultSpreadProxy) / 100, 3)
