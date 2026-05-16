"""금융위기 감지 — Credit-to-GDP Gap + GHS 위기예측 + 침체 대시보드.

순수 데이터 + 판정 함수. 외부 의존성 없음.
core/ 계층 소속 — macro(시장 해석) 엔진에서 소비.

학술 근거:
- BIS Basel III: Credit-to-GDP gap for CCyB (Drehmann & Tsatsaronis 2014)
- Greenwood, Hanson & Shleifer (2022, JoF): "Predictable Financial Crises"
- Reinhart & Rogoff (2009): "This Time Is Different"
- Dalio, R. (2018), *Principles for Navigating Big Debt Crises* Part 1:
  부채사이클 6단계 + 정책 4 레버(monetary/fiscal/credit/fx) 소진도
"""

from __future__ import annotations

from dartlab.macro.crisis._detectorsDalio import (
    _DALIO_PHASE_LABELS,
    _SUB_PHASE_LABELS,
    _VARIANT_LABELS,
    dalioDebtCyclePhase,
    dalioPolicyLeverStatus,
)

# 결과 타입 (분리: _detectorTypes.py SSOT, re-export 으로 BC 보존)
from dartlab.macro.crisis._detectorsHelpers import (
    _beautifulDeleveragingSubPhase,
    _dalioRegimeVariant,
    _oneSidedHpTrend,
)
from dartlab.macro.crisis._detectorTypes import (
    CreditGapResult,
    DalioPhaseResult,
    DalioPolicyLeverResult,
    FisherDeflationResult,
    GHSResult,
    KooRecessionResult,
    KRHousingStressResult,
    MinskyPhaseResult,
    RecessionDashboard,
)

__all_helpers__ = [
    "_DALIO_PHASE_LABELS",
    "_SUB_PHASE_LABELS",
    "_VARIANT_LABELS",
    "_beautifulDeleveragingSubPhase",
    "_dalioRegimeVariant",
    "_oneSidedHpTrend",
    "dalioDebtCyclePhase",
    "dalioPolicyLeverStatus",
]

# ══════════════════════════════════════
# Credit-to-GDP Gap (BIS 방법)
# ══════════════════════════════════════


