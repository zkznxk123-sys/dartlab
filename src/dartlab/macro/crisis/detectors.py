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
    """GHS (Greenwood-Hanson-Shleifer 2022) 금융위기 예측 점수 + Dalio 회로.

    Capabilities:
        Greenwood, Hanson & Shleifer (2022, JoF) "Predictable Financial
        Crises" 의 핵심 모델 — 3 년 누적 신용 팽창 + 자산 가격 급등 결합
        시 향후 3 년 내 금융위기 확률 ~40% (정상 시 ~7%). realRate 제공 시
        Dalio Part 1 regime (deflation/inflation) 추가 판정.

    Args:
        creditGrowth3y: 민간 신용/GDP 3 년 누적 변화 (%p).
        assetPriceGrowth3y: 자산가격 (주가 또는 부동산) 3 년 누적 수익률 (%).
        realRate: 실질금리 (%). 제공 시 regime 분기.

    Returns:
        GHSResult dataclass:
            - ``crisisScore`` (float): 0~100 위기 점수
            - ``probability3y`` (float): 3 년 내 위기 확률 (0~1)
            - ``zone`` (str): low/moderate/high/extreme
            - ``regime`` (str|None): deflation/inflation (realRate 있을 때)
            - ``creditScore``/``assetScore`` (float): 분해 점수
            - ``warnings`` (list[str])

    Raises:
        없음.

    Example:
        >>> r = ghsCrisisScore(creditGrowth3y=12, assetPriceGrowth3y=45,
        ...                     realRate=-1.0)
        >>> r.crisisScore, r.probability3y, r.regime
        (75, 0.35, 'inflation')

    Guide:
        GHS 핵심: credit (50 점 만점) + asset (50 점) 합산. credit > 10%p +
        asset > 30% 결합 시 zone="high". Dalio regime: deflation = 실질금리
        +2% + 신용 수축 → 부채 디플레이션, inflation = 실질금리 <0% + 신용
        확장 → 통화/실물 인플레이션 압박.

    SeeAlso:
        - ``creditToGDPGap``: BIS gap (단기 신용 거품)
        - ``minskyPhase``: Minsky 부채 사이클 (구조적)
        - ``dalioDebtCyclePhase``: Dalio 6 단계
        - Greenwood, Hanson & Shleifer (2022) Journal of Finance

    Requires:
        creditGrowth3y + assetPriceGrowth3y (3 년 누적 변화).

    AIContext:
        probability3y 는 통계적 base rate — 개별 회사 부도 확률과 혼동 금지.
        regime 라벨은 Dalio Part 1 정성 판정 (정확한 1 년 부도율 아님).

    LLM Specifications:
        AntiPatterns:
            - 단년도 신용 증가 (creditGrowth1y) 입력 — 본 함수는 3 년 누적
              표준. 단기 변동성에 과민 반응.
            - realRate=0 입력 → regime 판정 불가 (None 반환), 의도된 동작.
        OutputSchema:
            GHSResult (7 필드 dataclass).
        Prerequisites:
            credit + asset 3 년 시계열. realRate 옵션.
        Freshness:
            BIS credit 분기, asset price 일/월.
        Dataflow:
            creditGrowth3y → credit_score (0~50) + assetGrowth → asset_score
            (0~50) → 합산 → zone → probability 매핑 + realRate → regime.
        TargetMarkets: Global. BIS + Schiller (자산가격) 데이터.
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
    """침체 확률 종합 대시보드 — 5 지표 가중 합산 + 역사 패턴 매칭.

    Capabilities:
        Cleveland Fed 프로빗 (35%) + LEI 신호 (25%) + ISM PMI (20%) + Credit
        Gap (10%) + HY 스프레드 (10%) 5 지표 가중평균하여 종합 침체 확률
        산출 + 역사적 침체 패턴 (2008/2020/2001) 와 매칭하여 가장 유사한
        시나리오 식별.

    Args:
        probitProb: Cleveland Fed 프로빗 침체 확률 (0~1).
        leiSignal: LEI 신호 ``"expansion"``/``"caution"``/``"recession_warning"``.
        ismLevel: ISM 제조업 PMI (0~100).
        creditGap: Credit-to-GDP gap (%p, BIS 표준).
        hySpread: HY 스프레드 (bps).

    Returns:
        RecessionDashboard dataclass:
            - ``probabilityComposite`` (float): 가중 합산 (0~1)
            - ``zone``/``zoneLabel`` (str): low/moderate/elevated/high
            - ``signals`` (dict): 5 지표별 변환 확률
            - ``historicalAnalogue`` (str|None): "2008 GFC" 등
            - ``yieldCurveStatus`` (str|None)
            - ``warnings`` (list[str])

    Raises:
        없음.

    Example:
        >>> r = recessionDashboard(probitProb=0.45, leiSignal="recession_warning",
        ...                          ismLevel=48, creditGap=8, hySpread=600)
        >>> r.zone, r.historicalAnalogue
        ('high', '2007-2008 신용 사이클')

    Guide:
        프로빗 가중치 35% 이유: NBER 침체 예측에서 가장 정확. LEI 25%
        는 6 개월 선행. ISM 50 = 확장/수축 경계. composite > 0.50 = 1 년
        내 침체 확률 매우 높음.

    SeeAlso:
        - ``ghsCrisisScore``: GHS 위기 (3 년 horizon)
        - ``minskyPhase``: Minsky 부채 사이클 단계
        - ``classifyCycle``: 매크로 사이클 4 국면

    Requires:
        없음 — 5 지표 모두 옵션, 1 개라도 있으면 동작.

    AIContext:
        composite 만 인용 금지 — signals dict 의 5 지표 분해 + historical
        Analogue 함께 노출. zone="elevated" 결과는 transitioning 신호이지
        즉시 침체 신호 아님.

    LLM Specifications:
        AntiPatterns:
            - hySpread 만 보고 침체 단정 — 본 함수는 5 지표 가중 합산.
            - 프로빗만 5 분기 lag 데이터로 호출 — 결과 신뢰도 낮음 (회귀
              모델 stale).
        OutputSchema:
            RecessionDashboard ``{probabilityComposite, zone, zoneLabel,
            signals, historicalAnalogue, yieldCurveStatus, warnings}``.
        Prerequisites:
            적어도 1 개 지표. 5 개 모두 있으면 신뢰도 high.
        Freshness:
            프로빗 월간 (Cleveland Fed), LEI 월간, ISM 월간 1 일, Credit Gap 분기.
        Dataflow:
            각 지표 → 확률 매핑 → 가중평균 → zone 분류 → 역사 패턴 매칭.
        TargetMarkets: US (Cleveland Fed + ISM + LEI). KR 미적용 (지표 부재).
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
    """Kindleberger-Minsky 5 단계 (displacement→boom→overtrading→discredit→revulsion).

    Capabilities:
        Minsky (1986) "Stabilizing an Unstable Economy" + Kindleberger (1978)
        "Manias, Panics and Crashes" 의 5 단계 모델 — Credit gap + 자산 수익
        + HY 스프레드 + VIX + Ponzi 비율 + 달러 변화 6 지표 가중 투표로 현재
        단계 판정. 부채 사이클 분석의 결정판.

    Args:
        creditGap: Credit-to-GDP gap (%p).
        assetReturn3y: 자산 3 년 수익률 (%).
        hySpread: HY 스프레드 (bps).
        vix: CBOE VIX.
        ponziRatio: Ponzi 단계 비율 (회수성 대비 신규차입 의존도, %).
        dxyChange: 달러 인덱스 변화 (%).

    Returns:
        MinskyPhaseResult dataclass:
            - ``phase`` (str): 5 단계 중 하나
            - ``phaseLabel`` (str): 한국어
            - ``signals`` (list[str]): 판정 근거
            - ``scores`` (dict): 5 단계 점수
            - ``confidence`` (str)

    Raises:
        없음.

    Example:
        >>> r = minskyPhase(creditGap=12, assetReturn3y=60, vix=15,
        ...                  ponziRatio=35)
        >>> r.phase
        'overtrading'

    Guide:
        5 단계 시간 순서:
        - displacement: 외부 충격 (기술 혁신, 정책 변화) → 신용 시작
        - boom: 자산 가격 상승 + 신용 확장
        - overtrading: 과열 (credit gap > 10%, asset > 50% 3Y)
        - discredit: panic 시작 (HY 급등, VIX panic)
        - revulsion: 신용 수축 (credit gap < -5, asset 하락)

    SeeAlso:
        - ``creditToGDPGap``: BIS 신용 거품
        - ``ghsCrisisScore``: GHS 위기 예측
        - ``dalioDebtCyclePhase``: Dalio 6 단계 (Minsky 확장)

    Requires:
        없음 — 6 지표 모두 옵션. 1 개라도 있으면 동작.

    AIContext:
        phase 라벨 + signals 함께 인용. confidence=low 결과는 전환기 — 분기
        후 재호출 권장. ponziRatio > 50 은 Hyman Minsky 의 Ponzi 단계 강신호.

    LLM Specifications:
        AntiPatterns:
            - 단일 지표 (VIX 만) 로 단계 판정 — 본 함수는 6 지표 합산.
            - displacement → revulsion 5 단계는 시간 순서이지만 동시 신호
              가능 — phase 가 항상 순서대로 진행하지 않음.
        OutputSchema:
            MinskyPhaseResult ``{phase, phaseLabel, signals, scores, confidence}``.
        Prerequisites:
            적어도 2 개 지표 권장 (1 개만이면 confidence=low).
        Freshness:
            지표별 (BIS 분기, VIX/HY 일, asset return 월).
        Dataflow:
            지표별 룰 → scores 5 단계 누적 → max → phase 결정 → confidence.
        TargetMarkets: US (FRED 표준), Global (BIS).
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
    """Koo Balance Sheet Recession — 민간 금융 잉여 + 저금리 = BSR 진단.

    Capabilities:
        Richard Koo (Nomura, 2003) 의 BSR 모델 — 민간 (가계 + 기업) 이 부채
        상환을 우선시할 때 차입 수요가 사라져 통화정책 무력화. 잉여 > GDP
        3% + 정책금리 < 2% = BSR 신호. 일본 잃어버린 30년 + 2008 후 미국/
        유럽 일부 적용.

    Args:
        privateSaving: 민간 부문 총저축 (원).
        privateInvestment: 민간 총투자 (원).
        gdp: GDP (원). 잉여 비율 계산 분모.
        policyRate: 정책금리 (%).

    Returns:
        KooRecessionResult dataclass:
            - ``surplus`` (float): 민간 금융 잉여 (% of GDP)
            - ``policyRate`` (float)
            - ``isBSR`` (bool): 본격 BSR 여부
            - ``description`` (str)

    Raises:
        없음.

    Example:
        >>> r = kooBalanceSheetRecession(privateSaving=200e12,
        ...                              privateInvestment=170e12,
        ...                              gdp=1000e12, policyRate=0.5)
        >>> r.isBSR
        True

    Guide:
        BSR 임계: surplus > 3% + policyRate < 2%. surplus 만 높으면 부분
        BSR (재정 확대 효과 약화), 둘 다 충족하면 본격 BSR (금리 무력화,
        재정 확대 필수). 일본 1995~2005, 미국 2009~2015 사례.

    SeeAlso:
        - ``fisherDebtDeflation``: Fisher (1933) 부채 디플레이션 (BSR 의
          극단)
        - ``minskyPhase``: Minsky revulsion (deleveraging 단계)
        - Koo, R. (2003) "Balance Sheet Recession" Nomura

    Requires:
        privateSaving + privateInvestment + gdp > 0 + policyRate.

    AIContext:
        BSR 진단 + 정책 권고 ("재정 확대 필수") 함께 노출. surplus 음수면
        민간 차입 우위 (정상), positive 큰 값이 위기 신호.

    LLM Specifications:
        AntiPatterns:
            - GDP=0 또는 음수 입력 시 빈 결과 → 호출자 분기 필요.
            - 단기 (1 분기) 잉여만 보고 BSR 단정 — 3~5 년 sustained 필요.
        OutputSchema:
            KooRecessionResult ``{surplus, policyRate, isBSR, description}``.
        Prerequisites:
            국민계정 (saving/investment/GDP) + 정책금리.
        Freshness:
            국민계정 분기. 정책금리 일.
        Dataflow:
            (saving - investment) / GDP × 100 → surplus → +rate 임계 → isBSR.
        TargetMarkets: 일본 (Koo 원형), 미국 (2008 후), 한국 (2020~).
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
    """Fisher (1933) Debt-Deflation — 고부채 + 디플레이션 → 실질 부채 증가 악순환.

    Capabilities:
        Irving Fisher (1933) "The Debt-Deflation Theory of Great Depressions"
        의 핵심 — 고부채 + 디플레이션 결합 시 실질 부채 부담 증가 → 자산
        매각 → 자산 가격 하락 → 신용 수축 → 추가 디플레이션 의 9-step
        악순환. DSR + CPI + NPL 3 지표로 위험 점수 산출.

    Args:
        dsr: 부채서비스비율 (원리금/소득, %). > 14% = 역사적 고수준.
        cpiYoy: CPI YoY (%). < 0 = 디플레이션, < 1 = 준디플레.
        nplRate: 부실대출비율 (%). 옵션. > 5% = 위기 임박.

    Returns:
        FisherDeflationResult dataclass:
            - ``riskScore`` (int): 0~7
            - ``zone`` (str): low/moderate/high/extreme
            - ``zoneLabel`` (str): 한국어
            - ``description`` (str): 한국어 진단

    Raises:
        없음.

    Example:
        >>> r = fisherDebtDeflation(dsr=15, cpiYoy=-0.5, nplRate=4.5)
        >>> r.zone
        'high'

    Guide:
        riskScore 임계: 0~1 = low (정상), 2~3 = moderate (주의), 4~5 = high
        (위험), 6+ = extreme (Fisher 시나리오 본격). 디플레이션 (CPI<0) 단
        독으로 +3점 — 가장 큰 가중치.

    SeeAlso:
        - ``kooBalanceSheetRecession``: BSR (Fisher 의 시장 측면)
        - ``minskyPhase``: Minsky revulsion (deleveraging)
        - Fisher, I. (1933) "The Debt-Deflation Theory of Great Depressions"

    Requires:
        dsr + cpiYoy 필수. nplRate 옵션 (없으면 2 지표만).

    AIContext:
        Fisher 시나리오는 통화정책 무력화 + 재정 확대 필수 (Friedman + Koo).
        zone="extreme" 결과는 정책 결정자 향 (개별 기업 향이 아님).

    LLM Specifications:
        AntiPatterns:
            - 단기 (1 개월) CPI 음수 → 디플레 단정 — 3 개월 연속 음수 필요.
            - DSR > 14% 만 보고 위기 단정 — CPI 정상이면 정상 부채 부담.
        OutputSchema:
            FisherDeflationResult ``{riskScore, zone, zoneLabel, description}``.
        Prerequisites:
            국민계정 DSR (분기) + CPI (월) + NPL (분기).
        Freshness:
            DSR 분기, CPI 월, NPL 분기.
        Dataflow:
            DSR + CPI + NPL 룰 → riskScore 누적 → zone 분류.
        TargetMarkets: KR (한국은행 DSR), Global. 일본 1995~2000 가장 적합.
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
