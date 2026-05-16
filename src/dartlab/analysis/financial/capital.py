"""1-2 자금 구조 분석 — 계산만 담당.

블록 조립은 story/builders.py가 한다.
여기는 company.select() → 계산 → dict/숫자 반환.
"""

from __future__ import annotations

from dartlab.analysis.financial.accountSums import sumBorrowings
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_QUARTERS = 5
_MAX_YEARS = 8


# ── 유틸 ──


def _quarterlyCols(periods: list[str], maxQ: int = _MAX_QUARTERS) -> list[str]:
    """기간 목록에서 분기 컬럼 추출. 분기가 없으면 연간 컬럼 fallback (EDGAR 호환).

    Parameters
    ----------
    periods : list[str]
        전체 기간 문자열 목록 (예: ``["2024Q4", "2024Q3", "2024"]``).
    maxQ : int
        반환할 최대 컬럼 수.

    Returns
    -------
    list[str]
        최신순 정렬된 분기(또는 연간 fallback) 컬럼 목록.
    """
    quarterly = sorted([c for c in periods if "Q" in c], reverse=True)[:maxQ]
    if quarterly:
        return quarterly
    # EDGAR fallback: 연간 데이터 (2024, 2023, ...)
    return sorted([c for c in periods if c.isdigit() and len(c) == 4], reverse=True)[:maxQ]


def _getRatios(company):
    """RatioResult 객체 — 내부 compute 전용 (attribute access).

    Returns
    -------
    RatioResult | None
        회사의 재무비율 객체. 데이터 없으면 None.
    """
    try:
        return company._finance.ratios
    except (ValueError, KeyError, AttributeError):
        return None


import contextvars

_analysisCurrency: contextvars.ContextVar[str] = contextvars.ContextVar("analysis_currency", default="KRW")


def _fmtAmt(value) -> str:
    """금액을 조/억 또는 B/M 단위로 포맷 (순수 문자열, story import 없이).

    Parameters
    ----------
    value : float | None
        포맷할 금액 (원 또는 달러).

    Returns
    -------
    str
        단위 포함 문자열. KRW이면 ``"1.2조"``, ``"500억"``, USD이면 ``"$1.2B"``, ``"$500M"`` 등.
        None이면 ``"-"``.
    """
    if value is None:
        return "-"
    absVal = abs(value)
    sign = "-" if value < 0 else ""
    if _analysisCurrency.get() == "USD":
        if absVal >= 1_000_000_000:
            return f"{sign}${absVal / 1_000_000_000:.1f}B"
        if absVal >= 1_000_000:
            return f"{sign}${absVal / 1_000_000:.0f}M"
        if absVal >= 1_000:
            return f"{sign}${absVal / 1_000:.0f}K"
        return f"{sign}${absVal:,.0f}"
    if absVal >= 1_0000_0000_0000:
        return f"{sign}{absVal / 1_0000_0000_0000:.1f}조"
    if absVal >= 1_0000_0000:
        return f"{sign}{absVal / 1_0000_0000:.0f}억"
    if absVal >= 1_0000:
        return f"{sign}{absVal / 1_0000:.0f}만"
    return f"{sign}{absVal:,.0f}"


# ── 계산 함수들 ──


@memoizedCalc
def _latestAnnualVal(company, stmt: str, accountName: str) -> float | None:
    """select(stmt, [accountName])에서 최신 연도 값을 꺼낸다.

    회사마다 한국어 변형이 달라서 accountName 매칭 실패 가능 → None 반환.

    Parameters
    ----------
    company : Company
        대상 기업 객체.
    stmt : str
        재무제표 구분 (``"BS"``, ``"IS"``, ``"CF"``).
    accountName : str
        계정과목명.

    Returns
    -------
    float | None
        최신 연도의 계정 값 (원). 데이터 없으면 None.
    """
    try:
        result = company.select(stmt, [accountName])
    except (ValueError, KeyError):
        return None
    parsed = toDictBySnakeId(result)
    if parsed is None:
        return None
    data, allPeriods = parsed
    row = data.get(accountName)
    if row is None:
        return None
    yCols = annualColsFromPeriods(allPeriods, None, 1)
    if not yCols:
        return None
    return row.get(yCols[0])


