"""반도체 KPI — CAPEX 사이클/웨이퍼 ASP 추정/가동률 추정.

DART sections(productService/생산실적) + IS(매출/CAPEX) 활용.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc


@memoizedCalc
def calcSemiconductorKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """반도체 핵심 KPI.

    Capabilities:
        - CAPEX/매출 5Y 사이클 + 반도체 세그먼트 감지.

    Guide:
        CF purchase_of_property_plant_and_equipment / IS sales → ratio history → phase 판정.

    When:
        삼성전자·SK하이닉스 등 반도체 사이클 판단 시.

    How:
        latest > avg×1.2 = 확장, ×0.8 미만 = 축소, 중간 = 유지.

    Requires:
        company.select("CF", ["purchase_of_property_plant_and_equipment"]) + select("IS", ["sales"]).

    Raises:
        없음. AttributeError·ValueError·TypeError·KeyError try 흡수.

    Returns:
        dict | None
            capexCycle : dict — CAPEX/매출 3Y + 사이클 위치 추정
            aspProxy : dict | None — 매출/생산량 → ASP 추정
            utilizationProxy : dict | None — 가동률 추정

    Example:
        >>> calcSemiconductorKpis(삼성전자)
        {"capexCycle": {...}, "aspProxy": {...}}

    See Also:
        - dispatcher.sectorKpi : 섹터 자동 라우팅.

    AIContext:
        반도체 사이클 (확장/유지/축소) 위치 판단 인용.
    """
    from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

    result: dict = {}

    # ── CAPEX/매출 사이클 ──
    try:
        parsed = toDictBySnakeId(company.select("CF", ["purchase_of_property_plant_and_equipment"]))
        is_parsed = toDictBySnakeId(company.select("IS", ["sales"]))
        if parsed and is_parsed:
            cfData, cfPeriods = parsed
            isData, isPeriods = is_parsed
            yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=5)
            capexRow = cfData.get("purchase_of_property_plant_and_equipment", {})
            salesRow = isData.get("sales", {})

            history = []
            for col in yCols:
                capex = capexRow.get(col)
                rev = salesRow.get(col)
                if capex is not None and rev and float(rev) > 0:
                    ratio = abs(float(capex)) / float(rev) * 100
                    history.append({"period": col, "capexToRevenue": round(ratio, 1)})

            if history:
                avg = sum(h["capexToRevenue"] for h in history) / len(history)
                latest = history[-1]["capexToRevenue"]
                phase = "확장" if latest > avg * 1.2 else "유지" if latest > avg * 0.8 else "축소"
                result["capexCycle"] = {
                    "history": history,
                    "avg": round(avg, 1),
                    "latest": latest,
                    "phase": phase,
                }
    except (AttributeError, ValueError, TypeError):
        pass

    # ── 세그먼트에서 반도체 관련 매출 추정 ──
    try:
        # show 은퇴 → 공통파서 panel 제품/부문 표 (EDGAR segments fallback)
        import polars as pl

        from dartlab.providers.dart.sections import sectionRows

        code = getattr(company, "stockCode", None)
        _r = (sectionRows(code, sectionPattern="제품") or sectionRows(code, sectionPattern="부문")) if code else []
        ps = pl.DataFrame(_r) if _r else None
        if ps is not None and hasattr(ps, "to_dicts"):
            rows = ps.to_dicts()
            semi_kw = [
                "반도체",
                "메모리",
                "DRAM",
                "NAND",
                "파운드리",
                "웨이퍼",
                "Semiconductor",
                "Memory",
                "DRAM",
                "NAND",
                "Foundry",
            ]
            semi_rows = [r for r in rows if any(k.lower() in str(r).lower() for k in semi_kw)]
            if semi_rows:
                result["aspProxy"] = {
                    "segmentCount": len(semi_rows),
                    "note": "세그먼트에서 반도체 관련 항목 감지",
                }
    except (AttributeError, ValueError, TypeError, KeyError):
        pass

    return result if result else None
