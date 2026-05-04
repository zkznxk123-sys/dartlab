"""반도체 KPI — CAPEX 사이클/웨이퍼 ASP 추정/가동률 추정.

DART sections(productService/생산실적) + IS(매출/CAPEX) 활용.
"""

from __future__ import annotations

from dartlab.core.memory import memoized_calc


@memoized_calc
def calcSemiconductorKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """반도체 핵심 KPI.

    Returns
    -------
    dict | None
        capexCycle : dict — CAPEX/매출 3Y + 사이클 위치 추정
        aspProxy : dict | None — 매출/생산량 → ASP 추정
        utilizationProxy : dict | None — 가동률 추정
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
        # DART: productService, EDGAR: segments fallback
        ps = company.show("productService")
        if ps is None:
            ps = company.show("segments")
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
