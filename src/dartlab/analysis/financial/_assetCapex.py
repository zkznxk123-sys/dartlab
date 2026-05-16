"""asset.py CAPEX + 투자부동산 + 무형자산 calc 분리.

분리 이유: asset.py 819 줄. 3 개 calc (calcCapexPattern · calcInvestmentPropertyTrend ·
calcIntangibleAssetDetail) 약 324 줄. asset.py 의 facade (자산구조 · 운전자본 · 플래그)
책임만 유지.

BC: asset 모듈에서 3 calc 모두 import 가능 (re-export).
"""

from __future__ import annotations

from typing import Any

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.calc import safePct as _pct
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId
from dartlab.core.utils.safe import get as _get

_MAX_YEARS = 8


@memoizedCalc
def calcCapexPattern(company, *, basePeriod: str | None = None) -> dict | None:
    """CAPEX vs 감가상각 + 건설중인자산 추이.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        latest : dict
            capex : float — 자본적지출 (원)
            depreciation : float — 감가상각비 (원)
            capexToDepRatio : float — CAPEX/감가상각 비율 (배)
            cip : float — 건설중인자산 (원)
            cipPct : float — 건설중인자산 비중 (%)
            investmentType : str — 투자 유형 판단
        history : list[dict] — 연도별 CAPEX 패턴 시계열
    """
    # CAPEX = 유형자산 취득(CF 투자활동에서)
    cfAccounts = ["유형자산의취득", "무형자산의취득", "감가상각비"]
    bsAccounts = ["건설중인자산", "유형자산", "자산총계"]
    isAccounts = ["감가상각비"]

    cfResult = company.select("CF", cfAccounts, strict=False)
    bsResult = company.select("BS", bsAccounts, strict=False)
    isResult = company.select("IS", isAccounts, strict=False)

    bsParsed = toDictBySnakeId(bsResult)
    if bsParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    cfData = toDictBySnakeId(cfResult)
    isData = toDictBySnakeId(isResult)

    cfDict = cfData[0] if cfData else {}
    isDict = isData[0] if isData else {}

    cipRow = bsData.get("건설중인자산", {})
    ppeRow = bsData.get("유형자산", {})
    taRow = bsData.get("자산총계", {})
    capexRow = cfDict.get("유형자산의취득", {})
    intCapexRow = cfDict.get("무형자산의취득", {})
    # 감가상각 3-tier fallback:
    # 1순위: IS 감가상각비 (있는 기업은 직접 사용)
    # 2순위: CF 영업활동 감가상각비 (한국전력 등)
    # 3순위: 업종별 추정 (유형자산 / 추정내용연수 10년)
    depRow = isDict.get("감가상각비") or cfDict.get("감가상각비") or {}

    yCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    def _getFlow2(row: dict, col: str) -> float:
        """CF/IS flow 행에서 값 추출 (None → 0)."""
        v = row.get(col)
        return v if v is not None else 0

    history = []
    latest = None

    # 감가상각 이상치 필터용 중앙값 사전 계산
    _rawDeps = [abs(_getFlow2(depRow, c)) for c in yCols]
    _validDeps = [d for d in _rawDeps if d > 0]
    _depMedian = sorted(_validDeps)[len(_validDeps) // 2] if _validDeps else 0

    for col in yCols:
        cip = _get(cipRow, col)
        ppe = _get(ppeRow, col)
        ta = _get(taRow, col)
        # CAPEX는 CF에서 음수로 나옴 → abs
        capex = abs(_getFlow2(capexRow, col)) + abs(_getFlow2(intCapexRow, col))
        dep = abs(_getFlow2(depRow, col))
        # 이상치 필터: 중앙값 대비 100배 이상 차이나면 스케일 오류로 판단
        if dep > 0 and _depMedian > 0:
            if dep / _depMedian > 100 or _depMedian / dep > 100:
                dep = 0  # 이상치 제거 → 아래 fallback으로 추정
        # 3순위 fallback: 감가상각 null이면 유형자산/10으로 추정
        if dep == 0 and ppe is not None and ppe > 0:
            dep = ppe / 10  # 평균 내용연수 10년 가정

        ratio = capex / dep if dep > 0 else None
        # CAPEX/감가상각 비율 상한: 10배 초과는 감가상각 추정 오류 가능성
        if ratio is not None and ratio > 10:
            ratio = None
        cipPct = _pct(cip, ta) if ta > 0 else 0

        entry = {
            "period": col,
            "capex": capex,
            "depreciation": dep,
            "capexToDepRatio": ratio,
            "cip": cip,
            "cipPct": cipPct,
        }
        history.append(entry)

        if latest is None:
            if ratio is not None and ratio > 1.5:
                investType = "적극 투자 — CAPEX가 감가상각의 1.5배 초과"
            elif ratio is not None and ratio > 1.0:
                investType = "성장 투자 — CAPEX > 감가상각"
            elif ratio is not None and ratio > 0:
                investType = "유지 투자 — CAPEX < 감가상각"
            else:
                investType = "투자 정보 부족"

            latest = {
                "capex": capex,
                "depreciation": dep,
                "capexToDepRatio": ratio,
                "cip": cip,
                "cipPct": cipPct,
                "investmentType": investType,
            }

    if latest is None:
        return None
    return {"latest": latest, "history": history}


# ── 투자부동산 추세 ──


@memoizedCalc
def calcInvestmentPropertyTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """투자부동산 비중 + 공정가치 변동 추세.

    부동산 비중이 높은 기업(REIT, 건설사, 보험사)에서 자산 분석 정확도 향상.
    notes.investmentProperty에서 항목별 시계열을 추출하여 총자산 대비 비중 추적.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        history : list[dict]
            period : str — 기간
            totalAssets : float — 총자산 (원)
            ipValue : float — 투자부동산 금액 (원)
            ipPct : float — 총자산 대비 비중 (%)
        trend : str | None — 비중 추세 ("비중 증가"|"비중 감소"|"안정")
        notesDetail : list[dict] | None — 주석 상세 데이터
    """
    bsResult = company.select("BS", ["자산총계", "투자부동산"])
    parsed = toDictBySnakeId(bsResult)
    if parsed is None:
        return None

    data, allPeriods = parsed
    taRow = data.get("자산총계", {})
    ipRow = data.get("투자부동산", {})

    # 투자부동산 계정이 아예 없거나 값이 전부 0이면 해당 없음
    if not ipRow or all(v is None or v == 0 for v in ipRow.values()):
        return None

    yCols = annualColsFromPeriods(allPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    history = []
    for col in yCols:
        ta = _get(taRow, col)
        ip = _get(ipRow, col)
        if ta <= 0:
            continue
        history.append(
            {
                "period": col,
                "totalAssets": ta,
                "ipValue": ip,
                "ipPct": round(ip / ta * 100, 2) if ip > 0 else 0,
            }
        )

    if not history:
        return None

    # 추세 판단
    trend = None
    pcts = [h["ipPct"] for h in history if h["ipPct"] > 0]
    if len(pcts) >= 2:
        diff = pcts[0] - pcts[-1]
        if diff > 2:
            trend = "비중 증가"
        elif diff < -2:
            trend = "비중 감소"
        else:
            trend = "안정"

    resultDict: dict[str, Any] = {"history": history, "trend": trend}

    # notes enrichment — 투자부동산 세부 항목 (공정가치, 취득/처분 등)
    from dartlab.analysis.financial.companyContext import fetchNotesDetail

    notesData = fetchNotesDetail(company, ["investmentProperty"])
    if notesData.get("investmentProperty"):
        resultDict["notesDetail"] = notesData["investmentProperty"]

    return resultDict


# ── 무형자산 상세 ──


@memoizedCalc
def calcIntangibleAssetDetail(company, *, basePeriod: str | None = None) -> dict | None:
    """무형자산 상세 분해 — 영업권/R&D/기타 비중 + 상각 추세.

    notes.intangibleAsset에서 항목별 시계열을 추출하여
    영업권 비중, R&D 자산화 추세, 손상차손 리스크를 분석.
    바이오/IT 등 IP 비중 높은 기업에서 이익품질 판단에 중요.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        items : list[dict]
            name : str — 항목명
            latestValue : float — 최근 금액 (원)
            pct : float — 무형자산 내 비중 (%)
        totalIntangible : float — 무형자산 합계 (원)
        totalAssets : float — 총자산 (원)
        intangiblePct : float — 총자산 대비 무형자산 비중 (%)
        goodwillPct : float | None — 영업권 비중 (%)
        trend : str | None — 비중 추세 ("비중 증가"|"비중 감소"|"안정")
        notesDetail : list[dict] | None — 주석 원본
    """
    from dartlab.analysis.financial.companyContext import fetchNotesDetail
    from dartlab.core.utils.helpers import parseNumStr

    notesData = fetchNotesDetail(company, ["intangibleAsset"])
    rawRows = notesData.get("intangibleAsset")

    # notes 없으면 BS에서 기본 분해
    bsResult = company.select("BS", ["무형자산", "영업권", "자산총계"])
    bsParsed = toDictBySnakeId(bsResult)
    if bsParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    intRow = bsData.get("무형자산", {})
    gwRow = bsData.get("영업권", {})
    taRow = bsData.get("자산총계", {})

    yCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if not yCols:
        return None

    latestCol = yCols[0]
    totalInt = _get(intRow, latestCol) + _get(gwRow, latestCol)
    ta = _get(taRow, latestCol)

    if totalInt <= 0:
        return None

    # notes 상세가 있으면 항목별 분해
    items = []
    if rawRows:
        for row in rawRows:
            item = str(row.get("항목", "")).strip()
            if not item or any(kw in item for kw in ("합계", "총계", "소계")):
                continue
            v = parseNumStr(row.get(str(latestCol)))
            if v is not None and v > 0:
                items.append(
                    {"name": item, "latestValue": v, "pct": round(v / totalInt * 100, 1) if totalInt > 0 else 0}
                )
        items.sort(key=lambda x: x["latestValue"], reverse=True)
        items = items[:8]

    # 영업권 비중
    gw = _get(gwRow, latestCol)
    goodwillPct = round(gw / totalInt * 100, 1) if totalInt > 0 and gw > 0 else None

    # 총자산 대비 무형자산 비중 추세
    trend = None
    intPcts = []
    for col in yCols:
        intVal = _get(intRow, col) + _get(gwRow, col)
        taVal = _get(taRow, col)
        if taVal > 0 and intVal > 0:
            intPcts.append(intVal / taVal * 100)
    if len(intPcts) >= 2:
        diff = intPcts[0] - intPcts[-1]
        if diff > 2:
            trend = "비중 증가"
        elif diff < -2:
            trend = "비중 감소"
        else:
            trend = "안정"

    resultDict: dict[str, Any] = {
        "items": items,
        "totalIntangible": totalInt,
        "totalAssets": ta,
        "intangiblePct": round(totalInt / ta * 100, 1) if ta > 0 else 0,
        "goodwillPct": goodwillPct,
        "trend": trend,
    }

    if rawRows:
        resultDict["notesDetail"] = rawRows

    return resultDict


# ── 자산 플래그 ──
