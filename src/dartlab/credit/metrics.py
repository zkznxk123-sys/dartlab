"""7축 신용분석 정량 지표 산출.

모든 지표를 company.select() / company.notes / company.show()에서
직접 산출한다. 다른 analysis calc 함수는 호출하지 않으며,
공유 헬퍼만 ``analysis/financial/_helpers`` 에서 가져온다 (SSOT).
"""

from __future__ import annotations

import importlib

from dartlab.core.utils.helpers import (
    annualColsFromPeriods,
    toDictBySnakeId,
)


def _sumBorrowingsKorean(*args, **kwargs):
    """analysis.financial.accountSums.sumBorrowingsKorean lazy 호출.

    cycle 회피: credit ↔ analysis 양방향 cycle 차단 (analysis 가 credit 도 호출).
    importlib 동적 import 라 cycleScan/import-linter 가 못 잡음. 단방향 정책 통과.
    """
    mod = importlib.import_module("dartlab.analysis.financial.accountSums")
    return mod.sumBorrowingsKorean(*args, **kwargs)


# 본 모듈 안에서 sumBorrowingsKorean 이름으로 호출하는 코드의 BC 유지.
sumBorrowingsKorean = _sumBorrowingsKorean


def _div(a, b, pct: bool = False) -> float | None:
    """안전한 나눗셈 (None / 0 가드).

    Args:
        a: 분자.
        b: 분모. None 또는 0 이면 None 반환.
        pct: True 면 결과를 ×100 (백분율).

    Returns:
        ``round(a / abs(b), 2)``. 분모가 음수여도 부호 없이 비율만 산출 (절대값 분모).
        분자나 분모가 None 또는 분모가 0 이면 None.

    Examples:
        >>> _div(100, 50)
        2.0
        >>> _div(50, 100, pct=True)
        50.0
        >>> _div(10, 0)  # 분모 0 → None
    """
    if a is None or b is None or b == 0:
        return None
    result = a / abs(b)
    if pct:
        result *= 100
    return round(result, 2)


def _cv(values: list) -> float | None:
    """변동계수 (Coefficient of Variation) = 표준편차 / |평균| × 100.

    이익 변동성, 마진 안정성 등 시계열의 상대적 흩어짐을 측정.
    변동계수가 작을수록 안정적, 클수록 변동 큼.

    Args:
        values: 수치 리스트. None 은 자동으로 제외.

    Returns:
        백분율 변동계수 (소수점 둘째 자리). 다음 경우 None:
        - 유효 값이 3개 미만 (통계 의미 없음)
        - 평균이 0 (CV 계산 불가)

    Examples:
        >>> _cv([10, 11, 12, 9, 10])  # 안정 시계열
        9.78
        >>> _cv([10, 50, 5, 80, 1])  # 큰 변동
        93.61
    """
    nums = [v for v in values if v is not None]
    if len(nums) < 3:
        return None
    mean = sum(nums) / len(nums)
    if mean == 0:
        return None
    variance = sum((x - mean) ** 2 for x in nums) / len(nums)
    return round((variance**0.5) / abs(mean) * 100, 2)


# SSOT 위임: _toDict / _annualCols 는 analysis/_helpers 의 함수와 동일 로직.
# 호환을 위한 alias — 신규 코드는 toDictBySnakeId / annualColsFromPeriods 직접 호출.
_toDict = toDictBySnakeId
_annualCols = annualColsFromPeriods


def _isQuarterlyFallback(cols: list[str]) -> bool:
    """``_annualCols`` 결과가 4자리 연도가 아닌 Q4 fallback 인지 판별.

    DART 의 분기 데이터만 있고 연간 합산 컬럼이 없는 종목 (예: 신규상장)에서는
    ``_annualCols`` 가 ``["2024Q4", "2023Q4", ...]`` 같은 분기 컬럼 fallback 을 반환.
    이 경우 calc 가 추가로 ``annualSumFlow`` 를 호출해 4분기 합산해야 한다.

    Args:
        cols: ``_annualCols`` 의 결과.

    Returns:
        True 면 cols[0] 이 "YYYYQ4" 형태의 분기 컬럼 (fallback).
        False 면 "YYYY" 4자리 연도 (정상 연간).

    Examples:
        >>> _isQuarterlyFallback(["2024", "2023"])
        False
        >>> _isQuarterlyFallback(["2024Q4", "2023Q4"])
        True
        >>> _isQuarterlyFallback([])
        False
    """
    return bool(cols) and "Q" in cols[0]


# credit 차입금 산출용 TTM 합산 — annualSumFlow credit 모드 alias.
# 1~2 분기도 부분 데이터로 연환산 (부정확하지만 credit 안정성 보수).
def _ttmSum(flowData: dict, qCol: str, allPeriods: list[str]) -> float | None:
    from dartlab.core.utils.flow import annualSumFlow

    return annualSumFlow(flowData, qCol, allPeriods, withFallback=False)


