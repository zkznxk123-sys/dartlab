"""macroCycle 자산 해석 + VIX/Cu/Au/FX/시장평가/실질금리 6 함수.

macro/cycles/macroCycle.py 가 992 줄 god module 이라 자산 해석 도메인 분리.
identity 보존을 위해 macroCycle.py 가 본 모듈에서 re-export 한다.

함수:
- interpretGoldDrivers — 금 3 요인 (달러/실질금리/안전수요)
- classifyVixRegime — VIX 레짐 (calm/normal/elevated/panic)
- copperGoldRatio — 구리/금 비율 → 위험선호
- interpretFxDrivers — 환율 드라이버 (성장/금리/심리)
- marketLevelValuation — Buffett/CAPE/EY-BY 종합 평가
- realRateRegime — 실질금리 4 레짐
"""

from __future__ import annotations

import math

from dartlab.macro.cycles._macroCycleHelpers import _normCdf
from dartlab.macro.cycles._macroCycleTypes import (
    CopperGoldSignal,
    FxDrivers,
    GoldDrivers,
    MarketValuation,
    RealRateRegimeResult,
    VixRegime,
)

# ══════════════════════════════════════


def interpretGoldDrivers(
    goldYoy: float,
    realRateChange: float,
    dxyChangePct: float,
    vix: float,
) -> GoldDrivers:
    """금 가격의 3요인 분해 해석.

    Args:
        gold_yoy: 금 YoY 변화율 (%)
        real_rate_change: 실질금리(DFII10) 변화 (%p, 양수=상승)
        dxy_change_pct: 달러인덱스 변화율 (%, 양수=달러강세)
        vix: VIX 수준

    Returns:
        GoldDrivers
    """
    # 실질금리 역상관: 실질금리 하락 → 금 상승압력
    if realRateChange < -0.3:
        rr = "상승압력"
    elif realRateChange > 0.3:
        rr = "하락압력"
    else:
        rr = "중립"

    # 달러 역상관: 달러 약세 → 금 상승압력
    if dxyChangePct < -2:
        dx = "상승압력"
    elif dxyChangePct > 2:
        dx = "하락압력"
    else:
        dx = "중립"

    # 안전자산 수요: VIX 급등 → 금 상승
    sh = "상승압력" if vix > 25 else "중립"

    # 지배적 요인 판별
    effects = {"실질금리": rr, "달러": dx, "안전자산": sh}
    up_count = sum(1 for v in effects.values() if v == "상승압력")
    down_count = sum(1 for v in effects.values() if v == "하락압력")

    if up_count > down_count:
        dominant = next(k for k, v in effects.items() if v == "상승압력")
    elif down_count > up_count:
        dominant = next(k for k, v in effects.items() if v == "하락압력")
    else:
        dominant = "복합"

    return GoldDrivers(
        realRateEffect=rr,
        dollarEffect=dx,
        safeHavenEffect=sh,
        dominant=dominant,
    )


# ══════════════════════════════════════
# VIX 구간 판정
# ══════════════════════════════════════


def classifyVixRegime(vix: float) -> VixRegime:
    """VIX 수준으로 시장 공포 구간 판정 + 분할매수 신호.

    Args:
        vix: CBOE VIX 수준

    Returns:
        VixRegime
    """
    if vix >= 40:
        return VixRegime(vix, "panic", "패닉", 3)
    if vix >= 30:
        return VixRegime(vix, "extreme_fear", "극단공포", 2)
    if vix >= 25:
        return VixRegime(vix, "fear", "공포", 1)
    if vix >= 20:
        return VixRegime(vix, "anxious", "불안", 0)
    if vix >= 15:
        return VixRegime(vix, "normal", "정상", 0)
    return VixRegime(vix, "complacent", "낙관", 0)


# ══════════════════════════════════════
# Copper/Gold Ratio (경기 선행)
# ══════════════════════════════════════


