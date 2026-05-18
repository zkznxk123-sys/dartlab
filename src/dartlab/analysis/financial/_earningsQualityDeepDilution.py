"""Dilution + 종합 anomaly — calcDilutionTrend · calcQualityAnomalies."""

from __future__ import annotations

from dartlab.analysis.financial._earningsQualityDeepProxies import (
    _calcEarningsQualityFlagsBase,
    calcBeneishMScore,
    detectAuditFlags,
)
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import toDictBySnakeId

_MAX_YEARS = 8


@memoizedCalc
def calcDilutionTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """기본 EPS vs 희석 EPS 괴리율 시계열 — 스톡옵션/전환사채 희석 리스크.

    notes.eps에서 기본주당이익과 희석주당이익을 추출하여
    희석 괴리율(%)의 추세를 추적한다.
    괴리율이 5% 이상이면 잠재 희석 리스크.

    Returns
    -------
    dict
        history : list[dict] — 기간별 EPS 희석 시계열
            period : str — 회계연도
            basicEps : float | None — 기본주당이익 (원)
            dilutedEps : float | None — 희석주당이익 (원)
            dilutionPct : float | None — 희석 괴리율 (%)
        latestDilution : float | None — 최신 기간 희석 괴리율 (%)
        trend : str | None — 희석 추세 (희석 증가/희석 감소/안정)

    Capabilities:
        - notes.eps 에서 basic vs diluted EPS 시계열 추출 + 괴리율 추세 분류
        - 5% 이상 = 잠재 희석 리스크 식별

    Guide:
        희석 괴리율 추세 ↑ = 신주발행/CB 등 dilution 압력 ↑. 5% 임계 보수적.

    When:
        희석 리스크 + AI EPS dilution 답변.

    How:
        notesDetail.eps → basic/diluted 매칭 → 시계열 계산.

    Requires:
        notes.eps 가용.

    Raises:
        없음.

    Example:
        >>> calcDilutionTrend(company)["latestDilution"]
        3.2

    See Also:
        - calcNonOperatingBreakdown : 영업외
        - companyContext.fetchNotesDetail

    AIContext:
        "EPS 희석 압력" 답변 시 latestDilution + trend 인용.
    """
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesData = fetchNotesDetail(company, ["eps"])
    epsDf = notesData.get("eps")
    if not epsDf:
        return None

    basicRow = None
    dilutedRow = None
    for row in epsDf:
        item = str(row.get("항목", "")).strip()
        if "희석" in item:
            dilutedRow = row
        elif "기본" in item or "주당" in item:
            if basicRow is None:
                basicRow = row

    if basicRow is None:
        return None

    periodCols = [k for k in basicRow if k not in ("항목",) and k.isdigit()]
    periodCols.sort(reverse=True)
    if not periodCols:
        return None

    from dartlab.core.utils.helpers import parseNumStr

    history = []
    for col in periodCols[:_MAX_YEARS]:
        basic = parseNumStr(basicRow.get(col))
        diluted = parseNumStr(dilutedRow.get(col)) if dilutedRow else None

        dilutionPct = None
        if basic is not None and diluted is not None and basic != 0:
            dilutionPct = round((basic - diluted) / abs(basic) * 100, 2)

        history.append(
            {
                "period": col,
                "basicEps": basic,
                "dilutedEps": diluted,
                "dilutionPct": dilutionPct,
            }
        )

    if not history:
        return None

    latestDilution = history[0]["dilutionPct"]

    trend = None
    dilutionVals = [h["dilutionPct"] for h in history if h["dilutionPct"] is not None]
    if len(dilutionVals) >= 2:
        diff = dilutionVals[0] - dilutionVals[-1]
        if diff > 2:
            trend = "희석 증가"
        elif diff < -2:
            trend = "희석 감소"
        else:
            trend = "안정"

    return {
        "history": history,
        "latestDilution": latestDilution,
        "trend": trend,
    }


