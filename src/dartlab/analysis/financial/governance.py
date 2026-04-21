"""5-1 지배구조 분석 -- 이 회사의 주인은 누구이며, 감시는 작동하는가.

report 데이터(최대주주, 임원, 감사의견)에서 지배구조 핵심 지표를 추출한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._helpers import MAX_RATIO_YEARS
from dartlab.analysis.financial._memoize import memoized_calc
from dartlab.core.polarsUtil import isEmptyDf

# ── 최대주주 지분 시계열 ──


@memoized_calc
def calcOwnershipTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """최대주주 지분율 시계열 + 최근 주주 구성.

    report.majorHolder에서 연도별 합산 지분율 추이와
    최신 시점 개별 주주(top 10)를 추출한다.

    Returns
    -------
    dict | None
        None: majorHolder 데이터 없음.
        history : list[dict] — 연도별 지분율 추이
            year : str — 연도
            ratio : float — 합산 지분율 (%)
            change : float — 전기 대비 변동 (%p)
        latestHolders : list[dict] — 최근 주주 구성 (상위 10명)
            name : str — 주주명
            relate : str — 관계
            ratio : float — 지분율 (%)
            shares : int — 보유 주식수
    """
    result = _safePivotMajorHolder(company)
    if result is None:
        return None

    years = result.years[-MAX_RATIO_YEARS:]
    ratios = result.totalShareRatio[-MAX_RATIO_YEARS:]

    history = []
    for i, y in enumerate(years):
        r = ratios[i] if i < len(ratios) else None
        prevR = ratios[i - 1] if i > 0 and (i - 1) < len(ratios) else None
        change = round(r - prevR, 2) if r is not None and prevR is not None else None
        history.append({"year": y, "ratio": r, "change": change})

    holders = result.latestHolders[:10] if result.latestHolders else []

    return (
        {
            "history": history,
            "latestHolders": holders,
        }
        if history
        else None
    )


# ── 이사회 구성 ──


@memoized_calc
def calcBoardComposition(company, *, basePeriod: str | None = None) -> dict | None:
    """이사회 구성 -- 사외이사비율, 전체 임원 수.

    report.executive에서 최신 분기 기준 이사회 구성을 추출한다.

    Returns
    -------
    dict
        totalCount : int — 전체 임원 수
        registeredCount : int — 등기임원 수
        outsideCount : int — 사외이사 수
        outsideRatio : float — 사외이사비율 (%)
    """
    result = _safePivotExecutive(company)
    if result is None:
        return None

    total = result.totalCount
    registered = result.registeredCount
    outside = result.outsideCount
    if total == 0:
        return None

    outsideRatio = round(outside / total * 100, 1) if total > 0 else None

    return {
        "totalCount": total,
        "registeredCount": registered,
        "outsideCount": outside,
        "outsideRatio": outsideRatio,
    }


# ── 감사의견 시계열 ──


@memoized_calc
def calcAuditOpinionTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """감사의견 + 감사인 시계열.

    report.audit에서 연도별 감사의견과 감사인을 추출한다.
    감사인 변경도 감지한다.

    Returns
    -------
    dict | None
        None: audit 데이터 없음.
        history : list[dict] — 연도별 감사 이력
            year : str — 연도
            opinion : str — 감사의견
            auditor : str — 감사인
            auditorChanged : bool — 감사인 변경 여부
    """
    result = _safePivotAudit(company)
    if result is None:
        return None

    years = result.years[-MAX_RATIO_YEARS:]
    opinions = result.opinions[-MAX_RATIO_YEARS:]
    auditors = result.auditors[-MAX_RATIO_YEARS:]

    history = []
    for i, y in enumerate(years):
        opinion = opinions[i] if i < len(opinions) else None
        auditor = auditors[i] if i < len(auditors) else None
        prevAuditor = auditors[i - 1] if i > 0 and (i - 1) < len(auditors) else None
        auditorChanged = auditor is not None and prevAuditor is not None and auditor != prevAuditor
        history.append(
            {
                "year": y,
                "opinion": opinion,
                "auditor": auditor,
                "auditorChanged": auditorChanged,
            }
        )

    return {"history": history} if history else None


# ── 플래그 ──


@memoized_calc
def calcGovernanceFlags(company, *, basePeriod: str | None = None) -> list[tuple[str, str]]:
    """지배구조 경고/기회 플래그.

    Returns
    -------
    list[tuple[str, str]]
        (message, severity) 쌍 목록. severity: "warning" | "opportunity"
    """
    flags: list[tuple[str, str]] = []

    # 최대주주 지분
    ownership = calcOwnershipTrend(company)
    if ownership and ownership["history"]:
        latest = ownership["history"][-1]
        r = latest.get("ratio")
        if r is not None:
            if r > 50:
                flags.append((f"최대주주 지분율 {r:.1f}% -- 과반 지배", "warning"))
            elif r < 20:
                flags.append((f"최대주주 지분율 {r:.1f}% -- 경영권 방어 취약", "warning"))

        # 지분 변동 추이
        history = ownership["history"]
        if len(history) >= 3:
            changes = [h["change"] for h in history[-3:] if h.get("change") is not None]
            if len(changes) >= 2 and all(c < -1.0 for c in changes):
                flags.append(("최대주주 지분 2기 연속 감소 -- 지분 희석 주의", "warning"))

    # 이사회 구성
    board = calcBoardComposition(company)
    if board:
        outsideRatio = board.get("outsideRatio")
        if outsideRatio is not None:
            if outsideRatio < 25:
                flags.append((f"사외이사비율 {outsideRatio:.0f}% -- 이사회 독립성 취약", "warning"))
            elif outsideRatio >= 50:
                flags.append((f"사외이사비율 {outsideRatio:.0f}% -- 이사회 독립성 양호", "opportunity"))

    # 감사의견
    audit = calcAuditOpinionTrend(company)
    if audit and audit["history"]:
        latest = audit["history"][-1]
        opinion = latest.get("opinion")
        if opinion and opinion != "적정의견" and opinion != "적정":
            flags.append((f"최근 감사의견: {opinion}", "warning"))

        # 감사인 변경
        changes = [h for h in audit["history"] if h.get("auditorChanged")]
        if len(changes) >= 2:
            flags.append(("감사인 잦은 변경 -- 감사 독립성 점검 필요", "warning"))

    return flags


# ── 임원보수 괴리 ──


@memoized_calc
def calcExecutivePayDivergence(company, *, basePeriod: str | None = None) -> dict | None:
    """임원 총보수 5Y 증가율 vs 매출/순이익 증가율 괴리.

    실적 부진에도 임원보수만 증가하는 패턴을 감지한다.

    Returns
    -------
    dict | None
        history : list[dict]
            year : str
            execPayTotal : float — 전체 임원 보수 총액 (원)
            revenue : float — 매출 (원)
            netIncome : float — 순이익 (원)
        cagr : dict
            execPay : float — 5Y CAGR (%)
            revenue : float — 5Y CAGR (%)
            netIncome : float — 5Y CAGR (%)
        divergence : float | None — execPay CAGR - 매출 CAGR (%p). 양수 = 매출보다 빨리 증가.
    """
    pay = _safePivotExecutivePay(company)
    if pay is None or pay.payByTypeDf is None:
        return None

    import polars as pl

    df = pay.payByTypeDf
    if isEmptyDf(df):
        return None

    # category 합산 → year별 전체 임원보수
    try:
        yearly = df.group_by("year").agg(pl.col("totalPay").sum().alias("total")).sort("year")
        payByYear: dict[str, float] = {str(r["year"]): float(r["total"] or 0) for r in yearly.to_dicts()}
    except (KeyError, TypeError, ValueError, pl.exceptions.PolarsError):
        return None

    if not payByYear:
        return None

    # 매출/순이익 매핑
    from dartlab.analysis.financial._helpers import toDictBySnakeId
    from dartlab.core.finance.helpers import annualColsFromPeriods

    parsed = toDictBySnakeId(company.select("IS", ["sales", "net_profit"]))
    if parsed is None:
        return None
    isData, periods = parsed
    yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=5)

    # 분기 컬럼 → 연도 매핑 (annual cols: "2024" 혹은 "2024Q4")
    def _yearOf(col: str) -> str:
        """기간 컬럼에서 연도 4자리 추출."""
        return col[:4]

    salesRow = isData.get("sales", {})
    niRow = isData.get("net_profit", {})

    history = []
    years = sorted(payByYear.keys())[-5:]  # 최근 5년 pay 데이터 기준
    for y in years:
        col = next((c for c in yCols if _yearOf(c) == y), None)
        rev = salesRow.get(col) if col else None
        ni = niRow.get(col) if col else None
        history.append(
            {
                "year": y,
                "execPayTotal": payByYear.get(y),
                "revenue": rev,
                "netIncome": ni,
            }
        )

    if len(history) < 2:
        return None

    def _cagr(vals: list[float | None]) -> float | None:
        """양수 값 리스트에서 CAGR 산출 (%)."""
        vv = [v for v in vals if v is not None and v > 0]
        if len(vv) < 2:
            return None
        first, last = vv[0], vv[-1]
        n = len(vv) - 1
        return round(((last / first) ** (1 / n) - 1) * 100, 2) if n > 0 else None

    cagr = {
        "execPay": _cagr([h["execPayTotal"] for h in history]),
        "revenue": _cagr([h["revenue"] for h in history]),
        "netIncome": _cagr([h["netIncome"] for h in history]),
    }

    divergence = None
    if cagr["execPay"] is not None and cagr["revenue"] is not None:
        divergence = round(cagr["execPay"] - cagr["revenue"], 2)

    return {"history": history, "cagr": cagr, "divergence": divergence}


# ── 외부이사 독립성 ──


@memoized_calc
def calcIndependentDirectorQuality(company, *, basePeriod: str | None = None) -> dict | None:
    """외부이사 독립성 — 비율 시계열 + 독립성 플래그.

    Returns
    -------
    dict | None
        history : list[dict]
            year : str
            total : int
            outside : int
            ratio : float — 사외이사 비율 (%)
        latest : dict — 최신 구성
        flags : list[str] — 독립성 우려 신호
    """
    from dartlab.core.finance.helpers import parseNumStr  # noqa: F401 (consistency)

    exec_ = _safePivotExecutive(company)
    if exec_ is None:
        return None

    # executivePayAllTotal / boardOfDirectors 등에서 연도별 구성이 제공될 수 있다
    # 간략히 현재 구성만 활용 — 시계열은 report.executive에 있는 경우만
    total = getattr(exec_, "totalCount", 0) or 0
    outside = getattr(exec_, "outsideCount", 0) or 0
    if total == 0:
        return None

    ratio = round(outside / total * 100, 1)

    flags: list[str] = []
    if ratio < 25:
        flags.append(f"사외이사비율 {ratio:.0f}% — 이사회 독립성 취약 (25% 기준)")
    elif ratio < 33:
        flags.append(f"사외이사비율 {ratio:.0f}% — 독립성 기준(1/3) 미달")
    if outside <= 2 and total >= 6:
        flags.append(f"사외이사 {outside}명 — 절대수 부족")

    latest = {"total": total, "outside": outside, "ratio": ratio}
    return {
        "history": [{"year": "latest", "total": total, "outside": outside, "ratio": ratio}],
        "latest": latest,
        "flags": flags,
    }


def _safePivotExecutivePay(company):
    """report.executivePay를 안전하게 가져온다."""
    try:
        result = company._report.executivePay
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


# ── 내부 헬퍼 ──


def _safePivotMajorHolder(company):
    """report.majorHolder를 안전하게 가져온다."""
    try:
        result = company._report.majorHolder
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


def _safePivotExecutive(company):
    """report.executive를 안전하게 가져온다."""
    try:
        result = company._report.executive
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


def _safePivotAudit(company):
    """report.audit를 안전하게 가져온다."""
    try:
        result = company._report.audit
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None
