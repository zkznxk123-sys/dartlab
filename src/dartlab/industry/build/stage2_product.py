"""2단계: KindList 주요제품 → 공정 중분류.

주요제품 텍스트를 토큰화하고, taxonomy 키워드와 매칭하여
각 회사가 산업 내 어떤 공정(stage)에 위치하는지 분류한다.
"""

from __future__ import annotations

import re

from dartlab.industry.taxonomy import loadTaxonomy, matchStageByKeywords
from dartlab.industry.types import IndustryNode


def _tokenizeProducts(text: str) -> list[str]:
    """주요제품 텍스트를 토큰으로 분리.

    "DRAM,NAND Flash,시스템LSI" → ["DRAM", "NAND Flash", "시스템LSI"]
    """
    if not text:
        return []
    tokens = re.split(r"[,;·/\n]", text)
    return [t.strip() for t in tokens if t.strip()]


def classify(
    nodes: list[IndustryNode],
    kindList: list[dict],
) -> list[IndustryNode]:
    """주요제품으로 공정 중분류를 수행한다.

    Parameters
    ----------
    nodes : list[IndustryNode]
        1단계 결과 (industry만 채워진 상태).
    kindList : list[dict]
        getKindList() dict 리스트. "종목코드", "주요제품" 키 필요.

    Returns
    -------
    list[IndustryNode]
        stage가 채워진 노드 리스트.
    """
    productMap: dict[str, str] = {}
    for row in kindList:
        code = row.get("종목코드", "")
        product = row.get("주요제품", "")
        if code and product:
            productMap[code] = product

    result: list[IndustryNode] = []
    for node in nodes:
        productText = productMap.get(node.stockCode, "")
        if not productText:
            result.append(node)
            continue

        stageKey, confidence, hitKws = matchStageByKeywords(
            node.industry, productText,
        )
        if stageKey and confidence > 0:
            # taxonomy에서 role/stream 가져오기
            from dartlab.industry.taxonomy import getIndustry

            ind = getIndustry(node.industry)
            stageInfo = ind.stageByKey(stageKey) if ind else None

            node.stage = stageKey
            node.role = stageInfo.role if stageInfo else ""
            node.stream = stageInfo.stream if stageInfo else ""
            node.confidence = max(node.confidence, confidence)
            node.source = "product"

        result.append(node)

    return result
