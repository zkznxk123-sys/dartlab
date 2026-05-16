"""5-1 지배구조 분석 -- 이 회사의 주인은 누구이며, 감시는 작동하는가.

report 데이터(최대주주, 임원, 감사의견, 임원보수)에서 지배구조 핵심 지표를
추출하며, 사업보고서 텍스트 섹션 파서(sanction, contingentLiability)로
제재·소송·채무보증 등 법적 이벤트 리스크를 집계한다.

DART 전용 섹션 기반 calc는 EDGAR Company에서 None을 반환한다 (SEC 공시 구조
한계 — 동등 소스 없음).
"""

from __future__ import annotations

from dartlab.core.financeDocAccessor import getFinanceDocAccessor
from dartlab.core.memory import memoizedCalc
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.core.utils.helpers import MAX_RATIO_YEARS, annualColsFromPeriods, toDictBySnakeId

# ── 최대주주 지분 시계열 ──


@memoizedCalc
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


@memoizedCalc
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


@memoizedCalc
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


# ── 임원보수 괴리 ──


@memoizedCalc
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
    from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

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


@memoizedCalc
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
    from dartlab.core.utils.helpers import parseNumStr  # noqa: F401 (consistency)

    exec_ = _safePivotExecutive(company)
    if exec_ is None:
        return None

    # executivePayAllTotal / boardOfDirectors 등에서 연도별 구성이 제공될 수 있다
    # 간략히 현재 구성만 활용 — 시계열은 report.executive에 있는 경우만
    # totalCount/outsideCount 가 None 또는 0 이면 임원 구성 데이터 없음 → 분석 불가
    total = getattr(exec_, "totalCount", None)
    outside = getattr(exec_, "outsideCount", None)
    if not total:
        return None
    if outside is None:
        outside = 0  # 사외이사 정보 누락 — 0 가정 후 비율 0% (보수적 신호)

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


# ── DART 전용 섹션 파이프라인 접근 ──


def _getDartStockCode(company) -> str | None:
    """DART Company에서 종목코드를 추출. EDGAR/다른 provider면 None.

    DART 전용 섹션 파이프라인(sanction, contingentLiability, relatedPartyTx)은
    사업보고서 parquet를 가정하므로 KRW 통화의 6자리 종목코드만 지원한다.
    """
    currency = getattr(company, "currency", None)
    if currency != "KRW":
        return None
    code = getattr(company, "stockCode", None) or getattr(company, "stock_code", None)
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return None
    return code


def _loadSanction(company):
    """sanction 파이프라인 호출. DART 외 or 데이터 없음 시 None."""
    code = _getDartStockCode(company)
    if not code:
        return None
    accessor = getFinanceDocAccessor()
    return accessor.sanction(code) if accessor else None


def _loadContingentLiability(company):
    """contingentLiability 파이프라인 호출."""
    code = _getDartStockCode(company)
    if not code:
        return None
    accessor = getFinanceDocAccessor()
    return accessor.contingentLiability(code) if accessor else None


def _fetchLatestEquity(company, *, basePeriod: str | None = None) -> int | None:
    """BS에서 최근 연도 자기자본(total_equity)을 추출. 실패 시 None."""
    try:
        parsed = toDictBySnakeId(company.select("BS", ["total_equity"]))
    except (AttributeError, ValueError, KeyError, TypeError):
        return None
    if parsed is None:
        return None
    bsData, periods = parsed
    yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=1)
    if not yCols:
        return None
    row = bsData.get("total_equity", {})
    val = row.get(yCols[-1])
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# ── 법적 이벤트 리스크 ──


# ── 오너 집중도 ──


def _loadExecutiveDocs(company):
    """docs/finance/executive 파이프라인 호출 — 개인별 임원 시계열."""
    code = _getDartStockCode(company)
    if not code:
        return None
    accessor = getFinanceDocAccessor()
    return accessor.executive(code) if accessor else None


# ── 대표이사 교체 ──


CEO_TURNOVER_WINDOW_YEARS = 5


def _loadRelatedPartyTx(company):
    """relatedPartyTx 파이프라인 호출. DART 외 or 데이터 없음 시 None."""
    code = _getDartStockCode(company)
    if not code:
        return None
    accessor = getFinanceDocAccessor()
    return accessor.relatedPartyTx(code) if accessor else None


# ── 특수관계자 거래 집중도 ──


RELATED_PARTY_PARSER_UNIT = 1_000_000  # 사업보고서 표준 단위(백만원) → 원


LEGAL_EVENT_WINDOW_YEARS = 3


# 분리된 깊이 분석 (BC re-export)
from dartlab.analysis.financial._governanceDeep import (  # noqa: E402, F401
    calcCEOTurnover,
    calcGovernanceFlags,
    calcLegalEventRisk,
    calcOwnerConcentration,
    calcRelatedPartyIntensity,
)
