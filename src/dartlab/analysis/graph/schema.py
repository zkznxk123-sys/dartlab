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
    METRIC = "metric"
    ACCOUNT = "account"
    SEGMENT = "segment"
    PERIOD = "period"
    EVENT = "event"
    MACRO = "macro"


class EdgeType(str, Enum):
    CAUSES = "causes"
    PART_OF = "partOf"
    DERIVED = "derived"
    COMPARES_TO = "comparesTo"
    ANOMALY = "anomaly"


@dataclass(frozen=True)
class Node:
    id: str  # unique — "metric:영업이익률:2024" 형태
    type: NodeType
    label: str  # 사람이 읽는 이름
    value: Any = None  # 수치 또는 문자열
    period: str = ""  # 기간
    unit: str = ""  # %, 조원, 배 등
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
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
        """
        self.nodes[node.id] = node

    def addEdge(self, edge: Edge) -> None:
        """엣지 추가 (forward + reverse 동시 등록).

        Parameters
        ----------
        edge : Edge
            추가할 엣지.
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
        node_id : str
            노드 고유 ID.

        Returns
        -------
        Node | None
            해당 노드. 없으면 None.
        """
        return self.nodes.get(nodeId)

    def outgoing(self, nodeId: str) -> list[Edge]:
        """node_id에서 나가는 엣지들 (forward).

        Parameters
        ----------
        node_id : str
            출발 노드 ID.

        Returns
        -------
        list[Edge]
            해당 노드에서 나가는 엣지 리스트.
        """
        return list(self.edges.get(nodeId, {}).values())

    def incoming(self, nodeId: str) -> list[Edge]:
        """node_id로 들어오는 엣지들 (역방향).

        Parameters
        ----------
        node_id : str
            도착 노드 ID.

        Returns
        -------
        list[Edge]
            해당 노드로 들어오는 엣지 리스트.
        """
        return list(self.reverse.get(nodeId, {}).values())

    def findNodes(self, *, type: NodeType | None = None, label: str = "") -> list[Node]:
        """조건 매칭 노드 검색.

        Parameters
        ----------
        type : NodeType, optional
            필터링할 노드 타입.
        label : str
            부분 매칭할 라벨 (대소문자 무시).

        Returns
        -------
        list[Node]
            조건에 맞는 노드 리스트.
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
        """
        return sum(len(targets) for targets in self.edges.values())

    def summary(self) -> str:
        """그래프 요약 문자열.

        Returns
        -------
        str
            "CompanyGraph(기업명): N nodes, M edges" 형식.
        """
        return f"CompanyGraph({self.corpName}): {len(self)} nodes, {self.edgeCount()} edges"
