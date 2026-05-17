"""review가 소비하는 calc 인터페이스 — credit 엔진 래퍼.

credit/ 독립 엔진이 계산의 단일 진실(source of truth)이다.
이 모듈은 review가 소비할 수 있는 calc 인터페이스를 제공하는 thin wrapper.

직접 접근: dartlab.credit("005930") 또는 c.credit()
story 경유: c.story("신용분석")

cross-dependency 방지: analysis ↛ credit, credit ↛ analysis.
이전에는 analysis/financial/creditRating.py에 있었으나
analysis-credit 간 순환 의존 제거를 위해 credit/ 내부로 이동.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc as _memoized_calc

# ── credit 엔진 호출 ──


def _evaluate(company, basePeriod=None):
    """credit 엔진 호출 (캐시 공유를 위한 내부 함수)."""
    from dartlab.credit.engine import evaluateCompany

    return evaluateCompany(company, detail=True, basePeriod=basePeriod)


# ═══════════════════════════════════════════════════════════
# calc 함수들 — review가 소비하는 인터페이스
# credit/ 엔진의 결과를 story 형식으로 변환
# ═══════════════════════════════════════════════════════════


@_memoized_calc
def calcCreditMetrics(company, *, basePeriod: str | None = None) -> dict | None:
    """신용분석 핵심 지표 시계열 — 7 축 metrics + 사업안정성.

    Capabilities:
        evaluateCompany 의 metricsHistory 노출 — 기간별 7 축 (상환력/레버리지/
        유동성/수익성/구조/시장신호/지배구조) 지표 시계열 + businessStability
        (opMarginCV, revenueCV 변동성 지표) 동행. 신용 점수 출력 전 입력 데이터
        가시화.

    Args:
        company: DartCompany | EdgarCompany 인스턴스.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 기간별 7 축 metrics (calcAllMetrics 결과).
            - ``businessStability`` (dict): opMarginCV/revenueCV 등 변동성.

    Raises:
        없음.

    Example:
        >>> r = calcCreditMetrics(Company("005930"))
        >>> r["history"][0]["repayment"]["interestCoverage"]
        18.5

    Guide:
        - 본 함수는 metrics 만 — 점수/등급은 calcCreditScore.
        - businessStability 의 CV (coefficient of variation) 가 낮을수록
          업황 안정 (CV < 0.2 = 매우 안정).
        - 7 축 metrics 가 axis_evaluators 의 입력.

    SeeAlso:
        - ``calcCreditScore``: 종합 등급
        - ``calcCreditHistory``: 등급 시계열
        - ``credit.scoring.metrics.calcAllMetrics``: 7 축 metrics 본체

    When:
        ``c.credit("metrics")`` / story 5-7 신용 섹션 raw 입력 필요할 때.

    How:
        ``_evaluate(detail=True)`` → metricsHistory + businessStability 추출 → dict.

    Requires:
        DART/EDGAR 재무 시계열 (IS/BS/CF + 시가총액).

    AIContext:
        history latest 키 인용 + businessStability CV 함께. metrics 단독 인용
        시 점수 변환 (calcCreditScore) 누락 명시.

    LLM Specifications:
        AntiPatterns:
            - metrics 인용으로 등급 추론 — calcCreditScore 필수.
            - 단년도 metric 만 인용 — history 시계열 함께.
        OutputSchema:
            ``{history: list[dict], businessStability: dict}``.
        Prerequisites:
            IS/BS/CF + 시가총액.
        Freshness:
            분기.
        Dataflow:
            evaluateCompany → metricsHistory → 7 축 metric + businessStability.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None
    history = result.get("metricsHistory")
    if not history:
        return None
    return {
        "history": history,
        "businessStability": result.get("businessStability"),
    }


