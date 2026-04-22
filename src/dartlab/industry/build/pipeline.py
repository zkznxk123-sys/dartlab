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
    """KindList DataFrame을 dict 리스트로 변환한다.

    Returns
    -------
    list[dict]
        종목코드/회사명/업종 등 KindList 컬럼을 포함하는 행별 딕셔너리.
    """
    from dartlab.gather.listing import getKindList

    df = getKindList()
    return df.to_dicts()


def _saveNodes(nodes: list[IndustryNode]) -> Path:
    """노드 리스트를 nodes.json으로 직렬화하여 저장한다.

    Parameters
    ----------
    nodes : list[IndustryNode]
        저장할 노드 리스트.

    Returns
    -------
    Path
        저장된 nodes.json 파일 경로.
    """
    data = [n.toDict() for n in nodes]
    _NODES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("nodes.json 저장: %d건", len(data))
    return _NODES_FILE


def _saveEdges(edges: list[IndustryEdge]) -> Path:
    """엣지 리스트를 edges.json으로 직렬화하여 저장한다.

    Parameters
    ----------
    edges : list[IndustryEdge]
        저장할 엣지 리스트.

    Returns
    -------
    Path
        저장된 edges.json 파일 경로.
    """
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
        logger.info(f"[industry] KindList: {len(kindList)}사")

    # 1단계: KSIC → 대분류
    nodes = stage1(kindList)
    if verbose:
        logger.info(f"[industry] 1단계 KSIC: {len(nodes)}사 분류")

    # 2단계: 주요제품 → 중분류
    nodes = stage2(nodes, kindList)
    staged = sum(1 for n in nodes if n.stage)
    if verbose:
        logger.info(f"[industry] 2단계 제품: {staged}사 공정 매칭")

    # 3단계: docs → 소분류
    if not skipDocs:
        nodes = stage3(nodes)
        docsStaged = sum(1 for n in nodes if n.source == "docs")
        if verbose:
            logger.info(f"[industry] 3단계 docs: {docsStaged}사 보강")

    # 4단계: override 적용
    nodes = stage4(nodes)
    manualCount = sum(1 for n in nodes if n.source == "manual")
    if verbose:
        logger.info(f"[industry] 4단계 override: {manualCount}건 적용")

    # updatedAt 일괄 설정
    for n in nodes:
        n.updatedAt = today

    # 재무 데이터 join (revenue → nodes)
    from dartlab.industry.build.financials import attachFinancials

    nodes = attachFinancials(nodes)
    revCount = sum(1 for n in nodes if n.revenue)
    if verbose:
        logger.info(f"[industry] 재무: {revCount}사 매출 데이터 join")

    # 엣지 빌드
    from dartlab.industry.build.edges import buildAllEdges

    edges = buildAllEdges(nodes, skipDocs=skipDocs)
    if verbose:
        logger.info(f"[industry] 엣지: {len(edges)}건 (network + docs)")

    # 저장
    _saveNodes(nodes)
    _saveEdges(edges)

    if verbose:
        total = len(nodes)
        withStage = sum(1 for n in nodes if n.stage)
        logger.info(
            "[industry] 완료: %d사, %d사 공정 매칭 (%.0f%%), %d 엣지",
            total,
            withStage,
            withStage / total * 100,
            len(edges),
        )

    return nodes


def loadNodes() -> list[IndustryNode]:
    """nodes.json을 읽어 IndustryNode 리스트로 역직렬화한다.

    Returns
    -------
    list[IndustryNode]
        로드된 노드 리스트. 파일 없거나 파싱 실패 시 빈 리스트.
    """
    if not _NODES_FILE.exists():
        return []
    try:
        data = json.loads(_NODES_FILE.read_text(encoding="utf-8"))
        return [IndustryNode.fromDict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []


def loadEdges() -> list[IndustryEdge]:
    """edges.json을 읽어 IndustryEdge 리스트로 역직렬화한다.

    Returns
    -------
    list[IndustryEdge]
        로드된 엣지 리스트. 파일 없거나 파싱 실패 시 빈 리스트.
    """
    if not _EDGES_FILE.exists():
        return []
    try:
        data = json.loads(_EDGES_FILE.read_text(encoding="utf-8"))
        return [IndustryEdge.fromDict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []
