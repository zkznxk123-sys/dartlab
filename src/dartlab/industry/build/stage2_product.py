"""2단계: KindList 주요제품 → 공정 중분류.

주요제품 텍스트를 토큰화하고, taxonomy 키워드와 매칭하여
각 회사가 산업 내 어떤 공정(stage)에 위치하는지 분류한다.
"""

from __future__ import annotations

import re

from dartlab.industry.taxonomy import matchStageByKeywords
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

    Capabilities:
        1 단계 결과 (산업만 채워짐) + KindList 주요제품 텍스트를 매칭해 stage 키 (예: memory /
        equipment) 를 채움. ``matchStageByKeywords`` 의 키워드 매칭 결과를 반영, confidence 도
        함께 채움.

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

    Raises:
        없음 — 주요제품 빈 종목은 stage 미채움.

    Example:
        >>> from dartlab.industry.build.stage2_product import classify
        >>> nodes = classify(stage1Nodes, kindList)
        >>> sum(1 for n in nodes if n.stage)
        2800

    Guide:
        ``stage3_docs.enrich`` 가 본 단계 confidence 낮은 종목을 docs 본문으로 추가 보정.
        본 단계만으로 매칭 안 되는 종목 다수 — docs / override 동행 필수.

    When:
        manifest 빌드 2 단계.

    How:
        KindList 의 (종목코드 → 주요제품) 매핑 구성 → nodes 루프 →
        ``taxonomy.matchStageByKeywords(node.industry, productText)`` 호출 → 결과 stage/conf
        채움.

    Requires:
        - 입력 nodes 의 industry 필드 (stage1_ksic 결과)
        - KindList 의 주요제품 컬럼

    See Also:
        - ``dartlab.industry.taxonomy.matchStageByKeywords`` : 본 함수의 매칭 코어
        - ``dartlab.industry.build.stage3_docs.enrich`` : docs 본문 보강 3 단계

    AIContext:
        AI 가 직접 호출하지 않는다 (배치). 답변에서 ``source=="product"`` 노드는 "주요제품 키워드
        매칭" 단서 인용.
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
            node.industry,
            productText,
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