@_memoized_calc
def calcCreditScore(company, *, basePeriod: str | None = None, overrides: dict | None = None) -> dict | None:
    """신용등급 종합 산출 — 7 축 가중합 + override 시나리오.

    Capabilities:
        7 축 (상환력/레버리지/유동성/수익성/구조/시장신호/지배구조) 가중합
        → 0~100 score → 20 단계 grade (AAA~D) + PD (확률) 매핑. overrides 로
        부채비율/IC 등 가정 교체 시나리오 가능. Damodaran credit synthetic
        rating + Moody's RiskCalc 표준 융합.

    Args:
        company: DartCompany | EdgarCompany.
        basePeriod: 기준 기간.
        overrides: 시나리오 가정 (CREDIT_KEYS 만). 예: ``{"debtRatio": 150}``.

    Returns:
        dict | None: evaluateCompany 결과 dict (grade, score, axes, ...).
            overrides 적용 시 ``overrides``/``overrideNote`` 키 추가.

    Raises:
        없음 (None 시 데이터 부족).

    Example:
        >>> r = calcCreditScore(Company("005930"))
        >>> r["grade"], r["score"]
        ('AA+', 87.5)
        >>> r2 = calcCreditScore(Company("005930"), overrides={"debtRatio": 200})
        >>> r2["overrideNote"]
        'AI/사용자 override 적용 시나리오'

    Guide:
        - investment grade (AAA~BBB-) vs speculative (BB+~D) 경계 주목.
        - 단년도 grade 단독 인용 금지 — calcCreditHistory 시계열 함께.
        - overrides 는 stress test 용 — 실제 등급과 구분 명시.

    SeeAlso:
        - ``calcCreditMetrics``: 7 축 metrics 입력
        - ``calcCreditHistory``: 등급 시계열
        - ``calcGradeImprovement``: 개선 시나리오

    When:
        ``c.credit("score")`` 호출. AI 가 stress 시나리오 답변 (overrides 주입) 시.

    How:
        ``_evaluate`` → result 반환 (overrides 있으면 validate 후 dict 에 주입).

    Requires:
        IS/BS/CF + 시가총액 + 시장신호 (베타/변동성).

    AIContext:
        grade + score + 핵심 axes 함께 인용. overrides 사용 시 가정 명시 +
        실제와 분리. PD 단독 인용 금지 (grade 매핑 표준).

    LLM Specifications:
        AntiPatterns:
            - 단년도 grade 단정 — 시계열 (calcCreditHistory) 함께.
            - overrides 결과를 실제 grade 로 인용 — 시나리오임 명시.
        OutputSchema:
            ``{grade: str, score: float, axes: list, pd: float, ...,
              overrides?: dict, overrideNote?: str}``.
        Prerequisites:
            IS/BS/CF + 시가총액.
        Freshness:
            분기.
        Dataflow:
            evaluateCompany → 7 축 score → 가중합 → grade mapping → (옵션)
            override applied.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    result = _evaluate(company, basePeriod)
    # override 적용: 시나리오 부채비율 등으로 등급 재산출
    if result and overrides:
        from dartlab.synth.overrides import validateOverrides

        ov = validateOverrides(overrides)
        if ov:
            result["overrides"] = ov
            result["overrideNote"] = "AI/사용자 override 적용 시나리오"
    return result


@_memoized_calc
def calcCreditHistory(company, *, basePeriod: str | None = None) -> dict | None:
    """신용등급 시계열.

    Capabilities:
        evaluateCompany metricsHistory 의 기간별 metric 을 다시 sectorThresholds 룩업 → metric
        score → 평균 → mapTo20Grade 로 변환해 기간별 grade 시계열 산출. ``stable`` 플래그로 등급
        변동성 판정.

    기간별 간이 점수를 산출하고, 등급 안정성을 판단한다.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 등급 시계열
            period : str — 기간 (예: "2024")
            score : float — 간이 위험 점수 (점)
            grade : str — 등급 코드 (예: "AA+")
            pdEstimate : float — 추정 부도확률 (%)
        stable : bool — 등급 안정성 (고유 등급 2개 이하면 True)
        latestGrade : str | None — 최신 기간 등급
        oldestGrade : str | None — 가장 오래된 기간 등급

    Raises:
        없음 — metricsHistory 부재 시 None.

    Example:
        >>> r = calcCreditHistory(Company("005930"))
        >>> r["stable"], r["latestGrade"]
        (True, 'AA+')

    Guide:
        본 함수는 5 개 metric 평균으로 간이 grade 추정 — engine 의 7 축 가중평균과 약간 다름.
        시계열 변동 추세 답변에 적합.

    When:
        ``c.credit("history")`` 호출. 등급 안정성 답변, Story 변화 섹션.

    How:
        ``_evaluate`` → metricsHistory 루프 → sectorThresholds.scoreMetric → 5 metric 평균 →
        mapTo20Grade → 기간별 entry.

    Requires:
        - IS/BS/CF 시계열 (``_evaluate`` 결과 metricsHistory) + sectorThresholds

    SeeAlso:
        - ``dartlab.credit.scoring.calcs.calcCreditScore`` : 7 축 정식 grade
        - ``dartlab.credit.scoring.creditScorecard.mapTo20Grade`` : 점수→등급

    AIContext:
        AI 답변 "등급 추세" 시 본 결과 직접 인용. ``stable=False`` 면 변동성 단서 필수.
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    from dartlab.credit.features.sectorThresholds import getThresholds
    from dartlab.credit.scoring.creditScorecard import mapTo20Grade, scoreMetric

    history_data = result.get("metricsHistory", [])
    if not history_data:
        return None

    sector, ig = None, None
    try:
        si = getattr(company, "sector", None)
        if si:
            sector, ig = si.sector, si.industryGroup
    except (AttributeError, ImportError):
        pass

    thresholds = getThresholds(sector, ig)
    history = []
    for h in history_data:
        scores = []
        for key, tKey in [
            ("ffoToDebt", "ffo_to_debt"),
            ("debtToEbitda", "debt_to_ebitda"),
            ("ebitdaInterestCoverage", "ebitda_interest_coverage"),
            ("debtRatio", "debt_ratio"),
            ("currentRatio", "current_ratio"),
        ]:
            s = scoreMetric(h.get(key), thresholds[tKey])
            if s is not None:
                scores.append(s)
        if scores:
            periodScore = round(sum(scores) / len(scores), 2)
            grade, _, pd = mapTo20Grade(periodScore)
            history.append(
                {
                    "period": h["period"],
                    "score": periodScore,
                    "grade": grade,
                    "pdEstimate": pd,
                }
            )

    if not history:
        return None

    grades = [h["grade"] for h in history]
    return {
        "history": history,
        "stable": len(set(grades)) <= 2,
        "latestGrade": history[0]["grade"] if history else None,
        "oldestGrade": history[-1]["grade"] if history else None,
    }


