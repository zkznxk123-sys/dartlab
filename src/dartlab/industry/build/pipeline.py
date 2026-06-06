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
    # F4.1: gather 직접 호출 → IndustryDataAccessor 위임 (정공법 B+C)
    from dartlab.core.di import getIndustryAccessor

    df = getIndustryAccessor().fetchListing()
    if df is None:
        return []
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

    Capabilities:
        KSIC → 제품 → docs → review 4 단계 + 재무 attach + 엣지 빌드를 1 회 실행. 결과는
        ``data/industry/{nodes,edges}.json`` 으로 직렬화. 전 종목 산업/공정/매출 manifest 생성.

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

    Raises:
        없음 — 개별 stage 실패 시 부분 결과로 진행.

    Example:
        >>> from dartlab.industry.build.pipeline import buildIndustryMap
        >>> nodes = buildIndustryMap(skipDocs=False, verbose=True)
        >>> sum(1 for n in nodes if n.stage)
        2800

    Guide:
        ``Industry().build()`` 의 위임 대상. 전 종목 panel parquet 스캔 + finance.parquet 로드로
        비용이 큼 — 일반 사용자 호출 금지.

    When:
        manifest stale 시 (재무 / KindList 갱신 후) 만. 일반 사용자는 ``Industry()(code)`` 조회.

    How:
        stage1_ksic.classify → stage2_product.classify → stage3_docs.enrich (선택) →
        stage4_review.applyOverrides → attachFinancials → buildAllEdges → _saveNodes / _saveEdges.

    Requires:
        - L1 raw: DART KindList + 사업보고서 + 재무 1+ 연도
        - L1.5 frame: scan/finance.parquet + docs/{code}.parquet

    See Also:
        - ``dartlab.industry.Industry.build`` : 본 함수 사용자 (사용자 친화 진입점)
        - ``dartlab.industry.build.stage1_ksic.classify`` : 1 단계
        - ``dartlab.industry.build.edges.buildAllEdges`` : 엣지 단계

    AIContext:
        AI 가 직접 호출하지 않는다 (배치). manifest 가 stale 일 가능성 (``updatedAt`` 필드 확인)
        만 답변에 단서로 명시.
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

    Raises:
        없음 — 파일 부재 / JSON 손상 모두 빈 리스트 반환.

    Example:
        >>> from dartlab.industry.build.pipeline import loadNodes
        >>> nodes = loadNodes()
        >>> nodes[0].stockCode, nodes[0].industry
        ('005930', 'semiconductor')

    Requires:
        - ``data/industry/nodes.json`` manifest (``buildIndustryMap()`` 이후 산출).
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

    Raises:
        없음 — 파일 부재 / JSON 손상 모두 빈 리스트 반환.

    Example:
        >>> from dartlab.industry.build.pipeline import loadEdges
        >>> edges = loadEdges()
        >>> edges[0].fromCode, edges[0].toCode, edges[0].edgeType
        ('006400', '005930', 'supplier')

    Requires:
        - ``data/industry/edges.json`` manifest (``buildIndustryMap()`` 이후 산출).
    """
    if not _EDGES_FILE.exists():
        return []
    try:
        data = json.loads(_EDGES_FILE.read_text(encoding="utf-8"))
        return [IndustryEdge.fromDict(d) for d in data]
    except (json.JSONDecodeError, OSError):
        return []
