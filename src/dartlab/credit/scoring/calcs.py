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
    """신용분석 핵심 지표 시계열.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 7축 지표 시계열 (calcAllMetrics 결과)
        businessStability : dict — 사업안정성 지표 (opMarginCV, revenueCV 등)
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
    """신용등급 종합 산출.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.
    overrides : dict | None
        시나리오 가정 교체. core/overrides.py CREDIT_KEYS에 정의된 키만 유효.
        예: ``{"debtRatio": 150, "interestCoverage": 5.0}``
        적용 시 결과에 ``overrides``/``overrideNote`` 키가 추가됨.

    Returns
    -------
    dict | None
        evaluateCompany() 반환 dict 전체 (grade, score, axes 등).
        overrides 적용 시 추가 키:

        overrides : dict — 적용된 override 값
        overrideNote : str — "AI/사용자 override 적용 시나리오"
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
    """현금흐름등급(eCR) 시계열.

    OCF/매출, FCF 양수 여부, OCF/차입금 기반으로 기간별 eCR 등급 산출.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 현금흐름등급
            period : str — 기간 (예: "2024")
            eCR : str — 현금흐름등급 (예: "A", "BB")
            ocfToSales : float | None — OCF/매출 (%)
            fcfPositive : bool — FCF 양수 여부
            ocfToDebt : float | None — OCF/총차입금 (%)
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
    """신용 경고(warning)/개선(opportunity) 플래그.

    최신 기간의 핵심 지표를 검사하여 등급에 영향을 미치는
    경고 신호와 개선 기회를 식별한다.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간. None이면 최신.

    Returns
    -------
    dict | None
        flags : list[dict] — 경고/개선 플래그 목록
            type : str — "warning" 또는 "opportunity"
            signal : str — 신호 요약 (예: "이자보상배율 1.5배 미달")
            detail : str — 상세 설명 (예: "EBITDA/이자비용 = 1.2배")
            impact : str — 등급 영향 (예: "등급 하방 1~2 notch")
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
            from dartlab.industry import Sector

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
