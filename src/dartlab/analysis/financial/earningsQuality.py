"""이익의 질 분석 — 발생액, 이익 지속성, M-Score 시계열.

이익이 현금으로 뒷받침되는지, 일회성인지, 조작 가능성이 있는지를 시계열로 추적한다.
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

import math

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_YEARS = 8


# ── 유틸 ──


from dartlab.analysis.financial._constants import ACCRUAL_RATIO_WARNING
from dartlab.core.utils.calc import safeDiv as _safe

# ── 발생액 분석 ──


@memoizedCalc
def calcBeneishMScore(
    *,
    salesT: float,
    salesT1: float,
    receivablesT: float,
    receivablesT1: float,
    cogsT: float,
    cogsT1: float,
    sgaT: float,
    sgaT1: float,
    grossPropertyT: float,
    grossPropertyT1: float,
    totalAssetsT: float,
    totalAssetsT1: float,
    netIncomeT: float,
    ocfT: float,
    leverageT: float,
    leverageT1: float,
    depreciationT: float,
    depreciationT1: float,
) -> dict:
    """Beneish M-Score (1999) — 분식 의심 8 변수 모델.

    공식: M = -4.84 + 0.92×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI
              + 0.115×DEPI - 0.172×SGAI + 4.679×TATA - 0.327×LVGI

    M > -1.78 → 분식 위험 (high_risk)
    M > -2.22 → watch zone
    M ≤ -2.22 → low_risk

    Returns
    -------
    dict
        mScore : float
        zone : "low_risk" | "watch" | "high_risk"
        components : dict — 8 변수
    """
    if salesT <= 0 or salesT1 <= 0 or totalAssetsT <= 0 or totalAssetsT1 <= 0:
        return {"mScore": None, "zone": "skip", "components": {}}

    try:
        # DSRI: Days Sales in Receivables Index
        dsri = (receivablesT / salesT) / (receivablesT1 / salesT1) if salesT1 > 0 else 1
        # GMI: Gross Margin Index (전기/당기)
        gm_t = (salesT - cogsT) / salesT
        gm_t1 = (salesT1 - cogsT1) / salesT1
        gmi = gm_t1 / gm_t if gm_t > 0 else 1
        # AQI: Asset Quality Index (비현금성 자산 비중)
        non_cur_t = totalAssetsT - grossPropertyT
        non_cur_t1 = totalAssetsT1 - grossPropertyT1
        aqi = (non_cur_t / totalAssetsT) / (non_cur_t1 / totalAssetsT1) if totalAssetsT1 > 0 else 1
        # SGI: Sales Growth Index
        sgi = salesT / salesT1
        # DEPI: Depreciation Index
        depT = depreciationT / (depreciationT + grossPropertyT) if (depreciationT + grossPropertyT) > 0 else 0.05
        dep_t1 = depreciationT1 / (depreciationT1 + grossPropertyT1) if (depreciationT1 + grossPropertyT1) > 0 else 0.05
        depi = dep_t1 / depT if depT > 0 else 1
        # SGAI: SGA Index
        sgai = (sgaT / salesT) / (sgaT1 / salesT1) if salesT1 > 0 else 1
        # TATA: Total Accruals to Total Assets
        accruals = netIncomeT - ocfT
        tata = accruals / totalAssetsT if totalAssetsT > 0 else 0
        # LVGI: Leverage Index
        lvgi = leverageT / leverageT1 if leverageT1 > 0 else 1
    except (ZeroDivisionError, TypeError, ValueError):
        return {"mScore": None, "zone": "skip", "components": {}}

    m_score = (
        -4.84
        + 0.92 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    if m_score > -1.78:
        zone = "high_risk"
    elif m_score > -2.22:
        zone = "watch"
    else:
        zone = "low_risk"

    return {
        "mScore": round(m_score, 3),
        "zone": zone,
        "components": {
            "DSRI": round(dsri, 3),
            "GMI": round(gmi, 3),
            "AQI": round(aqi, 3),
            "SGI": round(sgi, 3),
            "DEPI": round(depi, 3),
            "SGAI": round(sgai, 3),
            "TATA": round(tata, 4),
            "LVGI": round(lvgi, 3),
        },
        "interpretation": _beneishInterpretation(zone),
    }


def _beneishInterpretation(zone: str) -> str:
    return {
        "low_risk": "Beneish M ≤ -2.22 — 분식 위험 낮음",
        "watch": "Beneish M -2.22~-1.78 — 회색지대, 추가 검토 권장",
        "high_risk": "Beneish M > -1.78 — 분식 의심, 감사보고서 정밀 검토 필수",
    }.get(zone, "판정 불가")


def calcSloanAccruals(
    netIncome: float,
    ocf: float,
    totalAssets: float,
) -> dict:
    """Sloan Accruals (1996) — 발생액 비율.

    공식: Accruals = (NI - OCF) / Total Assets
    상위 quintile (Q1, accrual 큼) → 1년 후 underperform 경향

    Returns
    -------
    dict
        accrualRatio : float
        quintile : "Q1" (highest accrual, 위험) ~ "Q5" (cleanest)
        warning : str | None
    """
    if totalAssets is None or totalAssets <= 0 or netIncome is None or ocf is None:
        return {"accrualRatio": None, "quintile": "skip", "warning": None}

    accrual_ratio = (netIncome - ocf) / totalAssets

    # Quintile 분류 (Sloan 1996 KOSPI 근사)
    if accrual_ratio > 0.10:
        quintile = "Q1"
        warning = "발생액 > 10% — Sloan 분류 최고위험 quintile (1년 후 실적 후행 가능성)"
    elif accrual_ratio > 0.05:
        quintile = "Q2"
        warning = "발생액 5~10% — 주의 (일회성 이익 의심)"
    elif accrual_ratio > 0.0:
        quintile = "Q3"
        warning = None
    elif accrual_ratio > -0.05:
        quintile = "Q4"
        warning = None
    else:
        quintile = "Q5"
        warning = None

    return {
        "accrualRatio": round(accrual_ratio, 4),
        "quintile": quintile,
        "warning": warning,
    }


def _calcEarningsQualityFlagsBase(
    *,
    salesT: float,
    salesT1: float,
    receivablesT: float,
    receivablesT1: float,
    netIncomeT: float,
    ocfT: float,
    totalAssetsT: float,
    nonOperatingIncomeT: float | None = None,
    operatingIncomeT: float | None = None,
    goodwillT: float | None = None,
    capitalCfT: float | None = None,
) -> dict:
    """5 카테고리 회계 품질 이상치 종합 (Damodaran Ch.4).

    Returns
    -------
    dict
        score : int — 0~100 (100 = clean)
        flags : list[{category, severity, evidence, damodaranRef}]
    """
    flags = []
    score = 100

    # 카테고리 1: 분식 의심 — Sloan accrual 만 (Beneish 는 별도 호출)
    sloan = calcSloanAccruals(netIncomeT, ocfT, totalAssetsT)
    if sloan["quintile"] == "Q1":
        flags.append(
            {
                "category": "분식 의심",
                "severity": "high",
                "evidence": f"Sloan 발생액 {sloan['accrualRatio'] * 100:.1f}% — Q1 quintile",
                "damodaranRef": "Investment Valuation Ch.4 Earnings Quality",
            }
        )
        score -= 25
    elif sloan["quintile"] == "Q2":
        flags.append(
            {
                "category": "분식 의심",
                "severity": "medium",
                "evidence": f"Sloan 발생액 {sloan['accrualRatio'] * 100:.1f}% — Q2",
                "damodaranRef": "Sloan 1996",
            }
        )
        score -= 10

    # 카테고리 2: 일회성 거래 (영업외/영업이익 > 0.3)
    if nonOperatingIncomeT is not None and operatingIncomeT and operatingIncomeT > 0:
        ratio = abs(nonOperatingIncomeT) / abs(operatingIncomeT)
        if ratio > 0.3:
            flags.append(
                {
                    "category": "일회성 거래",
                    "severity": "medium",
                    "evidence": f"영업외/영업이익 {ratio * 100:.0f}% — 일회성 비중 큼",
                    "damodaranRef": "Damodaran Normalized Earnings Ch.22",
                }
            )
            score -= 15

    # 카테고리 3: 매출채권 급증 (DSO 전기 +20%)
    if salesT > 0 and salesT1 > 0:
        dso_t = receivablesT / salesT * 365
        dso_t1 = receivablesT1 / salesT1 * 365
        if dso_t1 > 0:
            dso_change_pct = (dso_t - dso_t1) / dso_t1 * 100
            if dso_change_pct > 20:
                flags.append(
                    {
                        "category": "매출채권 급증",
                        "severity": "high",
                        "evidence": f"DSO {dso_t1:.0f}일 → {dso_t:.0f}일 (+{dso_change_pct:.0f}%) — 매출 인식 공격적 의심",
                        "damodaranRef": "Aggressive Revenue Recognition (Ch.4)",
                    }
                )
                score -= 20

    # 카테고리 4: 자본 우회 (자본거래 > 영업CF)
    if capitalCfT is not None and ocfT and abs(ocfT) > 0:
        if abs(capitalCfT) > abs(ocfT):
            flags.append(
                {
                    "category": "자본 우회",
                    "severity": "medium",
                    "evidence": f"자본거래 {capitalCfT / 1e9:.0f}B vs 영업CF {ocfT / 1e9:.0f}B — 외부 자본 의존",
                    "damodaranRef": "Off-balance financing (Ch.4)",
                }
            )
            score -= 10

    # 카테고리 5: 영업권/총자산 > 30%
    if goodwillT is not None and totalAssetsT > 0:
        gw_ratio = goodwillT / totalAssetsT * 100
        if gw_ratio > 30:
            flags.append(
                {
                    "category": "영업권 과대",
                    "severity": "high",
                    "evidence": f"영업권/총자산 {gw_ratio:.0f}% — 손상 가능성",
                    "damodaranRef": "Goodwill Impairment Risk (Ch.4)",
                }
            )
            score -= 20
        elif gw_ratio > 15:
            flags.append(
                {
                    "category": "영업권 과대",
                    "severity": "low",
                    "evidence": f"영업권/총자산 {gw_ratio:.0f}%",
                    "damodaranRef": "Goodwill watch zone",
                }
            )
            score -= 5

    score = max(0, min(100, score))

    return {
        "score": score,
        "flags": flags,
        "sloanAccrual": sloan,
    }


def detectAuditFlags(auditOpinionText: str) -> list[dict]:
    """감사보고서 텍스트에서 위험 키워드 자동 감지.

    Damodaran Ch.4 + KICPA 표준 키워드.
    """
    if not auditOpinionText:
        return []

    text = str(auditOpinionText)
    flags = []

    keyword_severity = [
        ("의견거절", "critical", "감사 의견거절 — 재무제표 신뢰 붕괴"),
        ("부적정의견", "critical", "부적정의견 — 회계 기준 위반"),
        ("한정의견", "high", "한정의견 — 일부 항목 검증 불가"),
        ("계속기업 불확실성", "high", "계속기업 가정 의심"),
        ("계속기업 가정에 관한", "high", "계속기업 가정 의심"),
        ("내부통제 미흡", "high", "내부회계관리 미흡"),
        ("내부회계관리제도 비적정", "high", "내부회계관리 비적정"),
        ("재무제표 재작성", "high", "과거 재무제표 재작성"),
        ("특수관계자 거래", "low", "특수관계자 거래 비중 (양적 검토 필요)"),
        ("핵심감사사항", "low", "KAM 명시"),
    ]

    for kw, sev, desc in keyword_severity:
        if kw in text:
            flags.append(
                {
                    "keyword": kw,
                    "severity": sev,
                    "description": desc,
                }
            )

    return flags


def calcAccrualAnalysis(company, *, basePeriod: str | None = None) -> dict | None:
    """발생액(Accrual) 시계열 — 이익 중 현금이 아닌 비중.

    Returns
    -------
    dict
        history : list[dict] — 기간별 발생액 시계열
            period : str — 회계연도
            netIncome : float — 당기순이익 (원)
            ocf : float — 영업활동현금흐름 (원)
            totalAssets : float — 자산총계 (원)
            sloanAccrualRatio : float | None — Sloan 발생액비율 (배)
            accrualToRevenue : float | None — 발생액/매출액 (%)
            ocfToNi : float | None — 영업CF/순이익 (%)
        notesDetail : dict | None — 매출채권 대손충당금 주석 (있는 경우)
    """
    isResult = company.select("IS", ["당기순이익", "매출액"])
    cfResult = company.select("CF", ["영업활동현금흐름"])
    bsResult = company.select("BS", ["자산총계"])

    isParsed = toDictBySnakeId(isResult)
    cfParsed = toDictBySnakeId(cfResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or cfParsed is None or bsParsed is None:
        return None

    isData, _ = isParsed
    cfData, cfPeriods = cfParsed
    bsData, _ = bsParsed

    niRow = isData.get("당기순이익", {})
    revRow = isData.get("매출액", {})
    ocfRow = cfData.get("영업활동현금흐름", {})
    taRow = bsData.get("자산총계", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        ni = _getF(niRow, col)
        ocf = _getF(ocfRow, col)
        ta = _get(taRow, col)
        rev = _getF(revRow, col)
        accrual = ni - ocf

        history.append(
            {
                "period": col,
                "netIncome": ni,
                "ocf": ocf,
                "totalAssets": ta,
                "sloanAccrualRatio": _safe(accrual, ta) if ta > 0 else None,
                "accrualToRevenue": _safe(accrual, rev) * 100 if rev > 0 and _safe(accrual, rev) is not None else None,
                "ocfToNi": (lambda r: r if abs(r) <= 1000 else None)(_safe(ocf, ni) * 100)
                if ni != 0 and _safe(ocf, ni) is not None
                else None,
            }
        )

    if not history:
        return None

    result: dict = {"history": history}

    # notes enrichment — 매출채권 대손충당금 상세
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesDetail = fetchNotesDetail(company, ["receivables"])
    if notesDetail:
        result["notesDetail"] = notesDetail

    return result


# ── 이익 지속성 ──


@memoizedCalc
def calcEarningsPersistence(company, *, basePeriod: str | None = None) -> dict | None:
    """이익 지속성 — 영업이익 vs 영업외손익, 변동성.

    Returns
    -------
    dict
        history : list[dict] — 기간별 이익 구성 시계열
            period : str — 회계연도
            operatingIncome : float — 영업이익 (원)
            preTaxIncome : float — 법인세차감전순이익 (원)
            nonOperatingIncome : float — 영업외손익 (원)
            nonOpRatio : float | None — 영업외/영업이익 비율 (%)
        earningsVolatility : float | None — 영업이익 변동계수 (배)
    """
    accounts = ["영업이익", "법인세차감전순이익", "세전이익"]
    isResult = company.select("IS", accounts)
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None

    isData, isPeriods = isParsed
    opRow = isData.get("영업이익", {})
    # 세전이익 fallback
    ptRow = isData.get("법인세차감전순이익", isData.get("세전이익", {}))

    yCols = annualColsFromPeriods(isPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    opValues = []
    for col in yCols:
        opIncome = _getF2(opRow, col)
        ptIncome = _getF2(ptRow, col)
        nonOp = ptIncome - opIncome

        nonOpRatio = None
        if opIncome > 0:
            nonOpRatio = abs(nonOp) / opIncome * 100

        history.append(
            {
                "period": col,
                "operatingIncome": opIncome,
                "preTaxIncome": ptIncome,
                "nonOperatingIncome": nonOp,
                "nonOpRatio": nonOpRatio,
            }
        )
        if opIncome != 0:
            opValues.append(opIncome)

    # 변동계수 (CV = std / |mean|)
    earningsVolatility = None
    if len(opValues) >= 3:
        mean = sum(opValues) / len(opValues)
        if mean != 0:
            variance = sum((v - mean) ** 2 for v in opValues) / len(opValues)
            earningsVolatility = math.sqrt(variance) / abs(mean)

    return {"history": history, "earningsVolatility": earningsVolatility} if history else None


# ── Beneish M-Score 시계열 ──


# ── 플래그 ──


@memoizedCalc
def calcEarningsQualityFlags(company, *, basePeriod: str | None = None) -> dict:
    """이익 품질 경고 신호.

    Returns
    -------
    dict
        flags : list[str] — 경고 메시지 목록 (발생액 과다, CF 부족, M-Score 초과 등)
        enrichedFlags : list[dict] — 구조화된 플래그 (정밀도/기저율/학술근거 포함)
            code : str — 플래그 코드
            message : str — 경고 메시지
            precision : float | None — 정밀도
            baseRate : str — 표본 기반
            reference : str — 학술 근거
            sectorNote : str — 업종별 주의사항
    """
    flags: list[str] = []
    enriched: list[dict] = []

    accrual = calcAccrualAnalysis(company, basePeriod=basePeriod)
    if accrual and accrual["history"]:
        h0 = accrual["history"][0]
        sar = h0.get("sloanAccrualRatio")
        if sar is not None and sar > ACCRUAL_RATIO_WARNING:
            flags.append(f"Sloan 발생액비율 {sar:.1%} — 이익 현금화 부족")
        ocfNi = h0.get("ocfToNi")
        if ocfNi is not None and 0 < ocfNi < 40:
            flags.append(f"영업CF/순이익 {ocfNi:.0f}% — 이익 대비 현금 부족")

    persistence = calcEarningsPersistence(company, basePeriod=basePeriod)
    if persistence:
        if persistence["history"]:
            h0 = persistence["history"][0]
            nonOpRatio = h0.get("nonOpRatio")
            nonOpIncome = h0.get("nonOperatingIncome")
            if nonOpRatio is not None and nonOpRatio > 30:
                if nonOpIncome is not None and nonOpIncome < 0:
                    suffix = " (일회성 항목 가능성)" if nonOpRatio > 100 else ""
                    flags.append(f"영업외손실 비중 {nonOpRatio:.0f}% — 영업이익을 상쇄{suffix}")
                else:
                    suffix = " (일회성 항목 가능성)" if nonOpRatio > 100 else ""
                    flags.append(f"영업외이익 비중 {nonOpRatio:.0f}% — 일회성 이익 의존{suffix}")

        cv = persistence.get("earningsVolatility")
        if cv is not None and cv > 0.5:
            flags.append(f"이익 변동계수 {cv:.2f} — 이익 변동성 높음")

    beneish = calcBeneishTimeline(company, basePeriod=basePeriod)
    if beneish and beneish["history"]:
        h0 = beneish["history"][0]
        ms = h0.get("mScore")
        if ms is not None and ms > -1.78:
            msg = f"Beneish M-Score {ms:.2f} — 임계값 초과, 이익 조작 가능성"
            flags.append(msg)
            meta = beneish.get("diagnosticMeta", {})
            enriched.append(
                {
                    "code": "BENEISH_MANIPULATOR",
                    "message": msg,
                    "precision": meta.get("precision"),
                    "baseRate": meta.get("sampleBase", ""),
                    "reference": meta.get("reference", ""),
                    "sectorNote": meta.get("krNote", ""),
                }
            )

    return {"flags": flags, "enrichedFlags": enriched}


# ── Richardson 3계층 발생액 분해 ──


# ── 영업외손익 분해 ──


# ── EPS 희석 분석 ──


# ── Phase 7 G26: Damodaran Ch.4 회계 품질 이상치 (Beneish + Sloan + 5 카테고리) ──


# 분리된 깊이 분석 (BC re-export)
from dartlab.analysis.financial._earningsQualityDeep import (  # noqa: E402, F401
    calcBeneishTimeline,
    calcDilutionTrend,
    calcNonOperatingBreakdown,
    calcQualityAnomalies,
    calcRichardsonAccrual,
)
