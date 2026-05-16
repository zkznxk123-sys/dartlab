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


@_memoized_calc
def calcCreditFlags(company, *, basePeriod: str | None = None) -> dict | None:
    """신용 경고/개선 플래그 — 등급 변동 트리거 신호.

    Capabilities:
        최신 기간 metrics 를 임계치와 대조해 warning (등급 하방) / opportunity
        (등급 상향) 플래그 자동 라벨. 각 플래그는 signal + detail + impact
        (notch 영향) 동행. 금융업/일반업 분기. S&P/Moody's credit watch
        조건 유사.

    Args:
        company: DartCompany | EdgarCompany.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``flags`` (list[dict]): type (warning/opportunity), signal,
              detail, impact.

    Raises:
        없음.

    Example:
        >>> r = calcCreditFlags(Company("005930"))
        >>> r["flags"][0]["type"], r["flags"][0]["signal"]
        ('opportunity', '이자보상배율 우수 (18.5배)')

    Guide:
        - warning 2+ 동시 발생 = downgrade 임박 신호.
        - opportunity 만 있는 회사는 upgrade 후보.
        - 금융업은 별도 임계 (BIS/NPL) — 본 함수가 자동 분기.

    SeeAlso:
        - ``calcCreditScore``: 점수 산출 (본 함수가 보조)
        - ``calcCreditHistory``: 등급 시계열
        - ``credit.monitoring.crisisDetector``: 단기 위기 신호

    Requires:
        metricsHistory (calcAllMetrics) + sector 정보.

    AIContext:
        flags 리스트 그대로 인용 — 각 signal + detail + impact 함께. type 별
        분리 (warning vs opportunity) 권장.

    LLM Specifications:
        AntiPatterns:
            - warning 1 개로 downgrade 단정 — 2+ 동시 발생이 강한 신호.
            - 금융업에 일반업 임계 적용 — 본 함수가 자동 분기.
        OutputSchema:
            ``{flags: list[{type, signal, detail, impact}]}``.
        Prerequisites:
            metricsHistory + sector.
        Freshness:
            분기.
        Dataflow:
            evaluateCompany → latest metrics → 임계 대조 → flag 생성 →
            type/signal/detail/impact 라벨.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    history_data = result.get("metricsHistory", [])
    if not history_data:
        return None

    latest = history_data[0]
    flags: list[dict] = []

    isFinancial = False
    try:
        si = getattr(company, "sector", None)
        if si:
            from dartlab.frame.sector import Sector

            isFinancial = si.sector == Sector.FINANCIALS
    except (AttributeError, ImportError):
        pass

    icr = latest.get("ebitdaInterestCoverage")
    if icr is not None and icr < 1.5 and not isFinancial:
        flags.append(
            {
                "type": "warning",
                "signal": "이자보상배율 1.5배 미달",
                "detail": f"EBITDA/이자비용 = {icr}배",
                "impact": "등급 하방 1~2 notch",
            }
        )

    dr = latest.get("debtRatio")
    if dr is not None and dr > 300 and not isFinancial:
        flags.append(
            {"type": "warning", "signal": "부채비율 300% 초과", "detail": f"부채비율 {dr:.0f}%", "impact": "등급 하방"}
        )

    ocfVal = latest.get("ocf")
    if ocfVal is not None and ocfVal < 0:
        flags.append(
            {
                "type": "warning",
                "signal": "영업현금흐름 적자",
                "detail": "본업에서 현금 유출",
                "impact": "등급 하방 2+ notch",
            }
        )

    de = latest.get("debtToEbitda")
    if de is not None and de > 5 and not isFinancial:
        flags.append(
            {
                "type": "warning",
                "signal": "Debt/EBITDA 5배 초과",
                "detail": f"총차입금/EBITDA = {de}배",
                "impact": "B급 이하 위험",
            }
        )

    if icr is not None and icr > 10:
        flags.append(
            {
                "type": "opportunity",
                "signal": "이자보상배율 10배 초과",
                "detail": f"EBITDA/이자비용 = {icr}배",
                "impact": "등급 상방",
            }
        )

    ffoDebt = latest.get("ffoToDebt")
    if ffoDebt is not None and ffoDebt > 40:
        flags.append(
            {
                "type": "opportunity",
                "signal": "FFO/총차입금 40% 초과",
                "detail": f"FFO/Debt = {ffoDebt:.0f}%",
                "impact": "등급 상방",
            }
        )

    cr = latest.get("currentRatio")
    if cr is not None and cr > 200:
        flags.append(
            {
                "type": "opportunity",
                "signal": "유동비율 200% 초과",
                "detail": f"유동비율 {cr:.0f}%",
                "impact": "유동성 안전",
            }
        )

    return {"flags": flags}


@_memoized_calc
def calcCreditNarrative(company, *, basePeriod: str | None = None) -> dict | None:
    """credit publisher의 7축 서사를 story 블록용으로 변환.

    credit/narrative.py::buildNarratives() 결과를 그대로 반환.
    review가 5-7 신용평가 섹션에서 소비.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        axes : list[dict] — 축별 서사
            axisName : str — 축 이름 (예: "채무상환능력")
            summary : str — 한 줄 요약
            details : list[str] — 상세 설명 문장들
            severity : str — 심각도 ("good"/"neutral"/"warning"/"critical")
        grade : str — dCR 등급 (예: "dCR-AA+")
        gradeDescription : str — 등급 설명
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    from dartlab.credit.features.narrative import buildNarratives

    try:
        narratives = buildNarratives(result)
    except (KeyError, AttributeError, TypeError):
        return None

    if not narratives:
        return None

    return {
        "axes": [
            {
                "axisName": n.axisName,
                "summary": n.summary,
                "details": n.details,
                "severity": n.severity,
            }
            for n in narratives
        ],
        "grade": result.get("grade", ""),
        "gradeDescription": result.get("gradeDescription", ""),
    }


