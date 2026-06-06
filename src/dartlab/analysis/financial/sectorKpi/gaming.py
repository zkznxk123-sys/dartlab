"""게임·엔터 KPI — IP 포트폴리오/콘텐츠 집중도/매출 구성.

DART panel(productService) + IS 활용.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc


@memoizedCalc
def calcGamingKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """게임·엔터 핵심 KPI.

    Capabilities:
        - productService 매출 분해 → IP 포트폴리오 HHI + 1위 IP 의존도.

    Guide:
        rows → 매출액 추출 → share 계산 → HHI · top1 share.

    When:
        넥슨/엔씨/카카오게임즈 등 IP 비즈니스 평가 시.

    How:
        제품별 매출 share → 제곱합×10000 = HHI. >4000 고집중, >2500 중집중, 이하 분산.

    Requires:
        company.panel("productService") 또는 panel("segments") rows 존재.

    Raises:
        없음. AttributeError·ValueError·TypeError·KeyError try 흡수.

    Returns:
        dict | None
            ipPortfolio : dict — IP별 매출 추정 + HHI
            contentConcentration : dict | None — 주력 IP 의존도

    Example:
        >>> calcGamingKpis(엔씨소프트)
        {"ipPortfolio": {...}, "contentConcentration": {...}}

    See Also:
        - dispatcher.sectorKpi : 섹터 자동 라우팅.

    AIContext:
        IP 집중 위험 (단일 IP 매출 의존) 평가 인용.
    """
    result: dict = {}

    try:
        import polars as pl

        from dartlab.providers.dart.panel.text import panelTableRows

        code = getattr(company, "stockCode", None)
        _r = (
            (panelTableRows(code, sectionPattern="제품") or panelTableRows(code, sectionPattern="부문")) if code else []
        )
        ps = pl.DataFrame(_r) if _r else None
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
                    "verdict": "고집중" if hhi > 4000 else "중집중" if hhi > 2500 else "분산",
                }
    except (AttributeError, ValueError, TypeError, KeyError):
        pass

    return result if result else None
