"""Beneish M-Score 시계열 — calcBeneishTimeline 본체."""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

_getF3 = _get
_MAX_YEARS = 8


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

    yCols = annualColsFromPeriods(isPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS + 1)
    if len(yCols) < 2:
        return None

    history = []
    for i in range(len(yCols) - 1):
        col = yCols[i]
        prevCol = yCols[i + 1]

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

        if prevRev <= 0 or rev <= 0 or prevTa <= 0 or ta <= 0:
            history.append({"period": col, "mScore": None})
            continue

        dsri = (rec / rev) / (prevRec / prevRev) if prevRec > 0 else 1.0

        gm = (rev - cogs) / rev
        prevGm = (prevRev - prevCogs) / prevRev if prevRev > 0 else 0
        gmi = prevGm / gm if gm > 0 else 1.0

        aqi_t = 1 - ca / ta - ppe / ta
        aqi_prev = 1 - prevCa / prevTa - prevPpe / prevTa
        aqi = aqi_t / aqi_prev if abs(aqi_prev) > 0.001 else 1.0

        sgi = rev / prevRev

        depi = 1.0

        sgai = (sga / rev) / (prevSga / prevRev) if prevSga > 0 else 1.0

        lev_t = tl / ta
        lev_prev = prevTl / prevTa if prevTa > 0 else 0
        lvgi = lev_t / lev_prev if lev_prev > 0 else 1.0

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
