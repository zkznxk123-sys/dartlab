"""Earnings Quality — 회계 품질 이상치 학술 표준.

근거:
- Beneish M-Score (1999) "The Detection of Earnings Manipulation" Financial Analysts Journal
- Sloan Accruals (1996) "Do Stock Prices Fully Reflect Information in Accruals?"
- Damodaran *Investment Valuation* Ch.4 "Earnings Quality"

5 카테고리:
1. 분식 의심 (Beneish M)
2. 일회성 거래 (영업외 비중)
3. 매출채권 급증 (DSO 변화)
4. 자본 우회 (자본거래 vs 영업CF)
5. 영업권 과대 (Goodwill impairment risk)

L0 순수 계산. dict 반환. narrate 는 review 만.
"""

from __future__ import annotations

import math


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
        dep_t = depreciationT / (depreciationT + grossPropertyT) if (depreciationT + grossPropertyT) > 0 else 0.05
        dep_t1 = depreciationT1 / (depreciationT1 + grossPropertyT1) if (depreciationT1 + grossPropertyT1) > 0 else 0.05
        depi = dep_t1 / dep_t if dep_t > 0 else 1
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


def calcEarningsQualityFlags(
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
        flags.append({
            "category": "분식 의심",
            "severity": "high",
            "evidence": f"Sloan 발생액 {sloan['accrualRatio']*100:.1f}% — Q1 quintile",
            "damodaranRef": "Investment Valuation Ch.4 Earnings Quality",
        })
        score -= 25
    elif sloan["quintile"] == "Q2":
        flags.append({
            "category": "분식 의심",
            "severity": "medium",
            "evidence": f"Sloan 발생액 {sloan['accrualRatio']*100:.1f}% — Q2",
            "damodaranRef": "Sloan 1996",
        })
        score -= 10

    # 카테고리 2: 일회성 거래 (영업외/영업이익 > 0.3)
    if nonOperatingIncomeT is not None and operatingIncomeT and operatingIncomeT > 0:
        ratio = abs(nonOperatingIncomeT) / abs(operatingIncomeT)
        if ratio > 0.3:
            flags.append({
                "category": "일회성 거래",
                "severity": "medium",
                "evidence": f"영업외/영업이익 {ratio*100:.0f}% — 일회성 비중 큼",
                "damodaranRef": "Damodaran Normalized Earnings Ch.22",
            })
            score -= 15

    # 카테고리 3: 매출채권 급증 (DSO 전기 +20%)
    if salesT > 0 and salesT1 > 0:
        dso_t = receivablesT / salesT * 365
        dso_t1 = receivablesT1 / salesT1 * 365
        if dso_t1 > 0:
            dso_change_pct = (dso_t - dso_t1) / dso_t1 * 100
            if dso_change_pct > 20:
                flags.append({
                    "category": "매출채권 급증",
                    "severity": "high",
                    "evidence": f"DSO {dso_t1:.0f}일 → {dso_t:.0f}일 (+{dso_change_pct:.0f}%) — 매출 인식 공격적 의심",
                    "damodaranRef": "Aggressive Revenue Recognition (Ch.4)",
                })
                score -= 20

    # 카테고리 4: 자본 우회 (자본거래 > 영업CF)
    if capitalCfT is not None and ocfT and abs(ocfT) > 0:
        if abs(capitalCfT) > abs(ocfT):
            flags.append({
                "category": "자본 우회",
                "severity": "medium",
                "evidence": f"자본거래 {capitalCfT/1e9:.0f}B vs 영업CF {ocfT/1e9:.0f}B — 외부 자본 의존",
                "damodaranRef": "Off-balance financing (Ch.4)",
            })
            score -= 10

    # 카테고리 5: 영업권/총자산 > 30%
    if goodwillT is not None and totalAssetsT > 0:
        gw_ratio = goodwillT / totalAssetsT * 100
        if gw_ratio > 30:
            flags.append({
                "category": "영업권 과대",
                "severity": "high",
                "evidence": f"영업권/총자산 {gw_ratio:.0f}% — 손상 가능성",
                "damodaranRef": "Goodwill Impairment Risk (Ch.4)",
            })
            score -= 20
        elif gw_ratio > 15:
            flags.append({
                "category": "영업권 과대",
                "severity": "low",
                "evidence": f"영업권/총자산 {gw_ratio:.0f}%",
                "damodaranRef": "Goodwill watch zone",
            })
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
            flags.append({
                "keyword": kw,
                "severity": sev,
                "description": desc,
            })

    return flags
