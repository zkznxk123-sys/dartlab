"""4단계 빌드 오케스트레이터.

taxonomy.json + KindList + docs → nodes.json + edges.json 생성.

사용법::

    from dartlab.industry.build.pipeline import buildIndustryMap
    buildIndustryMap()
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from dartlab.industry.types import IndustryEdge, IndustryNode

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1]
_NODES_FILE = _DATA_DIR / "nodes.json"
_EDGES_FILE = _DATA_DIR / "edges.json"


def _getKindListDicts() -> list[dict]:
    """KindList를 dict 리스트로 변환."""
    from dartlab.gather.listing import getKindList

    df = getKindList()
    return df.to_dicts()


def _saveNodes(nodes: list[IndustryNode]) -> Path:
    """nodes.json에 저장."""
    data = [n.toDict() for n in nodes]
    _NODES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("nodes.json 저장: %d건", len(data))
    return _NODES_FILE


def _saveEdges(edges: list[IndustryEdge]) -> Path:
    """edges.json에 저장."""
    data = [e.toDict() for e in edges]
    _EDGES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("edges.json 저장: %d건", len(data))
    return _EDGES_FILE


def buildIndustryMap(
    *,
    skipDocs: bool = False,
    verbose: bool = True,
) -> list[IndustryNode]:
    """4단계 파이프라인을 실행하여 nodes.json을 생성한다.

    Parameters
    ----------
    skipDocs : bool
        True이면 3단계(docs 스캔) 생략. 빠른 테스트용.
    verbose : bool
        진행 상황 출력.

    Returns
    -------
    list[IndustryNode]
        빌드된 전종목 노드 리스트.
    """
    from dartlab.industry.build.stage1_ksic import classify as stage1
    from dartlab.industry.build.stage2_product import classify as stage2
    from dartlab.industry.build.stage3_docs import enrich as stage3
    from dartlab.industry.build.stage4_review import applyOverrides as stage4

    today = date.today().isoformat()

    # KindList 로드
    kindList = _getKindListDicts()
    if verbose:
        print(f"[industry] KindList: {len(kindList)}사")

    # 1단계: KSIC → 대분류
    nodes = stage1(kindList)
    if verbose:
        print(f"[industry] 1단계 KSIC: {len(nodes)}사 분류")

    # 2단계: 주요제품 → 중분류
    nodes = stage2(nodes, kindList)
    staged = sum(1 for n in nodes if n.stage)
    if verbose:
        print(f"[industry] 2단계 제품: {staged}사 공정 매칭")

    # 3단계: docs → 소분류
    if not skipDocs:
        nodes = stage3(nodes)
        docsStaged = sum(1 for n in nodes if n.source == "docs")
        if verbose:
            print(f"[industry] 3단계 docs: {docsStaged}사 보강")

    # 4단계: override 적용
    nodes = stage4(nodes)
    manualCount = sum(1 for n in nodes if n.source == "manual")
    if verbose:
        print(f"[industry] 4단계 override: {manualCount}건 적용")

    # updatedAt 일괄 설정
    for n in nodes:
        n.updatedAt = today

    # 엣지 빌드
    from dartlab.industry.build.edges import buildAllEdges

    edges = buildAllEdges(nodes, skipDocs=skipDocs)
    if verbose:
        print(f"[industry] 엣지: {len(edges)}건 (network + docs)")

    # 저장
    _saveNodes(nodes)
    _saveEdges(edges)

    if verbose:
        total = len(nodes)
        withStage = sum(1 for n in nodes if n.stage)
        print(
            f"[industry] 완료: {total}사, {withStage}사 공정 매칭 ({withStage / total * 100:.0f}%), {len(edges)} 엣지"
        )

    return nodes


def loadNodes() -> list[IndustryNode]:
    """nodes.json 로드."""
    if not _NODES_FILE.exists():
        return []
    try:
        data = json.loads(_NODES_FILE.read_text(encoding="utf-8"))
        return [IndustryNode.fromDict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []


def loadEdges() -> list[IndustryEdge]:
    """edges.json 로드."""
    if not _EDGES_FILE.exists():
        return []
    try:
        data = json.loads(_EDGES_FILE.read_text(encoding="utf-8"))
        return [IndustryEdge.fromDict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []
