"""10영역 인사이트 등급 분석.

영역: performance, profitability, health, cashflow, governance, risk, opportunity,
      predictability, uncertainty, coreEarnings
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartlab.analysis.financial.insight.benchmark import getBenchmark, sectorAdjustment
from dartlab.analysis.financial.insight.detector import detectIncompleteYear
from dartlab.analysis.financial.insight.types import Flag, InsightResult
from dartlab.analysis.financial.ratios import RatioResult
from dartlab.core.utils.extract import getAnnualValues, getLatest
from dartlab.frame.sector import Sector

if TYPE_CHECKING:
    from dartlab.core.protocols import CompanyProtocol as Company


from dartlab.analysis.financial.insight._gradingForecast import (
    analyzeCoreEarnings,
    analyzePredictability,
    analyzeUncertainty,
    disclosureGapFlags,
)
from dartlab.analysis.financial.insight._gradingGovernance import (
    _analyzeGovernanceFromSections,
    analyzeGovernance,
)
from dartlab.analysis.financial.insight._gradingHelpers import (
    _getGrowthYoY,
    _getVolatility,
    _predictabilityGrade,
    _scoreToGrade,
    _uncertaintyGrade,
)


def analyzePerformance(
    aSeries: dict,
    aYears: list[str],
    qSeries: dict,
    qPeriods: list[str],
    isFinancial: bool = False,
) -> InsightResult:
    """실적 성장성 — 매출 + 영업이익 YoY + 변동성 (불완전 연도 자동 제외).

    Capabilities:
        연간 매출/영업이익 YoY 성장률 + 분기 시계열 변동성 (max quarterly
        change) 결합. 불완전 연도 (현재 진행 중 1Q/2Q/3Q) 자동 감지 + 제외
        (detectIncompleteYear). 금융업은 매출 대신 영업이익 사용.

    Args:
        aSeries: 연간 재무 시계열 dict (IS).
        aYears: 연간 기간 라벨 리스트.
        qSeries: 분기 재무 시계열 dict.
        qPeriods: 분기 기간 라벨 리스트.
        isFinancial: 금융업 여부. True 면 영업이익 기반.

    Returns:
        InsightResult dataclass:
            - ``grade`` (str): A~F
            - ``summary`` (str): 한국어
            - ``details`` (list[str])
            - ``risks``/``opportunities`` (list[Flag])

    Raises:
        없음. revGrowth=None 시 grade='N'.

    Example:
        >>> r = analyzePerformance(aSeries, ["2021","2022","2023"], qSeries, qPeriods)
        >>> r.grade, r.summary
        ('A', '매출 고성장 +25%, 영업이익 동반 성장')

    Guide:
        매출 성장률 임계: >20% = 고성장 (+3 score), 10~20% = 양호 (+2),
        0~10% = 안정 (+1), -10~0% = 감소, < -10% = 급감 (-2 + danger).
        영업이익 +50%+ = 급증, < -30% = 급감. 변동성 30%+ = warning.

    SeeAlso:
        - ``analyzeProfitability``: 수익성 (성장 + 마진)
        - ``calcStructuralBreak``: 매출/영업이익 구조변화점 감지
        - ``detectIncompleteYear``: 불완전 연도 식별

    Requires:
        aSeries 의 IS/sales + IS/operating_profit 시계열 ≥ 2 년.

    AIContext:
        성장률 단독 인용 금지 — 변동성 + 영업이익 동반 성장 여부 함께. 불완전
        연도 (예 2024 3Q) 가 자동 제외되므로 분기 정확도 영향 없음.

    LLM Specifications:
        AntiPatterns:
            - 단년도 YoY 만으로 grade 단정 — 본 함수는 3 년 추세 가능 시 활용.
            - 매출 급감 (-10%) → automatic F — 일회성 (M&A 분할 등) 가능
              하므로 영업이익 동반 확인.
        OutputSchema:
            InsightResult ``{grade, summary, details, risks, opportunities}``.
        Prerequisites:
            IS 시계열 ≥ 2 년 + 분기 시계열 (변동성용).
        Freshness:
            최신 분기. 불완전 연도 자동 제외.
        Dataflow:
            IS → revGrowth/opGrowth/volatility → score 누적 → grade →
            risks/opps Flag 생성.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    lastYear, qCount = detectIncompleteYear(qPeriods)
    incomplete = qCount < 4

    revVals = getAnnualValues(aSeries, "IS", "sales")
    opVals = getAnnualValues(aSeries, "IS", "operating_profit")

    if incomplete and len(aYears) > 1:
        useRevVals = revVals[:-1]
        useOpVals = opVals[:-1]
        correctionNote = f"(불완전연도 {lastYear} {qCount}Q 제외)"
    else:
        useRevVals = revVals
        useOpVals = opVals
        correctionNote = ""

    if isFinancial and not any(v is not None for v in useRevVals):
        useRevVals = useOpVals
        revLabel = "영업이익"
    else:
        revLabel = "매출"

    revGrowth = _getGrowthYoY(useRevVals)
    opGrowth = _getGrowthYoY(useOpVals)

    qRevVals = qSeries.get("IS", {}).get("sales", [])
    if isFinancial and not any(v is not None for v in qRevVals):
        qRevVals = qSeries.get("IS", {}).get("operating_profit", [])
    revVolatility = _getVolatility(qRevVals)
    qOpVals = qSeries.get("IS", {}).get("operating_profit", [])
    opVolatility = _getVolatility(qOpVals)

    details: list[str] = []
    risks: list[Flag] = []
    opps: list[Flag] = []
    score = 0

    if correctionNote:
        details.append(correctionNote)

    if revGrowth is not None:
        if revGrowth > 20:
            details.append(f"{revLabel} 고성장 (+{revGrowth:.1f}%)")
            opps.append(Flag("strong", "growth", f"{revLabel} {revGrowth:.1f}% 성장"))
            score += 3
        elif revGrowth > 10:
            details.append(f"{revLabel} 성장세 양호 (+{revGrowth:.1f}%)")
            score += 2
        elif revGrowth > 0:
            details.append(f"{revLabel} 소폭 성장 (+{revGrowth:.1f}%)")
            score += 1
        elif revGrowth > -10:
            details.append(f"{revLabel} 소폭 감소 ({revGrowth:.1f}%)")
        else:
            details.append(f"{revLabel} 급감 ({revGrowth:.1f}%)")
            risks.append(Flag("danger", "finance", f"{revLabel} {revGrowth:.1f}% 급감"))
            score -= 2

    if opGrowth is not None and not isFinancial:
        if opGrowth > 50:
            details.append(f"영업이익 급증 (+{opGrowth:.1f}%)")
            opps.append(Flag("strong", "growth", f"영업이익 {opGrowth:.1f}% 급증"))
            score += 3
        elif opGrowth > 15:
            details.append(f"영업이익 증가 (+{opGrowth:.1f}%)")
            score += 2
        elif opGrowth < -30:
            details.append(f"영업이익 급감 ({opGrowth:.1f}%)")
            risks.append(Flag("danger", "finance", f"영업이익 {opGrowth:.1f}% 급감"))
            score -= 2
        elif opGrowth < -10:
            details.append(f"영업이익 감소 ({opGrowth:.1f}%)")
            risks.append(Flag("warning", "finance", f"영업이익 {opGrowth:.1f}% 감소"))
            score -= 1

    if revVolatility is not None and revVolatility > 30:
        details.append(f"{revLabel} 변동성 높음 (분기 최대 {revVolatility:.1f}%)")
        risks.append(Flag("warning", "finance", f"{revLabel} 변동성 {revVolatility:.1f}%"))

    if not isFinancial and opVolatility is not None and opVolatility > 50:
        details.append(f"영업이익 변동성 높음 (분기 최대 {opVolatility:.1f}%)")
        risks.append(Flag("warning", "finance", f"영업이익 변동성 {opVolatility:.1f}%"))

    grade = _scoreToGrade(score, 6)
    if revGrowth is None:
        summary = "실적 데이터 부족"
    elif revGrowth > 20 and opGrowth and opGrowth > 30:
        summary = f"{revLabel}·이익 고성장"
    elif revGrowth > 10 and opGrowth and opGrowth > 10:
        summary = f"{revLabel}·이익 동반 성장"
    elif revGrowth > 0:
        summary = f"{revLabel} 성장세 유지"
    elif revGrowth > -10:
        summary = f"{revLabel} 정체"
    else:
        summary = f"{revLabel} 감소 추세"

    return InsightResult(grade, summary, details, risks, opps)


