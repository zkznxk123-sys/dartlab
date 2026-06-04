"""3단계: docs 텍스트 → 소분류 (공정/역할 보강).

docs parquet의 businessOverview, productService, rawMaterial 텍스트를 스캔하여
2단계 결과의 stage를 보강하거나 신뢰도를 갱신한다.

Company 객체를 로드하지 않고 parquet을 직접 LazyFrame으로 스캔한다 (메모리 안전).
"""

from __future__ import annotations

import logging
import re

from dartlab.industry.taxonomy import getIndustry, matchStageByKeywords
from dartlab.industry.types import IndustryNode

logger = logging.getLogger(__name__)

# section_title → topic 매핑 패턴
_TITLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"사업의\s*개요|사업\s*내용|사업개요|주요\s*사업"), "businessOverview"),
    (re.compile(r"매출.*구성|주요.*제품|제품.*서비스|매출.*비중"), "productService"),
    (re.compile(r"원재료|원자재|부자재"), "rawMaterial"),
]

# topic별 가중치 (산업 정보 밀도)
_TOPIC_WEIGHT: dict[str, float] = {
    "businessOverview": 1.0,
    "productService": 1.2,
    "rawMaterial": 0.8,
}


def _extractTexts(code: str) -> dict[str, str]:
    """한 종목 panel 섹션 본문에서 산업 관련 텍스트를 추출 (L1.5 frame SSOT 경유)."""
    from dartlab.frame.sections import sectionTexts

    df = sectionTexts(code)
    if df is None or df.is_empty():
        return {}

    topicTexts: dict[str, list[str]] = {}
    for row in df.iter_rows(named=True):
        title = row.get("sectionLeaf") or ""
        content = row.get("contentRaw") or ""
        if not content or len(content) <= 20:
            continue
        for pattern, topic in _TITLE_PATTERNS:
            if pattern.search(title):
                topicTexts.setdefault(topic, []).append(content)
                break

    return {topic: "\n".join(texts) for topic, texts in topicTexts.items()}


def enrich(nodes: list[IndustryNode]) -> list[IndustryNode]:
    """docs 텍스트로 노드의 stage/confidence를 보강한다.

    Capabilities:
        2 단계까지 채워진 노드 중 stage 가 비어있거나 confidence 가 낮은 종목에 대해 ``docs/
        {code}.parquet`` 본문 (사업의 내용 / 원재료 등 토픽별 가중 합성) 으로 stage 재매칭.
        보강 시 ``source="docs"`` 마킹.

    Parameters
    ----------
    nodes : list[IndustryNode]
        2단계까지 처리된 노드 리스트.

    Returns
    -------
    list[IndustryNode]
        docs 분석으로 보강된 노드 리스트.

    Raises:
        없음 — docs 폴더 부재 시 warning + 입력 그대로 반환.

    Example:
        >>> from dartlab.industry.build.stage3_docs import enrich
        >>> nodes = enrich(stage2Nodes)
        >>> sum(1 for n in nodes if n.source == "docs")
        720

    Guide:
        ``buildIndustryMap`` 의 3 단계. docs parquet 전 종목 스캔이라 비용이 큼 — ``skipDocs=True``
        로 단계 건너뛰기 가능 (빠른 테스트).

    When:
        manifest 빌드 3 단계. KindList 주요제품 만으로 stage 매칭 안 되는 종목 보강 시.

    How:
        nodes 인덱스 (종목별) → 종목별 ``docs/{code}.parquet`` 토픽 스캔 → 합성 텍스트 →
        ``matchStageByKeywords`` → 결과 stage/conf 으로 노드 업데이트.

    Requires:
        - L1.5 frame: docs parquet 폴더
        - 입력 nodes (stage1+2 결과)

    See Also:
        - ``dartlab.industry.taxonomy.matchStageByKeywords`` : 매칭 코어
        - ``dartlab.industry.build.stage4_review.applyOverrides`` : 4 단계 보정

    AIContext:
        AI 가 직접 호출하지 않는다 (배치). 답변에서 ``source=="docs"`` 노드는 "사업보고서 본문
        분석 결과" 단서 인용.
    """
    # 종목코드별 노드 인덱스
    nodeMap: dict[str, list[IndustryNode]] = {}
    for node in nodes:
        nodeMap.setdefault(node.stockCode, []).append(node)

    for code, codeNodes in nodeMap.items():
        texts = _extractTexts(code)
        if not texts:
            continue

        # 전체 텍스트를 합산 (가중치 적용)
        combinedText = ""
        for topic, text in texts.items():
            weight = _TOPIC_WEIGHT.get(topic, 0.5)
            combinedText += text * (1 if weight <= 1.0 else 2) + "\n"

        for node in codeNodes:
            stageKey, confidence, hitKws = matchStageByKeywords(
                node.industry,
                combinedText,
            )

            if stageKey and confidence > 0:
                # docs 결과가 기존보다 신뢰도 높으면 갱신
                if confidence > node.confidence or not node.stage:
                    ind = getIndustry(node.industry)
                    stageInfo = ind.stageByKey(stageKey) if ind else None
                    node.stage = stageKey
                    node.role = stageInfo.role if stageInfo else node.role
                    node.stream = stageInfo.stream if stageInfo else node.stream
                    node.confidence = confidence
                    node.source = "docs"

    return nodes