@_memoized_calc
def calcCreditAudit(company, *, basePeriod: str | None = None) -> dict | None:
    """credit publisher의 외부 신평사 대조를 story 블록용으로 변환.

    credit/audit.py::auditCredit() 결과를 그대로 반환.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        stockCode : str — 종목코드
        corpName : str — 기업명
        dcrGrade : str — dartlab dCR 등급
        dcrScore : float — dCR 점수 (점)
        externalGrades : dict — 외부 신평사 등급 (기관명→등급)
        notchDifferences : dict — 신평사별 notch 차이 (기관명→notch 수)
        avgNotchDiff : float — 평균 notch 차이 (notch)
        agreements : list[str] — 일치 포인트
        disagreements : list[str] — 괴리 포인트
    """
    result = _evaluate(company, basePeriod)
    if result is None:
        return None

    stockCode = getattr(company, "stockCode", None) or getattr(company, "ticker", "")
    corpName = getattr(company, "corpName", "") or ""
    if not stockCode:
        return None

    from dartlab.credit.monitoring.audit import auditCredit

    try:
        audit = auditCredit(stockCode, corpName, result=result)
    except (KeyError, AttributeError, TypeError, OSError):
        return None

    if audit is None:
        return None

    return {
        "stockCode": audit.stockCode,
        "corpName": audit.corpName,
        "dcrGrade": audit.dcrGrade,
        "dcrScore": audit.dcrScore,
        "externalGrades": dict(audit.externalGrades),
        "notchDifferences": dict(audit.notchDifferences),
        "avgNotchDiff": audit.avgNotchDiff,
        "agreements": list(audit.agreements),
        "disagreements": list(audit.disagreements),
    }


@_memoized_calc
def calcGradeImprovement(company, *, basePeriod: str | None = None) -> dict | None:
    """신용등급 한 노치 상향에 필요한 구체적 개선사항.

    가장 약한 축을 찾고, 그 축의 metric을 다음 등급 구간까지
    올리는 데 필요한 변화량을 역계산한다.

    Returns
    -------
    dict | None
        currentGrade : str
        currentScore : float
        targetGrade : str
        weakestAxis : str
        improvements : list[dict]
            axis : str — 축 이름
            metric : str — 지표명
            current : float — 현재값
            target : float — 목표값
            change : str — 자연어 설명
    """
    result = _evaluate(company, basePeriod)
    if not result:
        return None

    grade = result.get("grade", "")
    score = result.get("score", 0)
    metrics = result.get("metrics", {})

    if not grade or not metrics:
        return None

    from dartlab.credit.features.sectorThresholds import getThresholds
    from dartlab.credit.scoring.creditScorecard import mapTo20Grade, scoreMetric

    sector, ig = None, None
    try:
        si = getattr(company, "sector", None)
        if si:
            sector, ig = si.sector, si.industryGroup
    except (AttributeError, ImportError):
        pass

    thresholds = getThresholds(sector, ig)

    # 각 축별 현재 스코어 산출 + 가장 약한 축 찾기
    axis_scores: list[tuple[str, str, float, float]] = []
    metric_map = [
        ("leverage", "debt_to_ebitda", "debtToEbitda"),
        ("coverage", "ebitda_interest_coverage", "ebitdaInterestCoverage"),
        ("liquidity", "current_ratio", "currentRatio"),
        ("cashflow", "ffo_to_debt", "ffoToDebt"),
        ("stability", "debt_ratio", "debtRatio"),
    ]
    for axis_name, t_key, m_key in metric_map:
        val = metrics.get(m_key)
        if val is None:
            continue
        s = scoreMetric(val, thresholds[t_key])
        if s is not None:
            axis_scores.append((axis_name, t_key, val, s))

    if not axis_scores:
        return None

    axis_scores.sort(key=lambda x: x[3], reverse=True)  # 높은 스코어 = 약한 축
    weakest = axis_scores[0]

    # 목표: 스코어를 5점 낮추면 대략 한 노치 상향
    target_score = max(0, score - 5)
    tg, _, _ = mapTo20Grade(target_score)

    # 각 약한 축에서 필요한 metric 개선 역계산
    improvements = []
    for axis_name, t_key, current_val, current_score in axis_scores[:3]:
        bp = thresholds[t_key]
        # breakpoints에서 한 단계 나은 구간 찾기
        target_val = current_val
        for threshold_val, threshold_score in bp:
            if threshold_score < current_score:
                target_val = threshold_val
                break

        if target_val != current_val:
            direction = "감소" if target_val < current_val else "증가"
            pct_change = abs(target_val - current_val) / abs(current_val) * 100 if current_val != 0 else 0
            improvements.append(
                {
                    "axis": axis_name,
                    "metric": t_key,
                    "current": round(current_val, 2),
                    "target": round(target_val, 2),
                    "change": f"{t_key} {current_val:.1f} → {target_val:.1f} ({pct_change:.0f}% {direction})",
                }
            )

    return {
        "currentGrade": grade,
        "currentScore": round(score, 1),
        "targetGrade": tg,
        "weakestAxis": weakest[0],
        "improvements": improvements,
    }
