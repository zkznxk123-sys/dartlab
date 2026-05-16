"""capital.py 현금흐름 + 부실 calc 분리.

분리 이유: capital.py 873 줄. calcCashFlowStructure (98) + _sign + _classifyCfPattern
+ _isFinancialCompany + calcDistressIndicators (67) 등 약 240 줄. 별도 모듈로 빼서
capital.py 의 facade (자본/부채/이자/유동성) 책임 유지.

BC: capital 모듈에서 두 calc + 헬퍼 모두 import 가능 (re-export).
순환 import 회피: capital.py 의 _quarterlyCols / _getRatios / _MAX_QUARTERS 는
함수 내부 lazy import 또는 인자 전달로 처리.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_QUARTERS = 5
_MAX_YEARS = 8


@memoizedCalc
def calcCashFlowStructure(company, *, basePeriod: str | None = None) -> dict | None:
    """영업CF/투자CF/재무CF + FCF + CF 패턴.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        tableRows : list[dict] — CF 항목별 기간 매핑 행
        cols : list[str] — 기간 컬럼
        pattern : str | None — CF 패턴 진단
        metrics : list[tuple[str, str]] | None — FCF 등 요약 지표
    """
    from dartlab.analysis.financial.capital import _getRatios, _quarterlyCols

    result = company.select(
        "CF",
        ["영업활동현금흐름", "투자활동현금흐름", "재무활동으로인한현금흐름", "유형자산의취득"],
    )
    parsed = toDictBySnakeId(result)
    if parsed is None:
        return None

    data, allPeriods = parsed
    ocfRow = data.get("operating_cashflow") or data.get("cash_flows_from_operating_activities")
    if ocfRow is None:
        return None
    icfRow = data.get("investing_cashflow") or data.get("cash_flows_from_investing_activities")
    fcfRow = data.get("cash_flows_from_financing_activities") or data.get("financing_cashflow")
    capexRow = data.get("purchase_of_property_plant_and_equipment")

    qCols = _quarterlyCols(allPeriods, _MAX_QUARTERS)
    if not qCols:
        return None

    rawRows: list[dict] = []
    rawRows.append({"": "영업CF", **{c: ocfRow.get(c) for c in qCols}})
    if icfRow:
        rawRows.append({"": "투자CF", **{c: icfRow.get(c) for c in qCols}})
    if fcfRow:
        rawRows.append({"": "재무CF", **{c: fcfRow.get(c) for c in qCols}})
    if capexRow:
        freeRow: dict = {"": "FCF"}
        for c in qCols:
            ocf = ocfRow.get(c)
            capex = capexRow.get(c)
            if ocf is not None and capex is not None:
                free = ocf + capex if capex < 0 else ocf - capex
                freeRow[c] = free
            else:
                freeRow[c] = None
        rawRows.append(freeRow)

    # CF 패턴 분류 (분기 우선, 분기 데이터 없으면 연간 fallback)
    latestCol = qCols[0]
    ocfSign = _sign(ocfRow.get(latestCol))
    icfSign = _sign((icfRow or {}).get(latestCol))
    fcfSign = _sign((fcfRow or {}).get(latestCol))
    pattern = _classifyCfPattern(ocfSign, icfSign, fcfSign)
    if pattern is None:
        # Q4 기준으로 재시도 (재무CF가 특정 분기에만 있는 기업 대응)
        q4Cols = sorted([c for c in allPeriods if c.endswith("Q4")], reverse=True)
        for qc in q4Cols[:3]:
            ocfA = _sign(ocfRow.get(qc))
            icfA = _sign((icfRow or {}).get(qc))
            fcfA = _sign((fcfRow or {}).get(qc))
            pattern = _classifyCfPattern(ocfA, icfA, fcfA)
            if pattern is not None:
                break

    # 추가 지표
    ratios = _getRatios(company)
    metrics = None
    if ratios is not None:
        extra = []
        ocfm = getattr(ratios, "operatingCfMargin", None)
        if ocfm is not None:
            extra.append(("영업CF 마진", f"{ocfm:.1f}%"))
        cxr = getattr(ratios, "capexRatio", None)
        if cxr is not None:
            extra.append(("CAPEX/매출", f"{cxr:.1f}%"))
        ftor = getattr(ratios, "fcfToOcfRatio", None)
        if ftor is not None:
            extra.append(("FCF/OCF", f"{ftor:.0f}%"))
        if extra:
            metrics = extra

    return {
        "tableRows": rawRows,
        "cols": qCols,
        "pattern": pattern,
        "metrics": metrics,
    }


def _sign(val) -> str:
    """양/음/0 부호.

    Returns
    -------
    str
        ``"+"``, ``"-"``, ``"0"``, 또는 ``"?"`` (None).
    """
    if val is None:
        return "?"
    if val > 0:
        return "+"
    if val < 0:
        return "-"
    return "0"


def _classifyCfPattern(ocf: str, icf: str, fcf: str) -> str | None:
    """영업/투자/재무 CF 부호 조합으로 패턴 분류.

    Parameters
    ----------
    ocf : str
        영업CF 부호 (``"+"``, ``"-"``, ``"0"``, ``"?"``).
    icf : str
        투자CF 부호.
    fcf : str
        재무CF 부호.

    Returns
    -------
    str | None
        CF 패턴 한국어 설명 (예: ``"성숙형 — 영업으로 벌어 투자하고 부채 상환"``).
        미분류 조합이면 None.
    """
    patterns = {
        ("+", "-", "-"): "성숙형 — 영업으로 벌어 투자하고 부채 상환",
        ("+", "-", "+"): "확장형 — 영업 + 외부 조달로 적극 투자",
        ("+", "+", "-"): "구조조정형 — 자산 매각하며 부채 상환",
        ("-", "-", "+"): "위기형 — 영업 적자를 외부 차입으로 메움",
        ("-", "+", "+"): "축소형 — 자산 매각 + 차입으로 영업 적자 보전",
        ("-", "+", "-"): "전환형 — 자산 매각으로 부채 상환, 영업 회복 필요",
        # 재무CF 미보고("?" 또는 "0") — 영업/투자만으로 부분 분류
        ("+", "-", "?"): "성숙형 — 영업으로 벌어 투자 (재무CF 미보고)",
        ("+", "-", "0"): "성숙형 — 영업으로 벌어 투자 (재무CF 미보고)",
        ("-", "-", "?"): "위기형 — 영업+투자 모두 유출 (재무CF 미보고)",
        ("-", "-", "0"): "위기형 — 영업+투자 모두 유출 (재무CF 미보고)",
    }
    return patterns.get((ocf, icf, fcf))


def _isFinancialCompany(company) -> bool:
    """금융업 판별 (capital.py 내부용).

    Returns
    -------
    bool
        금융업/지주사이면 True.
    """
    try:
        sector = getattr(company, "sector", None)
        if sector is not None:
            from dartlab.frame.sector import Sector

            if sector.sector == Sector.FINANCIALS:
                return True
        name = getattr(company, "corpName", "") or ""
        if any(k in name for k in ("지주", "홀딩스", "Holdings")):
            return True
    except (AttributeError, ImportError):
        pass
    return False


@memoizedCalc
def calcDistressIndicators(company, *, basePeriod: str | None = None) -> dict | None:
    """Altman Z, Ohlson O, Piotroski F, Springate S.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict | None
        metrics : list[tuple[str, str]] — (지표명, 값+판정 문자열) 쌍 목록
    """
    from dartlab.analysis.financial.capital import _getRatios

    ratios = _getRatios(company)
    if ratios is None:
        return None

    isFinancial = _isFinancialCompany(company)
    metrics = []

    # Altman Z-Score: 비금융 제조업용 모형 — 금융업에는 적용 불가
    if not isFinancial:
        az = getattr(ratios, "altmanZScore", None)
        if az is None:
            az = getattr(ratios, "altmanZppScore", None)
        if az is not None:
            if az > 2.99:
                quality = "안전"
            elif az > 1.81:
                quality = "회색지대"
            else:
                quality = "부실 위험"
            metrics.append(("Altman Z", f"{az:.2f} — {quality}"))

    op = getattr(ratios, "ohlsonProbability", None)
    if op is not None:
        metrics.append(("Ohlson 부실확률", f"{op:.1f}%"))
    else:
        os_ = getattr(ratios, "ohlsonOScore", None)
        if os_ is not None:
            metrics.append(("Ohlson O-Score", f"{os_:.2f}"))

    pf = getattr(ratios, "piotroskiFScore", None)
    if pf is not None:
        maxF = getattr(ratios, "piotroskiMaxScore", 9)
        if pf >= 7:
            quality = "재무 건전"
        elif pf >= 4:
            quality = "보통"
        else:
            quality = "재무 약화"
        metrics.append(("Piotroski F", f"{pf}/{maxF} — {quality}"))

    ss = getattr(ratios, "springateSScore", None)
    if ss is not None:
        quality = "안전" if ss > 0.862 else "부실 위험"
        metrics.append(("Springate S", f"{ss:.2f} — {quality}"))

    if not metrics:
        return None

    return {"metrics": metrics}
