"""그래프 스키마 — 노드/엣지 타입 + CompanyGraph 자료구조.

외부 의존성 0 — dict-of-dicts (NetworkX 불필요).
메모리 < 50MB 목표 (Company 500MB 위에 얇은 레이어).

6 노드 타입:
    METRIC    — 재무 지표 (영업이익률, ROE, 부채비율 등)
    ACCOUNT   — 계정 (매출액, 영업이익 등)
    SEGMENT   — 사업부/부문
    PERIOD    — 기간 (2024, 2024Q4 등)
    EVENT     — 이벤트 (사이클 정점, 배당 증가 등)
    MACRO     — 매크로 지표 (금리, 환율 등)

5 엣지 타입:
    CAUSES      — A가 B의 원인 (마진 하락 → 이익 감소)
    PART_OF     — A가 B의 구성 요소 (DX부문 → 매출)
    DERIVED     — A에서 B가 계산됨 (매출-원가 → 영업이익)
    COMPARES_TO — 같은 레벨 비교 (동종업계 평균 vs 나)
    ANOMALY     — 이상치 신호 (Z-Score < 1.8, 발생액 비정상)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """6 노드 타입 — METRIC/ACCOUNT/SEGMENT/PERIOD/EVENT/MACRO."""

    METRIC = "metric"
    ACCOUNT = "account"
    SEGMENT = "segment"
    PERIOD = "period"
    EVENT = "event"
    MACRO = "macro"


class EdgeType(str, Enum):
    """5 엣지 타입 — CAUSES/PART_OF/DERIVED/COMPARES_TO/ANOMALY."""

    CAUSES = "causes"
    PART_OF = "partOf"
    DERIVED = "derived"
    COMPARES_TO = "comparesTo"
    ANOMALY = "anomaly"


@dataclass(frozen=True)
class Node:
    """그래프 노드 — id + type + label + (value/period/unit/meta)."""

    id: str  # unique — "metric:영업이익률:2024" 형태
    type: NodeType
    label: str  # 사람이 읽는 이름
    value: Any = None  # 수치 또는 문자열
    period: str = ""  # 기간
    unit: str = ""  # %, 조원, 배 등
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """그래프 엣지 — source/target + type + (weight/label)."""

    source: str  # node id
    target: str  # node id
    type: EdgeType
    weight: float = 1.0  # 연결 강도 (정규화 가능)
    label: str = ""  # "매출 51% 차지" 같은 설명


class CompanyGraph:
    """기업 재무 인과 그래프.

    dict-of-dicts 구조. NetworkX 없이 순수 Python.
    nodes: {id: Node}
    edges: {source_id: {target_id: Edge}}
    reverse: {target_id: {source_id: Edge}}  ← 역방향 (causes 추적용)
    """

    def __init__(self, stockCode: str = "", corpName: str = "") -> None:
        """그래프 초기화.

        Parameters
        ----------
        stockCode : str
            종목코드.
        corpName : str
            기업명.
        """
        self.stockCode = stockCode
        self.corpName = corpName
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, dict[str, Edge]] = {}  # forward
        self.reverse: dict[str, dict[str, Edge]] = {}  # backward

    def addNode(self, node: Node) -> None:
        """노드 추가 (동일 id면 덮어쓰기).

        Parameters
        ----------
        node : Node
            추가할 노드.

        Requires:
            node.id 유효.

        Raises:
            없음.

        Example:
            >>> g.addNode(Node(id='n1', type='company', label='X'))
        """
        self.nodes[node.id] = node

    def addEdge(self, edge: Edge) -> None:
        """엣지 추가 (forward + reverse 동시 등록).

        Capabilities:
            - source → target forward + reverse 양방향 동시 등록
            - 동일 (src, tgt) 면 덮어쓰기

        Args:
            edge: 추가할 Edge.

        Guide:
            traverse 양방향 탐색을 위해 forward + reverse 둘 다 유지.

        When:
            CompanyGraph 빌드 + AI 관계 답변.

        How:
            edges[src][tgt] = edge + reverse[tgt][src] = edge.

        Requires:
            edge.source/target 가 그래프 노드.

        Raises:
            없음.

        Example:
            >>> g.addEdge(Edge(source='a', target='b'))

        See Also:
            - addNode : 노드 등록
            - outgoing / incoming : 탐색

        AIContext:
            그래프 빌드 invisible. AI 답변 시 traverse 만 호출.
        """
        # forward
        if edge.source not in self.edges:
            self.edges[edge.source] = {}
        self.edges[edge.source][edge.target] = edge
        # reverse (backward traversal용)
        if edge.target not in self.reverse:
            self.reverse[edge.target] = {}
        self.reverse[edge.target][edge.source] = edge

    def getNode(self, nodeId: str) -> Node | None:
        """노드 ID로 조회.

        Parameters
        ----------
        nodeId : str
            노드 고유 ID.

        Returns
        -------
        Node | None
            해당 노드. 없으면 None.

        Requires:
            nodeId 문자열.

        Raises:
            없음.

        Example:
            >>> g.getNode('n1').label
            'X'
        """
        return self.nodes.get(nodeId)

    def outgoing(self, nodeId: str) -> list[Edge]:
        """node_id에서 나가는 엣지들 (forward).

        Parameters
        ----------
        nodeId : str
            출발 노드 ID.

        Returns
        -------
        list[Edge]
            해당 노드에서 나가는 엣지 리스트.

        Requires:
            nodeId 가 그래프에 있을 필요는 없음 (없으면 빈 list).

        Raises:
            없음.

        Example:
            >>> [e.target for e in g.outgoing('n1')]
            ['n2']
        """
        return list(self.edges.get(nodeId, {}).values())

    def incoming(self, nodeId: str) -> list[Edge]:
        """node_id로 들어오는 엣지들 (역방향).

        Parameters
        ----------
        nodeId : str
            도착 노드 ID.

        Returns
        -------
        list[Edge]
            해당 노드로 들어오는 엣지 리스트.

        Requires:
            없음.

        Raises:
            없음.

        Example:
            >>> [e.source for e in g.incoming('n2')]
            ['n1']
        """
        return list(self.reverse.get(nodeId, {}).values())

    def findNodes(self, *, type: NodeType | None = None, label: str = "") -> list[Node]:
        """조건 매칭 노드 검색.

        Capabilities:
            - type 필터 + label substring 검색
            - 두 조건 AND

        Args:
            type: 노드 타입 (선택).
            label: 라벨 부분 매칭 (대소문자 무시).

        Returns:
            list[Node] — 매칭 노드.

        Guide:
            type=NodeType.COMPANY + label="삼성" → 삼성 계열사 노드 조회.

        When:
            graph traverse 진입점 + AI 관계 탐색 답변.

        How:
            self.nodes 순회 → type/label 조건 필터.

        Requires:
            그래프 빌드 완료.

        Raises:
            없음.

        Example:
            >>> g.findNodes(type=NodeType.COMPANY, label="삼성")
            [Node(...)]

        See Also:
            - outgoing / incoming : 관계 탐색
            - traverse.* : BFS/DFS

        AIContext:
            "이 그래프의 X 타입 노드" 답변 시 사용.
        """
        results = []
        for n in self.nodes.values():
            if type and n.type != type:
                continue
            if label and label.lower() not in n.label.lower():
                continue
            results.append(n)
        return results

    def __len__(self) -> int:
        return len(self.nodes)

    def edgeCount(self) -> int:
        """전체 엣지 수.

        Returns
        -------
        int
            그래프 내 총 엣지 수.

        Requires:
            없음.

        Raises:
            없음.

        Example:
            >>> g.edgeCount()
            42
        """
        return sum(len(targets) for targets in self.edges.values())

    def summary(self) -> str:
        """그래프 요약 문자열.

        Returns
        -------
        str
            "CompanyGraph(기업명): N nodes, M edges" 형식.

        Requires:
            없음.

        Raises:
            없음.

        Example:
            >>> g.summary()
            'CompanyGraph(삼성전자): 12 nodes, 42 edges'
        """
        return f"CompanyGraph({self.corpName}): {len(self)} nodes, {self.edgeCount()} edges"