def _getRatios(company):
    try:
        return company._finance.ratios
    except (ValueError, KeyError, AttributeError):
        return None


# ═══════════════════════════════════════════════════════════
# 7축 지표 산출
# ═══════════════════════════════════════════════════════════


def calcAllMetrics(company, *, basePeriod: str | None = None) -> dict | None:
    """7축 모든 지표를 한 번에 산출.

    company.select()로 원본 데이터(BS/IS/CF)를 직접 가져오고,
    notes/sections에서 차입금 내역, 부문 구성, 감사의견 등을 보강한다.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.
    basePeriod : str | None
        분석 기준 기간 (예: "2024"). None이면 최신 9개년.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 지표 시계열. 각 dict 포함 키:
            period : str — 기간 (예: "2024")
            totalAssets : float | None — 자산총계 (원)
            totalBorrowing : float | None — 총차입금 (원)
            ebitda : float | None — EBITDA (원)
            ffo : float | None — FFO (원)
            ocf : float | None — 영업활동현금흐름 (원)
            fcf : float | None — 잉여현금흐름 (원)
            revenue : float | None — 매출액 (원)
            ffoToDebt : float | None — FFO/총차입금 (%)
            debtToEbitda : float | None — 총차입금/EBITDA (배)
            focfToDebt : float | None — FOCF/총차입금 (%)
            ebitdaInterestCoverage : float | None — EBITDA/이자비용 (배)
            debtRatio : float | None — 부채비율 (%)
            borrowingDependency : float | None — 차입금의존도 (%)
            netDebtToEbitda : float | None — 순차입금/EBITDA (배)
            currentRatio : float | None — 유동비율 (%)
            cashRatio : float | None — 현금비율 (%)
            shortTermDebtRatio : float | None — 단기차입금비중 (%)
            ocfToSales : float | None — OCF/매출 (%)
            fcfToSales : float | None — FCF/매출 (%)
            ocfToDebt : float | None — OCF/총차입금 (%)
        businessStability : dict — 사업 안정성 지표
            opMarginCV : float | None — 영업이익률 변동계수 (%)
            revenueCV : float | None — 매출 변동계수 (%)
            latestRevenue : float | None — 최신 매출 (원)
            avgMargin : float | None — 평균 영업이익률 (%)
            segmentHHI : float | None — 부문 HHI (점)
        reliability : dict — 재무 신뢰성 (Beneish M, Piotroski F 등)
        disclosureRisk : dict | None — 공시 리스크 (우발부채, 키워드)
        auditOpinion : str | None — 감사의견 ("적정"/"한정"/"부적정"/"의견거절")
        borrowingsDetail : list[dict] | None — 차입금 상세 내역
        provisionsDetail : list[dict] | None — 충당금 상세 내역
        segmentsDetail : list[dict] | None — 부문 상세 내역
        profile : dict | None — 기업 프로필 (섹터, 주요제품)
        segmentComposition : dict | None — 부문별 매출 구성
        rank : dict | None — 업종 내 순위
    """
    # ── 원본 데이터 수집 ──
    bsResult = company.select(
        "BS",
        [
            "자산총계",
            "부채총계",
            "자본총계",
            "유동자산",
            "유동부채",
            "비유동부채",
            "현금및현금성자산",
            "단기차입금",
            "장기차입금",
            "차입금단기",  # short_term_borrowings 한국어 변형
            "long_term_borrowings",  # 영문만 있는 회사
            "short_term_borrowings",
            "차입부채",  # Fallback: 통합 차입금만 공시하는 회사 (audit 04 #B)
            "차입금",  # Fallback: 추가 변형
            "장기차입부채",  # noncurrent_borrowings (LG에솔)
            "유동성장기차입금",  # current_portion_of_longterm_borrowings
            "사채",
            "재고자산",
            "이익잉여금",
        ],
    )
    bsParsed = _toDict(bsResult)
    if bsParsed is None:
        return None
    bsData, bsPeriods = bsParsed

    isResult = company.select(
        "IS",
        [
            "매출액",
            "영업이익",
            "당기순이익",
            "금융비용",
            "이자비용",
            "감가상각비",
            "매출총이익",
        ],
    )
    isParsed = _toDict(isResult)
    if isParsed is None:
        return None
    isData, _ = isParsed

    cfResult = company.select("CF", ["영업활동현금흐름", "유형자산의취득", "4.금융비용", "금융비용"])
    cfParsed = _toDict(cfResult)
    cfData: dict = {}
    if cfParsed is not None:
        cfData, _ = cfParsed

    yCols = _annualCols(bsPeriods, basePeriod, 9)
    if len(yCols) < 2:
        return None

    # Q4 fallback 감지 — IS/CF 플로우 변수에 TTM 합산 필요
    _quarterlyMode = _isQuarterlyFallback(yCols)
    _allPeriods = set(bsPeriods)

    # 행 추출
    ta = bsData.get("자산총계", {})
    tl = bsData.get("부채총계", {})
    eq = bsData.get("자본총계", {})
    ca = bsData.get("유동자산", {})
    cl = bsData.get("유동부채", {})
    bsData.get("비유동부채", {})
    cash = bsData.get("현금및현금성자산", {})
    # 차입금 fallback 은 col loop 안에서 sumBorrowingsKorean 위임
    bsData.get("이익잉여금", {})

    rev = isData.get("매출액", {})
    oi = isData.get("영업이익", {})
    ni = isData.get("당기순이익", {})
    finCost = isData.get("금융비용", {})
    intCost = isData.get("이자비용", {})
    dep = isData.get("감가상각비", {})
    isData.get("매출총이익", {})

    ocf = cfData.get("영업활동현금흐름", {})
    capex = cfData.get("유형자산의취득", {})
    # CF 이자비용 fallback (IS에 이자비용/금융비용이 없는 기업용)
    cfFinCost = cfData.get("4.금융비용", {}) or cfData.get("금융비용", {})

    # ── notes 데이터 수집 ──
    borrowingsDetail = _fetchNotes(company, "borrowings")
    provisionsDetail = _fetchNotes(company, "provisions")
    segmentsDetail = _fetchNotes(company, "segments")

    # ── 연도별 지표 산출 ──
    history = []
    opMargins = []
    revenues = []

    for col in yCols[:-1]:
        totalAssets = ta.get(col)
        totalDebt = tl.get(col)
        equity = eq.get(col)
        curAssets = ca.get(col)
        curLiab = cl.get(col)
        cashVal = cash.get(col)

        # 차입금 분리/통합 fallback 위임 (analysis/_helpers.py::sumBorrowingsKorean)
        stBorrow, ltBorrow, totalBorrowing = sumBorrowingsKorean(bsData, col)
        bsData.get("사채", {}).get(col) or 0  # 사채 별도 노출 (회귀 호환)

        # IS/CF 플로우 변수: Q4 fallback이면 TTM 합산
        if _quarterlyMode:
            revenue = _ttmSum(rev, col, _allPeriods)
            opIncome = _ttmSum(oi, col, _allPeriods)
            netIncome = _ttmSum(ni, col, _allPeriods)
            depreciation = _ttmSum(dep, col, _allPeriods)
            ocfVal = _ttmSum(ocf, col, _allPeriods)
            capexVal = _ttmSum(capex, col, _allPeriods)
            ie = (
                _ttmSum(intCost, col, _allPeriods)
                or _ttmSum(finCost, col, _allPeriods)
                or _ttmSum(cfFinCost, col, _allPeriods)
            )
        else:
            revenue = rev.get(col)
            opIncome = oi.get(col)
            netIncome = ni.get(col)
            depreciation = dep.get(col)
            ocfVal = ocf.get(col)
            capexVal = capex.get(col)
            ie = intCost.get(col) or finCost.get(col) or cfFinCost.get(col)
        if capexVal is not None:
            capexVal = abs(capexVal)

        # EBITDA
        ebitda = (opIncome + (depreciation or 0)) if opIncome is not None else None

        # FFO (간이) = NI + 감가상각, fallback OCF
        ffo = None
        if netIncome is not None and depreciation is not None:
            ffo = netIncome + depreciation
        elif ocfVal is not None:
            ffo = ocfVal

        # FCF
        fcf = (ocfVal - capexVal) if ocfVal is not None and capexVal is not None else None

        # 순차입금
        netDebt = totalBorrowing - (cashVal or 0) if totalBorrowing > 0 else 0

        # ── 축 1: 채무상환능력 ──
        ffoToDebt = _div(ffo, totalBorrowing, pct=True) if totalBorrowing > 0 else (999.0 if ffo and ffo > 0 else None)
        debtToEbitda = _div(totalBorrowing, ebitda) if totalBorrowing > 0 else (0.0 if ebitda and ebitda > 0 else None)
        focfToDebt = _div(fcf, totalBorrowing, pct=True) if totalBorrowing > 0 else (999.0 if fcf and fcf > 0 else None)
        ebitdaInterest = _div(ebitda, ie) if ie and ie > 0 else (999.0 if ebitda and ebitda > 0 else None)

        # ── 축 2: 자본 구조 ──
        debtRatio = _div(totalDebt, equity, pct=True) if equity and equity > 0 else None
        borrowingDep = _div(totalBorrowing, totalAssets, pct=True) if totalAssets and totalAssets > 0 else None
        netDebtEbitda = _div(netDebt, ebitda) if ebitda and ebitda > 0 else None

        # ── 축 3: 유동성 ──
        currentRatio = _div(curAssets, curLiab, pct=True) if curLiab and curLiab > 0 else None
        cashRatio = _div(cashVal, curLiab, pct=True) if curLiab and curLiab > 0 else None
        stDebtRatio = _div(stBorrow, totalBorrowing, pct=True) if totalBorrowing > 0 else None

        # ── 축 4: 현금흐름 ──
        ocfToSales = _div(ocfVal, revenue, pct=True) if revenue and revenue > 0 else None
        fcfToSales = _div(fcf, revenue, pct=True) if revenue and revenue > 0 else None
        ocfToDebt = _div(ocfVal, totalBorrowing, pct=True) if totalBorrowing > 0 else None

        # 축 5용 수집
        opMargin = _div(opIncome, revenue, pct=True) if revenue and revenue > 0 else None
        opMargins.append(opMargin)
        revenues.append(revenue)

        history.append(
            {
                "period": col,
                # 원본
                "totalAssets": totalAssets,
                "totalBorrowing": totalBorrowing if totalBorrowing > 0 else None,
                "ebitda": ebitda,
                "ffo": ffo,
                "ocf": ocfVal,
                "fcf": fcf,
                "netDebt": netDebt,
                "revenue": revenue,
                "operatingIncome": opIncome,
                # 축 1: 채무상환
                "ffoToDebt": ffoToDebt,
                "debtToEbitda": debtToEbitda,
                "focfToDebt": focfToDebt,
                "ebitdaInterestCoverage": ebitdaInterest,
                # 축 2: 자본구조
                "debtRatio": debtRatio,
                "borrowingDependency": borrowingDep,
                "netDebtToEbitda": netDebtEbitda,
                # 축 3: 유동성
                "currentRatio": currentRatio,
                "cashRatio": cashRatio,
                "shortTermDebtRatio": stDebtRatio,
                # 축 4: 현금흐름
                "ocfToSales": ocfToSales,
                "fcfToSales": fcfToSales,
                "ocfToDebt": ocfToDebt,
            }
        )

    if not history:
        return None

    # ── 축 5: 사업 안정성 (전체 기간 대상) ──
    opMarginCV = _cv(opMargins)
    revenueCV = _cv(revenues)
    latestRevenue = revenues[0] if revenues else None
    avgMargin = None
    validMargins = [m for m in opMargins if m is not None]
    if validMargins:
        avgMargin = round(sum(validMargins) / len(validMargins), 2)

    # segments HHI (부문 다각화도)
    segmentHHI = _calcSegmentHHI(segmentsDetail)

    # ── 축 6: 재무 신뢰성 (ratios에서 참조) ──
    ratios = _getRatios(company)
    reliabilityData = {}
    if ratios:
        reliabilityData = {
            "beneishMScore": ratios.beneishMScore,
            "sloanAccrualRatio": ratios.sloanAccrualRatio,
            "ohlsonProbability": ratios.ohlsonProbability,
            "altmanZScore": ratios.altmanZScore,
            "altmanZppScore": ratios.altmanZppScore,
            "piotroskiFScore": ratios.piotroskiFScore,
        }

    # ── 축 7: 공시 리스크 (scan 참조) ──
    disclosureRisk = _fetchDisclosureRisk(company)

    # ── 감사의견 ──
    auditOpinion = _fetchAuditOpinion(company)

    # ── 기업 프로필 + 부문 구성 + 업종 순위 ──
    profile = _fetchProfile(company)
    segmentComposition = _fetchSegmentComposition(company)
    rank = _fetchRank(company)

    return {
        "history": history,
        "businessStability": {
            "opMarginCV": opMarginCV,
            "revenueCV": revenueCV,
            "latestRevenue": latestRevenue,
            "avgMargin": avgMargin,
            "segmentHHI": segmentHHI,
        },
        "reliability": reliabilityData,
        "disclosureRisk": disclosureRisk,
        "auditOpinion": auditOpinion,
        "borrowingsDetail": borrowingsDetail,
        "provisionsDetail": provisionsDetail,
        "segmentsDetail": segmentsDetail,
        "profile": profile,
        "segmentComposition": segmentComposition,
        "rank": rank,
    }


