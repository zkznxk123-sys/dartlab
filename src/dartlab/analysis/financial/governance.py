"""5-1 지배구조 분석 -- 이 회사의 주인은 누구이며, 감시는 작동하는가.

report 데이터(최대주주, 임원, 감사의견, 임원보수)에서 지배구조 핵심 지표를
추출하며, 사업보고서 텍스트 섹션 파서(sanction, contingentLiability)로
제재·소송·채무보증 등 법적 이벤트 리스크를 집계한다.

DART 전용 섹션 기반 calc는 EDGAR Company에서 None을 반환한다 (SEC 공시 구조
한계 — 동등 소스 없음).
"""

from __future__ import annotations

from dartlab.analysis.financial._helpers import MAX_RATIO_YEARS
from dartlab.analysis.financial._memoize import memoized_calc
from dartlab.core.finance.helpers import annualColsFromPeriods, toDictBySnakeId
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

    # 오너 집중도 (본인/특수관계 분리)
    owner = calcOwnerConcentration(company)
    if owner and owner.get("latest"):
        lt = owner["latest"]
        top1 = lt.get("top1Share") or 0.0
        totalR = lt.get("topHolderRatio") or 0.0
        # 소유-지배 괴리 패턴: 본인 지분 적은데 특수관계 포함 총합이 큰 경우
        if top1 < 10 and totalR >= 40:
            flags.append(
                (
                    f"본인 지분 {top1:.1f}% vs 특수관계 포함 {totalR:.1f}% -- 소유-지배 괴리 큼",
                    "warning",
                )
            )
        # 과소 지배 — 20% 미만 + 특수관계도 낮음
        if totalR > 0 and totalR < 20:
            flags.append(
                (f"본인+특수관계 {totalR:.1f}% -- 경영권 방어 취약", "warning")
            )
        # 본인 지분 5년 급격 희석
        ch = owner.get("top1Change5y")
        if ch is not None and ch <= -5:
            flags.append(
                (f"본인 지분 5년간 {ch:+.1f}%p 희석 -- 승계/상속 이벤트 가능", "warning")
            )

    # 법적 이벤트 리스크 (제재·소송·채무보증)
    legal = calcLegalEventRisk(company)
    if legal:
        n = legal.get("windowYears", LEGAL_EVENT_WINDOW_YEARS)
        sanctionCount = legal.get("sanctionCount") or 0
        if sanctionCount >= 1:
            amt = legal.get("sanctionAmount") or 0
            # 1억 이상만 금액 표시 — 파서 단위 혼재로 1억 미만은 불확실
            amtText = f" (누적 {amt / 1e8:.1f}억원)" if amt >= 1_0000_0000 else ""
            flags.append(
                (f"최근 {n}년 제재 {sanctionCount}건{amtText} -- 규제 리스크", "warning")
            )
        lawsuitCount = legal.get("lawsuitCount") or 0
        lawsuitAmount = legal.get("lawsuitAmount") or 0
        if lawsuitCount >= 1 or lawsuitAmount >= 100_0000_0000:
            amtText = (
                f" (청구금액 {lawsuitAmount / 1e8:.0f}억원)"
                if lawsuitAmount >= 1_0000_0000
                else ""
            )
            flags.append(
                (f"최근 {n}년 소송 {lawsuitCount}건{amtText} -- 법적 분쟁 진행", "warning")
            )
        gRatio = legal.get("guaranteeToEquity")
        if gRatio is not None and gRatio >= 50:
            flags.append(
                (f"채무보증/자기자본 {gRatio:.0f}% -- 우발채무 부담 큼", "warning")
            )

    # 특수관계자 거래 집중도
    rpt = calcRelatedPartyIntensity(company)
    if rpt and rpt.get("latest"):
        lt = rpt["latest"]
        rev = lt.get("relatedRevenueRatio")
        if rev is not None and rev >= 30:
            trend = rpt.get("trend", "unknown")
            trendText = {"increasing": ", 증가 추세", "decreasing": ", 감소 추세", "stable": ""}.get(
                trend, ""
            )
            flags.append(
                (
                    f"특수관계 매출 {rev:.0f}%{trendText} -- 내부거래 의존 높음",
                    "warning",
                )
            )
        gRatio = lt.get("relatedGuaranteeRatio")
        if gRatio is not None and gRatio >= 20:
            flags.append(
                (
                    f"특수관계 보증/자기자본 {gRatio:.0f}% -- 계열 지원 부담",
                    "warning",
                )
            )

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
    try:
        from dartlab.providers.dart.docs.finance.sanction import sanction

        return sanction(code)
    except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
        return None