def _calcNetDebtEbitda(company, finDebt: float) -> float | None:
    """순차입금/EBITDA — 차입 감당 능력.

    Parameters
    ----------
    company : Company
        대상 기업 객체.
    finDebt : float
        금융부채 합계 (원).

    Returns
    -------
    float | None
        순차입금/영업이익 (배). 순현금이면 0.0, 영업이익 없으면 None.
    """
    # 현금 미수집 (None) → finDebt 만으로 netDebt 추정. 진짜 0 (현금 0) 은 사실상 없음.
    cash = _latestAnnualVal(company, "BS", "현금및현금성자산")
    if cash is None:
        return None  # 현금 미수집 시 netDebt 정확도 낮음 → None 으로 정직 표시
    netDebt = finDebt - cash
    if netDebt <= 0:
        return 0.0  # 순현금
    opIncome = _latestAnnualVal(company, "IS", "영업이익")
    if opIncome is not None and opIncome > 0:
        return netDebt / opIncome  # EBITDA 대신 영업이익 기반 (보수적)
    return None


def _calcImpliedBorrowingRate(company, finDebt: float) -> float | None:
    """암묵적 차입금리 — 금융비용/금융부채.

    Parameters
    ----------
    company : Company
        대상 기업 객체.
    finDebt : float
        금융부채 합계 (원).

    Returns
    -------
    float | None
        암묵적 차입금리 (%). 금융부채 없거나 이자비용 없으면 None.
    """
    if finDebt <= 0:
        return None
    ie = _latestAnnualVal(company, "IS", "이자비용") or _latestAnnualVal(company, "IS", "금융비용")
    if ie is None or ie <= 0:
        return None
    return ie / finDebt * 100


@memoizedCalc
def calcCapitalOverview(company, *, basePeriod: str | None = None) -> dict | None:
    """총자산/총부채/자기자본/순차입금 스냅샷.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        metrics : list[tuple[str, str]] — (항목명, 값 문자열) 쌍 목록
    """
    ratios = _getRatios(company)
    if ratios is None:
        return None

    metrics = []

    ta = getattr(ratios, "totalAssets", None)
    if ta is not None:
        metrics.append(("총자산", _fmtAmt(ta)))

    tl = getattr(ratios, "totalLiabilities", None)
    dr = getattr(ratios, "debtRatio", None)
    if tl is not None:
        label = _fmtAmt(tl)
        if dr is not None:
            label += f" (부채비율 {dr:.0f}%)"
        metrics.append(("총부채", label))

    te = getattr(ratios, "totalEquity", None)
    er = getattr(ratios, "equityRatio", None)
    if te is not None:
        label = _fmtAmt(te)
        if er is not None:
            label += f" (자기자본비율 {er:.0f}%)"
        metrics.append(("자기자본", label))

    nd = getattr(ratios, "netDebt", None)
    if nd is not None:
        if nd < 0:
            metrics.append(("순차입금", f"{_fmtAmt(abs(nd))} (순현금)"))
        else:
            ndr = getattr(ratios, "netDebtRatio", None)
            label = _fmtAmt(nd)
            if ndr is not None:
                label += f" (순차입금비율 {ndr:.0f}%)"
            metrics.append(("순차입금", label))

    if not metrics:
        return None

    return {"metrics": metrics}