@_memoized_calc
def calcCashFlowGrade(company, *, basePeriod: str | None = None) -> dict | None:
    """현금흐름등급 (eCR) 시계열 — OCF 기반 자체 신용등급.

    Capabilities:
        OCF/매출 + FCF 양수 여부 + OCF/총차입금 세 가지로 기간별 eCR 등급
        (AAA~D 매핑) 산출. Moody's CFR (Corporate Family Rating) 의 cash flow
        강도 component 와 유사. 회계상 등급 (calcCreditScore) 와 직교 — 현금
        창출력 단독 평가.

    Args:
        company: DartCompany | EdgarCompany.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``history`` (list[dict]): 기간별 (period, eCR, ocfToSales,
              fcfPositive, ocfToDebt).

    Raises:
        없음.

    Example:
        >>> r = calcCashFlowGrade(Company("005930"))
        >>> r["history"][0]["eCR"], r["history"][0]["ocfToSales"]
        ('A', 18.5)  # OCF/매출 18.5% → A 등급

    Guide:
        - eCR > 회계 grade 면 현금 우위 (적자 회사가 현금 창출은 우수).
        - eCR < 회계 grade 면 현금 약점 (이익 보이지만 현금 부족 — 매출채권
          누적 의심).
        - FCF 음수 3 기 연속 = downgrade 신호.

    SeeAlso:
        - ``calcCreditScore``: 회계 grade
        - ``calcDistressScore``: Altman Z
        - ``analysis.financial.calcCashGenerationQuality``: OCF 품질

    When:
        ``c.credit("cashflow")`` 호출. AI 답변 "현금 창출 grade" 시.

    How:
        metricsHistory 루프 → ocfToSales / fcfPositive / ocfToDebt → ``cashFlowGrade`` 호출 →
        기간별 eCR.

    Requires:
        CF (영업현금흐름) + IS (매출) + BS (차입금) 시계열.

    AIContext:
        eCR + ocfToSales + ocfToDebt 함께. 회계 grade 와 비교 시 차이 해석
        (현금/이익 괴리).

    LLM Specifications:
        AntiPatterns:
            - eCR 단독 인용으로 회계 grade 대체 — 두 grade 모두 노출.
            - FCF 음수 단년도 단정 — 3 기 추세 함께.
        OutputSchema:
            ``{history: list[dict 5키]}``.
        Prerequisites:
            CF + IS + BS 시계열.
        Freshness:
            분기.
        Dataflow:
            metricsHistory → ocfToSales + fcfPositive + ocfToDebt → cashFlowGrade
            함수 → eCR.
        TargetMarkets: KR (DART), US (EDGAR — CF Statement 표준).
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    from dartlab.credit.scoring.creditScorecard import cashFlowGrade

    history_data = result.get("metricsHistory", [])
    if not history_data:
        return None

    history = []
    for h in history_data:
        eCR = cashFlowGrade(
            h.get("ocfToSales"),
            h.get("fcf") is not None and (h.get("fcf") or 0) > 0,
            h.get("ocfToDebt"),
        )
        history.append(
            {
                "period": h["period"],
                "eCR": eCR,
                "ocfToSales": h.get("ocfToSales"),
                "fcfPositive": h.get("fcf") is not None and (h.get("fcf") or 0) > 0,
                "ocfToDebt": h.get("ocfToDebt"),
            }
        )

    return {"history": history} if history else None


@_memoized_calc
def calcCreditPeerPosition(company, *, basePeriod: str | None = None) -> dict | None:
    """업종 내 신용 순위.

    Capabilities:
        대상 회사 최신 분기 4 핵심 지표 (부채비율/IC/FFO-Debt/유동비율) 를 dict 로 노출. peer
        비교 데이터는 현재 미구현 (``peerAvailable=False``) — 호출자가 별도 peer 매칭 필요.

    최신 기간의 핵심 지표를 추출하여 peer 비교 기반 제공.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        latestPeriod : str — 최신 분석 기간
        metrics : dict — 핵심 비교 지표
            debtRatio : float | None — 부채비율 (%)
            ebitdaInterestCoverage : float | None — EBITDA/이자비용 (배)
            ffoToDebt : float | None — FFO/총차입금 (%)
            currentRatio : float | None — 유동비율 (%)
        peerAvailable : bool — peer 데이터 가용 여부

    Raises:
        없음.

    Example:
        >>> r = calcCreditPeerPosition(Company("005930"))
        >>> r["metrics"]["debtRatio"]
        38.5

    Guide:
        ``peerAvailable=False`` 이면 peer 분포는 ``industry.calcs.companyCalcs.calcSectorMetrics``
        결과와 결합 권장. 본 함수 단독으로는 "내 지표" 만 노출.

    When:
        ``c.credit("peer")`` 호출. AI 가 동종 비교 답변 시 본 결과 + sectorMetrics 결합.

    How:
        ``_evaluate`` → metricsHistory[0] 추출 → 4 metric 노출.

    Requires:
        - IS/BS/CF 시계열 (evaluateCompany 결과)

    See Also:
        - ``dartlab.industry.calcs.companyCalcs.calcSectorMetrics`` : 동종 분포

    AIContext:
        AI 답변 시 "동종 분포 별도 조회 필요" 단서 명시. metric 단독 인용으로 "업계 1 위" 단정
        금지.
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    history_data = result.get("metricsHistory", [])
    if not history_data:
        return None

    latest = history_data[0]
    return {
        "latestPeriod": latest.get("period"),
        "metrics": {
            "debtRatio": latest.get("debtRatio"),
            "ebitdaInterestCoverage": latest.get("ebitdaInterestCoverage"),
            "ffoToDebt": latest.get("ffoToDebt"),
            "currentRatio": latest.get("currentRatio"),
        },
        "peerAvailable": False,
    }


# ── calcCreditFlags + calcCreditNarrative + calcCreditAudit + calcGradeImprovement → _calcsAdvanced.py 분리 ──

from dartlab.credit.scoring._calcsAdvanced import (  # noqa: E402, F401
    calcCreditAudit,
    calcCreditFlags,
    calcCreditNarrative,
    calcGradeImprovement,
)