def copperGoldRatio(
    copper: float,
    gold: float,
    prevCopper: float | None = None,
    prevGold: float | None = None,
) -> CopperGoldSignal:
    """Copper/Gold Ratio → 경기 선행.

    구리 = 산업수요, 금 = 안전자산. 비율 상승 = 경기 낙관.
    10Y 국채 수익률과 강한 상관.
    """
    if gold <= 0:
        return CopperGoldSignal(0, "stable", "판별불가", "neutral", "금 가격 데이터 없음")

    ratio = copper / gold
    prev_ratio = (prevCopper / prevGold) if prevCopper and prevGold and prevGold > 0 else None

    if prev_ratio is not None:
        change_pct = ((ratio - prev_ratio) / prev_ratio) * 100
    else:
        change_pct = 0.0

    if change_pct > 3:
        return CopperGoldSignal(
            round(ratio, 4),
            "rising",
            "상승",
            "expansion",
            f"Cu/Au {ratio:.4f} ({change_pct:+.1f}%) — 산업수요 확대, 경기 낙관",
        )
    elif change_pct < -3:
        return CopperGoldSignal(
            round(ratio, 4),
            "falling",
            "하락",
            "contraction",
            f"Cu/Au {ratio:.4f} ({change_pct:+.1f}%) — 안전자산 선호, 경기 비관",
        )
    else:
        return CopperGoldSignal(
            round(ratio, 4), "stable", "안정", "neutral", f"Cu/Au {ratio:.4f} ({change_pct:+.1f}%) — 안정"
        )


# ══════════════════════════════════════
# 환율 3요인 분해
# ══════════════════════════════════════


def interpretFxDrivers(
    fxChangePct: float,
    rateDiffChange: float | None = None,
    tradeBalanceYoy: float | None = None,
    vix: float | None = None,
) -> FxDrivers:
    """환율 변동의 3요인 분해 해석.

    환율 = f(양국금리차, 무역수지, 위험선호도)
    금리차 확대 → 자본유출 → 원화약세
    무역흑자 확대 → 달러유입 → 원화강세
    VIX 상승 → 위험회피 → 원화약세 (EM 통화 특성)

    Args:
        fx_change_pct: 환율 변화율 (%, 양수=원화약세)
        rate_diff_change: 한미 금리차 변화 (%p, 양수=미국금리상대상승)
        trade_balance_yoy: 무역수지 YoY 변화 (%, 양수=흑자확대)
        vix: VIX 수준

    Returns:
        FxDrivers
    """
    # 1) 금리차 요인
    if rateDiffChange is not None and rateDiffChange > 0.2:
        rd_effect = "원화약세"
    elif rateDiffChange is not None and rateDiffChange < -0.2:
        rd_effect = "원화강세"
    else:
        rd_effect = "중립"

    # 2) 무역수지 요인
    if tradeBalanceYoy is not None and tradeBalanceYoy > 10:
        trade_effect = "원화강세"
    elif tradeBalanceYoy is not None and tradeBalanceYoy < -10:
        trade_effect = "원화약세"
    else:
        trade_effect = "중립"

    # 3) 위험선호도 요인 (VIX 기반)
    if vix is not None and vix > 25:
        risk_effect = "원화약세"
    elif vix is not None and vix < 15:
        risk_effect = "원화강세"
    else:
        risk_effect = "중립"

    # 지배적 요인 판별
    effects = {"금리차": rd_effect, "무역수지": trade_effect, "위험선호도": risk_effect}
    # fx_change_pct가 양수(약세)인데 어느 요인이 약세 방향인지
    fx_direction = "원화약세" if fxChangePct > 0 else "원화강세"
    matching = [name for name, eff in effects.items() if eff == fx_direction and eff != "중립"]
    if matching:
        dominant = matching[0]  # 일치하는 첫 요인
    elif any(v != "중립" for v in effects.values()):
        dominant = next(name for name, eff in effects.items() if eff != "중립")
    else:
        dominant = "미확인"

    # 금리차-환율 방향 불일치 감지
    divergence = None
    if rateDiffChange is not None and abs(fxChangePct) > 2:
        rd_implied = "원화약세" if rateDiffChange > 0.2 else ("원화강세" if rateDiffChange < -0.2 else "중립")
        if rd_implied != "중립" and rd_implied != fx_direction:
            divergence = f"금리차는 {rd_implied} 방향이나 환율은 {fx_direction} → 비금리 요인(무역수지, 자본유입) 지배"

    return FxDrivers(
        rateDiffEffect=rd_effect,
        tradeEffect=trade_effect,
        riskEffect=risk_effect,
        dominant=dominant,
        divergence=divergence,
    )


# ══════════════════════════════════════
# 시장 레벨 밸류에이션 (Buffett Indicator)
# ══════════════════════════════════════