@memoizedCalc
def calcCapitalTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """자본총계·이익잉여금 시계열.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        tables : list[tuple[str, list[dict], list[str]]] — (라벨, 행 목록, 기간 컬럼) 튜플
    """
    result = company.select("BS", ["자본총계", "이익잉여금", "미처분이익잉여금(결손금)"])
    parsed = toDictBySnakeId(result)
    if parsed is None or "total_stockholders_equity" not in parsed[0]:
        return None

    data, allPeriods = parsed
    from dartlab.core.utils.helpers import mergeRows

    equityRow = data["total_stockholders_equity"]
    retainedRow = mergeRows(data.get("retained_earnings"), data.get("unappropriated_retained_earnings_deficit"))

    tables = []
    yCols = annualColsFromPeriods(allPeriods, basePeriod, _MAX_YEARS)
    if yCols:
        yearTable = _buildCapitalTable(equityRow, retainedRow, yCols)
        if yearTable:
            tables.append(("연도별", yearTable, yCols))

    qCols = _quarterlyCols(allPeriods, _MAX_QUARTERS)
    if qCols:
        qtrTable = _buildCapitalTable(equityRow, retainedRow, qCols)
        if qtrTable:
            tables.append(("분기별", qtrTable, qCols))

    if not tables:
        return None

    return {"tables": tables}


def _buildCapitalTable(equityRow: dict, retainedRow: dict | None, cols: list[str]) -> list[dict]:
    """자본구조 테이블 행 구성.

    Parameters
    ----------
    equityRow : dict
        자본총계 {period: value} 매핑.
    retainedRow : dict | None
        이익잉여금 {period: value} 매핑.
    cols : list[str]
        표시할 기간 컬럼 목록.

    Returns
    -------
    list[dict]
        테이블 행 목록. 각 행은 ``{"": 항목명, period: 값, ...}`` 형태.
    """
    rows: list[dict] = []
    rows.append({"": "자본총계", **{c: equityRow.get(c) for c in cols}})

    if retainedRow:
        rows.append({"": "이익잉여금", **{c: retainedRow.get(c) for c in cols}})

        paidInRow: dict = {"": "자본금+잉여금"}
        for c in cols:
            eq = equityRow.get(c)
            re = retainedRow.get(c)
            if eq is not None and re is not None:
                paidInRow[c] = eq - re
            else:
                paidInRow[c] = None
        rows.append(paidInRow)

        pctRow: dict = {"": "→ 내부유보 비중"}
        for c in cols:
            eq = equityRow.get(c)
            re = retainedRow.get(c)
            if eq and re and eq != 0:
                pctRow[c] = f"{re / eq * 100:.0f}%"
            else:
                pctRow[c] = "-"
        rows.append(pctRow)

    return rows


@memoizedCalc
def calcDebtTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """부채총계·금융부채·영업부채 시계열.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        tables : list[tuple[str, list[dict], list[str]]] — (라벨, 행 목록, 기간 컬럼) 튜플
    """
    result = company.select("BS", ["부채총계", "단기차입금", "장기차입금", "차입부채", "사채"])
    parsed = toDictBySnakeId(result)
    if parsed is None or "total_liabilities" not in parsed[0]:
        return None

    data, allPeriods = parsed
    liabRow = data["total_liabilities"]
    stbRow = data.get("shortterm_borrowings")
    ltbRow = data.get("longterm_borrowings")
    unifiedBorrowRow = data.get("borrowings")  # 통합 차입금 fallback
    bondRow = data.get("debentures")
    # stb/ltb 둘 다 없는 회사 → unifiedBorrow 를 stb 위치로
    if stbRow is None and ltbRow is None and unifiedBorrowRow is not None:
        stbRow = unifiedBorrowRow

    tables = []
    yCols = annualColsFromPeriods(allPeriods, basePeriod, _MAX_YEARS)
    if yCols:
        yearTable = _buildDebtTable(liabRow, stbRow, ltbRow, bondRow, yCols)
        if yearTable:
            tables.append(("연도별", yearTable, yCols))

    qCols = _quarterlyCols(allPeriods, _MAX_QUARTERS)
    if qCols:
        qtrTable = _buildDebtTable(liabRow, stbRow, ltbRow, bondRow, qCols)
        if qtrTable:
            tables.append(("분기별", qtrTable, qCols))

    if not tables:
        return None

    return {"tables": tables}