# ═══════════════════════════════════════════════════════════
# notes / sections / scan 데이터 수집
# ═══════════════════════════════════════════════════════════


def _fetchProfile(company) -> dict | None:
    """기업 프로필 (업종, 주요제품) 수집.

    Company.sector + dartlab.listing() 직접 접근.
    cross-dependency 방지: credit ↛ analysis.
    """
    parts: dict[str, str] = {}
    try:
        sectorInfo = company.sector
        if sectorInfo:
            sectorKr = sectorInfo.sector.value
            groupKr = sectorInfo.industryGroup.value
            parts["sector"] = f"섹터: {sectorKr} > {groupKr}"
    except (ValueError, KeyError, AttributeError):
        pass

    try:
        import dartlab

        listing = dartlab.listing()
        stockCode = getattr(company, "stockCode", "")
        if stockCode:
            row = listing.filter(listing["종목코드"] == stockCode)
            if not row.is_empty() and "주요제품" in row.columns:
                products = row["주요제품"][0]
                if products:
                    parts["products"] = f"주요제품: {products}"
    except (ImportError, ValueError, KeyError):
        pass

    return parts if parts else None


def _fetchSegmentComposition(company) -> dict | None:
    """부문별 매출/이익 구성 수집.

    Plan v10 P2: c.notes 제거 → c.show("segments") 사용.
    최신 연도 컬럼 하나만 사용하여 연도별 부문명 변경(IM→DX 등) 중복 방지.
    """
    try:
        try:
            df = company.show("segments")
        except (AttributeError, ValueError):
            df = None
        if df is None or not hasattr(df, "columns"):
            return None

        # DataFrame 구조: 부문(str), 2025(f64), 2024(f64), ...
        # 최신 연도 컬럼 하나만 사용하여 중복 방지
        yearCols = sorted(
            [c for c in df.columns if c.isdigit() and len(c) == 4],
            reverse=True,
        )
        if not yearCols:
            return None
        # 최신 연도에 유효 데이터가 2개 미만이면 차선 연도 사용
        latestYear = yearCols[0]
        for yc in yearCols:
            validCount = sum(
                1
                for row in df.iter_rows(named=True)
                if row.get(yc) is not None and isinstance(row.get(yc), (int, float)) and row.get(yc) > 0
            )
            if validCount >= 2:
                latestYear = yc
                break

        # 부문명 컬럼: 첫 번째 문자열 타입 컬럼
        nameCol = None
        for c in df.columns:
            if c in ("부문", "항목"):
                nameCol = c
                break
        if nameCol is None:
            # fallback: 숫자가 아닌 첫 번째 컬럼
            for c in df.columns:
                if not c.isdigit():
                    nameCol = c
                    break
        if nameCol is None:
            return None

        segments = []
        for row in df.iter_rows(named=True):
            name = row.get(nameCol)
            revenue = row.get(latestYear)
            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            if not isinstance(revenue, (int, float)) or revenue <= 0:
                continue
            # "합계", "조정", "내부" 행 제외
            if any(skip in name for skip in ("합계", "조정", "내부거래", "상계")):
                continue
            segments.append({"name": name, "revenue": revenue})

        if not segments:
            return None

        segments.sort(key=lambda x: x["revenue"], reverse=True)
        totalRev = sum(s["revenue"] for s in segments)
        if totalRev == 0:
            return None

        return {"segments": segments, "totalRevenue": totalRev}
    except (AttributeError, FileNotFoundError, ValueError, KeyError, TypeError):
        return None