def analyzeProfitability(
    ratios: RatioResult,
    aSeries: dict,
    isFinancial: bool = False,
    sector: Sector = Sector.UNKNOWN,
    market: str = "KR",
) -> InsightResult:
    """수익성 분석 — 영업이익률 + ROE + ROA + 섹터 보정 + DuPont 분해.

    Capabilities:
        영업이익률 + 순이익률 (NM-OM 갭으로 영업외 영향 분석) + ROE + ROA
        + 섹터 벤치마크 보정 (sectorAdjustment) 결합. 금융업은 별도 함수
        (_analyzeProfitabilityFinancial). GICS 섹터별 다른 임계값 (IT 30%+,
        utility 5%+ 등).

    Args:
        ratios: RatioResult dataclass (operatingMargin, netMargin, roe, roa).
        aSeries: 연간 재무 시계열 dict.
        isFinancial: 금융업 여부. True 면 분기.
        sector: GICS 섹터 (Sector enum). 섹터 벤치마크 보정 입력.
        market: ``"KR"``/``"US"``. 벤치마크 선택 (KR/US 시장 ROE 평균 다름).

    Returns:
        InsightResult dataclass:
            - ``grade`` (str): A~F
            - ``summary`` (str)
            - ``details`` (list[str]): 영업이익률 + ROE + 레버리지 + 갭
            - ``risks``/``opportunities`` (list[Flag])

    Raises:
        없음.

    Example:
        >>> r = analyzeProfitability(ratios, aSeries, sector=Sector.IT, market="KR")
        >>> r.grade
        'A'  # IT 섹터 영업이익률 28%, ROE 22%

    Guide:
        영업이익률 임계 (비금융): > 20% = 우수 (+3), 10~20% = 양호 (+2),
        5~10% = 보통 (+1), 0~5% = 저조 (-1), < 0% = 적자 (-2). ROE > 15% =
        우수, > 10% = 양호. 섹터 보정으로 IT/utility 차이 반영.

    SeeAlso:
        - ``analyzePerformance``: 성장성 (수익성과 보완)
        - ``analyzeHealth``: 재무건전성 (ROE/레버리지 cross-check)
        - ``getBenchmark``: 섹터 벤치마크 룩업

    Requires:
        ratios = calcRatios 결과. sector enum (Sector.UNKNOWN 도 가능).

    AIContext:
        섹터별 임계값 차이 큼 — IT 영업이익률 20%+ 가 평균이지만 utility 는
        5%+ 가 우수. grade 만 인용 금지, 섹터 벤치마크 비교 함께.

    LLM Specifications:
        AntiPatterns:
            - 섹터 무시하고 절대 임계값 사용 — IT 의 5% 영업이익률을 "보통"
              평가하는 건 부정확 (IT 평균 25%+ 대비 매우 낮음).
            - 적자 회사를 자동 F — 신규 IPO 또는 turnaround 회사는 분기마다
              개선 추세 확인 필수.
        OutputSchema:
            InsightResult ``{grade, summary, details, risks, opportunities}``.
        Prerequisites:
            ratios (operatingMargin, netMargin, roe, roa) + sector enum.
        Freshness:
            최신 분기.
        Dataflow:
            ratios → 임계 + 섹터 보정 (getBenchmark) → score 누적 → grade.
        TargetMarkets: KR (DART), US (EDGAR). 섹터/market 별 분기.
    """
    details: list[str] = []
    risks: list[Flag] = []
    opps: list[Flag] = []
    score = 0

    if isFinancial:
        return _analyzeProfitabilityFinancial(aSeries, details, risks, opps)

    om = ratios.operatingMargin
    nm = ratios.netMargin
    roe = ratios.roe
    roa = ratios.roa

    if om is not None:
        if om > 20:
            details.append(f"영업이익률 우수 ({om:.1f}%)")
            opps.append(Flag("strong", "finance", f"영업이익률 {om:.1f}%"))
            score += 3
        elif om > 10:
            details.append(f"영업이익률 양호 ({om:.1f}%)")
            score += 2
        elif om > 5:
            details.append(f"영업이익률 보통 ({om:.1f}%)")
            score += 1
        elif om < 0:
            details.append(f"영업적자 ({om:.1f}%)")
            risks.append(Flag("danger", "finance", f"영업이익률 {om:.1f}% — 적자"))
            score -= 2
        else:
            details.append(f"영업이익률 저조 ({om:.1f}%)")
            score -= 1

    if om is not None and nm is not None and om != 0:
        gap = nm - om
        gapRatio = (gap / abs(om)) * 100
        if abs(gapRatio) > 50:
            if gap > 0:
                details.append(f"영업외수익 발생 (순이익률 {nm:.1f}% > 영업이익률 {om:.1f}%)")
                risks.append(Flag("warning", "finance", "본업 외 수익에 의존"))
            else:
                details.append(f"영업외비용 발생 (순이익률 {nm:.1f}% < 영업이익률 {om:.1f}%)")
                risks.append(Flag("warning", "finance", "영업외비용 확인 필요"))
        elif abs(gap) < 2 and nm > 0:
            details.append("영업이익≈순이익 — 본업 중심 수익구조")
            opps.append(Flag("positive", "finance", "건전한 수익구조"))

    if roe is not None:
        if roe > 20:
            details.append(f"ROE 우수 ({roe:.1f}%)")
            opps.append(Flag("strong", "finance", f"ROE {roe:.1f}%"))
            score += 2
        elif roe > 10:
            details.append(f"ROE 양호 ({roe:.1f}%)")
            score += 1
        elif roe < 5:
            details.append(f"ROE 저조 ({roe:.1f}%)")

    if roe is not None and roa is not None and roa > 0:
        leverage = roe / roa
        if isFinancial:
            # 금융업은 구조적으로 레버리지가 높음 (예수부채). 경고 대상이 아님
            details.append(f"금융업 레버리지 {leverage:.1f}x (구조적 특성)")
        elif leverage > 4:
            details.append(f"높은 레버리지로 ROE 달성 (ROE/ROA={leverage:.1f}x)")
            risks.append(Flag("warning", "finance", f"ROE/ROA {leverage:.1f}x — 부채 활용 높음"))
        elif leverage < 1.5 and roe > 15:
            details.append("낮은 레버리지로 고ROE — 진성 수익성")
            opps.append(Flag("strong", "finance", f"레버리지 {leverage:.1f}x로 ROE {roe:.1f}%"))

    bm = getBenchmark(sector, market)
    omAdj = sectorAdjustment(om, bm.omMedian, bm.omQ1, bm.omQ3)
    roeAdj = sectorAdjustment(roe, bm.roeMedian, bm.roeQ1, bm.roeQ3)
    adj = omAdj + roeAdj
    if adj != 0:
        score += adj
        direction = "상향" if adj > 0 else "하향"
        details.append(
            f"[섹터 보정 {direction}: {sector.value} 대비 OM{'↑' if omAdj > 0 else '↓' if omAdj < 0 else '→'} ROE{'↑' if roeAdj > 0 else '↓' if roeAdj < 0 else '→'}]"
        )

    grade = _scoreToGrade(score, 5)
    summary = "수익성 " + ("우수" if score >= 4 else "양호" if score >= 2 else "보통" if score >= 0 else "개선 필요")
    return InsightResult(grade, summary, details, risks, opps)


