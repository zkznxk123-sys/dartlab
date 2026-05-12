"""3단계: docs 텍스트 → 소분류 (공정/역할 보강).

docs parquet의 businessOverview, productService, rawMaterial 텍스트를 스캔하여
2단계 결과의 stage를 보강하거나 신뢰도를 갱신한다.

Company 객체를 로드하지 않고 parquet을 직접 LazyFrame으로 스캔한다 (메모리 안전).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import polars as pl

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


def _docsDir() -> Path:
    """docs parquet 디렉토리."""
    from dartlab.frame.dataConfig import DATA_RELEASES
    from dartlab.frame.dataLoader import _getDataRoot

    return _getDataRoot() / DATA_RELEASES["docs"]["dir"]


def _extractTexts(parquetPath: Path) -> dict[str, str]:
    """하나의 docs parquet에서 산업 관련 텍스트를 추출."""
    try:
        df = (
            pl.scan_parquet(str(parquetPath))
            .select(["section_title", "section_content"])
            .filter(pl.col("section_content").is_not_null())
            .filter(pl.col("section_content").str.len_chars() > 20)
            .collect(engine="streaming")
        )
    except (pl.exceptions.PolarsError, OSError, FileNotFoundError):
        return {}

    topicTexts: dict[str, list[str]] = {}
    for row in df.iter_rows(named=True):
        title = row.get("section_title") or ""
        content = row.get("section_content") or ""
        for pattern, topic in _TITLE_PATTERNS:
            if pattern.search(title):
                topicTexts.setdefault(topic, []).append(content)
                break

    return {topic: "\n".join(texts) for topic, texts in topicTexts.items()}


def enrich(nodes: list[IndustryNode]) -> list[IndustryNode]:
    """docs 텍스트로 노드의 stage/confidence를 보강한다.

    Parameters
    ----------
    nodes : list[IndustryNode]
        2단계까지 처리된 노드 리스트.

    Returns
    -------
    list[IndustryNode]
        docs 분석으로 보강된 노드 리스트.
    """
    docsDir = _docsDir()
    if not docsDir.exists():
        logger.warning("docs 디렉토리 없음: %s", docsDir)
        return nodes

    # 종목코드별 노드 인덱스
    nodeMap: dict[str, list[IndustryNode]] = {}
    for node in nodes:
        nodeMap.setdefault(node.stockCode, []).append(node)

    for code, codeNodes in nodeMap.items():
        pqPath = docsDir / f"{code}.parquet"
        if not pqPath.exists():
            continue

        texts = _extractTexts(pqPath)
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