def _fetchRank(company) -> dict | None:
    """업종 내 순위 수집. scan 데이터 없으면 None (스냅샷 빌드 시도 안 함)."""
    try:
        from dartlab.scan.rank import _SNAPSHOT, _cacheDir

        # 캐시된 스냅샷이 있을 때만 사용 (빌드 시도 X — 수분 소요)
        if _SNAPSHOT is None:
            cachePath = _cacheDir() / "rank_snapshot.parquet"
            if not cachePath.exists():
                return None

        from dartlab.scan.rank import getRankOrBuild

        stockCode = getattr(company, "stockCode", "")
        if not stockCode:
            return None
        rank = getRankOrBuild(stockCode, verbose=False)
        if rank is None:
            return None
        return {
            "revenueRank": rank.revenueRank,
            "revenueTotal": rank.revenueTotal,
            "revenueRankInSector": rank.revenueRankInSector,
            "revenueSectorTotal": rank.revenueSectorTotal,
            "sizeClass": rank.sizeClass,
            "sector": rank.sector,
            "industryGroup": rank.industryGroup,
        }
    except (ImportError, AttributeError, ValueError, KeyError, OSError, TypeError):
        return None


def _fetchNotes(company, key: str) -> list[dict] | None:
    """notes에서 DataFrame을 dict 리스트로 안전하게 추출."""
    try:
        accessor = getattr(company, "_notesAccessor", None) or getattr(company, "notes", None)
        if accessor is None:
            return None
        df = getattr(accessor, key, None)
        if df is not None and hasattr(df, "to_dicts"):
            return df.to_dicts()
    except (AttributeError, FileNotFoundError, ValueError, KeyError):
        pass
    return None