def _analyzeProfitabilityFinancial(
    aSeries: dict,
    details: list[str],
    risks: list[Flag],
    opps: list[Flag],
) -> InsightResult:
    """금융업 전용 수익성 분석 (ROE/ROA/CIR).

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.
    details : list[str]
        세부 항목 리스트 (in-place 추가).
    risks : list[Flag]
        리스크 플래그 리스트 (in-place 추가).
    opps : list[Flag]
        기회 플래그 리스트 (in-place 추가).

    Returns
    -------
    InsightResult
        grade : str — 'A'~'F' 등급
        summary : str — 금융업 수익성 요약
        details : list[str] — ROE, ROA, CIR 세부 항목
        risks : list[Flag] — 금융업 수익성 리스크
        opportunities : list[Flag] — 금융업 수익성 강점
    """
    details.append("[금융업 수익성 기준 적용]")
    score = 0
    netIncome = getLatest(aSeries, "IS", "net_profit")
    totalAssets = getLatest(aSeries, "BS", "total_assets")
    totalEquity = getLatest(aSeries, "BS", "owners_of_parent_equity") or getLatest(
        aSeries, "BS", "total_stockholders_equity"
    )
    opIncome = getLatest(aSeries, "IS", "operating_profit")
    opExpense = getLatest(aSeries, "IS", "operating_expense")

    roe = (netIncome / totalEquity) * 100 if netIncome and totalEquity and totalEquity > 0 else None
    roa = (netIncome / totalAssets) * 100 if netIncome and totalAssets and totalAssets > 0 else None
    cir = (
        (opExpense / (opExpense + opIncome)) * 100
        if opExpense is not None and opIncome is not None and (opExpense + opIncome) != 0
        else None
    )

    if roe is not None:
        if roe > 10:
            details.append(f"ROE 우수 ({roe:.1f}%)")
            opps.append(Flag("strong", "finance", f"금융업 ROE {roe:.1f}%"))
            score += 3
        elif roe > 8:
            details.append(f"ROE 양호 ({roe:.1f}%)")
            score += 2
        elif roe > 5:
            details.append(f"ROE 보통 ({roe:.1f}%)")
            score += 1
        else:
            details.append(f"ROE 저조 ({roe:.1f}%)")
            risks.append(Flag("warning", "finance", f"금융업 ROE {roe:.1f}%"))

    if roa is not None:
        if roa > 0.7:
            details.append(f"ROA 양호 ({roa:.2f}%)")
            score += 1
        elif roa > 0.4:
            details.append(f"ROA 보통 ({roa:.2f}%)")
        elif roa > 0:
            details.append(f"ROA 저조 ({roa:.2f}%)")
        else:
            details.append(f"ROA 적자 ({roa:.2f}%)")
            risks.append(Flag("danger", "finance", f"금융업 ROA {roa:.2f}%"))
            score -= 2

    if cir is not None:
        if cir < 50:
            details.append(f"CIR {cir:.1f}% — 효율적 운영")
            opps.append(Flag("positive", "finance", f"CIR {cir:.1f}%"))
            score += 1
        elif cir < 60:
            details.append(f"CIR {cir:.1f}% — 보통")
        else:
            details.append(f"CIR {cir:.1f}% — 비효율")
            risks.append(Flag("warning", "finance", f"CIR {cir:.1f}%"))

    grade = _scoreToGrade(score, 5)
    summary = "금융업 수익성 " + (
        "우수" if score >= 4 else "양호" if score >= 2 else "보통" if score >= 0 else "개선 필요"
    )
    return InsightResult(grade, summary, details, risks, opps)


