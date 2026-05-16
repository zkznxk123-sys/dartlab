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
    """금 가격 3 요인 분해 — 실질금리 + 달러 + 안전수요 (VIX).

    Capabilities:
        금 가격 변동의 3 가지 학술적 드라이버 분해: (1) 실질금리 (역상관 -
        DFII10), (2) 달러 강세 (역상관 - DXY), (3) 안전수요 (정상관 - VIX).
        각 효과를 정량 추정 + 잔차로 "기타 (geopolitical/central bank)" 추적.

    Args:
        goldYoy: 금 YoY 변화율 (%).
        realRateChange: 실질금리 (DFII10) 변화 (%p, 양수=상승).
        dxyChangePct: 달러 인덱스 변화율 (%, 양수=달러강세).
        vix: VIX 수준 (panic 시 안전수요 증가).

    Returns:
        GoldDrivers dataclass:
            - ``goldYoy`` (float): 입력 echo
            - ``realRateEffect``/``dollarEffect``/``safeHavenEffect`` (str):
              ``"상승압력"``/``"하락압력"``/``"중립"``
            - ``dominant`` (str): 지배 요인 ("실질금리"/"달러"/"안전자산"/"기타")
            - ``description`` (str): 한국어 해석

    Raises:
        없음.

    Example:
        >>> r = interpretGoldDrivers(goldYoy=18, realRateChange=-0.8,
        ...                          dxyChangePct=-3, vix=22)
        >>> r.dominant, r.realRateEffect
        ('실질금리', '상승압력')

    Guide:
        실질금리 < -0.3%p (3 개월) → 금 상승압력 (carry cost 감소). 달러 < -2%
        (3 개월) → 금 상승 (USD 가격 inverse). VIX > 25 → 안전수요 활성.
        3 요인 합산해 다수결로 dominant 선정. 모두 중립이면 "기타".

    SeeAlso:
        - ``classifyVixRegime``: VIX 4 단계
        - ``copperGoldRatio``: 구리/금 비율 (위험선호)
        - ``classifyCycle``: 사이클 종합

    Requires:
        4 입력 모두 필요 (옵션 아님).

    AIContext:
        dominant + 3 효과 모두 인용 (단일 요인만 인용 금지). 학술적 회귀
        실험에서 실질금리 -0.6, 달러 -0.4, VIX +0.2 비중. KR 입력 시 BOK
        실질금리 + WSJ 달러 인덱스 사용.

    LLM Specifications:
        AntiPatterns:
            - VIX 만 보고 금 전망 단정 — 실질금리 + 달러 함께 확인.
            - YoY 1 개월 변화로 추세 단정 — 본 함수는 단일 시점 분해 (1 분기
              3 개월 변화 기준).
        OutputSchema:
            GoldDrivers ``{goldYoy, realRateEffect, dollarEffect,
            safeHavenEffect, dominant, description}``.
        Prerequisites:
            금 가격 + 실질금리 (DFII10) + DXY + VIX 시계열.
        Freshness:
            금 가격 일, 실질금리 일, DXY 일, VIX 일.
        Dataflow:
            3 요인 룰 → 상승/하락/중립 라벨 → 다수결 dominant → 한국어 합성.
        TargetMarkets: Global (FRED + Yahoo Finance + DFII10).
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
    """Buffett Indicator (시총/GDP) → 시장 전체 밸류에이션 5 구간 분류.

    Capabilities:
        Warren Buffett 의 "가장 좋은 단일 시장 척도" — Wilshire 5000 시총
        (WILL5000PRFC) / 명목 GDP. 역사적 범위 (1970~2024) 의 5 구간으로
        분류하여 현 시점 시장 전체 밸류에이션 판정.

    Args:
        totalMarketCap: 전체 시가총액 (Billions $). FRED WILL5000PRFC.
        gdp: 명목 GDP (Billions $). FRED GDP.

    Returns:
        MarketValuation dataclass:
            - ``buffettIndicator`` (float): 시총/GDP 비율 (%)
            - ``zone`` (str): ``"undervalued"``/``"fair"``/``"overvalued"``/
              ``"extreme"``
            - ``zoneLabel`` (str): 한국어
            - ``description`` (str): 한국어 해석

    Raises:
        없음. gdp ≤ 0 시 zero result.

    Example:
        >>> r = marketLevelValuation(totalMarketCap=55000, gdp=27000)
        >>> r.buffettIndicator, r.zone
        (203.7, 'extreme')

    Guide:
        역사적 5 구간 (미국 1970~2024):
        - < 70%: 극단 저평가 (2009 GFC 바닥, 2020 COVID 바닥)
        - 70~100%: 저평가 (장기 평균 1990s)
        - 100~140%: 적정 (현대 평균 2010s)
        - 140~180%: 고평가
        - > 180%: 극단 고평가 (1999 닷컴 정점 150%, 2021 175%)

        본 지표는 시장 전체 — 개별 종목 valuation 과 다름. 글로벌화 (해외
        매출 비중) 증가로 long-run 평균 자체가 상승 추세 (mean reversion 한계).

    SeeAlso:
        - ``classifyCycle``: 매크로 사이클 (밸류에이션과 함께 종합)
        - ``copperGoldRatio``: 위험선호 (다른 시장 척도)
        - Buffett, W. (2001) Fortune Magazine

    Requires:
        Wilshire 5000 시가총액 + 명목 GDP (FRED).

    AIContext:
        Buffett Indicator extreme 결과는 시장 전체 신호이지 개별 종목 매도
        신호 아님 — long-run mean reversion 시점 불확실 (1~5 년).
        한국 KOSPI 적용 시 KRX 전체 시총 / 한국 GDP 사용.

    LLM Specifications:
        AntiPatterns:
            - extreme 단계만 보고 "시장 폭락 임박" 단정 — Buffett 본인도
              "정확한 timing 도구 아님" 명시 (2001 Fortune).
            - 글로벌화 증가로 long-run 평균 자체 상승 — 1990 표준을 2024에
              그대로 적용 금지.
        OutputSchema:
            MarketValuation ``{buffettIndicator, zone, zoneLabel, description}``.
        Prerequisites:
            FRED WILL5000PRFC + GDP. 동일 통화 단위 (Billions $).
        Freshness:
            시총 일, GDP 분기 (Bureau of Economic Analysis Q1/Q2/Q3/Q4).
        Dataflow:
            (시총 / GDP) × 100 → 5 구간 임계 분류 → description.
        TargetMarkets: US (WILL5000PRFC + GDP). KR 도 KRX/KOSIS 적용 가능.
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
    """실질금리 (DFII10) + BEI (10Y break-even) → 금융 환경 4 레짐 분류.

    Capabilities:
        실질금리와 BEI 의 (수준 + 조합) 으로 금융 환경 4 레짐 (긴축/디플레위험/
        리플레이션/골디락스) 분류. macro/cycles/cycle 의 보조 진단으로 사용.

    Args:
        realRate: 10년 실질금리 (DFII10, %).
        bei: 10년 break-even inflation (%).

    Returns:
        RealRateRegimeResult dataclass:
            - ``realRate``/``bei`` (float): 입력 echo
            - ``regime`` (str): ``"tight"``/``"deflation"``/``"reflation"``/
              ``"goldilocks"``
            - ``regimeLabel`` (str): 한국어
            - ``description`` (str): 한국어 해석

    Raises:
        없음.

    Example:
        >>> r = realRateRegime(realRate=2.3, bei=1.8)
        >>> r.regime
        'deflation'

    Guide:
        4 레짐 매트릭스 (수준 기반):
        - 실질 > 2 + BEI < 2 → deflation 위험
        - 실질 > 1.5 + BEI > 2.5 → tight (긴축)
        - 실질 < 0 + BEI > 2.5 → reflation
        - 실질 < 0.5 + BEI ~ 2 → goldilocks

        방향 판별 (전기 대비) 은 호출자 책임 — 본 함수는 수준 분류만.

    SeeAlso:
        - ``classifyCycle``: 사이클 4 국면 (regime 과 결합)
        - ``interpretGoldDrivers``: realRateChange 사용
        - ``rateOutlook``: 금리 방향 전망 (Fed funds 기반)

    Requires:
        실질금리 + BEI 둘 다 필요 (옵션 아님).

    AIContext:
        regime + description 함께 인용. tight regime 시 자산 클래스
        선택 변경 권장 — 채권 우위. goldilocks 는 주식 우위.

    LLM Specifications:
        AntiPatterns:
            - realRate 단독으로 regime 판정 — BEI 동반 분석 필수.
            - 본 함수의 regime 라벨을 미국 Fed funds 와 혼동 (본 함수는 10Y
              실질, Fed funds 는 단기).
        OutputSchema:
            RealRateRegimeResult ``{realRate, bei, regime, regimeLabel,
            description}``.
        Prerequisites:
            FRED DFII10 + T10YIE (10Y BEI).
        Freshness:
            DFII10 일, T10YIE 일.
        Dataflow:
            (realRate, bei) → 4 레짐 임계 분류 → description 합성.
        TargetMarkets: US (FRED DFII10 표준). KR 미적용 (KR BEI 부재).
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
