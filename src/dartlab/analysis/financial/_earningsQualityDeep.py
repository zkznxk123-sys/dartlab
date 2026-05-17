"""earningsQuality.py 깊이 분석 — 5 종 분리.

calcBeneishTimeline + calcRichardsonAccrual + calcNonOperatingBreakdown +
calcDilutionTrend + calcQualityAnomalies 본체.
"""

from __future__ import annotations

import math

from dartlab.analysis.financial._constants import ACCRUAL_RATIO_WARNING
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.calc import safeDiv as _safe
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get
_MAX_YEARS = 8


def _beneishInterpretation(*args, **kwargs):
    """Beneish 해석 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.earningsQuality import _beneishInterpretation as _f

    return _f(*args, **kwargs)


def calcBeneishMScore(*args, **kwargs):
    """Beneish M-Score 본 점수 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcBeneishMScore(company)["mScore"]
        -2.1
    """
    from dartlab.analysis.financial.earningsQuality import calcBeneishMScore as _f

    return _f(*args, **kwargs)


def calcSloanAccruals(*args, **kwargs):
    """Sloan accruals — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcSloanAccruals(company)["accruals"]
        0.03
    """
    from dartlab.analysis.financial.earningsQuality import calcSloanAccruals as _f

    return _f(*args, **kwargs)


def calcAccrualAnalysis(*args, **kwargs):
    """발생액 분석 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcAccrualAnalysis(company)["score"]
        0.5
    """
    from dartlab.analysis.financial.earningsQuality import calcAccrualAnalysis as _f

    return _f(*args, **kwargs)


def calcEarningsPersistence(*args, **kwargs):
    """이익 지속성 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcEarningsPersistence(company)["score"]
        0.7
    """
    from dartlab.analysis.financial.earningsQuality import calcEarningsPersistence as _f

    return _f(*args, **kwargs)


def _calcEarningsQualityFlagsBase(*args, **kwargs):
    """flags base — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy)."""
    from dartlab.analysis.financial.earningsQuality import _calcEarningsQualityFlagsBase as _f

    return _f(*args, **kwargs)


def detectAuditFlags(*args, **kwargs):
    """감사 flag 검출 — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> detectAuditFlags(company)
        ['지정감사인', '한정의견']
    """
    from dartlab.analysis.financial.earningsQuality import detectAuditFlags as _f

    return _f(*args, **kwargs)


def calcEarningsQualityFlags(*args, **kwargs):
    """earnings quality flags — earningsQuality.py 본체 위임 (cycle 회피 lazy proxy).

    Requires:
        earningsQuality.py 본체 import.

    Raises:
        없음.

    Example:
        >>> calcEarningsQualityFlags(company)
        [('HIGH_ACCRUAL', '...')]
    """
    from dartlab.analysis.financial.earningsQuality import calcEarningsQualityFlags as _f

    return _f(*args, **kwargs)


@memoizedCalc
def calcBeneishTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """Beneish M-Score 시계열 — annual 데이터에서 직접 8변수 계산.

    8-Variable Model:
      DSRI(매출채권/매출 변화), GMI(매출총이익률 역전), AQI(자산품질 변화),
      SGI(매출성장), DEPI(감가상각률 변화, 기본1.0), SGAI(판관비율 변화),
      LVGI(레버리지 변화), TATA(발생액/총자산)

    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

    Returns
    -------
    dict
        history : list[dict] — 기간별 M-Score 시계열
            period : str — 회계연도
            mScore : float | None — Beneish M-Score (점수)
        threshold : float — 조작 판별 임계값 (-1.78)
        diagnosticMeta : dict — 진단 메타데이터
            precision : float — 정밀도
            falsePositiveRate : float — 위양성률
            reference : str — 학술 근거
            sampleBase : str — 표본 기반
            krNote : str — K-IFRS 환경 주의사항

    Capabilities:
        - annual 데이터에서 8 변수 Beneish 직접 계산 + 기간별 시계열 + threshold 비교
        - K-IFRS 환경 한계 명시 (precision/falsePositiveRate 메타)

    Guide:
        Beneish 1999 표준. M > -1.78 = 조작 의심. 한국 K-IFRS 환경에서 false positive 잦음.

    When:
        Earnings quality 시계열 + AI 회계 조작 의심 답변.

    How:
        snakeId pattern 으로 IS/BS/CF 추출 → 8 변수 계산 → M 합산.

    Requires:
        IS/BS/CF 시계열 ≥ 2 년.

    Raises:
        없음 — 데이터 부재 시 None.

    Example:
        >>> calcBeneishTimeline(company)["history"][-1]["mScore"]
        -2.05

    See Also:
        - calcBeneishMScore : 단일 기간
        - calcQualityAnomalies : 종합 anomaly

    AIContext:
        "이 종목 회계 조작 의심" 답변 시 mScore 시계열 + threshold 인용.
    """
    # snakeId 단일 패턴 (alias 양방향이 EDGAR↔DART 변형 자동 처리)
    isResult = company.select(
        "IS",
        ["매출액", "매출원가", "판매비와관리비", "당기순이익"],
    )
    bsResult = company.select(
        "BS",
        ["매출채권및기타채권", "유동자산", "유형자산", "자산총계", "유동부채", "부채총계"],
    )
    cfResult = company.select("CF", ["operating_cashflow"])

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    cfParsed = toDictBySnakeId(cfResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed
    cfData = cfParsed[0] if cfParsed else {}

    revRow = isData.get("sales", {})
    cogsRow = isData.get("cost_of_sales", {})
    sgaRow = isData.get("selling_and_administrative_expenses", {})
    niRow = isData.get("net_profit", {})
    recRow = bsData.get("trade_and_other_receivables", {})
    caRow = bsData.get("current_assets", {})
    ppeRow = bsData.get("tangible_assets", {})
    taRow = bsData.get("assets", {})
    clRow = bsData.get("current_liabilities", {})
    tlRow = bsData.get("liabilities", {})
    ocfRow = cfData.get("operating_cashflow", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS + 1)  # 전년 대비 필요 → 1년 더
    if len(yCols) < 2:
        return None

    history = []
    for i in range(len(yCols) - 1):
        col = yCols[i]  # 당기
        prevCol = yCols[i + 1]  # 전기

        rev = _getF3(revRow, col)
        prevRev = _getF3(revRow, prevCol)
        cogs = _getF3(cogsRow, col)
        prevCogs = _getF3(cogsRow, prevCol)
        sga = _getF3(sgaRow, col)
        prevSga = _getF3(sgaRow, prevCol)
        ni = _getF3(niRow, col)
        rec = _get(recRow, col)
        prevRec = _get(recRow, prevCol)
        ca = _get(caRow, col)
        prevCa = _get(caRow, prevCol)
        ppe = _get(ppeRow, col)
        prevPpe = _get(ppeRow, prevCol)
        ta = _get(taRow, col)
        prevTa = _get(taRow, prevCol)
        _get(clRow, col)
        _get(clRow, prevCol)
        tl = _get(tlRow, col)
        prevTl = _get(tlRow, prevCol)
        ocf = _getF3(ocfRow, col)

        # 분모가 0이면 계산 불가
        if prevRev <= 0 or rev <= 0 or prevTa <= 0 or ta <= 0:
            history.append({"period": col, "mScore": None})
            continue

        # DSRI: (매출채권t/매출t) / (매출채권t-1/매출t-1)
        dsri = (rec / rev) / (prevRec / prevRev) if prevRec > 0 else 1.0

        # GMI: 매출총이익률t-1 / 매출총이익률t
        gm = (rev - cogs) / rev
        prevGm = (prevRev - prevCogs) / prevRev if prevRev > 0 else 0
        gmi = prevGm / gm if gm > 0 else 1.0

        # AQI: (1 - 유동자산t/총자산t - 유형자산t/총자산t) / (1 - 유동자산t-1/총자산t-1 - 유형자산t-1/총자산t-1)
        aqi_t = 1 - ca / ta - ppe / ta
        aqi_prev = 1 - prevCa / prevTa - prevPpe / prevTa
        aqi = aqi_t / aqi_prev if abs(aqi_prev) > 0.001 else 1.0

        # SGI: 매출t / 매출t-1
        sgi = rev / prevRev

        # DEPI: 감가상각 데이터 없음 → 기본 1.0 (중립)
        depi = 1.0

        # SGAI: (판관비t/매출t) / (판관비t-1/매출t-1)
        sgai = (sga / rev) / (prevSga / prevRev) if prevSga > 0 else 1.0

        # LVGI: (부채총계t/총자산t) / (부채총계t-1/총자산t-1)
        lev_t = tl / ta
        lev_prev = prevTl / prevTa if prevTa > 0 else 0
        lvgi = lev_t / lev_prev if lev_prev > 0 else 1.0

        # TATA: (순이익 - 영업CF) / 총자산
        tata = (ni - ocf) / ta if ta > 0 else 0

        mScore = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )

        history.append({"period": col, "mScore": round(mScore, 4)})

    if not history:
        return None
    return {
        "history": history,
        "threshold": -1.78,
        "diagnosticMeta": {
            "precision": 0.76,
            "falsePositiveRate": 0.178,
            "reference": "Beneish(1999), 8변수",
            "sampleBase": "미국 제조업 1982-1992",
            "krNote": "K-IFRS 환경 미검증 — 정밀도 과대추정 가능",
        },
    }


@memoizedCalc
def calcRichardsonAccrual(company, *, basePeriod: str | None = None) -> dict | None:
    """Richardson et al. (2005) 3계층 발생액 분해.

    BS 변동 기반으로 발생액을 운전자본/비유동영업/금융으로 분리.
    신뢰도가 낮은 LTOACC가 클수록 이익 지속성이 낮다.

    WCACC  = (delta_CA - delta_Cash) - (delta_CL - delta_STD)  신뢰도 높음
    LTOACC = delta_NCOA - delta_NCOL                            신뢰도 낮음
    FINACC = delta_STI + delta_LTI - delta_LTD - delta_PSTK    중간

    학술근거: Richardson, Sloan, Soliman, Tuna (2005).

    Returns
    -------
    dict
        history : list[dict] — 기간별 3계층 발생액 시계열
            period : str — 회계연도
            wcacc : float | None — 운전자본 발생액/총자산 (%)
            ltoacc : float | None — 비유동영업 발생액/총자산 (%)
            finacc : float | None — 금융 발생액/총자산 (%)
            totalAccrual : float | None — 총발생액/총자산 (%)
            reliabilityScore : str | None — 이익 신뢰도 (high/medium/low)

    Capabilities:
        - BS 변동 기반 3계층 발생액 분해 (WCACC/LTOACC/FINACC)
        - reliabilityScore (high/medium/low) 분류

    Guide:
        Richardson et al. 2005 표준. LTOACC 가 클수록 이익 지속성 낮음 → 이익 품질 우려.

    When:
        Earnings quality 정밀 진단 + AI 발생액 분해 답변.

    How:
        BS 시계열 → 운전자본/비유동영업/금융 발생액 차분.

    Requires:
        BS 시계열 ≥ 2 년.

    Raises:
        없음 — 데이터 부재 시 None.

    Example:
        >>> calcRichardsonAccrual(company)["history"][-1]["reliabilityScore"]
        'medium'

    See Also:
        - calcSloanAccruals : 단순 Sloan
        - calcBeneishTimeline : 8 변수 Beneish

    AIContext:
        "이익 품질 정밀 진단" 답변 시 LTOACC + reliabilityScore 인용.
    """
    bsResult = company.select(
        "BS",
        [
            "유동자산",
            "비유동자산",
            "유동부채",
            "비유동부채",
            "현금및현금성자산",
            "단기차입금",
            "장기차입금",
            "차입금단기",
            "long_term_borrowings",
            "short_term_borrowings",
            "차입부채",
            "장기차입부채",
            "유동성장기차입금",
            "사채",
            "자산총계",
        ],
    )

    bsParsed = toDictBySnakeId(bsResult)
    if bsParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    caRow = bsData.get("current_assets", {})
    ncaRow = bsData.get("noncurrent_assets", {})
    clRow = bsData.get("current_liabilities", {})
    nclRow = bsData.get("noncurrent_liabilities", {})
    cashRow = bsData.get("cash_and_cash_equivalents", {})
    stRow = bsData.get("shortterm_borrowings", {})
    ltRow = bsData.get("longterm_borrowings", {})
    unifiedBorrowRow = bsData.get("borrowings", {})  # 통합 차입금 fallback
    bondRow = bsData.get("debentures", {})
    taRow = bsData.get("total_assets", {})

    # stRow/ltRow 가 모두 비어있으면 unifiedBorrow 를 stRow 로 사용
    if not stRow and not ltRow and unifiedBorrowRow:
        stRow = unifiedBorrowRow

    yCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS + 1)
    if len(yCols) < 2:
        return None

    history = []
    for i in range(len(yCols) - 1):
        col = yCols[i]
        prevCol = yCols[i + 1]

        # 델타 계산
        dCA = _get(caRow, col) - _get(caRow, prevCol)
        dCash = _get(cashRow, col) - _get(cashRow, prevCol)
        dCL = _get(clRow, col) - _get(clRow, prevCol)
        dSTD = _get(stRow, col) - _get(stRow, prevCol)
        dNCA = _get(ncaRow, col) - _get(ncaRow, prevCol)
        dNCL = _get(nclRow, col) - _get(nclRow, prevCol)
        dLTD = (_get(ltRow, col) + _get(bondRow, col)) - (_get(ltRow, prevCol) + _get(bondRow, prevCol))

        # 3계층 분해
        wcacc = (dCA - dCash) - (dCL - dSTD)
        ltoacc = dNCA - dNCL
        finacc = -dCash + dSTD + dLTD  # 금융자산 증가 - 금융부채 증가의 역

        totalAccrual = wcacc + ltoacc + finacc
        avgTA = (_get(taRow, col) + _get(taRow, prevCol)) / 2

        # 정규화 (총자산 평균 대비)
        wcaccNorm = round(wcacc / avgTA * 100, 2) if avgTA > 0 else None
        ltoaccNorm = round(ltoacc / avgTA * 100, 2) if avgTA > 0 else None
        finaccNorm = round(finacc / avgTA * 100, 2) if avgTA > 0 else None
        totalNorm = round(totalAccrual / avgTA * 100, 2) if avgTA > 0 else None

        # 신뢰도 판단: LTOACC 비중이 50% 이상이면 낮음
        if totalAccrual != 0 and avgTA > 0:
            ltoShare = (
                abs(ltoacc) / (abs(wcacc) + abs(ltoacc) + abs(finacc))
                if (abs(wcacc) + abs(ltoacc) + abs(finacc)) > 0
                else 0
            )
            reliability = "low" if ltoShare > 0.5 else "high" if ltoShare < 0.2 else "medium"
        else:
            reliability = None

        history.append(
            {
                "period": col,
                "wcacc": wcaccNorm,
                "ltoacc": ltoaccNorm,
                "finacc": finaccNorm,
                "totalAccrual": totalNorm,
                "reliabilityScore": reliability,
            }
        )

    return {"history": history} if history else None


@memoizedCalc
def calcNonOperatingBreakdown(company, *, basePeriod: str | None = None) -> dict | None:
    """영업외손익 항목별 분해 — 영업이익과 세전이익 사이의 갭.

    금융이익/비용, 지분법손익, 기타수익/비용을 개별 추적.
    영업외가 영업이익의 30% 이상이면 영업만으로 기업 판단 불가.

    Returns
    -------
    dict
        history : list[dict] — 기간별 영업외손익 분해 시계열
            period : str — 회계연도
            opIncome : float — 영업이익 (원)
            finIncome : float — 금융이익 (원)
            finCost : float — 금융비용 (원)
            netFinance : float — 순금융손익 (원)
            associateIncome : float — 지분법손익 (원)
            otherIncome : float — 기타수익 (원)
            otherExpense : float — 기타비용 (원)
            nonOpTotal : float | None — 영업외손익 합계 (원)
            nonOpRatio : float | None — 영업외/영업이익 비율 (%)
        notesDetail : dict | None — 관계기업 투자 주석 (있는 경우)

    Capabilities:
        - IS 영업외 항목 (금융이익/비용/지분법/기타) 시계열 분해 + 영업외 비중 산출
        - notesDetail 로 관계기업 투자 주석 보강

    Guide:
        영업외 비중이 영업이익 대비 30% 이상 = 이익 품질 저하 (영업 본업 외 의존).

    When:
        영업외 비중 분석 + AI "이익이 영업에서 나왔나" 답변.

    How:
        IS snakeId 추출 → 금융/지분법/기타 계산.

    Requires:
        IS 시계열 가용.

    Raises:
        없음.

    Example:
        >>> calcNonOperatingBreakdown(company)["history"][-1]["nonOpRatio"]
        15.2

    See Also:
        - calcRichardsonAccrual : 발생액 분해
        - earningsQuality.calcSloanAccruals

    AIContext:
        "이익이 본업에서" 답변 시 nonOpRatio 인용.
    """
    isResult = company.select(
        "IS",
        ["영업이익", "금융이익", "금융비용", "지분법관련손익", "기타수익", "기타비용", "법인세차감전순이익"],
    )

    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None

    isData, isPeriods = isParsed
    opRow = isData.get("영업이익", {})
    finIncRow = isData.get("금융이익", {})
    finCostRow = isData.get("금융비용", {})
    assocRow = isData.get("지분법관련손익", {})
    otherIncRow = isData.get("기타수익", {})
    otherExpRow = isData.get("기타비용", {})
    ptRow = isData.get("법인세차감전순이익", {})

    yCols = annualColsFromPeriods(isPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        op = _getF4(opRow, col)
        finInc = _getF4(finIncRow, col)
        finCost = _getF4(finCostRow, col)
        assoc = _getF4(assocRow, col)
        otherInc = _getF4(otherIncRow, col)
        otherExp = _getF4(otherExpRow, col)
        pt = _getF4(ptRow, col)

        netFinance = finInc - finCost
        nonOpTotal = pt - op if op != 0 else None
        nonOpRatio = round(abs(nonOpTotal) / abs(op) * 100, 1) if op != 0 and nonOpTotal is not None else None

        history.append(
            {
                "period": col,
                "opIncome": op,
                "finIncome": finInc,
                "finCost": finCost,
                "netFinance": netFinance,
                "associateIncome": assoc,
                "otherIncome": otherInc,
                "otherExpense": otherExp,
                "nonOpTotal": nonOpTotal,
                "nonOpRatio": nonOpRatio,
            }
        )

    if not history:
        return None

    result: dict = {"history": history}

    # notes enrichment — 관계기업 투자 상세
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesDetail = fetchNotesDetail(company, ["affiliates"])
    if notesDetail:
        result["notesDetail"] = notesDetail

    return result


@memoizedCalc
def calcDilutionTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """기본 EPS vs 희석 EPS 괴리율 시계열 — 스톡옵션/전환사채 희석 리스크.

    notes.eps에서 기본주당이익과 희석주당이익을 추출하여
    희석 괴리율(%)의 추세를 추적한다.
    괴리율이 5% 이상이면 잠재 희석 리스크.

    Returns
    -------
    dict
        history : list[dict] — 기간별 EPS 희석 시계열
            period : str — 회계연도
            basicEps : float | None — 기본주당이익 (원)
            dilutedEps : float | None — 희석주당이익 (원)
            dilutionPct : float | None — 희석 괴리율 (%)
        latestDilution : float | None — 최신 기간 희석 괴리율 (%)
        trend : str | None — 희석 추세 (희석 증가/희석 감소/안정)

    Capabilities:
        - notes.eps 에서 basic vs diluted EPS 시계열 추출 + 괴리율 추세 분류
        - 5% 이상 = 잠재 희석 리스크 식별

    Guide:
        희석 괴리율 추세 ↑ = 신주발행/CB 등 dilution 압력 ↑. 5% 임계 보수적.

    When:
        희석 리스크 + AI EPS dilution 답변.

    How:
        notesDetail.eps → basic/diluted 매칭 → 시계열 계산.

    Requires:
        notes.eps 가용.

    Raises:
        없음.

    Example:
        >>> calcDilutionTrend(company)["latestDilution"]
        3.2

    See Also:
        - calcNonOperatingBreakdown : 영업외
        - companyContext.fetchNotesDetail

    AIContext:
        "EPS 희석 압력" 답변 시 latestDilution + trend 인용.
    """
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesData = fetchNotesDetail(company, ["eps"])
    epsDf = notesData.get("eps")
    if not epsDf:
        return None

    # eps notes: [{항목, 2024, 2023, ...}]
    basicRow = None
    dilutedRow = None
    for row in epsDf:
        item = str(row.get("항목", "")).strip()
        if "희석" in item:
            dilutedRow = row
        elif "기본" in item or "주당" in item:
            if basicRow is None:
                basicRow = row

    if basicRow is None:
        return None

    # 기간 컬럼 추출
    periodCols = [k for k in basicRow if k not in ("항목",) and k.isdigit()]
    periodCols.sort(reverse=True)
    if not periodCols:
        return None

    from dartlab.core.utils.helpers import parseNumStr

    history = []
    for col in periodCols[:_MAX_YEARS]:
        basic = parseNumStr(basicRow.get(col))
        diluted = parseNumStr(dilutedRow.get(col)) if dilutedRow else None

        dilutionPct = None
        if basic is not None and diluted is not None and basic != 0:
            dilutionPct = round((basic - diluted) / abs(basic) * 100, 2)

        history.append(
            {
                "period": col,
                "basicEps": basic,
                "dilutedEps": diluted,
                "dilutionPct": dilutionPct,
            }
        )

    if not history:
        return None

    latestDilution = history[0]["dilutionPct"]

    # 추세: 최근 vs 과거 비교
    trend = None
    dilutionVals = [h["dilutionPct"] for h in history if h["dilutionPct"] is not None]
    if len(dilutionVals) >= 2:
        diff = dilutionVals[0] - dilutionVals[-1]
        if diff > 2:
            trend = "희석 증가"
        elif diff < -2:
            trend = "희석 감소"
        else:
            trend = "안정"

    return {
        "history": history,
        "latestDilution": latestDilution,
        "trend": trend,
    }


@memoizedCalc
def calcQualityAnomalies(company, *, basePeriod: str | None = None) -> dict | None:
    """Damodaran Ch.4 + Beneish (1999) + Sloan (1996) 학술 표준 회계 품질.

    기존 calcAccrualAnalysis 는 발생액 시계열. 이 함수는 **이상치 감지** 통합:
    - Beneish M-Score (8 변수)
    - Sloan Accrual quintile
    - 5 카테고리 (분식/일회성/매출채권/자본우회/영업권)
    - 감사보고서 키워드 자동 감지 (docs 활용)

    Returns
    -------
    dict
        score : int — 0~100
        flags : list[{category, severity, evidence, damodaranRef}]
        beneish : dict — M-Score + zone
        sloan : dict — 발생액 quintile
        auditFlags : list — 감사보고서 위험 키워드
        period : str

    Capabilities:
        - Beneish + Sloan + 5 카테고리 (분식/일회성/매출채권/자본우회/영업권) + 감사보고서 키워드 통합
        - 0~100 score 산출

    Guide:
        Damodaran reference 기반 종합. score ≥ 70 = 다중 anomaly 의심.

    When:
        Earnings quality 종합 + AI 회계 anomaly 답변.

    How:
        IS+BS+CF + docs → Beneish + Sloan + audit flags + 5 카테고리.

    Requires:
        IS/BS/CF + docs 가용.

    Raises:
        없음.

    Example:
        >>> calcQualityAnomalies(company)["score"]
        45

    See Also:
        - calcBeneishTimeline : Beneish 시계열
        - calcRichardsonAccrual : 발생액 분해

    AIContext:
        "회계 anomaly 종합" 답변 시 score + flags 인용.
    """
    # core 의 base 함수들이 본 모듈 안으로 머지됨 (S5b)
    # — calcBeneishMScore / _calcEarningsQualityFlagsBase / detectAuditFlags 는 모듈 상단 정의

    is_result = company.select("IS", ["매출액", "매출원가", "판매비와관리비", "당기순이익"])
    bs_result = company.select("BS", ["자산총계", "매출채권", "부채총계", "유형자산", "영업권"])
    cf_result = company.select("CF", ["영업활동현금흐름"])

    is_parsed = toDictBySnakeId(is_result)
    bs_parsed = toDictBySnakeId(bs_result)
    cf_parsed = toDictBySnakeId(cf_result)
    if is_parsed is None or bs_parsed is None:
        return None

    is_data, is_periods = is_parsed
    bs_data, _ = bs_parsed
    cf_data = cf_parsed[0] if cf_parsed else {}

    annual_years = [p for p in is_periods if p.isdigit() and len(p) == 4]
    if len(annual_years) < 2:
        return None
    t, t1 = annual_years[0], annual_years[1]

    def _ga(rowDict: dict, period: str, *keys: str) -> float | None:
        """다중 키 fallback으로 특정 기간 값 추출."""
        for k in keys:
            row = rowDict.get(k) or {}
            v = row.get(period)
            if v is not None:
                return float(v)
        return None

    sales_t = _ga(is_data, t, "sales", "매출액")
    sales_t1 = _ga(is_data, t1, "sales", "매출액")
    cogsT = _ga(is_data, t, "cost_of_sales", "매출원가")
    cogs_t1 = _ga(is_data, t1, "cost_of_sales", "매출원가")
    sgaT = _ga(is_data, t, "selling_and_administrative_expenses", "판매비와관리비")
    sga_t1 = _ga(is_data, t1, "selling_and_administrative_expenses", "판매비와관리비")
    ni_t = _ga(is_data, t, "net_profit", "net_income", "당기순이익")
    assets_t = _ga(bs_data, t, "total_assets", "자산총계")
    assets_t1 = _ga(bs_data, t1, "total_assets", "자산총계")
    receivables_t = _ga(bs_data, t, "trade_receivables", "매출채권")
    receivables_t1 = _ga(bs_data, t1, "trade_receivables", "매출채권")
    goodwill_t = _ga(bs_data, t, "goodwill", "영업권")
    liabilities_t = _ga(bs_data, t, "total_liabilities", "부채총계")
    liabilities_t1 = _ga(bs_data, t1, "total_liabilities", "부채총계")
    ppe_t = _ga(bs_data, t, "tangible_assets", "유형자산")
    ppe_t1 = _ga(bs_data, t1, "tangible_assets", "유형자산")
    ocfT = _ga(cf_data, t, "operating_cashflow")

    quality = _calcEarningsQualityFlagsBase(
        salesT=sales_t or 0,
        salesT1=sales_t1 or 0,
        receivablesT=receivables_t or 0,
        receivablesT1=receivables_t1 or 0,
        netIncomeT=ni_t or 0,
        ocfT=ocfT or 0,
        totalAssetsT=assets_t or 0,
        goodwillT=goodwill_t,
    )

    beneish = None
    if all(v is not None for v in (sales_t, sales_t1, cogsT, cogs_t1, sgaT, sga_t1, assets_t, assets_t1)):
        beneish = calcBeneishMScore(
            salesT=sales_t,
            salesT1=sales_t1,
            receivablesT=receivables_t or 0,
            receivablesT1=receivables_t1 or 0,
            cogsT=cogsT,
            cogsT1=cogs_t1,
            sgaT=sgaT,
            sgaT1=sga_t1,
            grossPropertyT=ppe_t or 0,
            grossPropertyT1=ppe_t1 or 0,
            totalAssetsT=assets_t,
            totalAssetsT1=assets_t1,
            netIncomeT=ni_t or 0,
            ocfT=ocfT or 0,
            leverageT=(liabilities_t / assets_t) if assets_t else 0,
            leverageT1=(liabilities_t1 / assets_t1) if assets_t1 else 0,
            depreciationT=0,
            depreciationT1=0,
        )

    # docs 활용 — 감사보고서 키워드
    audit_flags: list[dict] = []
    try:
        audit_df = company.show("auditOpinion")
        if audit_df is not None and hasattr(audit_df, "to_dicts"):
            seen: set = set()
            for row in audit_df.to_dicts():
                text = " ".join(str(v) for v in row.values() if isinstance(v, str))
                for f in detectAuditFlags(text):
                    key = f.get("keyword")
                    if key and key not in seen:
                        seen.add(key)
                        audit_flags.append(f)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    return {
        "score": quality["score"],
        "flags": quality["flags"],
        "beneish": beneish,
        "sloan": quality["sloanAccrual"],
        "auditFlags": audit_flags,
        "period": t,
    }