def _loadContingentLiability(company):
    """contingentLiability 파이프라인 호출."""
    code = _getDartStockCode(company)
    if not code:
        return None
    try:
        from dartlab.providers.dart.docs.finance.contingentLiability import contingentLiability

        return contingentLiability(code)
    except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
        return None


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


@memoized_calc
def calcOwnerConcentration(company, *, basePeriod: str | None = None) -> dict | None:
    """오너 집중도 — 본인/특수관계 분리 지분 시계열.

    report.majorHolder df에서 연도별 본인("본인") 지분과 특수관계인 합산
    지분을 분리한다. 한국 시장 특유의 "소유-지배 괴리(control-ownership
    disparity)"는 특수관계인을 통한 간접 지배가 크게 벌어질수록 커지므로,
    기존 합산 지분율(calcOwnershipTrend)만으로는 포착되지 않는 축이다.
    ECGI "Korea chaebol cash-flow rights" 연구와 MSCI Ownership & Control
    Key Issue 의 평가 방식에 대응한다.

    Parameters
    ----------
    company : Company
        분석 대상 기업 (DART).
    basePeriod : str, optional
        기준 기간. 현재 구현에서는 참고만 — 시계열 전부 반환.

    Returns
    -------
    dict | None
        None : majorHolder 데이터 없음.
        latest : dict — 최근 연도 스냅샷
            year : int — 연도
            topHolderRatio : float — 본인+특수관계 합산 지분 (%)
            top1Share : float — 본인 지분 (%)
            specialRelatedSum : float — 특수관계인 지분 합계 (%)
            specialRelatedCount : int — 특수관계인 수 (명)
        history : list[dict] — 연도별 추이 (최근 5년)
            year : int — 연도
            top1 : float — 본인 지분 (%)
            specialRelated : float — 특수관계 합계 (%)
            total : float — 본인+특수관계 합산 (%)
        top1Change5y : float | None — 5년간 본인 지분 변동폭 (%p)

    Raises
    ------
    없음 — 데이터 없음은 None 반환.

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> c.analysis("지배구조")["ownerConcentration"]

    Notes
    -----
    - 보통주 기준. 우선주는 집계에서 제외.
    - 합계행("계")는 제외하고 본인·특수관계인 개별 행만 집계.
    - `top1Change5y`는 5년 이상 데이터가 있을 때만 계산. 짧으면 None.

    Guide
    -----
    `top1Share < 10%`이면서 `topHolderRatio > 40%`이면 소유-지배 괴리가
    큰 패턴(특수관계인을 통한 간접 지배). `top1Change5y < -5%p`이면
    본인 지분 희석 국면으로 상속·승계 이벤트 신호일 수 있다.

    See Also
    --------
    calcOwnershipTrend : 합산 지분율 시계열 (본/특수 미분리).
    calcGovernanceFlags : 본 calc 결과를 warning/opportunity로 소비.
    """
    import polars as pl

    result = _safePivotMajorHolder(company)
    if result is None or result.df is None or result.df.is_empty():
        return None

    df = result.df.filter(pl.col("nm") != "계")
    if "nm" in df.columns:
        df = df.filter(pl.col("nm").is_not_null())
    if df.is_empty():
        return None

    history: list[dict] = []
    for year in sorted(df["year"].unique().to_list())[-MAX_RATIO_YEARS:]:
        yearDf = df.filter(pl.col("year") == year)
        if yearDf.is_empty():
            continue
        latestQ = yearDf["quarterNum"].max()
        snap = yearDf.filter(pl.col("quarterNum") == latestQ)

        top1 = 0.0
        specialRelated = 0.0
        for row in snap.iter_rows(named=True):
            r = row.get("trmend_posesn_stock_qota_rt") or 0.0
            relate = (row.get("relate") or "").strip()
            if not relate or relate == "-":
                continue
            # "본인" 포함이면 본인 ("최대주주 본인", "본인" 등). 단 "특수관계인"의 "인"과
            # 겹치므로 "특수관계"가 포함된 경우는 제외.
            if "본인" in relate and "특수관계" not in relate:
                top1 = max(top1, float(r))
            else:
                specialRelated += float(r)

        history.append(
            {
                "year": int(year),
                "top1": round(top1, 2),
                "specialRelated": round(specialRelated, 2),
                "total": round(top1 + specialRelated, 2),
            }
        )

    if not history:
        return None

    latestYear = history[-1]["year"]
    latestDf = df.filter(pl.col("year") == latestYear)
    latestQ = latestDf["quarterNum"].max()
    latestSnap = latestDf.filter(pl.col("quarterNum") == latestQ)
    specialRelatedCount = 0
    for row in latestSnap.iter_rows(named=True):
        relate = (row.get("relate") or "").strip()
        if not relate or relate == "-":
            continue
        if "본인" in relate and "특수관계" not in relate:
            continue
        specialRelatedCount += 1

    latest = {
        "year": latestYear,
        "topHolderRatio": history[-1]["total"],
        "top1Share": history[-1]["top1"],
        "specialRelatedSum": history[-1]["specialRelated"],
        "specialRelatedCount": specialRelatedCount,
    }

    top1Change5y: float | None = None
    if len(history) >= 5:
        top1Change5y = round(history[-1]["top1"] - history[-5]["top1"], 2)
    elif len(history) >= 2:
        top1Change5y = round(history[-1]["top1"] - history[0]["top1"], 2)

    return {
        "latest": latest,
        "history": history,
        "top1Change5y": top1Change5y,
    }


