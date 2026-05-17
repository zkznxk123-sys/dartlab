"""금융업 감지 + 불완전 연도 감지."""

from __future__ import annotations

from dartlab.analysis.financial.ratios import RatioResult
from dartlab.core.utils.extract import getAnnualValues, getLatest


def _parseYear(period: str) -> str:
    """period 문자열에서 연도 추출. 'YYYY_QN' / 'YYYY-QN' 모두 지원."""
    return period[:4]


def detectIncompleteYear(qPeriods: list[str]) -> tuple[str, int]:
    """최신 연도의 분기 수를 반환.

    Capabilities:
        - 최근 연도의 분기 카운트 → 4 미만이면 연간 합계 산출 차단 신호.

    Returns:
        (lastYear, quarterCount). quarterCount < 4면 불완전 연도.

    Guide:
        매 분기 종료 직후 호출. 4Q 누적 완료 전까지는 forecast/projection 로 표시.

    When:
        annualSeries 산출 직전. 불완전 연도면 연간 컬럼 제외 또는 표시 변경.

    How:
        qPeriods 마지막 entry 의 'YYYY' 접두로 startswith 카운트.

    Requires:
        qPeriods 비어있지 않음 (호출자가 검증).

    Raises:
        IndexError: qPeriods 가 빈 리스트.

    Example:
        >>> detectIncompleteYear(["2024_Q1", "2024_Q2", "2024_Q3"])
        ('2024', 3)

    See Also:
        - detectFinancialSector: 동일 모듈 다른 detector

    AIContext:
        ‘N 분기까지 발표’ 안내 시 인용. 연간 비교 시 incomplete 표시 의무.
    """
    lastPeriod = qPeriods[-1]
    lastYear = _parseYear(lastPeriod)
    qCount = sum(1 for p in qPeriods if p.startswith(lastYear))
    return lastYear, qCount


def detectFinancialSector(
    aSeries: dict,
    ratios: RatioResult,
) -> tuple[bool, list[str]]:
    """금융업 자동 감지 (신호 2개 이상이면 금융업).

    Capabilities:
        - 6 신호 (매출 부재 · 부채비율 > 500% · 유동성 미공시 · 이자/순이자/보험수익)
          중 ≥ 2 충족 시 금융업 판정.

    신호 후보 6개:
    1. sales 없고 operating_profit 있음
    2. 부채비율 500% 초과
    3. 유동자산/유동부채 데이터 없음
    4. 이자수익 계정 존재
    5. 순이자수익 계정 존재
    6. 보험수익 계정 존재

    Parameters
    ----------
    aSeries : dict
        finance.timeseries 시계열 dict.
    ratios : RatioResult
        재무비율 결과.

    Returns
    -------
    tuple[bool, list[str]]
        (금융업 여부, 감지된 신호 목록).

    Guide:
        GICS Financials 섹터가 정확하지 않은 한국 회사 보정. KB금융·삼성생명 같은 케이스 자동 분류.

    When:
        analyzeFinancial 초입 단계. isFinancial 결과는 후속 룰 (anomaly·grading) 분기 입력.

    How:
        getLatest/getAnnualValues 로 6 계정 존재 + ratios.debtRatio 임계 비교.

    Requires:
        aSeries 시계열 + ratios.debtRatio · currentRatio 사전 산출.

    Raises:
        없음.

    Example:
        >>> detectFinancialSector(aSeries, ratios)
        (True, ['부채비율 1200%', '이자수익 계정 존재'])

    See Also:
        - detectFinancialSectorAnomaly: 금융업 전용 이상치
        - analyzeFinancial: 상위 호출자

    AIContext:
        ‘금융업 분류 근거’ 답변 시 signals 목록 인용.
    """
    signals: list[str] = []

    revVals = getAnnualValues(aSeries, "IS", "sales")
    opVals = getAnnualValues(aSeries, "IS", "operating_profit")
    hasRevenue = any(v is not None for v in revVals)
    hasOpIncome = any(v is not None for v in opVals)
    if not hasRevenue and hasOpIncome:
        signals.append("sales 없고 operating_profit 있음")

    if ratios.debtRatio is not None and ratios.debtRatio > 500:
        signals.append(f"부채비율 {ratios.debtRatio:.0f}%")

    if ratios.currentRatio is None and getLatest(aSeries, "BS", "current_assets") is None:
        signals.append("유동자산/유동부채 데이터 없음")

    if getLatest(aSeries, "IS", "interest_income") is not None:
        signals.append("이자수익 계정 존재")

    if getLatest(aSeries, "IS", "net_interest_income") is not None:
        signals.append("순이자수익 계정 존재")

    if getLatest(aSeries, "IS", "insurance_revenue") is not None:
        signals.append("보험수익 계정 존재")

    return len(signals) >= 2, signals
