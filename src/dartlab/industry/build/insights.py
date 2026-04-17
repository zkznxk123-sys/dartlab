"""공급망 인사이트 자동 계산.

각 회사의 공급망 관계에서 HHI(허핀달 지수), 집중도, 공정 다양성 등을 계산.
벤치마크: Interos.ai, Bloomberg SPLC — 공급망 리스크 지표.
"""

from __future__ import annotations

from typing import Any


def calcHHI(supplierAmounts: list[float]) -> float:
    """허핀달-허시만 지수 (공급망 집중도).

    각 공급사의 거래금액 점유율 제곱의 합. 0~10000 (단위: %²).
    - HHI < 1500: 분산 (안전)
    - HHI 1500~2500: 중간 (주의)
    - HHI > 2500: 집중 (고위험)

    Parameters
    ----------
    supplierAmounts : list[float]
        공급사별 거래금액 리스트 (억원).

    Returns
    -------
    float
        HHI 값 (0~10000).
    """
    total = sum(a for a in supplierAmounts if a and a > 0)
    if total == 0:
        return 0.0
    hhi = 0.0
    for a in supplierAmounts:
        if not a or a <= 0:
            continue
        share = (a / total) * 100  # %
        hhi += share * share
    return round(hhi, 0)


def riskLabel(hhi: float) -> str:
    """HHI 값을 위험 라벨로 변환한다.

    Parameters
    ----------
    hhi : float
        허핀달-허시만 지수 (0~10000).

    Returns
    -------
    str
        "데이터 부족" (0) / "분산" (<1500) / "중간" (<2500) / "집중" (>=2500).
    """
    if hhi == 0:
        return "데이터 부족"
    if hhi < 1500:
        return "분산"
    if hhi < 2500:
        return "중간"
    return "집중"


def calcTopNRatio(supplierAmounts: list[float], n: int = 3) -> float:
    """상위 N 공급사가 차지하는 비중을 계산한다.

    amount가 양수인 공급사만 대상. 최대 100%.

    Parameters
    ----------
    supplierAmounts : list[float]
        공급사별 거래금액 리스트 (억원).
    n : int
        상위 몇 개까지 합산할지 (기본 3).

    Returns
    -------
    float
        상위 N사 비중 (%, 0.0~100.0).
    """
    amounts = sorted([a for a in supplierAmounts if a and a > 0], reverse=True)
    total = sum(amounts)
    if total == 0:
        return 0.0
    topN = sum(amounts[:n])
    return round((topN / total) * 100, 1)


def calcSupplyInsights(
    stockCode: str,
    edges: list[Any],
    nodes: list[Any],
) -> dict:
    """한 회사의 공급망 인사이트 종합 계산.

    Parameters
    ----------
    stockCode : str
        대상 회사 코드.
    edges : list
        전체 IndustryEdge 리스트.
    nodes : list
        전체 IndustryNode 리스트.

    Returns
    -------
    dict
        supplierCount : int — 공급사 수 (건)
        customerCount : int — 고객사 수 (건)
        preciseEdgeCount : int — 거래금액 있는 정밀 엣지 수 (건)
        totalSupplyAmount : float — 총 매입금액 (억원)
        hhi : float — 허핀달-허시만 지수 (0~10000)
        hhiRisk : str — 위험 라벨
        top1Ratio : float — 최대 공급사 비중 (%)
        top3Ratio : float — 상위 3사 비중 (%)
        industryDiversity : int — 공급사 소속 산업 수 (개)
        stageDiversity : int — 공급사 소속 공정 수 (개)
        topSupplyIndustries : list[tuple] — 공급 산업 상위 5
        topSupplyStages : list[tuple] — 공급 공정 상위 5
    """
    # 이 회사가 to인 supplier 엣지 (공급받는 관계)
    incoming = [e for e in edges if e.toCode == stockCode and e.edgeType == "supplier"]
    outgoing = [e for e in edges if e.fromCode == stockCode and e.edgeType in ("supplier", "customer")]

    # HHI — 매입액 기준 (amount 있는 것만)
    incomingAmounts = [e.amount for e in incoming if e.amount and e.amount > 0]
    hhi = calcHHI(incomingAmounts)
    top3 = calcTopNRatio(incomingAmounts, n=3)
    top1 = calcTopNRatio(incomingAmounts, n=1)

    # 공정 다양성 (공급사들이 어떤 공정에 속하는지)
    nodeByCode = {n.stockCode: n for n in nodes}
    industrySupply: dict[str, int] = {}
    stageSupply: dict[str, int] = {}
    for e in incoming:
        from_node = nodeByCode.get(e.fromCode)
        if not from_node:
            continue
        industrySupply[from_node.industry] = industrySupply.get(from_node.industry, 0) + 1
        if from_node.stage:
            stageSupply[from_node.stage] = stageSupply.get(from_node.stage, 0) + 1

    # 총 거래금액
    totalAmount = sum(a for a in incomingAmounts)

    # 정밀 엣지 개수 (amount 있는 것)
    preciseCount = sum(1 for e in incoming if e.amount and e.amount > 0)

    return {
        "supplierCount": len(incoming),
        "customerCount": len([e for e in outgoing if e.edgeType == "customer"]),
        "preciseEdgeCount": preciseCount,
        "totalSupplyAmount": totalAmount,  # 억원
        "hhi": hhi,
        "hhiRisk": riskLabel(hhi),
        "top1Ratio": top1,
        "top3Ratio": top3,
        "industryDiversity": len(industrySupply),
        "stageDiversity": len(stageSupply),
        "topSupplyIndustries": sorted(industrySupply.items(), key=lambda x: -x[1])[:5],
        "topSupplyStages": sorted(stageSupply.items(), key=lambda x: -x[1])[:5],
    }


def calcIndustryConcentration(
    industryId: str,
    nodes: list[Any],
) -> dict:
    """산업 내 매출 집중도 지표를 계산한다.

    Parameters
    ----------
    industryId : str
        산업 ID (taxonomy 기준).
    nodes : list[Any]
        전체 IndustryNode 리스트.

    Returns
    -------
    dict
        companyCount : int — 매출 양수 기업 수 (개)
        totalRevenue : float — 산업 총 매출 (억원)
        hhi : float — 매출 기준 HHI (0~10000)
        hhiRisk : str — 위험 라벨
        top3Ratio : float — 상위 3사 매출 비중 (%)
        topN : list[dict] — 상위 5사 정보 (stockCode/corpName/stage/revenue)
    """
    members = [n for n in nodes if n.industry == industryId and n.revenue and n.revenue > 0]
    if not members:
        return {
            "companyCount": 0,
            "totalRevenue": 0,
            "hhi": 0,
            "top3Ratio": 0,
            "topN": [],
        }

    revenues = sorted([n.revenue for n in members], reverse=True)
    totalRev = sum(revenues)
    hhi = calcHHI(revenues)
    top3 = calcTopNRatio(revenues, n=3)

    # 상위 5사
    sortedMembers = sorted(members, key=lambda n: n.revenue or 0, reverse=True)
    topN = [
        {"stockCode": n.stockCode, "corpName": n.corpName, "stage": n.stage, "revenue": n.revenue}
        for n in sortedMembers[:5]
    ]

    return {
        "companyCount": len(members),
        "totalRevenue": totalRev,
        "hhi": hhi,
        "hhiRisk": riskLabel(hhi),
        "top3Ratio": top3,
        "topN": topN,
    }