def analyzeHealth(ratios: RatioResult, isFinancial: bool = False, currency: str = "KRW") -> InsightResult:
    """재무건전성 분석 — 부채비율 + 유동비율 + O-Score + Z''-Score + Piotroski.

    Capabilities:
        재무비율 + Altman Z''-Score (회사 부도예측) + Ohlson O-Score
        (10 변수) + Piotroski F-Score (9 가지) 결합하여 재무건전성 5 등급
        분류. 금융업/비금융업 분기, KRW/USD 통화별 다른 임계값 적용.

    Args:
        ratios: RatioResult dataclass — debtRatio, currentRatio, quickRatio,
            zScore, oScore, fScore, interestCoverage 등 포함.
        isFinancial: 금융업 여부. True 면 부채비율 기준 완화 (은행 BIS 8% 등).
        currency: ``"KRW"`` 또는 ``"USD"``. 임계값 분기 (예 부채비율 200%
            기준이 미국 시장에선 다름).

    Returns:
        InsightResult dataclass:
            - ``grade`` (str): A/B/C/D/F
            - ``summary`` (str): 한국어 요약
            - ``details`` (list[str]): 5+ 지표 분석 라인
            - ``risks`` (list[Flag]): 건전성 리스크 (warning/danger)
            - ``opportunities`` (list[Flag]): 건전성 강점

    Raises:
        없음. ratios=None 시 grade='N' 반환.

    Example:
        >>> from dartlab.core.ratios import calcRatios
        >>> ratios = calcRatios(company.finance.timeseries)
        >>> r = analyzeHealth(ratios)
        >>> r.grade, r.summary
        ('A', '재무건전성 우수 — 부채비율 80%, 유동비율 250%')

    Guide:
        Altman Z''-Score: > 2.9 = safe, 1.23~2.9 = grey, < 1.23 = distress.
        Piotroski F-Score: 9 = 최고, 0~3 = 부실. Ohlson O-Score 0.5 이상 =
        부도 확률 50%+. 본 함수는 3 모델 합산 + 부채비율 정성 평가.

    SeeAlso:
        - ``analyzeCashflow``: 현금흐름 (건전성과 보완)
        - ``credit.engine.evaluateCompany``: 종합 신용등급
        - ``dartlab.synth.distress.chsModel.calcCHS``: CHS 부도확률

    Requires:
        ratios = ``calcRatios(finance.timeseries)`` 결과.

    AIContext:
        grade + risks 함께 인용. F 등급 결과는 distress 신호 — credit 엔진
        호출 권장 (Track A 7 축 분해). 금융업 (은행/보험) 은 부채비율 1000%+
        가 정상이므로 isFinancial=True 명시 필수.

    LLM Specifications:
        AntiPatterns:
            - 비금융업 부채비율 200%+ → automatic F 단정 — 영업 부담 (예
              항공/조선) 고려 필요. 본 함수는 업종 보정 별도 적용.
            - O-Score 단독 인용 — Altman + Piotroski 와 cross-check 필수.
        OutputSchema:
            InsightResult ``{grade, summary, details, risks, opportunities}``.
        Prerequisites:
            ratios 가 calcRatios 출력 (RatioResult 인스턴스).
        Freshness:
            ratios = 최신 분기 (마감 후 30~45 일).
        Dataflow:
            ratios → 부채비율 + 유동/당좌비율 + Altman Z''-Score + Ohlson
            O-Score + Piotroski F-Score → 가중 score → grade 매핑.
        TargetMarkets: KR (DART), US (EDGAR). 통화별 임계값 분기.
    """
    details: list[str] = []
    risks: list[Flag] = []
    opps: list[Flag] = []
    score = 0
    dr = ratios.debtRatio
    cr = ratios.currentRatio

    if isFinancial:
        details.append("[금융업 기준 적용]")
        if dr is not None:
            if dr < 1000:
                details.append(f"부채비율 {dr:.0f}% — 금융업 양호")
                opps.append(Flag("positive", "finance", f"금융업 부채비율 {dr:.0f}%"))
                score += 3
            elif dr < 1500:
                details.append(f"부채비율 {dr:.0f}% — 금융업 보통")
                score += 1
            elif dr < 2000:
                details.append(f"부채비율 {dr:.0f}% — 금융업 다소 높음")
            else:
                details.append(f"부채비율 {dr:.0f}% — 금융업 과다")
                risks.append(Flag("warning", "finance", f"금융업 부채비율 {dr:.0f}%"))
                score -= 1
    elif currency == "USD":
        # US 기업: 자사주매입으로 equity 축소가 일반적, 부채비율 높음이 정상
        if dr is not None:
            if dr < 100:
                details.append(f"부채비율 매우 양호 ({dr:.0f}%)")
                opps.append(Flag("strong", "finance", f"부채비율 {dr:.0f}%"))
                score += 3
            elif dr < 200:
                details.append(f"부채비율 양호 ({dr:.0f}%)")
                opps.append(Flag("positive", "finance", f"부채비율 {dr:.0f}%"))
                score += 2
            elif dr < 400:
                details.append(f"부채비율 보통 ({dr:.0f}%)")
                score += 1
            elif dr < 600:
                details.append(f"부채비율 다소 높음 ({dr:.0f}%)")
            else:
                details.append(f"부채비율 과다 ({dr:.0f}%)")
                risks.append(Flag("warning", "finance", f"부채비율 {dr:.0f}%"))
                score -= 1

        if cr is not None:
            if cr > 150:
                details.append(f"유동성 매우 충분 ({cr:.0f}%)")
                opps.append(Flag("positive", "finance", f"유동비율 {cr:.0f}%"))
                score += 2
            elif cr > 100:
                details.append(f"유동성 충분 ({cr:.0f}%)")
                score += 1
            elif cr > 80:
                details.append(f"유동성 보통 ({cr:.0f}%)")
            else:
                details.append(f"유동성 부족 ({cr:.0f}%)")
                risks.append(Flag("warning", "finance", f"유동비율 {cr:.0f}%"))
                score -= 1
    else:
        if dr is not None:
            if dr < 50:
                details.append(f"부채비율 매우 양호 ({dr:.0f}%)")
                opps.append(Flag("strong", "finance", f"부채비율 {dr:.0f}%"))
                score += 3
            elif dr < 100:
                details.append(f"부채비율 양호 ({dr:.0f}%)")
                opps.append(Flag("positive", "finance", f"부채비율 {dr:.0f}%"))
                score += 2
            elif dr < 150:
                details.append(f"부채비율 보통 ({dr:.0f}%)")
                score += 1
            elif dr < 200:
                details.append(f"부채비율 다소 높음 ({dr:.0f}%)")
            else:
                details.append(f"부채비율 과다 ({dr:.0f}%)")
                risks.append(Flag("warning", "finance", f"부채비율 {dr:.0f}%"))
                score -= 1

        if cr is not None:
            if cr > 200:
                details.append(f"유동성 매우 충분 ({cr:.0f}%)")
                opps.append(Flag("positive", "finance", f"유동비율 {cr:.0f}%"))
                score += 2
            elif cr > 150:
                details.append(f"유동성 충분 ({cr:.0f}%)")
                score += 1
            elif cr > 100:
                details.append(f"유동성 보통 ({cr:.0f}%)")
            elif cr < 100:
                details.append(f"유동성 부족 ({cr:.0f}%)")
                risks.append(Flag("warning", "finance", f"유동비율 {cr:.0f}%"))
                score -= 1

    # ── 부실 예측 모델 신호 (ratios에서 계산된 값 활용) ──
    # Ohlson O-Score: P(bankruptcy) > 10% → 경고
    if ratios.ohlsonProbability is not None:
        if ratios.ohlsonProbability > 20:
            details.append(f"O-Score 부도확률 {ratios.ohlsonProbability:.1f}% — 고위험")
            risks.append(Flag("danger", "distress", f"O-Score P(부도) {ratios.ohlsonProbability:.1f}%"))
            score -= 2
        elif ratios.ohlsonProbability > 10:
            details.append(f"O-Score 부도확률 {ratios.ohlsonProbability:.1f}% — 주의")
            risks.append(Flag("warning", "distress", f"O-Score P(부도) {ratios.ohlsonProbability:.1f}%"))
            score -= 1

    # Altman Z''-Score (금융업 포함 범용)
    if ratios.altmanZppScore is not None:
        if ratios.altmanZppScore < 1.1:
            details.append(f"Z''-Score {ratios.altmanZppScore:.2f} — 부실 영역")
            risks.append(Flag("danger", "distress", f"Z'' {ratios.altmanZppScore:.2f} (부실)"))
            score -= 2
        elif ratios.altmanZppScore < 2.6:
            details.append(f"Z''-Score {ratios.altmanZppScore:.2f} — 회색 영역")
            risks.append(Flag("warning", "distress", f"Z'' {ratios.altmanZppScore:.2f} (회색)"))
            score -= 1
        elif ratios.altmanZppScore > 5:
            details.append(f"Z''-Score {ratios.altmanZppScore:.2f} — 안전")
            score += 1

    grade = _scoreToGrade(score, 7)
    label = "금융업 재무건전성" if isFinancial else "재무건전성"
    summary = f"{label} " + ("우수" if score >= 5 else "안정" if score >= 2 else "보통" if score >= 0 else "주의 필요")
    return InsightResult(grade, summary, details, risks, opps)