def creditToGDPGap(creditGDPSeries: list[float]) -> CreditGapResult:
    """Credit-to-GDP Gap (BIS Basel III CCyB 표준) → 신용 거품 + 완충자본 산출.

    Capabilities:
        Drehmann & Tsatsaronis (2014) 의 BIS 방법론 — credit/GDP 시계열에
        one-sided HP filter (λ=400,000) 적용하여 trend 추출 후 gap = actual -
        trend 산출. gap > 2 = 거품 신호, BIS CCyB (counter-cyclical capital
        buffer) 자동 산출.

    Args:
        creditGDPSeries: 분기별 신용/GDP 비율 시계열 (%). 최소 4 기간, 20+
            기간 권장 (BIS 표준).

    Returns:
        CreditGapResult dataclass:
            - ``gap`` (float): actual - trend
            - ``trend`` (float): HP filter 추출 추세
            - ``actual`` (float): 최신 신용/GDP
            - ``zone`` (str): ``"normal"``/``"caution"``/``"alert"``/
              ``"critical"``
            - ``zoneLabel`` (str): 한국어
            - ``ccybBuffer`` (float): BIS CCyB 권고 자본 (% of RWA)
            - ``description`` (str)

    Raises:
        없음. 시계열 < 4 시 빈 결과.

    Example:
        >>> import polars as pl
        >>> series = [...]  # 분기 신용/GDP, 20+ 기간
        >>> r = creditToGDPGap(series)
        >>> r.zone, r.ccybBuffer
        ('alert', 1.5)  # 1.5% RWA 추가 자본 권고

    Guide:
        BIS 임계 (Basel III): gap < 2 = normal (CCyB=0), 2~5 = caution
        (CCyB=0.5 점진), 5~10 = alert (CCyB 1~2%), >10 = critical (CCyB
        2.5% upper bound). 한국은 BOK FSR 매년 발표.

    SeeAlso:
        - ``ghsCrisisScore``: GHS (Greenwood-Hanson-Shleifer) 위기 예측
        - ``minskyPhase``: Minsky 부채 사이클 단계
        - Drehmann & Tsatsaronis (2014) BIS Quarterly Review

    Requires:
        creditGDPSeries 최소 4 기간 (HP filter 안정). 20+ 기간 권장.

    AIContext:
        gap > 5 결과는 거품 우려 — 신용 사이클 위치 + Minsky/Dalio 와 함께
        cross-check. ccybBuffer 는 정책 권고이지 즉시 위험 신호 아님.

    LLM Specifications:
        AntiPatterns:
            - 4 기간 미만 series → 빈 결과 (zoneLabel="데이터부족") 무시 금지.
            - 단일 국가 gap 만 인용 — 글로벌 sync (BIS Q3-Q4) 확인.
        OutputSchema:
            CreditGapResult (7 필드 dataclass).
        Prerequisites:
            BIS/한국은행 credit/GDP 분기 series.
        Freshness:
            분기 단위 (BIS Q3 발표 = 1 분기 lag).
        Dataflow:
            series → _oneSidedHpTrend (λ=400000) → trend → gap = last - trend
            → zone 임계 분류 → CCyB 매핑.
        TargetMarkets: Global (BIS 표준). KR 도 한국은행 FSR.
    """
    if len(creditGDPSeries) < 4:
        return CreditGapResult(
            gap=0.0,
            trend=0.0,
            actual=0.0,
            zone="normal",
            zoneLabel="데이터부족",
            ccybBuffer=0.0,
            description="Credit-to-GDP 시계열 데이터 부족",
        )

    trend_series = _oneSidedHpTrend(creditGDPSeries, lamb=400_000.0)
    actual = creditGDPSeries[-1]
    trend = trend_series[-1]
    gap = actual - trend

    # CCyB 완충자본 (BIS 규칙)
    if gap <= 2.0:
        ccyb = 0.0
    elif gap >= 10.0:
        ccyb = 2.5
    else:
        ccyb = 2.5 * (gap - 2.0) / 8.0

    # 구간 판별
    if gap < 2:
        zone, zone_label = "normal", "정상"
        desc = f"Credit-to-GDP gap {gap:+.1f}%p — 구조적 불균형 없음"
    elif gap < 6:
        zone, zone_label = "watch", "주의"
        desc = f"Credit-to-GDP gap {gap:+.1f}%p — 신용 팽창 초기, CCyB {ccyb:.1f}%"
    elif gap < 10:
        zone, zone_label = "warning", "경고"
        desc = f"Credit-to-GDP gap {gap:+.1f}%p — 신용 과열, CCyB {ccyb:.1f}%"
    else:
        zone, zone_label = "danger", "위험"
        desc = f"Credit-to-GDP gap {gap:+.1f}%p — 금융 불안정 위험, CCyB 최대 2.5%"

    return CreditGapResult(
        gap=round(gap, 2),
        trend=round(trend, 2),
        actual=round(actual, 2),
        zone=zone,
        zoneLabel=zone_label,
        ccybBuffer=round(ccyb, 2),
        description=desc,
    )


# ══════════════════════════════════════
# GHS 금융위기 예측 (Greenwood-Hanson-Shleifer 2022)
# ══════════════════════════════════════


def ghsCrisisScore(
    creditGrowth3y: float,
    assetPriceGrowth3y: float,
    realRate: float | None = None,
) -> GHSResult:
    """GHS 금융위기 예측 점수.

    Args:
        creditGrowth3y: 민간 신용/GDP의 3년 누적 변화 (%p)
        assetPriceGrowth3y: 자산가격(주가 또는 부동산)의 3년 누적 수익률 (%)
        realRate: 실질금리 (%). 제공 시 regime (deflation/inflation) 판정.

    Returns:
        GHSResult: 위기 점수 + 3년 내 위기 확률 + regime (Dalio).

    GHS 핵심: 3년간 급격한 신용 팽창 + 자산 가격 급등이 동시에 발생하면
    향후 3년 내 금융위기 확률 ~40% (정상 시 ~7%).

    Regime (Dalio 확장): 같은 위기 점수라도
    - deflation: 실질금리 >= 2% + 신용 수축 → 부채 디플레이션 압박
    - inflation: 실질금리 <= 0% + 신용 확장 → 화폐/실물 인플레이션 압박
    """
    # 신용 팽창 점수 (0-50)
    if creditGrowth3y > 15:
        credit_score = 50
    elif creditGrowth3y > 10:
        credit_score = 35
    elif creditGrowth3y > 5:
        credit_score = 20
    elif creditGrowth3y > 0:
        credit_score = 10
    else:
        credit_score = 0

    # 자산 가격 점수 (0-50)
    if assetPriceGrowth3y > 80:
        asset_score = 50
    elif assetPriceGrowth3y > 50:
        asset_score = 35
    elif assetPriceGrowth3y > 30:
        asset_score = 20
    elif assetPriceGrowth3y > 10:
        asset_score = 10
    else:
        asset_score = 0

    score = credit_score + asset_score

    # 위기 확률 추정 (GHS 실증 기반 근사)
    if score >= 70:
        crisis_prob = 0.40
    elif score >= 50:
        crisis_prob = 0.25
    elif score >= 30:
        crisis_prob = 0.12
    else:
        crisis_prob = 0.07

    if score >= 70:
        zone, zone_label = "danger", "위험"
    elif score >= 50:
        zone, zone_label = "elevated", "경계"
    elif score >= 30:
        zone, zone_label = "caution", "주의"
    else:
        zone, zone_label = "normal", "정상"

    desc = (
        f"GHS 점수 {score}/100 (신용 {creditGrowth3y:+.1f}%p, 자산 {assetPriceGrowth3y:+.0f}%) "
        f"→ 3년 내 위기 확률 {crisis_prob * 100:.0f}%"
    )

    # Dalio regime 판정
    regime: str | None = None
    regime_label: str | None = None
    if realRate is not None:
        if realRate >= 2.0 and creditGrowth3y < 0:
            regime, regime_label = "deflation", "디플레이션형"
        elif realRate <= 0.0 and creditGrowth3y > 5:
            regime, regime_label = "inflation", "인플레이션형"

    return GHSResult(
        score=round(score, 1),
        zone=zone,
        zoneLabel=zone_label,
        components={
            "creditGrowth3y": round(creditGrowth3y, 2),
            "assetPriceGrowth3y": round(assetPriceGrowth3y, 2),
            "creditScore": credit_score,
            "assetScore": asset_score,
        },
        crisisProb=round(crisis_prob, 3),
        description=desc,
        regime=regime,
        regimeLabel=regime_label,
    )


