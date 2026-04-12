"""게임·엔터 KPI — IP 포트폴리오/콘텐츠 집중도/매출 구성.

DART sections(productService) + IS 활용.
"""

from __future__ import annotations

from dartlab.analysis.financial._memoize import memoized_calc


@memoized_calc
def calcGamingKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """게임·엔터 핵심 KPI.

    Returns
    -------
    dict | None
        ipPortfolio : dict — IP별 매출 추정 + HHI
        contentConcentration : dict | None — 주력 IP 의존도
    """
    result: dict = {}

    try:
        ps = company.show("productService")
        if ps is None:
            ps = company.show("segments")
        if ps is not None and hasattr(ps, "to_dicts"):
            rows = ps.to_dicts()
            if not rows:
                return None

            products = []
            total_rev = 0
            for r in rows:
                name = str(r.get("product", r.get("매출유형", "")))
                amt = abs(float(r.get("amount", r.get("매출액", 0)) or 0))
                if amt > 0:
                    products.append({"name": name, "revenue": amt})
                    total_rev += amt

            if products and total_rev > 0:
                for p in products:
                    p["share"] = round(p["revenue"] / total_rev * 100, 1)

                shares = [p["share"] / 100 for p in products]
                hhi = round(sum(s**2 for s in shares) * 10000)

                products.sort(key=lambda x: x["revenue"], reverse=True)
                top1_share = products[0]["share"] if products else 0

                result["ipPortfolio"] = {
                    "products": products[:10],
                    "hhi": hhi,
                    "totalRevenue": total_rev,
                }
                result["contentConcentration"] = {
                    "topIp": products[0]["name"] if products else "",
                    "topShare": top1_share,
                    "hhi": hhi,
                    "verdict": "고집중" if hhi > 4000 else "중집중" if hhi > 2500 else "분���",
                }
    except (AttributeError, ValueError, TypeError, KeyError):
        pass

    return result if result else None