def analyzeCashflow(
    ratios: RatioResult,
    aSeries: dict,
    isFinancial: bool = False,
) -> InsightResult:
    """현금흐름 분석 — OCF/매출 + FCF 마진 + OCF/NI 안정성 (Sloan accrual 보강).

    Capabilities:
        영업현금흐름 마진 + FCF 마진 + OCF/NI (이익품질) + CF 추세 (3 년 CAGR)
        결합. Sloan (1996) accrual 분해와 연계해 "현금 뒷받침" 이익 vs 발생액
        의존 이익 구분. 금융업은 _analyzeCashflowFinancial 별도 분기.

    Args:
        ratios: RatioResult dataclass (ocfMargin, fcfMargin, ocfToNi 포함).
        aSeries: 연간 재무 시계열 dict (CF/IS).
        isFinancial: 금융업 여부. True 면 별도 함수로 분기.

    Returns:
        InsightResult dataclass:
            - ``grade`` (str): A~F
            - ``summary`` (str)
            - ``details`` (list[str]): OCF/매출, FCF 마진, OCF/NI 등
            - ``risks`` (list[Flag]): warning/danger 플래그
            - ``opportunities`` (list[Flag]): 강점 플래그

    Raises:
        없음.

    Example:
        >>> r = analyzeCashflow(ratios, aSeries=company.finance.timeseries)
        >>> r.grade
        'A'  # OCF/매출 15%, FCF 마진 10%, OCF/NI 1.2

    Guide:
        OCF/매출 > 15% = 매우 우수, 10~15% = 양호, < 5% = 부족. FCF 마진 양수
        (3 년 연속) = 자본배분 여력. OCF/NI > 1 = 이익이 현금으로 뒷받침,
        < 0.7 = 발생액 의존 (Sloan 경고).

    SeeAlso:
        - ``analyzeHealth``: 재무건전성 (현금흐름과 보완)
        - ``calcEarningsMomentum``: Sloan 분해 단독 호출
        - ``dartlab.synth.distress.chsFeatures``: CHS PD 계산

    Requires:
        ratios + aSeries (CF/IS 시계열 ≥ 3 년).

    AIContext:
        OCF/NI < 0.5 결과는 분식 위험 가능 — Sloan 의 academic 신호이지 즉시
        분식 단정 금지. 동종업종 평균과 비교 (calcPeerPrediction) 권장.

    LLM Specifications:
        AntiPatterns:
            - 단년도 OCF 만 보고 결론 — 3 년 평균 + 추세 (CAGR) 필수.
            - 신규 IPO 회사의 CapEx 큰 음수 FCF 를 "현금흐름 부실" 로 단정 —
              성장 회사는 정상 (Amazon 1997~2010 사례).
        OutputSchema:
            InsightResult ``{grade, summary, details, risks, opportunities}``.
        Prerequisites:
            CF 시계열 (operating_cashflow, capex) ≥ 3 년 + IS net_income.
        Freshness:
            최신 분기 + 3 년 시계열.
        Dataflow:
            ratios → ocfMargin/fcfMargin/ocfToNi 룰 → score 누적 → grade.
        TargetMarkets: KR (DART), US (EDGAR 표준 CF 동일).
    """
    if isFinancial:
        return _analyzeCashflowFinancial(aSeries)

    details: list[str] = []
    risks: list[Flag] = []
    opps: list[Flag] = []
    score = 0
    opCF = ratios.operatingCashflowTTM
    fcf = ratios.fcf
    revenue = ratios.revenueTTM

    if opCF is not None:
        if opCF > 0:
            details.append("영업활동 현금 창출 양호")
            score += 2
        else:
            details.append("영업활동 현금 적자")
            risks.append(Flag("danger", "finance", "영업CF 적자"))
            score -= 2

    if fcf is not None:
        if fcf > 0:
            if revenue and revenue > 0:
                fcfMargin = (fcf / revenue) * 100
                if fcfMargin > 15:
                    details.append(f"FCF 마진 우수 ({fcfMargin:.1f}%)")
                    opps.append(Flag("strong", "cashflow", f"FCF 마진 {fcfMargin:.1f}%"))
                    score += 3
                elif fcfMargin > 5:
                    details.append(f"FCF 마진 양호 ({fcfMargin:.1f}%)")
                    opps.append(Flag("positive", "cashflow", f"FCF 마진 {fcfMargin:.1f}%"))
                    score += 2
                else:
                    details.append(f"FCF 양호, 마진 저조 ({fcfMargin:.1f}%)")
                    score += 1
            else:
                details.append("FCF 양호")
                score += 1
        elif opCF and opCF > 0:
            details.append("FCF 적자 — 투자 확대 중")
            opps.append(Flag("positive", "growth", "적극 투자 (영업CF 양호)"))
        else:
            details.append("FCF 적자 — 현금 부족")
            risks.append(Flag("warning", "finance", "FCF + 영업CF 부진"))
            score -= 1

    cfVals = getAnnualValues(aSeries, "CF", "operating_cashflow")
    validCf = [v for v in cfVals if v is not None]
    if len(validCf) >= 2:
        improving = validCf[-1] > validCf[-2]
        if improving and validCf[-1] > 0:
            details.append("영업CF 개선 추세")
            score += 1
        elif not improving and validCf[-1] < validCf[-2]:
            details.append("영업CF 악화 추세")

    grade = _scoreToGrade(score, 6)
    summary = "현금흐름 " + ("우수" if score >= 5 else "양호" if score >= 2 else "보통" if score >= 0 else "주의")
    return InsightResult(grade, summary, details, risks, opps)