# ══════════════════════════════════════
# 침체 확률 종합 대시보드
# ══════════════════════════════════════


def recessionDashboard(
    probitProb: float | None = None,
    leiSignal: str | None = None,
    ismLevel: float | None = None,
    creditGap: float | None = None,
    hySpread: float | None = None,
) -> RecessionDashboard:
    """침체 확률 종합 대시보드.

    Args:
        probitProb: Cleveland Fed 프로빗 침체 확률 (0-1)
        leiSignal: LEI 신호 ("expansion" | "caution" | "recession_warning")
        ismLevel: ISM PMI (0-100)
        creditGap: Credit-to-GDP gap (%p)
        hySpread: HY 스프레드 (bps)

    Returns:
        RecessionDashboard: 종합 침체 확률 + 역사 패턴 매칭
    """
    signals: dict[str, float | None] = {}
    weights: list[tuple[float, float]] = []  # (weight, probability)

    # 프로빗 (가장 높은 가중치)
    if probitProb is not None:
        signals["probit"] = round(probitProb, 4)
        weights.append((0.35, probitProb))

    # LEI 신호
    if leiSignal is not None:
        lei_prob = {"expansion": 0.05, "caution": 0.25, "recession_warning": 0.65}.get(leiSignal, 0.15)
        signals["lei"] = round(lei_prob, 4)
        weights.append((0.25, lei_prob))

    # ISM
    if ismLevel is not None:
        if ismLevel < 45:
            ism_prob = 0.60
        elif ismLevel < 48:
            ism_prob = 0.35
        elif ismLevel < 50:
            ism_prob = 0.20
        else:
            ism_prob = 0.05
        signals["ism"] = round(ism_prob, 4)
        weights.append((0.20, ism_prob))

    # Credit gap (장기 신호, 낮은 가중치)
    if creditGap is not None:
        if creditGap > 10:
            cg_prob = 0.40
        elif creditGap > 6:
            cg_prob = 0.20
        elif creditGap > 2:
            cg_prob = 0.10
        else:
            cg_prob = 0.05
        signals["creditGap"] = round(cg_prob, 4)
        weights.append((0.10, cg_prob))

    # HY 스프레드
    if hySpread is not None:
        if hySpread > 700:
            hy_prob = 0.70
        elif hySpread > 500:
            hy_prob = 0.40
        elif hySpread > 400:
            hy_prob = 0.15
        else:
            hy_prob = 0.05
        signals["hySpread"] = round(hy_prob, 4)
        weights.append((0.10, hy_prob))

    # 가중 평균
    if weights:
        total_w = sum(w for w, _ in weights)
        composite = sum(w * p for w, p in weights) / total_w if total_w > 0 else 0.0
    else:
        composite = 0.0

    # 구간
    if composite < 0.15:
        zone, zone_label = "low", "낮음"
    elif composite < 0.30:
        zone, zone_label = "moderate", "보통"
    elif composite < 0.50:
        zone, zone_label = "elevated", "경계"
    else:
        zone, zone_label = "high", "높음"

    # 역사 패턴 매칭 (단순 규칙 기반)
    historical = "normal"
    if composite > 0.5 and creditGap is not None and creditGap > 8:
        historical = "resembles_2008"  # 신용위기형
    elif composite > 0.4 and ismLevel is not None and ismLevel < 45:
        historical = "resembles_2001"  # 제조업 침체형
    elif composite > 0.3 and hySpread is not None and hySpread > 600:
        historical = "resembles_2020"  # 급성 충격형

    desc = f"침체 확률 종합 {composite * 100:.1f}% ({zone_label})"
    if historical != "normal":
        year = historical.split("_")[1]
        desc += f" — {year}년 패턴과 유사"

    return RecessionDashboard(
        composite=round(composite, 4),
        zone=zone,
        zoneLabel=zone_label,
        components=signals,
        historicalMatch=historical if historical != "normal" else None,
        description=desc,
    )


