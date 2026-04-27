"""1-4 현금흐름 — 계산만 담당.

CF 3구간(영업/투자/재무) + FCF + 이익의 현금 뒷받침 + CF 패턴.
블록 조립은 story/builders.py가 한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from dartlab.analysis.financial._helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.analysis.financial._memoize import memoized_calc

_MAX_YEARS = 8


# ── 유틸 ──


# ── CF 패턴 분류 ──


def _classifyCfPattern(ocf: float, icf: float, fcf: float) -> str | None:
    """영업/투자/재무 CF 부호 조합으로 패턴 분류."""

    def _s(v: float) -> str:
        """CF 부호를 '+' / '-' / '0' 문자로 변환."""
        if v > 0:
            return "+"
        if v < 0:
            return "-"
        return "0"

    patterns = {
        ("+", "-", "-"): "성숙형 — 영업으로 벌어 투자하고 부채 상환",
        ("+", "-", "+"): "확장형 — 영업 + 외부 조달로 적극 투자",
        ("+", "+", "-"): "구조조정형 — 자산 매각하며 부채 상환",
        ("-", "-", "+"): "위기형 — 영업 적자를 외부 차입으로 메움",
        ("-", "+", "+"): "축소형 — 자산 매각 + 차입으로 영업 적자 보전",
        ("-", "+", "-"): "전환형 — 자산 매각으로 부채 상환, 영업 회복 필요",
        # 재무CF가 0(미보고)인 경우 — 영업/투자만으로 부분 분류
        ("+", "-", "0"): "성숙형 — 영업으로 벌어 투자 (재무CF 미보고)",
        ("-", "-", "0"): "위기형 — 영업+투자 모두 유출 (재무CF 미보고)",
        ("+", "+", "0"): "구조조정형 — 자산 매각 진행 (재무CF 미보고)",
        ("-", "+", "0"): "축소형 — 자산 매각으로 영업 적자 보전 (재무CF 미보고)",
    }
    return patterns.get((_s(ocf), _s(icf), _s(fcf)))


# ── 메인: CF 3구간 + FCF ──


@memoized_calc
def calcCashFlowOverview(company, *, basePeriod: str | None = None) -> dict | None:
    """영업CF/투자CF/재무CF + FCF 시계열.

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            ocf : float — 영업활동현금흐름 (원)
            icf : float — 투자활동현금흐름 (원)
            fcfFinancing : float — 재무활동현금흐름 (원)
            capex : float — 설비투자 (원)
            fcf : float — 잉여현금흐름 (원)
            pattern : str — CF 패턴 분류 ("성숙형"|"확장형"|"위기형" 등)
    """
    # snakeId 단일 패턴 (alias 양방향 자동 매핑)
    cfAccounts = [
        "영업활동현금흐름",
        "투자활동현금흐름",
        "재무활동으로인한현금흐름",
        "유형자산의취득",
        "무형자산의취득",
    ]
    result = company.select("CF", cfAccounts)
    parsed = toDictBySnakeId(result)
    if parsed is None:
        return None

    data, allPeriods = parsed
    ocfRow = data.get("operating_cashflow", {})
    if not ocfRow:
        return None
    icfRow = data.get("investing_cashflow", {})
    finRow = data.get("cash_flows_from_financing_activities", {})
    capexRow = data.get("purchase_of_property_plant_and_equipment", {})
    intCapexRow = data.get("purchase_of_intangible_assets", {})
    # Note: SK하이닉스 2025Q4 같이 raw 데이터에 결손이면 None — calc 결과도 None.
    # `c.show("CF")` 의 derived row (`financing_cashflow`) 는 별도 데이터 소스로,
    # mergeAliasRows 가 양방향 머지 처리 (core/finance/labels.py).

    yCols = annualColsFromPeriods(allPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        ocf = _getF(ocfRow, col)
        icf = _getF(icfRow, col)
        fin = _getF(finRow, col)
        # CAPEX: CF에서 음수로 나옴 -> abs
        capex = abs(_getF(capexRow, col)) + abs(_getF(intCapexRow, col))
        fcf = ocf - capex

        entry = {
            "period": col,
            "ocf": ocf,
            "icf": icf,
            "fcfFinancing": fin,
            "capex": capex,
            "fcf": fcf,
            "pattern": _classifyCfPattern(ocf, icf, fin),
        }
        history.append(entry)

    if not history:
        return None

    # Phase 7 G24: FCF 변화 driver 분해
    try:
        from dartlab.core.finance.attribution import decomposeFcfChange

        for i in range(len(history) - 1):
            cur = history[i]
            prev = history[i + 1]
            if all(isinstance(cur.get(k), (int, float)) for k in ("fcf", "ocf", "capex")) and all(
                isinstance(prev.get(k), (int, float)) for k in ("fcf", "ocf", "capex")
            ):
                attr = decomposeFcfChange(
                    fcfT=cur["fcf"],
                    fcfT1=prev["fcf"],
                    ocfT=cur["ocf"],
                    ocfT1=prev["ocf"],
                    capexT=cur["capex"],
                    capexT1=prev["capex"],
                )
                cur["fcfDrivers"] = attr.get("drivers") or []
    except (ImportError, AttributeError, TypeError, ValueError):
        pass

    # Phase 8 A5
    from dartlab.macro.turningPoint import injectTurningPoints

    return {"history": history, "turningPoints": injectTurningPoints(history, seriesKey="fcf", minDeltaPct=40.0)}


# ── 이익의 현금 뒷받침 ──


@memoized_calc
def calcCashQuality(company, *, basePeriod: str | None = None) -> dict | None:
    """영업CF/순이익, 영업CF/매출 — 이익이 현금으로 뒷받침되는가.

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            ocf : float — 영업활동현금흐름 (원)
            netIncome : float — 당기순이익 (원)
            revenue : float — 매출액 (원)
            ocfToNi : float — 영업CF/순이익 (%)
            ocfMargin : float — 영업CF/매출 (%)
    """
    cfResult = company.select("CF", ["영업활동현금흐름"])
    isResult = company.select("IS", ["당기순이익", "매출액"])

    cfParsed = toDictBySnakeId(cfResult)
    isParsed = toDictBySnakeId(isResult)
    if cfParsed is None or isParsed is None:
        return None

    cfData, cfPeriods = cfParsed
    isData, _ = isParsed

    ocfRow = cfData.get("영업활동현금흐름", {})
    niRow = isData.get("당기순이익", {})
    revRow = isData.get("매출액", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        ocf = _getF2(ocfRow, col)
        ni = _getF2(niRow, col)
        rev = _getF2(revRow, col)

        ocfToNi = ocf / ni * 100 if ni != 0 else None
        # 극단값 클램핑: ±1000% 초과는 "의미 없는 비율" → None
        if ocfToNi is not None and abs(ocfToNi) > 1000:
            ocfToNi = None
        ocfMargin = ocf / rev * 100 if rev > 0 else None

        history.append(
            {
                "period": col,
                "ocf": ocf,
                "netIncome": ni,
                "revenue": rev,
                "ocfToNi": ocfToNi,
                "ocfMargin": ocfMargin,
            }
        )

    if not history:
        return None
    return {"history": history}


# ── CF 플래그 ──


@memoized_calc
def calcCashFlowFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """현금흐름 경고 신호.

    Returns
    -------
    list[str]
        경고 플래그 문자열 목록.
    """
    flags = []

    overview = calcCashFlowOverview(company, basePeriod=basePeriod)
    if overview and overview["history"]:
        h0 = overview["history"][0]

        # 영업CF 적자
        if h0["ocf"] < 0:
            flags.append("영업CF 적자 — 본업에서 현금이 나오지 않음")

        # FCF 적자
        if h0["fcf"] < 0 and h0["ocf"] > 0:
            flags.append("FCF 적자 — 영업CF보다 투자가 큼")

        # 위기형/축소형 패턴
        pat = h0.get("pattern", "")
        if pat and ("위기형" in pat or "축소형" in pat):
            flags.append(f"CF 패턴: {pat}")

        # 영업CF 3년 연속 감소
        hist = overview["history"]
        if len(hist) >= 3:
            ocfs = [h["ocf"] for h in hist[:3]]
            if ocfs[0] < ocfs[1] < ocfs[2]:
                flags.append("영업CF 3년 연속 감소")

    quality = calcCashQuality(company, basePeriod=basePeriod)
    if quality and quality["history"]:
        q0 = quality["history"][0]

        # 영업CF/순이익 < 40% (이익 대비 현금 부족)
        ratio = q0.get("ocfToNi")
        if ratio is not None and 0 < ratio < 40:
            flags.append(f"영업CF/순이익 {ratio:.0f}% — 이익의 현금 뒷받침 부족")

        # 영업CF 마진 < 0
        margin = q0.get("ocfMargin")
        if margin is not None and margin < 0:
            flags.append(f"영업CF 마진 {margin:.1f}% — 매출 대비 현금 유출")

    return flags


# ── 영업CF 내부 분해 (BS 변동 기반) ──


@memoized_calc
def calcOcfDecomposition(company, *, basePeriod: str | None = None) -> dict | None:
    """영업CF를 구성요소로 분해 — 현금흐름의 원천을 파악.

    대부분 기업이 CF에 개별 조정항목을 안 쓰므로 BS 변동으로 간접 추정.

    OCF ≈ 순이익 + 비현금비용(감가상각 추정) + 운전자본 변동
    운전자본 변동 = -(delta_AR) - (delta_Inv) + (delta_AP)

    Returns
    -------
    dict
        history : list[dict]
            period : str — 기간
            ni : float — 당기순이익 (원)
            ocf : float — 영업활동현금흐름 (원)
            depEstimate : float — 감가상각 추정치 (원)
            wcEffect : float — 운전자본 변동 효과 (원)
            arChange : float — 매출채권 변동 (원)
            invChange : float — 재고자산 변동 (원)
            apChange : float — 매입채무 변동 (원)
            residual : float — 잔차 (원)
    """
    isResult = company.select("IS", ["당기순이익"])
    cfResult = company.select("CF", ["영업활동현금흐름"])
    bsResult = company.select(
        "BS",
        ["매출채권및기타채권", "재고자산", "매입채무", "유형자산"],
    )

    isParsed = toDictBySnakeId(isResult)
    cfParsed = toDictBySnakeId(cfResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or cfParsed is None or bsParsed is None:
        return None

    isData, _ = isParsed
    cfData, cfPeriods = cfParsed
    bsData, _ = bsParsed

    niRow = isData.get("당기순이익", {})
    ocfRow = cfData.get("영업활동현금흐름", {})
    arRow = bsData.get("매출채권및기타채권", {})
    invRow = bsData.get("재고자산", {})
    apRow = bsData.get("매입채무", {})
    ppeRow = bsData.get("유형자산", {})

    from dartlab.analysis.financial._helpers import annualColsFromPeriods

    yCols = annualColsFromPeriods(cfPeriods, basePeriod, 9)
    if len(yCols) < 2:
        return None

    history = []
    for i in range(len(yCols) - 1):
        col = yCols[i]
        prevCol = yCols[i + 1]

        ni = _getF3(niRow, col)
        ocf = _getF3(ocfRow, col)
        ppe = _get(ppeRow, col)

        # 감가상각 추정 (유형자산/10)
        depEst = ppe / 10 if ppe > 0 else 0

        # 운전자본 변동 (BS delta)
        arChange = _get(arRow, col) - _get(arRow, prevCol)  # 증가=현금유출
        invChange = _get(invRow, col) - _get(invRow, prevCol)
        apChange = _get(apRow, col) - _get(apRow, prevCol)  # 증가=현금유입
        wcEffect = -arChange - invChange + apChange

        # 잔차 (설명 안 되는 부분: 영업외, 세금, 기타 조정)
        residual = ocf - ni - depEst - wcEffect

        history.append(
            {
                "period": col,
                "ni": ni,
                "ocf": ocf,
                "depEstimate": round(depEst),
                "wcEffect": round(wcEffect),
                "arChange": round(arChange),
                "invChange": round(invChange),
                "apChange": round(apChange),
                "residual": round(residual),
            }
        )

    return {"history": history} if history else None