def _loadRelatedPartyTx(company):
    """relatedPartyTx 파이프라인 호출. DART 외 or 데이터 없음 시 None."""
    code = _getDartStockCode(company)
    if not code:
        return None
    try:
        from dartlab.providers.dart.docs.finance.relatedPartyTx import relatedPartyTx

        return relatedPartyTx(code)
    except (ValueError, KeyError, TypeError, AttributeError, FileNotFoundError):
        return None


# ── 특수관계자 거래 집중도 ──


RELATED_PARTY_PARSER_UNIT = 1_000_000  # 사업보고서 표준 단위(백만원) → 원


@memoized_calc
def calcRelatedPartyIntensity(company, *, basePeriod: str | None = None) -> dict | None:
    """특수관계자 거래 집중도 — 매출·매입·보증의 내부거래 비율 시계열.

    사업보고서 「X. 대주주 등과의 거래내용」에서 특수관계자 매출·매입·
    채무보증을 추출하고 전사 매출·자산 대비 비율을 산출한다. tunneling
    (자산·수익 이전) 문헌과 ISS Audit&Risk pillar 에 대응하는 축으로,
    지주·계열 중심 기업의 이해충돌 가능성을 포착한다.

    Parameters
    ----------
    company : Company
        분석 대상 기업 (DART).
    basePeriod : str, optional
        비율 계산용 기준 기간. 미지정 시 최신.

    Returns
    -------
    dict | None
        None : relatedPartyTx 데이터 없음 또는 DART 외 provider.
        latest : dict — 최근 연도 비율
            year : int — 연도
            relatedSales : int — 특수관계 매출 (원)
            relatedPurchases : int — 특수관계 매입 (원)
            relatedGuarantee : int — 특수관계 보증 잔액 (원)
            totalRevenue : int | None — 전사 매출 (원)
            totalEquity : int | None — 자기자본 (원)
            relatedRevenueRatio : float | None — 전사 매출 대비 매출 (%)
            relatedPurchaseRatio : float | None — 전사 매출 대비 매입 (%)
            relatedGuaranteeRatio : float | None — 자기자본 대비 보증 (%)
        history : list[dict] — 연도별 추이 (최근 5년)
            year : int
            relatedSales : int — 금액 (원)
            relatedPurchases : int — 금액 (원)
        trend : str — "increasing" | "stable" | "decreasing" | "unknown"
            최근 3년 매출 비율 추이. 데이터 부족 시 "unknown".

    Raises
    ------
    없음 — 데이터 없음은 None 반환.

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> c.analysis("지배구조")["relatedPartyIntensity"]

    Notes
    -----
    - 파서가 반환하는 금액은 사업보고서 표기 단위(백만원) 가정. calc 내부
      에서 원 단위로 환산 후 IS/BS 와 비율 계산.
    - 파서가 단위를 자동 감지하지 않으므로 공시 표 단위가 "천원"이나 "원"
      이면 비율이 과대/과소 추정된다. 1% 미만·10000% 초과 값은 단위 오류
      가능성이 있으니 원본 (`c.show("relatedPartyTx")`) 확인 권장.
    - 매입 비율은 전사 매출 대비로 일관성 유지 (매출원가 분해가 기업별
      일정치 않아 비교 가능성 우선).

    Guide
    -----
    `relatedRevenueRatio >= 30%` + `trend == "increasing"` 은 매출의 내부
    계열 의존도가 커지는 tunneling 신호. 지주·계열사 기업은 구조상 높게
    나올 수 있어 절대 수치보다 **피어 대비·추세**로 해석한다.

    See Also
    --------
    calcOwnerConcentration : 소유-지배 괴리 (별도 축).
    calcLegalEventRisk : 제재·소송 (별도 축).
    """
    import polars as pl

    rpt = _loadRelatedPartyTx(company)
    if rpt is None:
        return None
    if rpt.revenueTxDf is None and rpt.guaranteeDf is None:
        return None

    # 연도별 매출·매입·보증 합계 (백만원 → 원 환산)
    salesByYear: dict[int, int] = {}
    purchasesByYear: dict[int, int] = {}
    if rpt.revenueTxDf is not None and not rpt.revenueTxDf.is_empty():
        for row in rpt.revenueTxDf.iter_rows(named=True):
            y = row.get("year")
            if y is None:
                continue
            y = int(y)
            s = row.get("sales") or 0
            p = row.get("purchases") or 0
            salesByYear[y] = salesByYear.get(y, 0) + int(s) * RELATED_PARTY_PARSER_UNIT
            purchasesByYear[y] = purchasesByYear.get(y, 0) + int(p) * RELATED_PARTY_PARSER_UNIT

    guaranteeByYear: dict[int, int] = {}
    if rpt.guaranteeDf is not None and not rpt.guaranteeDf.is_empty():
        for row in rpt.guaranteeDf.iter_rows(named=True):
            y = row.get("year")
            if y is None:
                continue
            y = int(y)
            amt = row.get("amount") or 0
            guaranteeByYear[y] = guaranteeByYear.get(y, 0) + int(amt) * RELATED_PARTY_PARSER_UNIT

    allYears = sorted(set(salesByYear) | set(purchasesByYear) | set(guaranteeByYear))
    if not allYears:
        return None

    # 전사 매출 시계열
    revenueMap: dict[int, int] = {}
    try:
        parsed = toDictBySnakeId(company.select("IS", ["sales"]))
    except (AttributeError, ValueError, KeyError, TypeError):
        parsed = None
    if parsed is not None:
        isData, periods = parsed
        yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=10)
        salesRow = isData.get("sales", {})
        for col in yCols:
            try:
                yr = int(col[:4])
            except (ValueError, TypeError):
                continue
            v = salesRow.get(col)
            if v is not None:
                revenueMap[yr] = int(v)

    totalEquity = _fetchLatestEquity(company, basePeriod=basePeriod)

    history: list[dict] = []
    for y in allYears[-MAX_RATIO_YEARS:]:
        history.append(
            {
                "year": y,
                "relatedSales": salesByYear.get(y, 0),
                "relatedPurchases": purchasesByYear.get(y, 0),
            }
        )

    latestYear = allYears[-1]
    relatedSales = salesByYear.get(latestYear, 0)
    relatedPurchases = purchasesByYear.get(latestYear, 0)
    relatedGuarantee = guaranteeByYear.get(latestYear, 0)
    totalRevenue = revenueMap.get(latestYear)

    relatedRevenueRatio: float | None = None
    relatedPurchaseRatio: float | None = None
    relatedGuaranteeRatio: float | None = None
    if totalRevenue and totalRevenue > 0:
        relatedRevenueRatio = round(relatedSales / totalRevenue * 100, 1)
        relatedPurchaseRatio = round(relatedPurchases / totalRevenue * 100, 1)
    if totalEquity and totalEquity > 0:
        relatedGuaranteeRatio = round(relatedGuarantee / totalEquity * 100, 1)

    # 추세 판정: 매출 비율 기준 최근 3년 변화
    trend = "unknown"
    ratios: list[float] = []
    for h in history[-3:]:
        rev = revenueMap.get(h["year"])
        if rev and rev > 0:
            ratios.append(h["relatedSales"] / rev * 100)
    if len(ratios) >= 2:
        delta = ratios[-1] - ratios[0]
        if delta > 5:
            trend = "increasing"
        elif delta < -5:
            trend = "decreasing"
        else:
            trend = "stable"

    return {
        "latest": {
            "year": latestYear,
            "relatedSales": relatedSales,
            "relatedPurchases": relatedPurchases,
            "relatedGuarantee": relatedGuarantee,
            "totalRevenue": totalRevenue,
            "totalEquity": totalEquity,
            "relatedRevenueRatio": relatedRevenueRatio,
            "relatedPurchaseRatio": relatedPurchaseRatio,
            "relatedGuaranteeRatio": relatedGuaranteeRatio,
        },
        "history": history,
        "trend": trend,
    }