# ══════════════════════════════════════
# Minsky 5단계 판별 (Kindleberger-Minsky)
# ══════════════════════════════════════


def minskyPhase(
    creditGap: float | None = None,
    assetReturn3y: float | None = None,
    hySpread: float | None = None,
    vix: float | None = None,
    ponziRatio: float | None = None,
    dxyChange: float | None = None,
) -> MinskyPhaseResult:
    """Kindleberger-Minsky 순환 5단계 판별.

    이전(displacement) → 호황(boom) → 과열(overtrading) → 공황(discredit) → 전염(revulsion)
    """
    signals: list[str] = []
    scores = {"displacement": 0, "boom": 0, "overtrading": 0, "discredit": 0, "revulsion": 0}

    if creditGap is not None:
        if creditGap > 10:
            scores["overtrading"] += 3
            signals.append(f"Credit-to-GDP gap {creditGap:+.1f}%p — 과열")
        elif creditGap > 5:
            scores["boom"] += 2
            signals.append(f"Credit-to-GDP gap {creditGap:+.1f}%p — 호황")
        elif creditGap < -5:
            scores["revulsion"] += 2
            signals.append(f"Credit-to-GDP gap {creditGap:+.1f}%p — 신용 수축")

    if assetReturn3y is not None:
        if assetReturn3y > 60:
            scores["overtrading"] += 2
            signals.append(f"자산가격 3Y 수익률 {assetReturn3y:.0f}% — 과열")
        elif assetReturn3y > 30:
            scores["boom"] += 2
            signals.append(f"자산가격 3Y 수익률 {assetReturn3y:.0f}% — 호황")
        elif assetReturn3y < -20:
            scores["discredit"] += 2
            signals.append(f"자산가격 3Y 수익률 {assetReturn3y:.0f}% — 공황")

    if hySpread is not None:
        if hySpread > 600:
            scores["discredit"] += 3
            signals.append(f"HY 스프레드 {hySpread:.0f}bp — 공황")
        elif hySpread < 300:
            scores["overtrading"] += 1
            signals.append(f"HY 스프레드 {hySpread:.0f}bp — 과열(신용 완화)")

    if vix is not None:
        if vix > 35:
            scores["discredit"] += 2
        elif vix < 15:
            scores["overtrading"] += 1

    if ponziRatio is not None:
        if ponziRatio > 0.3:
            scores["overtrading"] += 2
            signals.append(f"Ponzi 비율 {ponziRatio:.1%} — 과열")
        elif ponziRatio > 0.2:
            scores["boom"] += 1

    if dxyChange is not None:
        if dxyChange > 5:
            scores["revulsion"] += 2
            signals.append(f"달러 급등 {dxyChange:+.1f}% — 전염")

    # 최고 점수 단계
    best = max(scores, key=scores.get)
    best_score = scores[best]

    labels = {
        "displacement": "이전",
        "boom": "호황",
        "overtrading": "과열",
        "discredit": "공황",
        "revulsion": "전염",
    }

    if best_score >= 4:
        confidence = "high"
    elif best_score >= 2:
        confidence = "medium"
    else:
        confidence = "low"
        best = "displacement"  # 판별 불가 시 초기 단계

    return MinskyPhaseResult(
        phase=best,
        phaseLabel=labels[best],
        confidence=confidence,
        signals=signals,
        description=f"Minsky 순환: {labels[best]} ({confidence})",
    )


# ══════════════════════════════════════
# Koo Balance Sheet Recession
# ══════════════════════════════════════


