"""이익 모멘텀 신호 — calcEarningsMomentum (Sloan 분해 + DuPont 추세).

predictionSignals.py 의 calc 1 분리. Sloan (1996) 의 현금 vs 발생액 분해와 DuPont 3 요소
(margin/turnover/leverage) 추세 결합으로 이익 가속/감속/reversal 진단.
"""

from __future__ import annotations

import logging

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.calc import safeDiv as _safe
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

log = logging.getLogger(__name__)
_MAX_YEARS = 8


# ══════════════════════════════════════
# calc 1: 이익 모멘텀/지속성
# ══════════════════════════════════════


@memoizedCalc
def calcEarningsMomentum(company, *, basePeriod: str | None = None) -> dict | None:
    """Sloan 분해 + DuPont 추세 → 이익 모멘텀 가속/감속 판정.

    Capabilities:
        Sloan (1996, AR) 의 현금 vs 발생액 분해와 DuPont 3 요소 (margin/
        turnover/leverage) 추세를 결합. 이익이 가속/감속/reversal 중 어느
        상태인지 + 현금 뒷받침 (OCF/NI) 강도를 함께 진단. predictionSignals
        의 5 신호 중 가장 핵심.

    Args:
        company: Company 객체. ``select("IS"|"CF"|"BS")`` 가능.
        basePeriod: 기준 기간. ``None`` 이면 최신.

    Returns:
        dict | None: 다음 키 (필수 데이터 누락 시 ``None``):
            - ``history`` (list[dict]): 연도별 Sloan 분해 (netIncome, ocf,
              accrual, sloanAccrualRatio, ocfToNi, margin, turnover, leverage)
            - ``momentum`` (str): ``"accelerating"``/``"decelerating"``/
              ``"reversing"``/``"stable"``
            - ``earningsDirection`` (str): ``"up"``/``"down"``/``"flat"``
            - ``persistenceScore`` (float): OCF/NI 평균 (점)
            - ``highAccrualWarning`` (bool): |accrual/자산| > 10% 경고
            - ``confidence`` (str): ``"high"``/``"medium"``/``"low"``

    Raises:
        없음.

    Example:
        >>> from dartlab import Company
        >>> r = calcEarningsMomentum(Company("005930"))
        >>> r["momentum"], r["highAccrualWarning"]
        ('accelerating', False)

    Guide:
        Sloan accrualRatio = (NI - OCF) / 평균자산. 양수 = 발생액 비중,
        음수 = 현금 우위. 10%+ 경고는 Sloan 의 earnings management 신호.
        DuPont 분해로 margin/turnover 중 어느 요인이 변화 주도하는지 표시.

    When:
        분기 결산 후 이익 모멘텀 + 현금 뒷받침 동시 점검 시점.

    How:
        IS/CF/BS 시계열 → Sloan accrual + DuPont 3 요소 추세 결합.

    SeeAlso:
        - ``calcPredictionSynthesis``: 본 함수 결과 + 4 신호 앙상블
        - ``calcStructuralBreak``: 변동성 구조 변화 검증
        - Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals
          and Cash Flows?" The Accounting Review

    Requires:
        Company.select("IS", "당기순이익|매출액|영업이익") +
        Company.select("CF", "영업활동현금흐름") +
        Company.select("BS", "자산총계|자본총계").

    AIContext:
        ``highAccrualWarning=True`` 결과를 단독 인용해 "분식회계 의심" 으로
        결론 짓지 말 것 — Sloan 의 통계적 신호이지 의도 판정 아님.
        ``momentum`` 라벨과 함께 ``persistenceScore`` 도 노출.

    LLM Specifications:
        AntiPatterns:
            - 단년도 결과만으로 momentum 판정 — 최소 3 년 history 필요
              (confidence=low 결과는 호출자가 horizon 늘려 재호출).
            - 자본총계 < 0 (자본잠식) 회사 — DuPont leverage 비정상 (0 또는
              음수) → momentum 판정 신뢰도 낮음.
        OutputSchema:
            상기 6 키 dict.
        Prerequisites:
            IS/CF/BS 시계열 ≥ 3 년 + 자본총계 양수.
        Freshness:
            최신 보고기간 (분기). basePeriod 로 과거 시점 분석 가능.
        Dataflow:
            select(IS/CF/BS) → toDictBySnakeId → 연도별 NI/OCF/자산
            → Sloan accrual = NI - OCF → momentum 분류 → persistence.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    isResult = company.select("IS", ["당기순이익", "매출액", "영업이익"])
    cfResult = company.select("CF", ["영업활동현금흐름"])
    bsResult = company.select("BS", ["자산총계", "자본총계"])

    isParsed = toDictBySnakeId(isResult)
    cfParsed = toDictBySnakeId(cfResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or cfParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    cfData, cfPeriods = cfParsed
    bsData, _ = bsParsed

    niRow = isData.get("당기순이익", {})
    revRow = isData.get("매출액", {})
    oiRow = isData.get("영업이익", {})
    ocfRow = cfData.get("영업활동현금흐름", {})
    taRow = bsData.get("자산총계", {})
    teRow = bsData.get("자본총계", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if len(yCols) < 3:
        return None

    # Phase 15 A1: Q4 함정 제거 — IS/CF flow 는 annualSumFlow (주석 실제 이행). BS 는 stock → 직접.
    from dartlab.core.utils.flow import annualSumFlow

    allIsPeriods = set(isPeriods)
    allCfPeriods = set(cfPeriods)

    history = []
    for col in yCols:
        ni = annualSumFlow(niRow, col, allIsPeriods, withFallback=True) or 0
        ocf = annualSumFlow(ocfRow, col, allCfPeriods, withFallback=True) or 0
        ta = _get(taRow, col)  # BS stock — Q4 가 연말잔액이라 그대로 OK
        rev = annualSumFlow(revRow, col, allIsPeriods, withFallback=True) or 0
        oi = annualSumFlow(oiRow, col, allIsPeriods, withFallback=True) or 0
        te = _get(teRow, col)  # BS stock
        accrual = ni - ocf

        margin = _safe(oi, rev) if rev != 0 else None
        turnover = _safe(rev, ta) if ta != 0 else None
        leverage = _safe(ta, te) if te != 0 else None

        history.append(
            {
                "period": col,
                "netIncome": ni,
                "ocf": ocf,
                "accrual": accrual,
                "sloanAccrualRatio": _safe(accrual, ta) if ta > 0 else None,
                "ocfToNi": _safe(ocf, ni) if ni != 0 else None,
                "margin": margin,
                "turnover": turnover,
                "leverage": leverage,
            }
        )

    if len(history) < 3:
        return None

    # 이익 방향성 판단 (최근 3년 추세)
    recentNi = [h["netIncome"] for h in history[:3]]
    niChanges = [recentNi[i] - recentNi[i + 1] for i in range(len(recentNi) - 1)]

    if all(d > 0 for d in niChanges):
        momentum = "accelerating"
        direction = "up"
    elif all(d < 0 for d in niChanges):
        momentum = "decelerating"
        direction = "down"
    elif len(niChanges) >= 2 and niChanges[0] > 0 and niChanges[1] < 0:
        momentum = "reversing"
        direction = "up"
    elif len(niChanges) >= 2 and niChanges[0] < 0 and niChanges[1] > 0:
        momentum = "reversing"
        direction = "down"
    else:
        momentum = "stable"
        direction = "flat"

    # 현금 지속성 점수 (OCF/NI 비율 기반)
    ocfToNiVals = [h["ocfToNi"] for h in history[:5] if h["ocfToNi"] is not None]
    if ocfToNiVals:
        avgOcfToNi = sum(ocfToNiVals) / len(ocfToNiVals)
        if avgOcfToNi >= 1.0:
            persistenceScore = min(90, 50 + avgOcfToNi * 20)
        elif avgOcfToNi >= 0.5:
            persistenceScore = 30 + avgOcfToNi * 40
        else:
            persistenceScore = max(10, avgOcfToNi * 60)
    else:
        persistenceScore = 50

    # 발생액 비율 기반 경고
    recentAccrual = [h["sloanAccrualRatio"] for h in history[:3] if h["sloanAccrualRatio"] is not None]
    highAccrual = any(abs(a) > 0.10 for a in recentAccrual) if recentAccrual else False

    # 신뢰도
    nYears = len(history)
    if nYears >= 5 and not highAccrual:
        confidence = "high"
    elif nYears >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "history": history,
        "momentum": momentum,
        "earningsDirection": direction,
        "persistenceScore": round(persistenceScore, 1),
        "highAccrualWarning": highAccrual,
        "confidence": confidence,
    }


__all__ = ["calcEarningsMomentum"]