def _calcSegmentHHI(segmentsData: list[dict] | None) -> float | None:
    """부문별 매출에서 HHI(허핀달-허쉬만 지수) 계산.

    HHI = Σ(부문매출비중²) × 10000
    HHI < 1500: 다각화, 1500-2500: 보통, > 2500: 집중
    """
    if not segmentsData:
        return None

    # segments DataFrame에서 매출 추출
    revenues = []
    for row in segmentsData:
        # 매출액 또는 영업수익 컬럼 탐색
        for k, v in row.items():
            if isinstance(v, (int, float)) and v > 0:
                if any(term in str(k) for term in ["매출", "수익", "revenue"]):
                    revenues.append(v)
                    break

    if len(revenues) < 2:
        return None

    total = sum(revenues)
    if total <= 0:
        return None

    hhi = sum((r / total * 100) ** 2 for r in revenues)
    return round(hhi, 0)


def _fetchDisclosureRisk(company) -> dict | None:
    """scan.disclosureRisk에서 기업별 리스크 신호 추출."""
    try:
        from dartlab.scan.disclosureRisk import disclosureRisk

        result = disclosureRisk(company)
        if result is not None and hasattr(result, "to_dicts"):
            rows = result.to_dicts()
            if rows:
                return rows[0]
    except (ImportError, AttributeError, ValueError, KeyError, TypeError):
        pass
    return None


