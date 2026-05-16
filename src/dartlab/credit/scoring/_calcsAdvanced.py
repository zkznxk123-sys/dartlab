"""credit/scoring/calcs.py 심층 calc 분리 — Flags · Narrative · Audit · GradeImprovement.

분리 이유: calcs.py 843 줄. 4 개 calc (calcCreditFlags 153 + calcCreditNarrative 88
+ calcCreditAudit 57 + calcGradeImprovement 144) 약 447 줄. calcs.py 의 facade
(metrics · score · history · cashflow · peerPosition) 책임 유지.

BC: credit.scoring.calcs 모듈에서 4 calc 모두 import 가능 (re-export).
순환 import 회피: _evaluate 는 함수 내부 lazy import.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc as _memoized_calc


def _evaluate(company, basePeriod=None):
    """credit 엔진 호출 (캐시 공유를 위한 내부 함수)."""
    from dartlab.credit.engine import evaluateCompany

    return evaluateCompany(company, detail=True, basePeriod=basePeriod)


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
    """7 축 서사 — credit publisher 의 axis별 narrative dict.

    Capabilities:
        credit/features/narrative.py::buildNarratives 결과 노출 — 7 축
        (상환력/레버리지/유동성/수익성/구조/시장신호/지배구조) 별 summary +
        details + severity (good/neutral/warning/critical). story 5-7 신용평가
        섹션의 raw 입력.

    Args:
        company: DartCompany | EdgarCompany.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``axes`` (list[dict]): axisName, summary, details list, severity.
            - ``grade`` (str): dCR 등급.
            - ``gradeDescription`` (str): 등급 설명.

    Raises:
        없음 (None 시 narrative 빌드 실패 또는 데이터 부족).

    Example:
        >>> r = calcCreditNarrative(Company("005930"))
        >>> r["axes"][0]["axisName"], r["axes"][0]["severity"]
        ('채무상환능력', 'good')

    Guide:
        - severity "critical" 축이 있으면 grade 가 낮을 가능성 큼 (downgrade).
        - severity "good" 축만 모이면 upgrade 후보.
        - details 는 LLM 인용 시 직역 권장 (특정 metric 값 포함).

    SeeAlso:
        - ``calcCreditScore``: 점수 산출 (본 narrative 와 paired)
        - ``calcCreditAudit``: 외부 신평사 대조
        - ``credit.features.narrative.buildNarratives``: 본체

    Requires:
        evaluateCompany 결과 (axes + metricsHistory).

    AIContext:
        axes 직역 인용 권장 (summary 1 줄 + 핵심 details 1~2 개). severity
        라벨 단독 인용 금지, summary + 핵심 metric 함께.

    LLM Specifications:
        AntiPatterns:
            - severity 라벨 단독 인용 — summary + 핵심 metric 함께.
            - 본 함수 결과로 grade 추론 — calcCreditScore 가 정답.
        OutputSchema:
            ``{axes: list[{axisName, summary, details: list, severity}],
              grade: str, gradeDescription: str}``.
        Prerequisites:
            evaluateCompany 결과.
        Freshness:
            분기.
        Dataflow:
            evaluateCompany → buildNarratives → 7 축 narrative + grade.
        TargetMarkets: KR (DART), US (EDGAR).
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
    """등급 한 notch 상향에 필요한 구체적 개선 — reverse engineering.

    Capabilities:
        현재 grade 의 가장 약한 축을 찾고, 그 축의 metric 을 다음 등급
        구간까지 올리는 데 필요한 변화량 역계산. 부채비율 N% 감축, IC X 배
        개선 등 정량 목표 자연어 노출. 경영진 IR / Treasury 의 개선 우선순위
        설정 입력.

    Args:
        company: DartCompany | EdgarCompany.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``currentGrade``/``currentScore`` (str/float): 현재 등급/점수.
            - ``targetGrade`` (str): 한 notch 위.
            - ``weakestAxis`` (str): 개선 최우선 축.
            - ``improvements`` (list[dict]): axis, metric, current, target,
              change (자연어).

    Raises:
        없음 (None 시 데이터 부족).

    Example:
        >>> r = calcGradeImprovement(Company("005930"))
        >>> r["improvements"][0]["change"]
        '부채비율 35% → 30% (5pp 감축)'

    Guide:
        - weakestAxis 가 leverage 면 부채비율/순차입금 감축.
        - profitability 면 마진 개선 (가격 인상 또는 원가 절감).
        - structure 면 사업포트폴리오 변경 (장기 트랙).
        - 단기 (분기 단위) 개선 가능 항목 vs 장기 (구조) 분리 해석.

    SeeAlso:
        - ``calcCreditScore``: 현재 등급
        - ``calcCreditFlags``: 경고/개선 신호
        - ``calcCreditNarrative``: 7 축 narrative

    Requires:
        evaluateCompany 결과 + sectorThresholds.

    AIContext:
        weakestAxis + improvements 직역 인용. "한 notch 상향" 이 현실적
        목표인지 (1~2 년) 또는 구조 개혁 (5+ 년) 필요인지 구분 명시.

    LLM Specifications:
        AntiPatterns:
            - 개선 목표를 "확정" 으로 인용 — 시나리오임 명시.
            - 모든 축 동시 개선 권고 — weakestAxis 부터 단계별.
        OutputSchema:
            ``{currentGrade: str, currentScore: float, targetGrade: str,
              weakestAxis: str, improvements: list[dict 5키]}``.
        Prerequisites:
            evaluateCompany + sectorThresholds.
        Freshness:
            분기.
        Dataflow:
            evaluateCompany → axis scores → 가장 약한 축 → metric 역계산 →
            target 값 + change 자연어.
        TargetMarkets: KR (DART), US (EDGAR).
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