def _buildDebtTable(liabRow: dict, stbRow, ltbRow, bondRow, cols: list[str]) -> list[dict]:
    """부채구조 테이블 행 구성.

    Parameters
    ----------
    liabRow : dict
        부채총계 {period: value} 매핑.
    stbRow : dict | None
        단기차입금 매핑.
    ltbRow : dict | None
        장기차입금 매핑.
    bondRow : dict | None
        사채 매핑.
    cols : list[str]
        표시할 기간 컬럼 목록.

    Returns
    -------
    list[dict]
        테이블 행 목록. 각 행은 ``{"": 항목명, period: 값, ...}`` 형태.
    """
    rows: list[dict] = []
    rows.append({"": "부채총계", **{c: liabRow.get(c) for c in cols}})

    finDebtRow: dict = {"": "금융부채"}
    hasFinDebt = False
    for c in cols:
        stb = (stbRow or {}).get(c)
        ltb = (ltbRow or {}).get(c)
        bond = (bondRow or {}).get(c)
        parts = [v for v in [stb, ltb, bond] if v is not None]
        if parts:
            finDebtRow[c] = sum(parts)
            hasFinDebt = True
        else:
            finDebtRow[c] = None

    if hasFinDebt:
        opDebtRow: dict = {"": "영업부채"}
        for c in cols:
            tl = liabRow.get(c)
            fd = finDebtRow.get(c)
            if tl is not None and fd is not None:
                opDebtRow[c] = tl - fd
            else:
                opDebtRow[c] = None
        rows.append(opDebtRow)
        rows.append(finDebtRow)

        pctRow: dict = {"": "→ 금융부채 비중"}
        for c in cols:
            tl = liabRow.get(c)
            fd = finDebtRow.get(c)
            if tl and fd and tl != 0:
                pctRow[c] = f"{fd / tl * 100:.0f}%"
            else:
                pctRow[c] = "-"
        rows.append(pctRow)

    return rows


@memoizedCalc
def calcInterestBurden(company, *, basePeriod: str | None = None) -> dict | None:
    """이자보상배율·이자비용.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        metrics : list[tuple[str, str]] — (항목명, 값 문자열) 쌍 목록
    """
    ratios = _getRatios(company)
    if ratios is None:
        return None

    metrics = []

    ic = getattr(ratios, "interestCoverage", None)
    if ic is not None:
        if ic >= 10:
            quality = "우수"
        elif ic >= 3:
            quality = "안정"
        elif ic >= 1.5:
            quality = "주의"
        else:
            quality = "위험"
        metrics.append(("이자보상배율", f"{ic:.1f}배 — {quality}"))

    ie = getattr(ratios, "interestExpense", None)
    if ie is not None:
        metrics.append(("이자비용", _fmtAmt(ie)))

    if not metrics:
        return None

    return {"metrics": metrics}


