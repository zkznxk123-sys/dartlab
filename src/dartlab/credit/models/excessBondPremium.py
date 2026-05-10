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

    Args:
        ebp: 현재 Excess Bond Premium (근사값)
        ebp_prev: 3개월 전 EBP (변화 방향용)

    Returns:
        dict with zone, recessionSignal, description
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
        hy_spread: ICE BofA HY OAS (bp)
        default_spread_proxy: 기대 부도 프리미엄 근사 (bp)
            예: BAA-AAA spread × 스케일 팩터, 또는 장기 평균 HY 스프레드의 60%

    Returns:
        EBP 근사값 (%p 단위, 예: 0.5 = 50bp)
    """
    return round((hySpread - defaultSpreadProxy) / 100, 3)