def _analyzeCashflowFinancial(aSeries: dict) -> InsightResult:
    """금융업 전용 현금흐름 분석.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.

    Returns
    -------
    InsightResult
        grade : str — 'A'~'F' 등급
        summary : str — 금융업 현금흐름 요약
        details : list[str] — 영업CF, 배당, 순이익 세부
        risks : list[Flag] — 리스크
        opportunities : list[Flag] — 강점
    """
    details: list[str] = ["[금융업 현금흐름]"]
    risks: list[Flag] = []
    opps: list[Flag] = []
    score = 0

    opCF = getLatest(aSeries, "CF", "operating_cashflow")
    dividendsPaid = getLatest(aSeries, "CF", "dividends_paid")
    netIncome = getLatest(aSeries, "IS", "net_profit")

    if opCF is not None:
        details.append(f"영업CF: {opCF / 1e8:,.0f}억")

    if dividendsPaid is not None and dividendsPaid > 0:
        details.append(f"배당 지급: {dividendsPaid / 1e8:,.0f}억")
        opps.append(Flag("positive", "shareholder", f"배당 지급 {dividendsPaid / 1e8:,.0f}억"))
        score += 1

    if netIncome is not None and netIncome > 0:
        details.append(f"순이익 {netIncome / 1e8:,.0f}억")
        score += 2

    grade = _scoreToGrade(score, 3)
    summary = "금융업 현금흐름 " + ("양호" if score >= 2 else "보통" if score >= 0 else "주의")
    return InsightResult(grade, summary, details, risks, opps)


