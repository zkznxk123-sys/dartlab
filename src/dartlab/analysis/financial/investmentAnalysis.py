"""투자 분석 -- ROIC, NOPAT, 투자 강도 시계열.

select()로 IS/BS/CF 원본 계정을 가져와서
투자가 실제로 가치를 만드는지를 금액과 함께 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

from dartlab.analysis.financial.accountSums import sumBorrowings
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import (
    annualColsFromPeriods,
    toDictBySnakeId,
)

_MAX_YEARS = 8


from dartlab.core.utils.calc import safePct as _pct  # noqa: E402


def _yoy(cur, prev) -> float | None:
    """전기대비 증감률 계산.

    Returns
    -------
    float | None
        YoY 변화율 (%). 계산 불가 시 None.
    """
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 2)


def _estimateWacc(company) -> float | None:
    """company에서 WACC 추정 (compute_company_wacc 래퍼).

    [성능] 자체 캐시 (None 결과도 캐싱) — review에서 5개 calc가 각자 호출하는데
    매번 fetch_price + fetchBeta 외부 API 호출 발생 (각 ~2.6s = 13s).
    None 결과도 캐시해야 외부 API 재호출 방지.
    memoized_calc은 None 결과를 캐시 안 함 → 자체 sentinel 캐시 사용.
    """

    def _isOptionalMarketDataError(exc: Exception) -> bool:
        try:
            import httpx

            from dartlab.gather.types import SourceUnavailableError
        except ImportError:
            return False
        return isinstance(exc, (httpx.HTTPError, SourceUnavailableError))

    cache = getattr(company, "_cache", None)
    _KEY = "_estimateWacc_v2"
    _SENTINEL = "__NONE__"
    if cache is not None and _KEY in cache:
        cached = cache[_KEY]
        return None if cached == _SENTINEL else cached

    result: float | None = None
    try:
        from dartlab.analysis.financial.proforma import computeCompanyWacc

        annual = company._buildFinanceSeries(freq="Y")
        if annual is not None:
            series, _ = annual
            sectorParams = getattr(company, "sectorParams", None)
            # 시총: gather.price 경유 (beta 감쇠에 필요)
            marketCap = None
            try:
                from dartlab.gather.infra.http import runAsync
                from dartlab.gather.sources.price import fetch

                stockCode = getattr(company, "stockCode", "")
                snapshot = runAsync(fetch(stockCode, market="KR")) if stockCode else None
                if snapshot:
                    marketCap = snapshot.marketCap
            except (ImportError, OSError, RuntimeError):
                pass
            except Exception as exc:
                if not _isOptionalMarketDataError(exc):
                    raise
            # 개별 beta
            betaCalc = None
            try:
                from dartlab.analysis.financial.proforma import _fetchBeta

                betaCalc = _fetchBeta(getattr(company, "stockCode", ""), getattr(company, "currency", "KRW"))
            except (ImportError, OSError, RuntimeError):
                pass
            except Exception as exc:
                if not _isOptionalMarketDataError(exc):
                    raise
            wacc, _ = computeCompanyWacc(
                series,
                sectorParams=sectorParams,
                marketCap=marketCap,
                currency=getattr(company, "currency", "KRW"),
                betaOverride=betaCalc,
            )
            result = round(wacc, 2)
    except (ImportError, AttributeError, TypeError, ValueError):
        result = None

    if cache is not None:
        cache[_KEY] = result if result is not None else _SENTINEL
    return result


# ── ROIC (NOPAT / 투하자본) ──


@memoizedCalc
def calcRoicTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """ROIC 시계열 -- 투하자본 대비 실제 수익률.

    IS에서 영업이익 + 세율, BS에서 자본 + 차입금으로 직접 계산.
    ROIC = NOPAT / Invested Capital

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 ROIC 시계열
            period : str — 기간
            operatingIncome : float | None — 영업이익
            effectiveTaxRate : float — 유효세율 (%)
            nopat : float | None — 세후영업이익
            equity : float | None — 자본총계
            totalBorrowing : float | None — 이자부차입금 합계
            cash : float | None — 현금및현금성자산
            investedCapital : float | None — 투하자본
            roic : float | None — ROIC (%)
            roicYoy : float | None — ROIC YoY 변화율 (%)
            waccEstimate : float | None — 추정 WACC (%)
            spread : float | None — ROIC - WACC (%p)
            decomposition : dict | None — Damodaran Excess Return 분해
                operatingMargin, assetTurnover, taxRetention, roicReconstructed,
                excessReturnPct, excessReturnAbs, marginContribution,
                turnoverContribution, dominantDriver
    """
    isResult = company.select("IS", ["영업이익", "법인세비용", "법인세차감전순이익", "매출액"])
    bsResult = company.select(
        "BS",
        [
            "자본총계",
            "단기차입금",
            "장기차입금",
            "차입금단기",
            "long_term_borrowings",
            "short_term_borrowings",
            "차입부채",
            "장기차입부채",
            "유동성장기차입금",
            "사채",
            "현금및현금성자산",
        ],
    )

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    opRow = isData.get("operating_profit", {})
    taxRow = isData.get("income_tax_expense") or isData.get("income_taxes", {})
    ptRow = isData.get("profit_before_tax", {})
    revRow = isData.get("sales", {})
    eqRow = bsData.get("total_stockholders_equity", {})
    bsData.get("shortterm_borrowings", {})
    bsData.get("longterm_borrowings", {})
    bsData.get("borrowings", {})
    bsData.get("debentures", {})
    cashRow = bsData.get("cash_and_cash_equivalents", {})

    yCols = annualColsFromPeriods(isPeriods, maxYears=_MAX_YEARS + 1, basePeriod=basePeriod)
    if len(yCols) < 2:
        return None

    history = []
    for i, col in enumerate(yCols[:-1]):
        yCols[i + 1] if i + 1 < len(yCols) else None
        opIncome = _getF(opRow, col)
        taxExpense = _getF(taxRow, col)
        ptIncome = _getF(ptRow, col)
        revenue = _getF(revRow, col)

        # 유효세율
        effectiveTaxRate = abs(taxExpense) / abs(ptIncome) if ptIncome != 0 else 0.25
        effectiveTaxRate = min(effectiveTaxRate, 0.5)

        nopat = round(opIncome * (1 - effectiveTaxRate)) if opIncome != 0 else None

        equity = _get(eqRow, col)
        # equity 누락(0) 시 인접 기간 값으로 fallback (매핑 공백 대응)
        if equity == 0:
            for adjCol in yCols:
                adjEq = _get(eqRow, adjCol)
                if adjEq > 0:
                    equity = adjEq
                    break
        # 차입금: 회사 키 패턴 무관 헬퍼
        totalBorrowing = sumBorrowings(bsData, col)
        cash = _get(cashRow, col)
        investedCapital = equity + totalBorrowing - cash

        roic = round(nopat / investedCapital * 100, 2) if nopat is not None and investedCapital > 0 else None

        history.append(
            {
                "period": col,
                "operatingIncome": opIncome if opIncome != 0 else None,
                "effectiveTaxRate": round(effectiveTaxRate * 100, 2),
                "nopat": nopat,
                "revenue": revenue if revenue != 0 else None,
                "equity": equity if equity != 0 else None,
                "totalBorrowing": totalBorrowing if totalBorrowing > 0 else None,
                "cash": cash if cash != 0 else None,
                "investedCapital": investedCapital if investedCapital > 0 else None,
                "roic": roic,
                "roicYoy": _yoy(roic, None),  # 이전 기간 ROIC는 아래서 계산
            }
        )

    # ROIC YoY 후처리 (history가 최신→과거 순)
    for i in range(len(history) - 1):
        cur = history[i].get("roic")
        prev = history[i + 1].get("roic")
        history[i]["roicYoy"] = _yoy(cur, prev)

    # WACC 추정 (최신 시점 1회만, 전 기간 동일 적용)
    waccEstimate = _estimateWacc(company)
    if waccEstimate is not None:
        for h in history:
            h["waccEstimate"] = waccEstimate
            roic = h.get("roic")
            h["spread"] = round(roic - waccEstimate, 2) if roic is not None else None

    # Damodaran Excess Return 분해 주입
    from dartlab.core.utils.calc import decomposeRoic

    for h in history:
        op = h.get("operatingIncome")
        rev = h.get("revenue")
        ic = h.get("investedCapital")
        etr = h.get("effectiveTaxRate")
        if op is None or rev is None or ic is None:
            h["decomposition"] = None
            continue
        decomp = decomposeRoic(
            operatingIncome=op,
            revenue=rev,
            investedCapital=ic,
            effectiveTaxRate=etr / 100.0 if etr is not None else None,
            wacc=h.get("waccEstimate"),
        )
        h["decomposition"] = decomp

    # Phase 7 G24: ROIC 변화 driver 분해 (Margin × Turnover × Tax)
    try:
        from dartlab.analysis.financial.attribution import decomposeRoicChange

        for i in range(len(history) - 1):
            cur = history[i]
            prev = history[i + 1]
            cur_d = cur.get("decomposition") or {}
            prev_d = prev.get("decomposition") or {}
            roic_t = cur.get("roic")
            roic_t1 = prev.get("roic")
            margin_t = cur_d.get("operatingMargin")
            margin_t1 = prev_d.get("operatingMargin")
            turnover_t = cur_d.get("assetTurnover")
            turnover_t1 = prev_d.get("assetTurnover")
            tax_t = cur.get("effectiveTaxRate")
            tax_t1 = prev.get("effectiveTaxRate")
            if all(
                isinstance(v, (int, float)) for v in (roic_t, roic_t1, margin_t, margin_t1, turnover_t, turnover_t1)
            ):
                attribution = decomposeRoicChange(
                    roicT=roic_t,
                    roicT1=roic_t1,
                    marginT=margin_t,
                    marginT1=margin_t1,
                    turnoverT=turnover_t,
                    turnoverT1=turnover_t1,
                    taxT=tax_t,
                    taxT1=tax_t1,
                )
                cur["drivers"] = attribution.get("drivers") or []
                cur["driversExplained"] = attribution.get("explainedPct")
    except (ImportError, AttributeError, TypeError, ValueError):
        pass

    # Phase 8 A5
    from dartlab.macro.cycles.turningPoint import injectTurningPoints

    return (
        {"history": history, "turningPoints": injectTurningPoints(history, seriesKey="roic", minDeltaPct=30.0)}
        if history
        else None
    )


# ── 투자 강도 ──


@memoizedCalc
def calcInvestmentIntensity(company, *, basePeriod: str | None = None) -> dict | None:
    """투자 강도 시계열 -- CAPEX/매출, 유무형 비율.

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 투자 강도 시계열
            period : str — 기간
            capex : float | None — CAPEX (유형+무형 취득)
            revenue : float | None — 매출액
            tangibleAssets : float | None — 유형자산
            intangibleAssets : float | None — 무형자산
            totalAssets : float | None — 자산총계
            capexToRevenue : float | None — CAPEX/매출 (%)
            tangibleRatio : float | None — 유형자산/총자산 (%)
            intangibleRatio : float | None — 무형자산/총자산 (%)
    """
    cfResult = company.select(
        "CF",
        ["purchase_of_property_plant_and_equipment", "purchase_of_intangible_assets"],
    )
    isResult = company.select("IS", ["매출액"])
    bsResult = company.select("BS", ["유형자산", "무형자산", "자산총계"])

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    cfParsed = toDictBySnakeId(cfResult)
    cfData = cfParsed[0] if cfParsed else {}
    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    capexRow = cfData.get("purchase_of_property_plant_and_equipment", {})
    intCapexRow = cfData.get("purchase_of_intangible_assets", {})
    revRow = isData.get("sales", {})
    ppeRow = bsData.get("tangible_assets", {})
    intRow = bsData.get("intangible_assets", {})
    taRow = bsData.get("자산총계", {})

    yCols = annualColsFromPeriods(isPeriods, maxYears=_MAX_YEARS, basePeriod=basePeriod)
    if not yCols:
        return None

    history = []
    for col in yCols:
        capex = abs(_getF2(capexRow, col)) + abs(_getF2(intCapexRow, col))
        rev = _getF2(revRow, col)
        ppe = _get(ppeRow, col)
        intangible = _get(intRow, col)
        ta = _get(taRow, col)

        history.append(
            {
                "period": col,
                "capex": capex if capex > 0 else None,
                "revenue": rev if rev != 0 else None,
                "tangibleAssets": ppe if ppe != 0 else None,
                "intangibleAssets": intangible if intangible != 0 else None,
                "totalAssets": ta if ta != 0 else None,
                "capexToRevenue": _pct(capex, rev),
                "tangibleRatio": _pct(ppe, ta),
                "intangibleRatio": _pct(intangible, ta),
            }
        )

    return {"history": history} if history else None


# ── NOPAT + 투하자본 ──


@memoizedCalc
def calcEvaTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """NOPAT + 투하자본 시계열.

    투하자본 = 자본총계 + 이자부차입금 - 현금 (ROIC와 동일 기준).

    Returns
    -------
    dict | None
        history : list[dict] — 기간별 EVA 시계열
            period : str — 기간
            nopat : float | None — 세후영업이익
            investedCapital : float — 투하자본
            nopatReturn : float | None — NOPAT/투하자본 (%)
            waccEstimate : float | None — 추정 WACC (%)
            eva : float | None — 경제적부가가치 (NOPAT - IC * WACC)
    """
    isResult = company.select("IS", ["영업이익", "법인세비용", "법인세차감전순이익"])
    bsResult = company.select(
        "BS",
        [
            "자본총계",
            "단기차입금",
            "장기차입금",
            "차입금단기",
            "long_term_borrowings",
            "short_term_borrowings",
            "차입부채",
            "장기차입부채",
            "유동성장기차입금",
            "사채",
            "현금및현금성자산",
        ],
    )

    isParsed = toDictBySnakeId(isResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    bsData, _ = bsParsed

    opRow = isData.get("operating_profit", {})
    taxRow = isData.get("income_tax_expense") or isData.get("income_taxes", {})
    ptRow = isData.get("profit_before_tax", {})
    eqRow = bsData.get("total_stockholders_equity", {})
    bsData.get("shortterm_borrowings", {})
    bsData.get("longterm_borrowings", {})
    bsData.get("borrowings", {})
    bsData.get("debentures", {})
    cashRow = bsData.get("cash_and_cash_equivalents", {})

    yCols = annualColsFromPeriods(isPeriods, maxYears=_MAX_YEARS, basePeriod=basePeriod)
    if not yCols:
        return None

    history = []
    for col in yCols:
        opIncome = _getF3(opRow, col)
        taxExpense = _getF3(taxRow, col)
        ptIncome = _getF3(ptRow, col)

        # 유효세율
        effectiveTaxRate = abs(taxExpense) / abs(ptIncome) if ptIncome != 0 else 0.25
        effectiveTaxRate = min(effectiveTaxRate, 0.5)

        nopat = opIncome * (1 - effectiveTaxRate) if opIncome != 0 else None

        equity = _get(eqRow, col)
        # 차입금: 회사 키 패턴 무관 헬퍼
        totalBorrowing = sumBorrowings(bsData, col)
        cash = _get(cashRow, col)
        investedCapital = equity + totalBorrowing - cash

        # NOPAT / 투하자본 = 투하자본수익률
        nopatReturn = None
        if nopat is not None and investedCapital > 0:
            nopatReturn = round(nopat / investedCapital * 100, 2)

        history.append(
            {
                "period": col,
                "nopat": nopat,
                "investedCapital": investedCapital,
                "nopatReturn": nopatReturn,
                "waccEstimate": None,
                "eva": None,
            }
        )

    # WACC 추정 + EVA 계산
    waccEstimate = _estimateWacc(company)
    if waccEstimate is not None:
        for h in history:
            h["waccEstimate"] = waccEstimate
            nopat = h.get("nopat")
            ic = h.get("investedCapital")
            if nopat is not None and ic is not None and ic > 0:
                h["eva"] = round(nopat - ic * waccEstimate / 100)

    return {"history": history} if history else None


# ── 타법인 출자 현황 (docs) ──


@memoizedCalc
def calcInvestmentInOther(company, *, basePeriod: str | None = None) -> dict | None:
    """investmentInOtherDetail docs 토픽에서 타법인 출자 총액 추출.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        totalBookValue : float | None — 출자 총 장부금액 (억원)
        description : str | None — 원문 서술 발췌
        period : str | None — 기준 연도
    """
    import re

    from dartlab.core.utils.helpers import parseNumStr

    result = company.show("investmentInOtherDetail")
    if result is None:
        return None

    import polars as pl

    if not isinstance(result, pl.DataFrame):
        return None

    # block index 형태 — text 블록에서 총액 서술 추출
    if "block" in result.columns and "preview" in result.columns:
        textBlocks = result.filter(pl.col("type") == "text")
        for row in textBlocks.iter_rows(named=True):
            preview = str(row.get("preview", ""))
            # "타법인 출자 금액은 장부금액 기준 59조 2,469억원" 패턴
            m = re.search(r"출자\s*금액[^\d]*?([\d,]+)\s*조\s*([\d,]+)\s*억", preview)
            if m:
                tril = parseNumStr(m.group(1))
                bil = parseNumStr(m.group(2))
                if tril is not None and bil is not None:
                    total = tril * 10000 + bil  # 억원 단위
                    # 연도 추출
                    ym = re.search(r"(\d{4})년", preview)
                    period = ym.group(1) if ym else None
                    return {
                        "totalBookValue": total,
                        "description": preview[:200],
                        "period": period,
                    }
            # "XX억원" 패턴 (조 단위 없는 경우)
            m2 = re.search(r"출자\s*금액[^\d]*?([\d,]+)\s*억", preview)
            if m2:
                bil = parseNumStr(m2.group(1))
                if bil is not None:
                    ym = re.search(r"(\d{4})년", preview)
                    period = ym.group(1) if ym else None
                    return {
                        "totalBookValue": bil,
                        "description": preview[:200],
                        "period": period,
                    }

    return None


# ── 플래그 ──


@memoizedCalc
def calcInvestmentFlags(company, *, basePeriod: str | None = None) -> list[str]:
    """투자 분석 경고 신호.

    Returns
    -------
    list[str]
        경고 메시지 문자열 리스트 (저ROIC 지속, 무형자산비율 급등 등).
    """
    flags = []

    roic = calcRoicTimeline(company, basePeriod=basePeriod)
    if roic and len(roic["history"]) >= 3:
        hist = roic["history"]
        declining = all(h.get("roic") is not None and h["roic"] < 5 for h in hist[:3])
        if declining:
            latest = hist[0].get("roic")
            flags.append(f"ROIC {latest:.1f}% — 3년 연속 저수익 (자본비용 미회수 가능성)")

    intensity = calcInvestmentIntensity(company, basePeriod=basePeriod)
    if intensity and len(intensity["history"]) >= 2:
        hist = intensity["history"]
        h0 = hist[0]
        h1 = hist[1]
        ir0 = h0.get("intangibleRatio")
        ir1 = h1.get("intangibleRatio")
        if ir0 is not None and ir1 is not None and ir0 - ir1 > 10:
            flags.append(f"무형자산비율 +{ir0 - ir1:.0f}%p 급등 — 대규모 인수 또는 영업권 증가")

    return flags