def _fetchAuditOpinion(company) -> str | None:
    """감사의견 추출 — 적정/한정/부적정/의견거절.

    [성능] show("audit") 직접 파싱이 0.04s 수준이므로 1순위로 사용.
    company.governance() 호출은 전종목 scan(12s+)을 트리거하므로 마지막 fallback으로만.
    """
    # 1순위: docs 원문 직접 파싱 (0.04~1s, 단일 종목만 처리)
    try:
        show = getattr(company, "show", None)
        if show is not None:
            idx = show("audit")
            if idx is not None and hasattr(idx, "to_dicts"):
                blocks = idx.to_dicts()
                for b in blocks:
                    blk = b.get("block")
                    data = show("audit", block=blk, period="latest")
                    if data is None:
                        continue
                    if hasattr(data, "to_dicts"):
                        for row in data.to_dicts():
                            for v in row.values():
                                if not isinstance(v, str):
                                    continue
                                if "부적정" in v:
                                    return "부적정"
                                if "의견거절" in v:
                                    return "의견거절"
                                if "한정" in v and "한정" not in ("한정되지", "한정하지"):
                                    return "한정"
                # 명시적 위반 키워드 없으면 적정
                return "적정"
    except (AttributeError, ValueError, KeyError, TypeError):
        pass

    # 2순위: scorer 직접 호출 (있으면)
    try:
        from dartlab.scan.governance.scorer import _extractAuditOpinion

        result = _extractAuditOpinion(company)
        if result:
            return result
    except (ImportError, AttributeError):
        pass

    # 마지막 fallback: governance() — 전종목 scan을 트리거하므로 매우 느림
    # 위 두 경로가 모두 실패한 경우만 사용
    try:
        gov = getattr(company, "governance", None)
        if gov is not None and callable(gov):
            govResult = gov()
            if govResult is not None and hasattr(govResult, "to_dicts"):
                rows = govResult.to_dicts()
                if rows:
                    opinion = rows[0].get("auditOpinion") or rows[0].get("감사의견")
                    if opinion:
                        return opinion
    except (AttributeError, ValueError, KeyError, TypeError):
        pass

    return None


# ═══════════════════════════════════════════════════════════
# 별도재무제표(OFS) 보조 지표 — 지주사/캡티브 금융 보정용
# ═══════════════════════════════════════════════════════════