def analyzeRiskSummary(insights: dict[str, InsightResult]) -> InsightResult:
    """8 인사이트 영역 리스크 통합 — 가장 위험한 영역 강조 + 종합 등급.

    Capabilities:
        8 인사이트 영역 (performance/profitability/health/cashflow/governance/
        predictability/uncertainty/coreEarnings) 의 risks Flag 를 모두 합쳐
        통합. severity 가중 (danger 3 / warning 2 / info 1) 합산하여 종합
        리스크 등급 산출.

    Args:
        insights: 영역별 InsightResult dict. analyzePerformance/Profitability/
            Health/Cashflow/Governance/Predictability/Uncertainty/CoreEarnings
            결과를 키-값으로 보유.

    Returns:
        InsightResult:
            - ``grade`` (str): A (낮은 리스크) ~ F (높은 리스크)
            - ``summary`` (str): 한국어 요약
            - ``details`` (list[str]): danger/warning 플래그 텍스트
            - ``risks`` (list[Flag]): 8 영역 전체 합집합

    Raises:
        없음. 빈 insights dict 시 grade='N'.

    Example:
        >>> insights = {"health": analyzeHealth(ratios),
        ...             "cashflow": analyzeCashflow(...)}
        >>> r = analyzeRiskSummary(insights)
        >>> r.grade, len(r.risks)
        ('B', 3)

    Guide:
        리스크 가중치: danger=3, warning=2, info=1. 합산 0~3 = A, 4~6 = B,
        7~9 = C, 10~14 = D, 15+ = F. 가장 많은 danger 가 어디서 왔는지
        details 첫 라인에 명시.

    SeeAlso:
        - ``analyzeOpportunitySummary``: 반대 (강점 통합)
        - ``credit.engine.evaluateCompany``: 본 함수와 별도 신용 등급
        - 본 함수 호출자: ``Company.insights``

    Requires:
        insights dict 가 영역별 InsightResult.risks 보유.

    AIContext:
        risks 리스트는 사용자 향 직접 텍스트 — 모두 노출 권장 (truncate
        금지). grade 만 인용 시 위험 종류 (governance vs health) 정보 손실.

    LLM Specifications:
        AntiPatterns:
            - 단일 영역 (예 health) 만 보고 종합 리스크 판단 — 8 영역 합집합 권장.
            - 빈 risks 리스트 → A 등급 — 실제 데이터 부족일 수도 있으므로
              insights 키 개수 확인 함께.
        OutputSchema:
            InsightResult ``{grade, summary, details, risks}``.
        Prerequisites:
            insights dict 의 영역별 InsightResult (risks 필드 보유).
        Freshness:
            영역별 InsightResult freshness (최신 분기).
        Dataflow:
            8 영역 risks → severity 가중 합산 → grade 매핑 → details
            (danger 우선) 합성.
        TargetMarkets: KR + US. 영역별 분석에 따라 분기.
    """
    allRisks: list[Flag] = []
    for key in [
        "performance",
        "profitability",
        "health",
        "cashflow",
        "governance",
        "predictability",
        "uncertainty",
        "coreEarnings",
    ]:
        if key in insights and insights[key] is not None:
            allRisks.extend(insights[key].risks)

    if not allRisks:
        return InsightResult("A", "특별한 리스크 없음", ["주요 재무지표 양호"])

    dangerCount = sum(1 for r in allRisks if r.level == "danger")
    warningCount = sum(1 for r in allRisks if r.level == "warning")

    if dangerCount >= 2:
        grade = "F"
        summary = f"중대 리스크 {dangerCount}건"
    elif dangerCount == 1:
        grade = "D"
        summary = f"리스크 경고 (위험 {dangerCount}, 주의 {warningCount})"
    elif warningCount > 3:
        grade = "D"
        summary = f"다수 주의 ({warningCount}건)"
    elif warningCount > 1:
        grade = "C"
        summary = f"일부 주의 ({warningCount}건)"
    else:
        grade = "B"
        summary = "경미한 주의 사항"

    return InsightResult(grade, summary, [r.text for r in allRisks], allRisks)


