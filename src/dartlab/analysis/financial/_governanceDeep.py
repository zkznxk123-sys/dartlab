"""governance.py 깊이 분석 — 5 종 분리.

calcGovernanceFlags + calcOwnerConcentration + calcCEOTurnover +
calcRelatedPartyIntensity + calcLegalEventRisk 본체.
"""

from __future__ import annotations

from dartlab.core.financeDocAccessor import getFinanceDocAccessor
from dartlab.core.memory import memoizedCalc
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.core.utils.helpers import MAX_RATIO_YEARS, annualColsFromPeriods, toDictBySnakeId

CEO_TURNOVER_WINDOW_YEARS = 5
RELATED_PARTY_PARSER_UNIT = 1_000_000
LEGAL_EVENT_WINDOW_YEARS = 3


def _safePivotExecutivePay(*args, **kwargs):
    from dartlab.analysis.financial.governance import _safePivotExecutivePay as _f

    return _f(*args, **kwargs)


def _safePivotMajorHolder(*args, **kwargs):
    from dartlab.analysis.financial.governance import _safePivotMajorHolder as _f

    return _f(*args, **kwargs)


def _safePivotExecutive(*args, **kwargs):
    from dartlab.analysis.financial.governance import _safePivotExecutive as _f

    return _f(*args, **kwargs)


def _safePivotAudit(*args, **kwargs):
    from dartlab.analysis.financial.governance import _safePivotAudit as _f

    return _f(*args, **kwargs)


def _getDartStockCode(*args, **kwargs):
    from dartlab.analysis.financial.governance import _getDartStockCode as _f

    return _f(*args, **kwargs)


def _loadSanction(*args, **kwargs):
    from dartlab.analysis.financial.governance import _loadSanction as _f

    return _f(*args, **kwargs)


def _loadContingentLiability(*args, **kwargs):
    from dartlab.analysis.financial.governance import _loadContingentLiability as _f

    return _f(*args, **kwargs)


def _fetchLatestEquity(*args, **kwargs):
    from dartlab.analysis.financial.governance import _fetchLatestEquity as _f

    return _f(*args, **kwargs)


def _loadExecutiveDocs(*args, **kwargs):
    from dartlab.analysis.financial.governance import _loadExecutiveDocs as _f

    return _f(*args, **kwargs)


def _loadRelatedPartyTx(*args, **kwargs):
    from dartlab.analysis.financial.governance import _loadRelatedPartyTx as _f

    return _f(*args, **kwargs)


def calcOwnershipTrend(*args, **kwargs):
    """최대주주 지분 시계열 — governance.py 본체로 위임 (cycle 회피용 lazy proxy)."""
    from dartlab.analysis.financial.governance import calcOwnershipTrend as _f

    return _f(*args, **kwargs)


def calcBoardComposition(*args, **kwargs):
    """이사회 구성 분석 — governance.py 본체로 위임 (cycle 회피용 lazy proxy)."""
    from dartlab.analysis.financial.governance import calcBoardComposition as _f

    return _f(*args, **kwargs)


def calcAuditOpinionTrend(*args, **kwargs):
    """감사 의견 시계열 — governance.py 본체로 위임 (cycle 회피용 lazy proxy)."""
    from dartlab.analysis.financial.governance import calcAuditOpinionTrend as _f

    return _f(*args, **kwargs)


def calcExecutivePayDivergence(*args, **kwargs):
    """임원 보수 괴리 — governance.py 본체로 위임 (cycle 회피용 lazy proxy)."""
    from dartlab.analysis.financial.governance import calcExecutivePayDivergence as _f

    return _f(*args, **kwargs)


def calcIndependentDirectorQuality(*args, **kwargs):
    """사외이사 품질 — governance.py 본체로 위임 (cycle 회피용 lazy proxy)."""
    from dartlab.analysis.financial.governance import calcIndependentDirectorQuality as _f

    return _f(*args, **kwargs)