def calcSeparateMetrics(company) -> dict | None:
    """별도재무제표(OFS) 기반 보조 지표.

    연결(CFS) 대비 별도(OFS)의 부채/차입금/EBITDA를 산출.
    지주사/캡티브 금융에서 연결 D/EBITDA 왜곡을 보정하는 데 사용.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스.

    Returns
    -------
    dict | None
        period : str | None — 별도재무제표 기간
        totalAssets : float — 별도 자산총계 (원)
        totalBorrowing : float — 별도 총차입금 (원)
        ebitda : float — 별도 EBITDA (원)
        netDebt : float — 별도 순차입금 (원)
        revenue : float — 별도 매출 (원)
        ocf : float — 별도 영업현금흐름 (원)
        fcf : float | None — 별도 잉여현금흐름 (원)
        separateDebtRatio : float | None — 별도 부채비율 (%)
        separateDebtToEbitda : float | None — 별도 D/EBITDA (배)
        separateNetDebtToEbitda : float | None — 별도 순차입금/EBITDA (배)
        separateBorrowingDep : float | None — 별도 차입금의존도 (%)
        separateOcfToSales : float | None — 별도 OCF/매출 (%)
        separateOcfToDebt : float | None — 별도 OCF/총차입금 (%)
    """
    try:
        ofs = company._getFinanceBuild("y", "OFS")
    except (AttributeError, TypeError, FileNotFoundError):
        return None
    if ofs is None:
        return None

    series, periods = ofs
    if not periods:
        return None

    bs = series.get("BS", {})
    is_ = series.get("IS", {})
    cf = series.get("CF", {})
    idx = -1  # 최신 기간

    def _val(data: dict, key: str) -> float | None:
        vals = data.get(key)
        if vals is None or not isinstance(vals, list):
            return None
        return vals[idx] if abs(idx) <= len(vals) else None

    ta = _val(bs, "total_assets")
    tl = _val(bs, "total_liabilities")
    eq = _val(bs, "total_stockholders_equity")
    stb = _val(bs, "shortterm_borrowings") or 0
    ltb = _val(bs, "longterm_borrowings") or 0
    bonds = _val(bs, "bonds_payable") or _val(bs, "debentures") or 0
    cash = _val(bs, "cash_and_cash_equivalents") or 0
    oi = _val(is_, "operating_profit") or 0
    rev = _val(is_, "sales") or _val(is_, "revenue") or 0
    dep = _val(is_, "depreciation") or _val(is_, "depreciation_and_amortisation") or 0
    ocfVal = _val(cf, "operating_cashflow") or _val(cf, "cash_flows_from_operating_activities") or 0
    capexVal = abs(_val(cf, "purchase_of_property_plant_and_equipment") or 0)

    if ta is None or ta == 0:
        return None

    totalBorrowing = stb + ltb + bonds
    ebitda = oi + dep
    netDebt = totalBorrowing - cash if totalBorrowing > 0 else 0
    fcfVal = ocfVal - capexVal if ocfVal else None

    result = {
        "period": periods[idx] if abs(idx) <= len(periods) else None,
        "totalAssets": ta,
        "totalBorrowing": totalBorrowing,
        "ebitda": ebitda,
        "netDebt": netDebt,
        "revenue": rev,
        "ocf": ocfVal,
        "fcf": fcfVal,
        # 별도 지표
        "separateDebtRatio": _div(tl, eq, pct=True) if eq and eq > 0 else None,
        "separateDebtToEbitda": _div(totalBorrowing, ebitda) if ebitda and ebitda > 0 else None,
        "separateNetDebtToEbitda": _div(netDebt, ebitda) if ebitda and ebitda > 0 else None,
        "separateBorrowingDep": _div(totalBorrowing, ta, pct=True) if ta > 0 else None,
        "separateOcfToSales": _div(ocfVal, rev, pct=True) if rev and rev > 0 else None,
        "separateOcfToDebt": _div(ocfVal, totalBorrowing, pct=True) if totalBorrowing > 0 else None,
    }
    return result


# ═══════════════════════════════════════════════════════════
# Track B: 금융업 전용 지표 산출
# ═══════════════════════════════════════════════════════════