def analyzeOpportunitySummary(insights: dict[str, InsightResult]) -> InsightResult:
    """기회 종합 분석.

    Parameters
    ----------
    insights : dict[str, InsightResult]
        영역별 인사이트 결과.

    Returns
    -------
    InsightResult
        grade : str — 'A'~'F' 등급
        summary : str — 기회 종합 요약
        details : list[str] — 개별 기회 텍스트 목록
        opportunities : list[Flag] — 전체 기회 플래그 취합
    """
    allOpps: list[Flag] = []
    for key in [
        "performance",
        "profitability",
        "health",
        "cashflow",
        "governance",
        "predictability",
        "uncertainty",
        "coreEarnings",
    ]:
        if key in insights and insights[key] is not None:
            allOpps.extend(insights[key].opportunities)

    if not allOpps:
        return InsightResult("D", "특별한 투자 기회 없음")

    strongCount = sum(1 for o in allOpps if o.level == "strong")
    positiveCount = sum(1 for o in allOpps if o.level == "positive")
    total = strongCount + positiveCount

    if strongCount >= 3 and total >= 5:
        grade = "A"
        summary = f"투자 매력 높음 ({strongCount}강점, {positiveCount}긍정)"
    elif strongCount >= 2:
        grade = "B"
        summary = f"투자 매력 있음 ({strongCount}강점)"
    elif strongCount >= 1 or positiveCount >= 3:
        grade = "C"
        summary = f"일부 긍정 ({strongCount}강점, {positiveCount}긍정)"
    elif positiveCount >= 1:
        grade = "D"
        summary = f"긍정 요소 미약 ({positiveCount}건)"
    else:
        grade = "F"
        summary = "투자 매력 없음"

    return InsightResult(grade, summary, [o.text for o in allOpps], opportunities=allOpps)