@memoizedCalc
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

    # 대표이사 교체 — 데이터 없으면 플래그 없음 (None safe check, 가짜 0 회피)
    ceo = calcCEOTurnover(company)
    if ceo:
        cnt = ceo.get("turnoverCount")
        n = ceo.get("windowYears", CEO_TURNOVER_WINDOW_YEARS)
        if cnt is not None and cnt >= 2:
            flags.append((f"최근 {n}년 대표이사 교체 {cnt}회 -- 경영진 불안정", "warning"))
        avgT = ceo.get("avgTenureYears")
        if avgT is not None and avgT < 3:
            flags.append((f"대표이사 평균 재임 {avgT:.1f}년 -- 단기 재임 구간 (crash risk)", "warning"))

    # 오너 집중도 (본인/특수관계 분리) — None 보고 누락 vs 0 진짜 무지분 구분
    owner = calcOwnerConcentration(company)
    if owner and owner.get("latest"):
        lt = owner["latest"]
        top1 = lt.get("top1Share")
        totalR = lt.get("topHolderRatio")
        # 소유-지배 괴리 패턴: 본인 지분 적은데 특수관계 포함 총합이 큰 경우
        if top1 is not None and totalR is not None and top1 < 10 and totalR >= 40:
            flags.append(
                (
                    f"본인 지분 {top1:.1f}% vs 특수관계 포함 {totalR:.1f}% -- 소유-지배 괴리 큼",
                    "warning",
                )
            )
        # 과소 지배 — 20% 미만 + 특수관계도 낮음
        if totalR is not None and 0 < totalR < 20:
            flags.append((f"본인+특수관계 {totalR:.1f}% -- 경영권 방어 취약", "warning"))
        # 본인 지분 5년 급격 희석
        ch = owner.get("top1Change5y")
        if ch is not None and ch <= -5:
            flags.append((f"본인 지분 5년간 {ch:+.1f}%p 희석 -- 승계/상속 이벤트 가능", "warning"))

    # 법적 이벤트 리스크 (제재·소송·채무보증) — None 보고 누락 vs 0 무이벤트 구분
    legal = calcLegalEventRisk(company)
    if legal:
        n = legal.get("windowYears", LEGAL_EVENT_WINDOW_YEARS)
        sanctionCount = legal.get("sanctionCount")
        if sanctionCount is not None and sanctionCount >= 1:
            amt = legal.get("sanctionAmount")
            # 1억 이상만 금액 표시 — 파서 단위 혼재로 1억 미만은 불확실
            amtText = f" (누적 {amt / 1e8:.1f}억원)" if amt is not None and amt >= 1_0000_0000 else ""
            flags.append((f"최근 {n}년 제재 {sanctionCount}건{amtText} -- 규제 리스크", "warning"))
        lawsuitCount = legal.get("lawsuitCount")
        lawsuitAmount = legal.get("lawsuitAmount")
        if (lawsuitCount is not None and lawsuitCount >= 1) or (
            lawsuitAmount is not None and lawsuitAmount >= 100_0000_0000
        ):
            amtText = (
                f" (청구금액 {lawsuitAmount / 1e8:.0f}억원)"
                if lawsuitAmount is not None and lawsuitAmount >= 1_0000_0000
                else ""
            )
            flags.append(
                (
                    f"최근 {n}년 소송 {lawsuitCount if lawsuitCount is not None else 0}건{amtText} -- 법적 분쟁 진행",
                    "warning",
                )
            )
        gRatio = legal.get("guaranteeToEquity")
        if gRatio is not None and gRatio >= 50:
            flags.append((f"채무보증/자기자본 {gRatio:.0f}% -- 우발채무 부담 큼", "warning"))

    # 특수관계자 거래 집중도
    rpt = calcRelatedPartyIntensity(company)
    if rpt and rpt.get("latest"):
        lt = rpt["latest"]
        rev = lt.get("relatedRevenueRatio")
        if rev is not None and rev >= 30:
            trend = rpt.get("trend", "unknown")
            trendText = {"increasing": ", 증가 추세", "decreasing": ", 감소 추세", "stable": ""}.get(trend, "")
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


@memoizedCalc
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


