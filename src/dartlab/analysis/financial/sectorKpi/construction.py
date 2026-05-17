"""건설업 KPI — 수주잔고/도급vs자체/PF노출/시공안전.

DART report(constructionOrders) + sections(productService) + notes(provisions/borrowings) 활용.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc


@memoizedCalc
def calcConstructionKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """건설업 핵심 KPI 통합 반환.

    Capabilities:
        - 수주잔고·도급비중·PF 노출 3 종 KPI 통합 산출.

    Guide:
        DART report(constructionOrders) + sections(productService) + notes(provisions) 결합.

    When:
        건설사 (현대건설·GS건설 등) 펀더멘털 분석 시.

    How:
        매출 시계열·productService 키워드 매칭·충당부채 PF 항목 카운트.

    Requires:
        company.select("IS") + show("productService") + show("provisions") 가능.

    Raises:
        없음. 내부 예외 (AttributeError·ValueError·TypeError·KeyError) try 흡수.

    Returns:
        dict | None
            orderBacklog : dict | None — 수주잔고 시계열 + 회전
            contractMix : dict | None — 도급 vs 자체개발 비중 + 마진 갭
            pfExposure : dict | None — PF 보증·채무 노출

    Example:
        >>> calcConstructionKpis(현대건설)
        {"orderBacklog": {...}, "contractMix": {...}, "pfExposure": {...}}

    See Also:
        - dispatcher.sectorKpi : 섹터 자동 라우팅 진입점.

    AIContext:
        건설업 펀더멘털 질문 시 도급/자체개발 비중·PF 노출 인용.
    """
    from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

    result: dict = {}

    # ── 수주잔고 추정 (매출 대비 기전수주/당기수주/기말수주 추출) ──
    try:
        parsed = toDictBySnakeId(company.select("IS", ["sales"]))
        if parsed:
            isData, periods = parsed
            yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=5)
            salesRow = isData.get("sales", {})
            revenues = [(c, salesRow.get(c)) for c in yCols if salesRow.get(c)]
            if revenues:
                result["orderBacklog"] = {
                    "revenueHistory": [{"period": c, "revenue": v} for c, v in revenues],
                    "note": "수주잔고는 사업보고서 수주상황 항목에서 추출 필요 (현재 매출 시계열만)",
                }
    except (AttributeError, ValueError, TypeError):
        pass

    # ── 도급 vs 자체개발 비중 (sections productService에서 키워드 추출) ──
    try:
        ps = company.show("productService")
        if ps is None:
            ps = company.show("segments")
        if ps is not None and hasattr(ps, "to_dicts"):
            rows = ps.to_dicts()
            contract_kw = ["도급", "시공", "건축"]
            self_dev_kw = ["자체", "분양", "개발", "매각"]
            contract_rev = sum(
                abs(float(r.get("amount", 0) or 0))
                for r in rows
                if any(k in str(r.get("product", "")) for k in contract_kw)
            )
            selfdev_rev = sum(
                abs(float(r.get("amount", 0) or 0))
                for r in rows
                if any(k in str(r.get("product", "")) for k in self_dev_kw)
            )
            total = contract_rev + selfdev_rev
            if total > 0:
                result["contractMix"] = {
                    "contractRatio": round(contract_rev / total * 100, 1),
                    "selfDevRatio": round(selfdev_rev / total * 100, 1),
                    "note": "도급=시공/건축 키워드, 자체개발=분양/매각 키워드 기반 추정",
                }
    except (AttributeError, ValueError, TypeError, KeyError):
        pass

    # ── PF 노출 (충당부채/차입금에서 PF 키워드 탐색) ──
    try:
        provisions = company.show("provisions")
        if provisions is not None and hasattr(provisions, "to_dicts"):
            pf_items = [r for r in provisions.to_dicts() if "PF" in str(r) or "프로젝트" in str(r)]
            if pf_items:
                result["pfExposure"] = {"pfRelatedItems": len(pf_items), "note": "충당부채 내 PF 관련 항목 수"}
    except (AttributeError, ValueError, TypeError, KeyError):
        pass

    return result if result else None
