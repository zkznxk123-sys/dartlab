"""2-hop 공급망 사전 계산.

각 회사에 대해:
- 1-hop 이웃 (egograph)은 enrichCompany 가 이미 저장
- **2-hop**: 1-hop 이웃의 추가 이웃 (A → B → C 경로의 C)

허브 노드(degree > 200) 처리:
- 전체 저장하면 수천 엣지 폭증 → 파일 크기 폭증
- 허브는 **1.5-hop 만** 저장 (자기 1-hop + 1-hop 이웃 중 amount 있는 상위 거래만)
- 일반 노드는 2-hop 전체

Returns
-------
dict[stockCode → {hop2Neighbors, hop2Edges, hub}]
- hop2Neighbors: [{stockCode, corpName, industry, viaCode, viaName, hopDistance}]
- hop2Edges: 2-hop 경로 상 핵심 엣지 (amount 우선 Top 50)
- hub: bool
"""

from __future__ import annotations

import logging

from dartlab.industry.build.pipeline import loadEdges, loadNodes

logger = logging.getLogger(__name__)

HUB_THRESHOLD = 200
HOP2_EDGE_LIMIT = 50  # 회사당 2-hop 엣지 최대


def computeHop2() -> dict[str, dict]:
    """전 종목 2-hop 공급망 사전 계산 — "내 공급사의 공급사" 를 미리 찾아둔다.

    nodes.json + edges.json 에서 인접 리스트를 구성하고, 각 회사별로
    1-hop 이웃의 이웃(2-hop)을 탐색한다. 허브 노드(degree > 200)는
    amount 있는 거래의 상대만 1단계 더 확장(1.5-hop)하여 폭증을 방지한다.

    Parameters
    ----------
    없음 — 내부적으로 loadNodes(), loadEdges() 호출.

    Returns
    -------
    dict[str, dict]
        stockCode → {
            hop2Neighbors : list[dict]
                stockCode : str — 2-hop 이웃 종목코드
                corpName : str — 회사명
                industry : str — 산업 ID
                viaCode : str — 경유 노드 종목코드
                viaName : str — 경유 노드 회사명
                hopDistance : int — 항상 2
            hop2Edges : list[dict]
                from : str — 출발 종목코드
                to : str — 도착 종목코드
                type : str — 엣지 타입 (supplier/customer/affiliate)
                amount : float | None — 거래 금액 (억원)
                ratio : float | None — 매입비중 (%)
                product : str — 거래 품목
                hop : int — 1 또는 2
                source : str — 데이터 소스
            hub : bool — 허브 노드 여부 (degree > HUB_THRESHOLD)
            direct1HopCount : int — 직접 이웃 수

    Notes
    -----
    - 허브 임계값: HUB_THRESHOLD = 200 (degree 초과 시 1.5-hop 제한)
    - hop2Neighbors 최대 100개, hop2Edges 최대 HOP2_EDGE_LIMIT(50)개
    - amount 기준 내림차순 정렬
    - 허브의 1.5-hop: amount 있는 1-hop 엣지 상대의 이웃만 확장 (최대 100)

    Examples
    --------
    >>> from dartlab.industry.build.hop2 import computeHop2
    >>> hop2 = computeHop2()
    >>> hop2['005930']['hub']  # 삼성전자가 허브인지
    False
    >>> len(hop2['005930']['hop2Neighbors'])  # 2-hop 이웃 수
    100
    """
    nodes = loadNodes()
    edges = loadEdges()

    nodeByCode = {n.stockCode: n for n in nodes}

    # 인접 리스트: stockCode → set(neighbor stockCode)
    adj: dict[str, set[str]] = {}
    # 엣지 상세: (a, b) → [edge list] (원래 정보 유지)
    edgeDetail: dict[tuple[str, str], list] = {}

    for e in edges:
        if not e.fromCode or not e.toCode:
            continue
        adj.setdefault(e.fromCode, set()).add(e.toCode)
        adj.setdefault(e.toCode, set()).add(e.fromCode)
        key = tuple(sorted([e.fromCode, e.toCode]))
        edgeDetail.setdefault(key, []).append(e)

    # Degree 계산 → 허브 식별
    degree = {code: len(neighbors) for code, neighbors in adj.items()}
    hubs = {code for code, d in degree.items() if d > HUB_THRESHOLD}
    logger.info(f"Hub nodes (degree > {HUB_THRESHOLD}): {len(hubs)}")

    out: dict[str, dict] = {}
    for code in adj.keys():
        isHub = code in hubs
        direct = adj.get(code, set())
        hop2_set: set[str] = set()
        hop2_via: dict[str, str] = {}  # 2-hop 노드 → 경유 노드

        if not isHub:
            # 일반 노드: 전체 2-hop 계산
            for mid in direct:
                for far in adj.get(mid, set()):
                    if far == code or far in direct:
                        continue
                    if far not in hop2_set:
                        hop2_set.add(far)
                        hop2_via[far] = mid
        else:
            # 허브(degree > 200): 전체 2-hop 은 수천 노드 폭증 → 제한적 확장
            # amount 있는 1-hop 엣지의 상대만 1단계 더 확장 (1.5-hop)
            for mid in direct:
                mid_key = tuple(sorted([code, mid]))
                mid_edges = edgeDetail.get(mid_key, [])
                has_amount = any(e.amount for e in mid_edges)
                if not has_amount:
                    continue
                for far in adj.get(mid, set()):
                    if far == code or far in direct:
                        continue
                    if far not in hop2_set and len(hop2_set) < 100:
                        hop2_set.add(far)
                        hop2_via[far] = mid

        hop2_neighbors = []
        for far_code in list(hop2_set)[:200]:
            far_node = nodeByCode.get(far_code)
            via_node = nodeByCode.get(hop2_via[far_code])
            if not far_node:
                continue
            hop2_neighbors.append(
                {
                    "stockCode": far_code,
                    "corpName": far_node.corpName,
                    "industry": far_node.industry,
                    "viaCode": hop2_via[far_code],
                    "viaName": via_node.corpName if via_node else "",
                    "hopDistance": 2,
                }
            )

        # 핵심 엣지: 이 회사에서 2 hop 경로에 있는 amount 있는 엣지 상위
        # 단순화: 1-hop 엣지 중 amount 있는 Top N + 그 이웃의 또다른 amount 엣지 Top
        edge_candidates = []
        for partner in direct:
            key = tuple(sorted([code, partner]))
            for e in edgeDetail.get(key, []):
                if e.amount:
                    edge_candidates.append(
                        {
                            "from": e.fromCode,
                            "to": e.toCode,
                            "type": e.edgeType,
                            "amount": e.amount,
                            "ratio": e.ratio,
                            "product": e.product,
                            "hop": 1,
                            "source": e.source,
                        }
                    )
        edge_candidates.sort(key=lambda x: x["amount"] or 0, reverse=True)

        if not isHub:
            # 일반 노드: 1-hop 이웃의 amount 엣지도 수집 (2-hop 경로)
            for partner in direct:
                for grand in adj.get(partner, set()):
                    if grand == code or grand in direct:
                        continue
                    key = tuple(sorted([partner, grand]))
                    for e in edgeDetail.get(key, []):
                        if e.amount:
                            edge_candidates.append(
                                {
                                    "from": e.fromCode,
                                    "to": e.toCode,
                                    "type": e.edgeType,
                                    "amount": e.amount,
                                    "ratio": e.ratio,
                                    "product": e.product,
                                    "hop": 2,
                                    "source": e.source,
                                }
                            )
            edge_candidates.sort(key=lambda x: x["amount"] or 0, reverse=True)

        out[code] = {
            "hop2Neighbors": hop2_neighbors[:100],
            "hop2Edges": edge_candidates[:HOP2_EDGE_LIMIT],
            "hub": isHub,
            "direct1HopCount": len(direct),
        }

    return out