@memoizedCalc
def calcCEOTurnover(company, *, basePeriod: str | None = None) -> dict | None:
    """대표이사 교체 — 최근 5년 교체 건수·평균 재임·현 CEO.

    사업보고서 「임원의 현황」 섹션 개인별 테이블에서 "대표이사" 담당업무
    문자열로 CEO 식별, 연도별 CEO 이름 집합 변동을 교체 이벤트로 카운트한다.
    MSCI Board refreshment 와 SSRN CEO tenure inverted-U 이론(취임 3년 이내
    고위험) 에 대응하는 축.

    Parameters
    ----------
    company : Company
        분석 대상 기업 (DART).
    basePeriod : str, optional
        기준 기간. 현재 구현에서는 참고만 — 최근 5년 시계열 반환.

    Returns
    -------
    dict | None
        None : executive docs 파서 데이터 없음 또는 DART 외 provider.
        windowYears : int — 집계 윈도우 (년). 상수 5.
        turnoverCount : int — 윈도우 내 CEO 교체 건수 (건). 전기에 없던
            새 CEO가 등장하거나 전기 CEO가 사라지면 1로 카운트한다.
        currentCeos : list[str] — 최근 연도 대표이사 이름.
        lastChangeYear : int | None — 마지막 교체가 감지된 연도.
        avgTenureYears : float | None — 시계열에서 관찰된 평균 재임 (년).
            한 CEO의 첫·마지막 출현 연도 차이 + 1 의 평균.
        history : list[dict] — 연도별 스냅샷
            year : int — 연도
            ceos : list[str] — 해당 연도 대표이사 이름
            added : list[str] — 전기 대비 새로 등장
            removed : list[str] — 전기 대비 빠진 이름

    Raises
    ------
    없음 — 데이터 없음은 None 반환.

    Examples
    --------
    >>> c = dartlab.Company("005930")
    >>> c.analysis("지배구조")["ceoTurnover"]

    Notes
    -----
    - CEO 식별은 임원 표의 "대표이사" / "CEO" 문자열 매칭 기반. 표기가 다른
      케이스(예: "각자 대표집행임원")는 파서 키워드에 포함되지 않으면 놓칠 수 있다.
    - 첫 연도는 비교 기준이 없어 교체 판정에서 제외된다.
    - 공동대표 체제에서는 동일 연도에 여러 이름이 등장하므로 `currentCeos`
      도 리스트로 반환한다.

    Guide
    -----
    `turnoverCount >= 2` 이면 5년간 경영진 불안정 신호. `avgTenureYears < 3`
    은 SSRN 연구의 bad-news hoarding 구간으로 crash risk 상승 경고.

    See Also
    --------
    calcGovernanceFlags : 교체 빈도를 warning 플래그로 소비.
    calcBoardComposition : 이사회 구성 (최신 스냅샷).
    """
    import polars as pl

    result = _loadExecutiveDocs(company)
    if result is None or result.individualDf is None or result.individualDf.is_empty():
        return None

    df = result.individualDf.filter(pl.col("isCeo"))
    if df.is_empty():
        return None

    years = sorted(df["year"].unique().to_list())
    recent = years[-CEO_TURNOVER_WINDOW_YEARS:]
    if not recent:
        return None

    ceosByYear: dict[int, set[str]] = {}
    for y in recent:
        names = [n for n in df.filter(pl.col("year") == y)["name"].to_list() if n]
        ceosByYear[int(y)] = set(names)

    history: list[dict] = []
    turnoverCount = 0
    lastChangeYear: int | None = None
    prev: set[str] | None = None
    for y in sorted(ceosByYear.keys()):
        current = ceosByYear[y]
        added: list[str] = []
        removed: list[str] = []
        if prev is not None:
            added = sorted(current - prev)
            removed = sorted(prev - current)
            if added or removed:
                turnoverCount += 1
                lastChangeYear = y
        history.append({"year": y, "ceos": sorted(current), "added": added, "removed": removed})
        prev = current

    # 평균 재임 — 윈도우 내 CEO별 (first, last) 연도 차이
    tenures: list[int] = []
    for ceo in {c for s in ceosByYear.values() for c in s}:
        presentYears = [y for y, s in ceosByYear.items() if ceo in s]
        if presentYears:
            tenures.append(max(presentYears) - min(presentYears) + 1)
    avgTenure = round(sum(tenures) / len(tenures), 1) if tenures else None

    latestYear = sorted(ceosByYear.keys())[-1]
    currentCeos = sorted(ceosByYear[latestYear])

    return {
        "windowYears": CEO_TURNOVER_WINDOW_YEARS,
        "turnoverCount": turnoverCount,
        "currentCeos": currentCeos,
        "lastChangeYear": lastChangeYear,
        "avgTenureYears": avgTenure,
        "history": history,
    }


@memoizedCalc
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


@memoizedCalc
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