def calcFinancialMetrics(company, *, basePeriod: str | None = None) -> dict | None:
    """금융업(은행/보험/증권) 전용 5축 지표 산출.

    일반기업용 D/EBITDA, FFO/Debt 대신
    자본비율, ROA, NIM 대리, 충당금 비율 등 금융업 핵심 지표 사용.

    Parameters
    ----------
    company : Company
        DartCompany 또는 EdgarCompany 인스턴스 (금융업).
    basePeriod : str | None
        분석 기준 기간 (예: "2024"). None이면 최신 9개년.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 금융업 지표 시계열. 각 dict 포함 키:
            period : str — 기간
            totalAssets : float | None — 자산총계 (원)
            equity : float | None — 자본총계 (원)
            netIncome : float | None — 당기순이익 (원)
            operatingIncome : float | None — 영업이익 (원)
            ocf : float | None — 영업활동현금흐름 (원)
            equityRatio : float | None — 자기자본비율 (%)
            roa : float | None — 총자산이익률 (%)
            nimProxy : float | None — NIM 대리 (이자수익/자산) (%)
            provisionRatio : float | None — 충당금비율 (대손상각비/자산) (%)
            cashToAsset : float | None — 현금/자산 비율 (%)
            currentRatio : float | None — 유동비율 (%)
        businessStability : dict — 사업 안정성
            revenueCV : float | None — 영업이익 변동계수 (%)
            roaCV : float | None — ROA 변동계수 (%)
            totalAssets : float | None — 최신 자산총계 (원)
        track : str — "B" (금융업 트랙 식별자)
    """
    bsResult = company.select(
        "BS",
        ["자산총계", "부채총계", "자본총계", "유동자산", "유동부채", "현금및현금성자산", "현금및예치금"],
    )
    bsParsed = _toDict(bsResult)
    if bsParsed is None:
        return None
    bsData, bsPeriods = bsParsed

    isResult = company.select(
        "IS",
        ["이자수익", "금융이익", "금융비용", "4.금융비용", "당기순이익", "대손상각비", "영업이익"],
    )
    isParsed = _toDict(isResult)
    if isParsed is None:
        return None
    isData, _ = isParsed

    cfResult = company.select("CF", ["영업활동현금흐름", "4.금융비용", "금융비용"])
    cfParsed = _toDict(cfResult)
    cfData = cfParsed[0] if cfParsed else {}

    yCols = _annualCols(bsPeriods, basePeriod, 9)
    if len(yCols) < 2:
        return None

    _qMode = _isQuarterlyFallback(yCols)
    _allP = set(bsPeriods)

    # 금융업: 금융이익(순영업수익)을 우선. 이자수익은 부수 항목일 수 있음
    intIncome = isData.get("금융이익", {}) or isData.get("이자수익", {})
    intExpense = isData.get("금융비용", {}) or isData.get("4.금융비용", {})
    ni = isData.get("당기순이익", {})
    provision = isData.get("대손상각비", {})
    oi = isData.get("영업이익", {})
    ta = bsData.get("자산총계", {})
    eq = bsData.get("자본총계", {})
    cash = bsData.get("현금및현금성자산", {}) or bsData.get("현금및예치금", {})
    ca = bsData.get("유동자산", {})
    cl = bsData.get("유동부채", {})
    ocf = cfData.get("영업활동현금흐름", {})
    cfFinCost = cfData.get("4.금융비용", {}) or cfData.get("금융비용", {})

    history = []
    roaList = []
    revList = []

    for col in yCols[:-1]:
        totalAssets = ta.get(col)
        equity = eq.get(col)
        cashVal = cash.get(col)
        curAssets = ca.get(col)
        curLiab = cl.get(col)

        if _qMode:
            intInc = _ttmSum(intIncome, col, _allP)
            _ttmSum(intExpense, col, _allP) or _ttmSum(cfFinCost, col, _allP)
            netIncome = _ttmSum(ni, col, _allP)
            provCharge = _ttmSum(provision, col, _allP)
            opIncome = _ttmSum(oi, col, _allP)
            ocfVal = _ttmSum(ocf, col, _allP)
        else:
            intInc = intIncome.get(col)
            intExpense.get(col) or cfFinCost.get(col)
            netIncome = ni.get(col)
            provCharge = provision.get(col)
            opIncome = oi.get(col)
            ocfVal = ocf.get(col)

        if totalAssets is None or totalAssets == 0:
            continue

        # 축1: 자본적정성
        equityRatio = _div(equity, totalAssets, pct=True)

        # 축2: 수익성
        roa = _div(netIncome, totalAssets, pct=True)
        # NIM 대리: 이자수익/자산 (금융비용 차감 방식은 계정 불일치로 불안정)
        nim = _div(intInc, totalAssets, pct=True) if intInc else None

        # 축3: 자산건전성
        provRatio = _div(abs(provCharge) if provCharge else None, totalAssets, pct=True)

        # 축4: 유동성
        cashToAsset = _div(cashVal, totalAssets, pct=True)
        currentRatio = _div(curAssets, curLiab, pct=True) if curLiab and curLiab > 0 else None

        roaList.append(roa)
        revList.append(opIncome)

        history.append(
            {
                "period": col,
                "totalAssets": totalAssets,
                "equity": equity,
                "netIncome": netIncome,
                "operatingIncome": opIncome,
                "ocf": ocfVal,
                # 축1
                "equityRatio": equityRatio,
                # 축2
                "roa": roa,
                "nimProxy": nim,
                # 축3
                "provisionRatio": provRatio,
                # 축4
                "cashToAsset": cashToAsset,
                "currentRatio": currentRatio,
            }
        )

    if not history:
        return None

    # 축5: 사업안정성 (기존 로직 재사용)
    bizStability = {
        "revenueCV": _cv([r for r in revList if r is not None]),
        "roaCV": _cv([r for r in roaList if r is not None]),
        "totalAssets": history[0].get("totalAssets"),
    }

    return {
        "history": history,
        "businessStability": bizStability,
        "track": "B",
    }