def marketLevelValuation(
    totalMarketCap: float,
    gdp: float,
) -> MarketValuation:
    """Buffett Indicator: 시가총액/GDP 비율로 시장 전체 밸류에이션 판정.

    Warren Buffett이 "가장 좋은 단일 지표"라고 언급한 시장 레벨 척도.
    WILL5000PRFC(Wilshire 5000 시가총액) / GDP(명목).

    역사적 범위 (미국):
    - <70%: 극단 저평가 (2009, 2020 바닥)
    - 70-100%: 저평가 (장기 평균 수준)
    - 100-140%: 적정 (현대 평균)
    - 140-180%: 고평가
    - >180%: 극단 고평가 (닷컴, 2021)

    Args:
        total_market_cap: 전체 시가총액 (Billions $) — WILL5000PRFC
        gdp: 명목 GDP (Billions $) — GDP

    Returns:
        MarketValuation
    """
    if gdp <= 0:
        return MarketValuation(0, "fair", "판별불가", "GDP 데이터 없음")

    ratio = (totalMarketCap / gdp) * 100

    if ratio < 70:
        zone, label = "deep_value", "극단저평가"
        desc = f"Buffett Indicator {ratio:.0f}% — 시장 극단 저평가 (역사적 바닥 수준)"
    elif ratio < 100:
        zone, label = "undervalued", "저평가"
        desc = f"Buffett Indicator {ratio:.0f}% — 시장 저평가 (장기 평균 하회)"
    elif ratio < 140:
        zone, label = "fair", "적정"
        desc = f"Buffett Indicator {ratio:.0f}% — 시장 적정 수준"
    elif ratio < 180:
        zone, label = "overvalued", "고평가"
        desc = f"Buffett Indicator {ratio:.0f}% — 시장 고평가 (조정 위험 상승)"
    else:
        zone, label = "extreme", "극단고평가"
        desc = f"Buffett Indicator {ratio:.0f}% — 시장 극단 고평가 (버블 경고)"

    return MarketValuation(
        buffettIndicator=round(ratio, 1),
        zone=zone,
        zoneLabel=label,
        description=desc,
    )


# ══════════════════════════════════════
# BEI / Real Rate 분해
# ══════════════════════════════════════


def realRateRegime(realRate: float, bei: float) -> RealRateRegimeResult:
    """실질금리 + BEI → 금융환경 4분면.

    | | BEI 상승 | BEI 하락 |
    |실질금리 상승| 긴축 | 디플레 위험 |
    |실질금리 하락| 리플레이션 | 골디락스 |

    (방향 판별은 호출자가 전기 대비 제공)
    여기서는 수준 기반으로 판별.
    """
    if realRate > 2.0 and bei < 2.0:
        return RealRateRegimeResult(
            round(realRate, 2),
            round(bei, 2),
            "deflation",
            "디플레위험",
            f"실질금리 {realRate:.2f}% 높음 + BEI {bei:.2f}% 낮음 — 디플레이션 위험",
        )
    elif realRate > 1.5 and bei > 2.5:
        return RealRateRegimeResult(
            round(realRate, 2),
            round(bei, 2),
            "tightening",
            "긴축",
            f"실질금리 {realRate:.2f}% + BEI {bei:.2f}% 동반 상승 — 금융 긴축",
        )
    elif realRate < 0.5 and bei > 2.5:
        return RealRateRegimeResult(
            round(realRate, 2),
            round(bei, 2),
            "reflation",
            "리플레이션",
            f"실질금리 {realRate:.2f}% 낮음 + BEI {bei:.2f}% 높음 — 리플레이션",
        )
    elif realRate < 1.0 and bei < 2.0:
        return RealRateRegimeResult(
            round(realRate, 2),
            round(bei, 2),
            "goldilocks",
            "골디락스",
            f"실질금리 {realRate:.2f}% + BEI {bei:.2f}% 모두 안정 — 골디락스",
        )
    else:
        return RealRateRegimeResult(
            round(realRate, 2),
            round(bei, 2),
            "neutral",
            "중립",
            f"실질금리 {realRate:.2f}%, BEI {bei:.2f}% — 뚜렷한 방향 없음",
        )


__all__ = [
    "classifyVixRegime",
    "copperGoldRatio",
    "interpretFxDrivers",
    "interpretGoldDrivers",
    "marketLevelValuation",
    "realRateRegime",
]