LEGAL_EVENT_WINDOW_YEARS = 3


@memoized_calc
def calcLegalEventRisk(company, *, basePeriod: str | None = None) -> dict | None:
    """법적 이벤트 리스크 — 최근 3년 제재·소송 + 채무보증/자기자본 집계.

    사업보고서 「III. 제재 현황」· 「2. 우발부채」 섹션에서 제재 건수·금액,
    소송 건수·금액, 자기자본 대비 채무보증 비율을 추출한다. 이벤트 스터디
    실증(벌칙공시 이후 누적초과수익률 음)과 ISS Governance QualityScore
    Audit&Risk 필러에 대응하는 축.

    Parameters
    ----------
    company : Company
        분석 대상 기업. DART Company만 지원 (EDGAR는 None 반환).
    basePeriod : str, optional
        자기자본 조회 기준 기간 (예: "2024Q4"). 미지정 시 최신.

    Returns
    -------
    dict | None
        None : sanction/contingent 데이터 없음 또는 DART 외 provider.
        sanctionCount : int — 최근 3년 제재 건수 (건)
        sanctionAmount : int — 최근 3년 제재 금액 합계 (원)
        lawsuitCount : int — 최근 3년 소송 건수 (건)
        lawsuitAmount : int — 최근 3년 소송 청구 금액 합계 (원)
        guaranteeAmount : int | None — 최근연도 채무보증 총액 (원)
        totalEquity : int | None — 최근연도 자기자본 (원)
        guaranteeToEquity : float | None — 자기자본 대비 채무보증 비율 (%)
        windowYears : int — 집계 윈도우 (년). 상수 3.
        recentEvents : list[dict] — 최근 이벤트 상위 5건
            year : int — 발생 연도
            kind : str — "sanction" 또는 "lawsuit"
            date : str — 발생일 (YYYY-MM-DD 또는 부분 문자열)
            party : str — 제재 기관 또는 소송 당사자
            description : str — 사건 내용·사유
            amount : int | None — 금액 (원). 미기재 시 None.

    Raises
    ------
    없음 — 데이터 없음은 None 반환.

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> c.analysis("지배구조")["legalEventRisk"]

    Notes
    -----
    - 집계 윈도우 3년은 이벤트 스터디 연구의 표준 관측 구간.
    - 제재·소송은 사업보고서 텍스트 섹션 기반이라 기업별 표 구조 차이로
      금액 추출이 실패하면 ``amount``는 None으로 두고 건수만 집계한다.
    - 채무보증은 최신 연도 stock 기준 (연결 또는 개별, 표기 기준 그대로).
    - EDGAR Company는 DART parquet을 가정하는 파이프라인 특성상 None 반환.

    Guide
    -----
    이벤트가 없으면 count=0, recentEvents=[] 반환 (None 아님).
    guaranteeToEquity >= 50%는 우발채무 부담이 큰 기업의 경고 신호로 본다.

    See Also
    --------
    calcGovernanceFlags : 본 calc 결과를 warning 플래그로 소비.
    """
    import datetime

    import polars as pl

    sanc = _loadSanction(company)
    cont = _loadContingentLiability(company)

    if sanc is None and cont is None:
        return None

    thisYear = datetime.datetime.now().year
    cutoff = thisYear - LEGAL_EVENT_WINDOW_YEARS

    sanctionCount = 0
    sanctionAmount = 0
    sanctionEvents: list[dict] = []
    if sanc is not None and sanc.sanctionDf is not None and not sanc.sanctionDf.is_empty():
        recent = sanc.sanctionDf.filter(pl.col("year") >= cutoff)
        sanctionCount = recent.height
        if "amountValue" in recent.columns and recent.height > 0:
            total = recent["amountValue"].sum()
            sanctionAmount = int(total) if total is not None else 0
        for row in recent.sort("year", descending=True).head(5).iter_rows(named=True):
            amt = row.get("amountValue")
            sanctionEvents.append(
                {
                    "year": row.get("year"),
                    "kind": "sanction",
                    "date": row.get("date") or "",
                    "party": row.get("agency") or row.get("subject") or "",
                    "description": row.get("action") or row.get("reason") or "",
                    "amount": int(amt) if amt is not None else None,
                }
            )

    lawsuitCount = 0
    lawsuitAmount = 0
    lawsuitEvents: list[dict] = []
    if cont is not None and cont.lawsuitDf is not None and not cont.lawsuitDf.is_empty():
        recent = cont.lawsuitDf.filter(pl.col("year") >= cutoff)
        lawsuitCount = recent.height
        if "amountValue" in recent.columns and recent.height > 0:
            total = recent["amountValue"].sum()
            lawsuitAmount = int(total) if total is not None else 0
        for row in recent.sort("year", descending=True).head(5).iter_rows(named=True):
            amt = row.get("amountValue")
            lawsuitEvents.append(
                {
                    "year": row.get("year"),
                    "kind": "lawsuit",
                    "date": row.get("filingDate") or "",
                    "party": row.get("parties") or "",
                    "description": row.get("description") or "",
                    "amount": int(amt) if amt is not None else None,
                }
            )

    guaranteeAmount: int | None = None
    if cont is not None and cont.guaranteeDf is not None and not cont.guaranteeDf.is_empty():
        latest = cont.guaranteeDf.sort("year", descending=True).head(1)
        if latest.height > 0 and "totalGuaranteeAmount" in latest.columns:
            val = latest["totalGuaranteeAmount"].item()
            guaranteeAmount = int(val) if val is not None else None

    totalEquity = _fetchLatestEquity(company, basePeriod=basePeriod)

    guaranteeToEquity: float | None = None
    if guaranteeAmount is not None and totalEquity and totalEquity > 0:
        guaranteeToEquity = round(guaranteeAmount / totalEquity * 100, 1)

    recentEvents = sorted(
        sanctionEvents + lawsuitEvents,
        key=lambda e: (e.get("year") or 0),
        reverse=True,
    )[:5]

    return {
        "sanctionCount": sanctionCount,
        "sanctionAmount": sanctionAmount,
        "lawsuitCount": lawsuitCount,
        "lawsuitAmount": lawsuitAmount,
        "guaranteeAmount": guaranteeAmount,
        "totalEquity": totalEquity,
        "guaranteeToEquity": guaranteeToEquity,
        "windowYears": LEGAL_EVENT_WINDOW_YEARS,
        "recentEvents": recentEvents,
    }