@memoizedCalc
def calcQualityAnomalies(company, *, basePeriod: str | None = None) -> dict | None:
    """Damodaran Ch.4 + Beneish (1999) + Sloan (1996) 학술 표준 회계 품질.

    기존 calcAccrualAnalysis 는 발생액 시계열. 이 함수는 **이상치 감지** 통합:
    - Beneish M-Score (8 변수)
    - Sloan Accrual quintile
    - 5 카테고리 (분식/일회성/매출채권/자본우회/영업권)
    - 감사보고서 키워드 자동 감지 (docs 활용)

    Returns
    -------
    dict
        score : int — 0~100
        flags : list[{category, severity, evidence, damodaranRef}]
        beneish : dict — M-Score + zone
        sloan : dict — 발생액 quintile
        auditFlags : list — 감사보고서 위험 키워드
        period : str

    Capabilities:
        - Beneish + Sloan + 5 카테고리 (분식/일회성/매출채권/자본우회/영업권) + 감사보고서 키워드 통합
        - 0~100 score 산출

    Guide:
        Damodaran reference 기반 종합. score ≥ 70 = 다중 anomaly 의심.

    When:
        Earnings quality 종합 + AI 회계 anomaly 답변.

    How:
        IS+BS+CF + docs → Beneish + Sloan + audit flags + 5 카테고리.

    Requires:
        IS/BS/CF + docs 가용.

    Raises:
        없음.

    Example:
        >>> calcQualityAnomalies(company)["score"]
        45

    See Also:
        - calcBeneishTimeline : Beneish 시계열
        - calcRichardsonAccrual : 발생액 분해

    AIContext:
        "회계 anomaly 종합" 답변 시 score + flags 인용.
    """
    is_result = company.select("IS", ["매출액", "매출원가", "판매비와관리비", "당기순이익"])
    bs_result = company.select("BS", ["자산총계", "매출채권", "부채총계", "유형자산", "영업권"])
    cf_result = company.select("CF", ["영업활동현금흐름"])

    is_parsed = toDictBySnakeId(is_result)
    bs_parsed = toDictBySnakeId(bs_result)
    cf_parsed = toDictBySnakeId(cf_result)
    if is_parsed is None or bs_parsed is None:
        return None

    is_data, is_periods = is_parsed
    bs_data, _ = bs_parsed
    cf_data = cf_parsed[0] if cf_parsed else {}

    annual_years = [p for p in is_periods if p.isdigit() and len(p) == 4]
    if len(annual_years) < 2:
        return None
    t, t1 = annual_years[0], annual_years[1]

    def _ga(rowDict: dict, period: str, *keys: str) -> float | None:
        for k in keys:
            row = rowDict.get(k) or {}
            v = row.get(period)
            if v is not None:
                return float(v)
        return None

    sales_t = _ga(is_data, t, "sales", "매출액")
    sales_t1 = _ga(is_data, t1, "sales", "매출액")
    cogsT = _ga(is_data, t, "cost_of_sales", "매출원가")
    cogs_t1 = _ga(is_data, t1, "cost_of_sales", "매출원가")
    sgaT = _ga(is_data, t, "selling_and_administrative_expenses", "판매비와관리비")
    sga_t1 = _ga(is_data, t1, "selling_and_administrative_expenses", "판매비와관리비")
    ni_t = _ga(is_data, t, "net_profit", "net_income", "당기순이익")
    assets_t = _ga(bs_data, t, "total_assets", "자산총계")
    assets_t1 = _ga(bs_data, t1, "total_assets", "자산총계")
    receivables_t = _ga(bs_data, t, "trade_receivables", "매출채권")
    receivables_t1 = _ga(bs_data, t1, "trade_receivables", "매출채권")
    goodwill_t = _ga(bs_data, t, "goodwill", "영업권")
    liabilities_t = _ga(bs_data, t, "total_liabilities", "부채총계")
    liabilities_t1 = _ga(bs_data, t1, "total_liabilities", "부채총계")
    ppe_t = _ga(bs_data, t, "tangible_assets", "유형자산")
    ppe_t1 = _ga(bs_data, t1, "tangible_assets", "유형자산")
    ocfT = _ga(cf_data, t, "operating_cashflow")

    quality = _calcEarningsQualityFlagsBase(
        salesT=sales_t or 0,
        salesT1=sales_t1 or 0,
        receivablesT=receivables_t or 0,
        receivablesT1=receivables_t1 or 0,
        netIncomeT=ni_t or 0,
        ocfT=ocfT or 0,
        totalAssetsT=assets_t or 0,
        goodwillT=goodwill_t,
    )

    beneish = None
    if all(v is not None for v in (sales_t, sales_t1, cogsT, cogs_t1, sgaT, sga_t1, assets_t, assets_t1)):
        beneish = calcBeneishMScore(
            salesT=sales_t,
            salesT1=sales_t1,
            receivablesT=receivables_t or 0,
            receivablesT1=receivables_t1 or 0,
            cogsT=cogsT,
            cogsT1=cogs_t1,
            sgaT=sgaT,
            sgaT1=sga_t1,
            grossPropertyT=ppe_t or 0,
            grossPropertyT1=ppe_t1 or 0,
            totalAssetsT=assets_t,
            totalAssetsT1=assets_t1,
            netIncomeT=ni_t or 0,
            ocfT=ocfT or 0,
            leverageT=(liabilities_t / assets_t) if assets_t else 0,
            leverageT1=(liabilities_t1 / assets_t1) if assets_t1 else 0,
            depreciationT=0,
            depreciationT1=0,
        )

    audit_flags: list[dict] = []
    try:
        audit_df = company.show("auditOpinion")
        if audit_df is not None and hasattr(audit_df, "to_dicts"):
            seen: set = set()
            for row in audit_df.to_dicts():
                text = " ".join(str(v) for v in row.values() if isinstance(v, str))
                for f in detectAuditFlags(text):
                    key = f.get("keyword")
                    if key and key not in seen:
                        seen.add(key)
                        audit_flags.append(f)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    return {
        "score": quality["score"],
        "flags": quality["flags"],
        "beneish": beneish,
        "sloan": quality["sloanAccrual"],
        "auditFlags": audit_flags,
        "period": t,
    }