@memoizedCalc
def calcLiquidity(company, *, basePeriod: str | None = None) -> dict | None:
    """유동성 4 지표 (유동비율 + 당좌비율 + 현금비율 + 순운전자본) 정성 평가 라벨.

    Capabilities:
        ratios 의 4 유동성 지표 + 순운전자본 (WC) 을 한국어 정성 라벨 (안정/
        보통/주의) 함께 산출. analysis() 의 안정성 축 표시용. credit
        engine 의 metrics 와 별도 (간단 표시 목적).

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``metrics`` (list[tuple[str, str]]): ("유동비율", "150% — 안정")
              형식. ratios=None 시 None.

    Raises:
        없음.

    Example:
        >>> r = calcLiquidity(Company("005930"))
        >>> r["metrics"][0]
        ('유동비율', '180% — 안정')

    Guide:
        임계값: 유동비율 ≥ 150% = 안정, 100~150% = 보통, < 100% = 주의.
        당좌비율 ≥ 100% = 즉시 동원 가능. 본 함수는 credit engine 의 7 축
        분해와 별도 — 사용자 보고용 간단 표시.

    SeeAlso:
        - ``credit.scoring.metrics.calcAllMetrics``: 7 축 정량 지표
        - ``narrateLiquidity``: credit 의 유동성 서사 생성
        - ``calcCashFlowStructure``: 현금흐름 구조 (보완)

    Requires:
        Company.finance (BS) + ratios 헬퍼.

    AIContext:
        라벨 "주의" 결과 단독 인용 금지 — 단기차입금 비중 + 현금 흐름 함께
        확인. KR 대기업은 차환 의존 (CR>150 + STDR>50) 흔하므로 모순 진단
        필요.

    LLM Specifications:
        AntiPatterns:
            - 유동비율 200%+ 회사 → "유동성 매우 우수" 단정 — 현금 보유 과다
              가능 (배당/투자 부진 신호). cashRatio 함께 확인.
            - ratios=None 시 None 반환 — 호출자 분기 필요.
        OutputSchema:
            ``{metrics: list[tuple[str, str]]}`` 또는 None.
        Prerequisites:
            BS 시계열 + _getRatios 헬퍼 로드.
        Freshness:
            BS 최신 분기.
        Dataflow:
            company → _getRatios → currentRatio/quickRatio/cashRatio + WC →
            한국어 라벨 → metrics list.
        TargetMarkets: KR (DART), US (EDGAR — 동일 비율 표준).
    """
    ratios = _getRatios(company)
    if ratios is None:
        return None

    metrics = []

    cr = getattr(ratios, "currentRatio", None)
    if cr is not None:
        quality = "안정" if cr >= 150 else "보통" if cr >= 100 else "주의"
        metrics.append(("유동비율", f"{cr:.0f}% — {quality}"))

    qr = getattr(ratios, "quickRatio", None)
    if qr is not None:
        metrics.append(("당좌비율", f"{qr:.0f}%"))

    car = getattr(ratios, "cashRatio", None)
    if car is not None:
        metrics.append(("현금비율", f"{car:.0f}%"))

    wc = getattr(ratios, "workingCapital", None)
    if wc is not None:
        metrics.append(("순운전자본", _fmtAmt(wc)))

    if not metrics:
        return None

    return {"metrics": metrics}


# ── calcCashFlowStructure + calcDistressIndicators + _sign/_classifyCfPattern/_isFinancialCompany → _capitalCashflow.py 분리 ──

from dartlab.analysis.financial._capitalCashflow import (  # noqa: E402, F401
    _classifyCfPattern,
    _isFinancialCompany,
    _sign,
    calcCashFlowStructure,
    calcDistressIndicators,
)

# ── 내부 헬퍼 ──


def _calcRetainedPct(equityRow, retainedRow) -> float | None:
    """이익잉여금 / 자본총계 비중.

    Returns
    -------
    float | None
        내부유보 비중 (%). 데이터 없으면 None.
    """
    if equityRow is None or retainedRow is None:
        return None
    for key in equityRow:
        eq = equityRow.get(key)
        re = retainedRow.get(key)
        if eq and re and eq != 0:
            return re / eq * 100
    return None


def _calcFinDebtPct(liabRow, stbRow, ltbRow, bondRow) -> float | None:
    """금융부채 / 부채총계 비중 — 최신 기간.

    Returns
    -------
    float | None
        금융부채 비중 (%). 데이터 없으면 None.
    """
    if liabRow is None:
        return None
    for key in liabRow:
        tl = liabRow.get(key)
        if tl is None or tl == 0:
            continue
        stb = (stbRow or {}).get(key)
        ltb = (ltbRow or {}).get(key)
        bond = (bondRow or {}).get(key)
        parts = [v for v in [stb, ltb, bond] if v is not None]
        if parts:
            return sum(parts) / tl * 100
    return None


# 분리된 함수 (BC re-export)
from dartlab.analysis.financial._capitalFunding import (  # noqa: E402, F401
    calcCapitalFlags,
    calcFundingSources,
)