def kooBalanceSheetRecession(
    privateSaving: float,
    privateInvestment: float,
    gdp: float,
    policyRate: float,
) -> KooRecessionResult:
    """Koo BSR: 민간 금융 잉여 + 저금리 = 재무상태표 침체.

    Args:
        privateSaving: 민간 부문 총저축
        privateInvestment: 민간 총투자
        gdp: GDP
        policyRate: 정책금리 (%)
    """
    if gdp <= 0:
        return KooRecessionResult(0, policyRate, False, "GDP 데이터 없음")

    surplus = ((privateSaving - privateInvestment) / gdp) * 100

    is_bsr = surplus > 3.0 and policyRate < 2.0

    if is_bsr:
        desc = (
            f"민간 금융 잉여 GDP의 {surplus:.1f}% + 정책금리 {policyRate:.2f}% "
            f"— 재무상태표 침체: 민간이 차입 대신 부채 상환 중. 재정 확대 필수"
        )
    elif surplus > 3.0:
        desc = f"민간 잉여 {surplus:.1f}% 높으나 금리 {policyRate:.2f}% — 부분적 BSR 징후"
    else:
        desc = f"민간 잉여 {surplus:.1f}%, 금리 {policyRate:.2f}% — 정상"

    return KooRecessionResult(round(surplus, 2), round(policyRate, 2), is_bsr, desc)


# ══════════════════════════════════════
# Fisher Debt-Deflation
# ══════════════════════════════════════


def fisherDebtDeflation(
    dsr: float,
    cpiYoy: float,
    nplRate: float | None = None,
) -> FisherDeflationResult:
    """Fisher Debt-Deflation: 고부채 + 디플레이션 → 실질 부채 증가 악순환.

    Args:
        dsr: 부채서비스비율 (원리금/소득, %)
        cpiYoy: CPI 전년대비 변화율 (%)
        nplRate: 부실대출비율 (%)
    """
    riskScore = 0

    if dsr > 14:
        riskScore += 2  # 역사적 고수준
    elif dsr > 11:
        riskScore += 1

    if cpiYoy < 0:
        riskScore += 3  # 디플레이션
    elif cpiYoy < 1:
        riskScore += 1  # 준디플레

    if nplRate is not None:
        if nplRate > 5:
            riskScore += 2
        elif nplRate > 2:
            riskScore += 1

    if riskScore >= 4:
        risk, risk_label = "high", "높음"
        desc = f"DSR {dsr:.1f}% + CPI {cpiYoy:.1f}% — 부채 디플레이션 악순환 위험"
    elif riskScore >= 2:
        risk, risk_label = "moderate", "보통"
        desc = f"DSR {dsr:.1f}% + CPI {cpiYoy:.1f}% — 부분적 디플레이션 압력"
    else:
        risk, risk_label = "low", "낮음"
        desc = f"DSR {dsr:.1f}% + CPI {cpiYoy:.1f}% — 정상"

    return FisherDeflationResult(
        round(dsr, 1), round(nplRate, 1) if nplRate else None, round(cpiYoy, 1), risk, risk_label, desc
    )


# ══════════════════════════════════════
# 한국 부동산-금융 스트레스
# ══════════════════════════════════════


def krHousingFinancialStress(
    housePriceYoy: float,
    householdDebtYoy: float | None = None,
) -> KRHousingStressResult:
    """한국 부동산-금융 스트레스: 주택가격 + 가계부채 복합.

    한국 가계부채/GDP = 91%. 주택가격 → 전세 → 대출 전이 경로.
    """
    score = 0
    if housePriceYoy > 10:
        score += 2  # 과열
    elif housePriceYoy < -5:
        score += 2  # 급락 (역방향 스트레스)

    if householdDebtYoy is not None:
        if householdDebtYoy > 8:
            score += 2
        elif householdDebtYoy > 5:
            score += 1

    if score >= 3:
        return KRHousingStressResult(
            round(housePriceYoy, 1),
            round(householdDebtYoy, 1) if householdDebtYoy else None,
            "high",
            "높음",
            f"주택가격 {housePriceYoy:+.1f}% + 가계부채 위험",
        )
    elif score >= 1:
        return KRHousingStressResult(
            round(housePriceYoy, 1),
            round(householdDebtYoy, 1) if householdDebtYoy else None,
            "moderate",
            "보통",
            f"주택가격 {housePriceYoy:+.1f}% — 경계 필요",
        )
    else:
        return KRHousingStressResult(
            round(housePriceYoy, 1),
            round(householdDebtYoy, 1) if householdDebtYoy else None,
            "low",
            "낮음",
            f"주택가격 {housePriceYoy:+.1f}% — 안정",
        )
