"""investmentAnalysis 의 EVA + InvestmentInOther + Flags cluster."""

from __future__ import annotations

from dartlab.analysis.financial._investmentAnalysisRoic import (
    _estimateWacc,
    _yoy,
    calcInvestmentIntensity,
    calcRoicTimeline,
)
from dartlab.analysis.financial.accountSums import sumBorrowings
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.calc import safePct as _pct
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get
_MAX_YEARS = 8


@memoizedCalc
def calcEvaTimeline(company, *, basePeriod: str | None = None) -> dict | None:
    """NOPAT + 투하자본 시계열.

    Capabilities:
        - NOPAT + 투하자본 + NOPAT/IC 수익률 + EVA (NOPAT - IC × WACC) 시계열.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간.

    Returns:
        dict | None: history 키에 nopat/investedCapital/nopatReturn/waccEstimate/
        eva 행 리스트. 데이터 부재 시 None.

    Guide:
        EVA > 0 = 자본비용 초과 가치 창출. 투하자본 = 자본총계 + 이자부차입
        금 - 현금 (ROIC 와 동일 기준). WACC 추정은 ``_estimateWacc``.

    When:
        Stern Stewart 식 가치 창출 진단·자본비용 회수 여부 시계열로 확인.

    How:
        IS 영업이익·법인세 → NOPAT, BS 자본/차입금/현금 → 투하자본 → 비율 계산.

    Requires:
        IS/BS rawNormalized parquet.

    Raises:
        없음.

    Example:
        >>> calcEvaTimeline(Company("005930"))
        {"history": [{"period": "...", "eva": 12345}]}

    SeeAlso:
        - ``calcRoicTimeline``: 동일 구조 비율 표시

    AIContext:
        AI 답변에서 EVA 절대값·자본비용 회수 인용 시.
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

    Capabilities:
        - 사업보고서 텍스트 블록에서 "조/억원" 출자 총액 패턴 정규식 매칭으로
          totalBookValue (억원) 추출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간 (현재 미사용).

    Returns:
        dict | None: totalBookValue/description/period 키. 패턴 매칭 실패 시
        None.

    Guide:
        DART 사업보고서 전용. 텍스트 정규식 매칭이므로 회사별 서술 차이에
        따라 누락 가능.

    When:
        타법인 출자 규모를 본문 서술 그대로 발췌해야 할 때.

    How:
        ``company.show("investmentInOtherDetail")`` 의 text 블록 preview 를
        정규식 ``출자 금액 ... 조 ... 억`` 패턴 매칭.

    Requires:
        DART investmentInOtherDetail docs 토픽 가용성.

    Raises:
        없음.

    Example:
        >>> calcInvestmentInOther(Company("005930"))
        {"totalBookValue": 12345, ...}

    SeeAlso:
        - ``calcInvestmentIntensity``: 본업 투자 강도

    AIContext:
        AI 답변에서 타법인 출자 총액 인용 시.
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

    Capabilities:
        - ROIC 3 년 연속 < 5% (자본비용 미회수)·무형자산비율 +10%p 급등 등을
          한국어 flags 로 산출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간.

    Returns:
        list[str]: 한국어 경고 메시지. 임계 미달 시 빈 리스트.

    Guide:
        flag 임계 — ROIC < 5% × 3 년 / 무형자산비율 +10%p 이상.

    When:
        보고서·UI 위험 배너에 투자 관련 경고 한 줄 표시할 때.

    How:
        하위 calc 결과를 임계값과 비교 후 한국어 포맷팅.

    Requires:
        ``calcRoicTimeline`` + ``calcInvestmentIntensity`` 가용성.

    Raises:
        없음.

    Example:
        >>> calcInvestmentFlags(Company("005930"))
        ["ROIC 3.2% — 3년 연속 ..."]

    SeeAlso:
        - ``calcRoicTimeline``: 본 함수 입력

    AIContext:
        AI 답변에서 투자 위험 한 줄 인용 시.
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
