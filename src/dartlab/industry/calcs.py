"""review 블록용 calc 함수 — 산업 내 위치.

nodes.json에서 조회. Company-bound.
"""

from __future__ import annotations

from typing import Any


def calcChainPosition(company: Any) -> dict | None:
    """이 회사의 산업 내 위치.

    Returns
    -------
    dict | None
        industry : str — 산업 ID
        industryName : str — 산업명
        stage : str — 공정 단계 key
        stageName : str — 공정명
        role : str — 역할 (제조/도매/소매/연구/서비스)
        stream : str — 위치 (upstream/midstream/downstream)
        confidence : float — 신뢰도
        source : str — 소스
        peers : list[dict] — 같은 공정의 다른 회사
    """
    from dartlab.industry.build.pipeline import loadNodes
    from dartlab.industry.taxonomy import getIndustry

    stockCode = getattr(company, "stockCode", "")
    if not stockCode:
        return None

    nodes = loadNodes()

    # 해당 종목의 primary 노드 찾기
    myNode = None
    for n in nodes:
        if n.stockCode == stockCode and n.primary:
            myNode = n
            break

    if myNode is None or not myNode.stage:
        return None

    ind = getIndustry(myNode.industry)
    if ind is None:
        return None

    stageInfo = ind.stageByKey(myNode.stage)

    # 같은 공정 peer
    peers = [
        {"stockCode": n.stockCode, "corpName": n.corpName, "confidence": n.confidence}
        for n in nodes
        if n.industry == myNode.industry
        and n.stage == myNode.stage
        and n.stockCode != stockCode
    ]
    peers.sort(key=lambda p: p["confidence"], reverse=True)

    return {
        "industry": myNode.industry,
        "industryName": ind.name,
        "stage": myNode.stage,
        "stageName": stageInfo.name if stageInfo else myNode.stage,
        "role": myNode.role,
        "stream": myNode.stream,
        "confidence": myNode.confidence,
        "source": myNode.source,
        "peers": peers[:10],
    }
