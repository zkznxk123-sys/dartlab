"""Skill Graph 모델 — 257 sub-spec 의 연결 관계를 그래프로 구조화.

3 주체 (외부 LLM · 내부 AI · 사람) 가 같은 그래프 위에서 진입 → 진행 → 결론
경로를 탐색하기 위한 데이터 모델. 본 모듈은 *순수* — 빌드만 하고 검증·차단은
graphLint.py 가 별도 책임.

Description
-----------
SkillSpec 리스트에서 nodes + edges 추출 후 in-degree/out-degree, entry/leaf/
orphan 분류, 깊이 순환 (cycle 3+ 노드 SCC) 검출, entries 에서 BFS 도달 가능
범위 계산.

본문 사용처:
- compiler.py: graph.json 빌드 시 nodes + edges 직렬화.
- registry.py::lintSkill: graph 정합성 lint (graphLint.py 가 사용).
- landing /skills/graph: 시각화 데이터 source.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Literal

from .models import SkillSpec

EdgeKind = Literal["successor", "predecessor", "linkedRecipe", "knowledge", "source"]


@dataclass(frozen=True)
class SkillNode:
    """그래프 노드 — SkillSpec 의 진입 식별 핵심 메타.

    Description
    -----------
    `id` 가 그래프 식별자. degree 는 빌드 시점 계산. cluster 는 engine group
    (예 engines.analysis 의 모든 axis 는 cluster='analysis') 또는 category.
    audiences 는 frontmatter 의 `audiences` dict 의 key 셋 (`llm`/`agent`/
    `human`) — 어느 주체용 본문이 있는지 표시.

    Parameters
    ----------
    id : str
        skill id (예 'engines.company.researchStarter').
    title : str
        사람 가독 제목.
    category : str
        start/runtime/operation/engines 4 카테고리.
    purpose : str
        1~2 문장 요약.
    inDegree : int
        다른 노드로부터 참조받는 수.
    outDegree : int
        다른 노드를 참조하는 수.
    cluster : str
        engine group 또는 category. graph 시각화 색상/그룹화.
    isEntry : bool
        진입점 노드 (frontmatter `entryHint` 또는 category='start').
    isLeaf : bool
        리프 노드 (frontmatter `isLeafNode` 또는 outDegree 0).
    isOrphan : bool
        어디서도 참조 안 받음 (inDegree 0 + entry 아님).
    audiences : tuple[str, ...]
        본문 directive 마커가 명시한 주체 셋.

    Returns
    -------
    SkillNode
        id : str
        title : str
        category : str

    Raises
    ------
    없음
        검증은 graphLint.py 가 별도 책임.

    Examples
    --------
    >>> node = SkillNode(id='x', title='X', category='engines', purpose='...',
    ...                  inDegree=2, outDegree=3, cluster='analysis',
    ...                  isEntry=False, isLeaf=False, isOrphan=False,
    ...                  audiences=('llm', 'agent'))
    >>> node.cluster
    'analysis'

    Notes
    -----
    frozen=True — 빌드 후 변경 금지. 변경 필요 시 새 SkillGraph 재빌드.

    Guide
    -----
    빌드 후 시각화 패키지 (d3/landing) 는 본 node 그대로 직렬화. category 와
    cluster 가 색상 매핑 키.

    See Also
    --------
    SkillGraph : 노드 + 엣지 + 메타 통합.
    """

    id: str
    title: str
    category: str
    purpose: str
    inDegree: int
    outDegree: int
    cluster: str | None
    isEntry: bool
    isLeaf: bool
    isOrphan: bool
    audiences: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillEdge:
    """그래프 엣지 — 한 노드에서 다른 노드로의 참조 관계.

    Description
    -----------
    kind 가 5 종 — `successor` (작업 흐름 다음 step, `successors` 필드),
    `predecessor` (이전 step, `predecessors` 필드),
    `linkedRecipe` (recipe step `linkedSkills` 필드),
    `knowledge` (참고 자료 `knowledgeRefs`),
    `source` (출처 `sourceRefs` 의 dartlab:// scheme 안 path).

    Parameters
    ----------
    src : str
        엣지 출발 노드 id.
    dst : str
        엣지 도착 노드 id.
    kind : EdgeKind
        5 종 중 하나.

    Returns
    -------
    SkillEdge
        src : str
        dst : str
        kind : EdgeKind

    Raises
    ------
    없음
        검증은 graphLint.py 가 별도 책임.

    Examples
    --------
    >>> edge = SkillEdge(src='engines.analysis', dst='engines.company', kind='knowledge')
    >>> edge.kind
    'knowledge'

    Notes
    -----
    양방향 자동 도출은 buildSkillGraph 가 successor ↔ predecessor 쌍으로
    수행하지 않는다 — 같은 엣지를 두 번 표현하지 않고 src/dst 만 명시.
    시각화 단계에서 양방향 표시 결정.

    Guide
    -----
    edge 종류별 시각화 스타일 — successor 실선, knowledge 점선,
    linkedRecipe 굵은선, source 회색 얇은선.

    See Also
    --------
    SkillNode : 엣지 끝점.
    """

    src: str
    dst: str
    kind: EdgeKind


@dataclass(frozen=True)
class SkillGraph:
    """257 sub-spec 의 전체 연결 그래프.

    Description
    -----------
    nodes + edges + 사전 계산된 메타 (entryNodes, cycles, orphanNodes,
    unreachableFromEntry). 빌드 1 회 후 frozen, 시각화·lint·검색이 본 객체를
    공유.

    Parameters
    ----------
    nodes : tuple[SkillNode, ...]
        모든 노드.
    edges : tuple[SkillEdge, ...]
        모든 엣지.
    entryNodes : tuple[str, ...]
        진입점 id (category='start' 또는 entryHint=True).
    cycles : tuple[tuple[str, ...], ...]
        3+ 노드 SCC (2-노드 양방향은 정상으로 제외).
    unreachableFromEntry : tuple[str, ...]
        entry 에서 maxHops 안 도달 못한 노드.
    orphanNodes : tuple[str, ...]
        inDegree 0 + entry 아님 (의도적 leaf 여부는 별도 판정).

    Returns
    -------
    SkillGraph

    Raises
    ------
    없음
        검증은 graphLint.py 가 별도 책임.

    Examples
    --------
    >>> from dartlab.skills.registry import listSkills
    >>> g = buildSkillGraph(listSkills())
    >>> len(g.nodes)
    257
    >>> isinstance(g.edges, tuple)
    True

    Notes
    -----
    cycles 는 *3 노드 이상* 만 — 2 노드 양방향 (A↔B) 은 dartlab 의 정상 패턴
    (parent-child 또는 cross-engine 양방향 인용). 3+ 노드 cycle 만 *추적
    어려운 회귀* 위험.

    Guide
    -----
    시각화 사용 — buildSkillGraph 결과를 그대로 d3 hierarchy 또는 force
    simulation 에 입력. cluster 별 색상은 categoryColors SSOT.

    See Also
    --------
    buildSkillGraph : SkillSpec 리스트 → SkillGraph 빌드.
    detectCycles : Tarjan SCC 알고리즘.
    reachableFromEntries : BFS 도달 가능 범위.
    """

    nodes: tuple[SkillNode, ...]
    edges: tuple[SkillEdge, ...]
    entryNodes: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]
    unreachableFromEntry: tuple[str, ...]
    orphanNodes: tuple[str, ...]


def _normalizeRef(value: str) -> str:
    """frontmatter ref 값에서 둘레 quote 제거 + strip."""
    return value.strip().strip('"').strip("'")


def _clusterFor(skillId: str, category: str) -> str | None:
    """skill id 에서 cluster 추출 — engines.{group}.{axis} 면 {group}, 그 외 category."""
    if category == "engines" and skillId.startswith("engines."):
        parts = skillId.split(".")
        if len(parts) >= 2:
            return parts[1]
    return category


def buildSkillGraph(specs: list[SkillSpec], *, maxHops: int = 6) -> SkillGraph:
    """SkillSpec 리스트 → SkillGraph 빌드.

    Description
    -----------
    1. nodes 빌드 — id, title, category, purpose, cluster, isEntry/Leaf/Orphan,
       audiences 사전 계산.
    2. edges 빌드 — 5 kind (successor/predecessor/linkedRecipe/knowledge/
       source) 추출.
    3. degree 계산.
    4. cycles 검출 — 3+ 노드 SCC 만 (Tarjan).
    5. reachability 계산 — entries 에서 BFS maxHops.
    6. orphan 분류 — inDegree 0 + entry 아님.

    Parameters
    ----------
    specs : list[SkillSpec]
        listSkills() 결과 또는 sub-set.
    maxHops : int, optional
        entry → 노드 도달 최대 hop. 기본 6.

    Returns
    -------
    SkillGraph
        nodes : tuple[SkillNode, ...]
        edges : tuple[SkillEdge, ...]
        entryNodes : tuple[str, ...]
        cycles : tuple[tuple[str, ...], ...]
        unreachableFromEntry : tuple[str, ...]
        orphanNodes : tuple[str, ...]

    Raises
    ------
    없음
        검증/lint 는 graphLint.py.

    Examples
    --------
    >>> from dartlab.skills.registry import listSkills
    >>> g = buildSkillGraph(listSkills())
    >>> len(g.entryNodes) > 0
    True

    Notes
    -----
    본 함수는 spec 의 ref 필드를 *그대로* 사용 (lint 통과 후 호출 가정).
    깨진 ref (dst 가 id 셋에 없는 경우) 는 edge 에서 *제외* 한다 — lint
    별도 책임.

    Guide
    -----
    compiler.py 가 빌드 시 본 함수 1 회 호출 → graph.json 직렬화. landing 빌드
    시 import.

    See Also
    --------
    detectCycles : 3+ 노드 SCC.
    reachableFromEntries : entry BFS.
    """
    ids = {s.id for s in specs}

    nodes_pre: dict[str, dict] = {}
    edges_list: list[SkillEdge] = []
    in_count: dict[str, int] = defaultdict(int)
    out_count: dict[str, int] = defaultdict(int)

    for spec in specs:
        cluster = _clusterFor(spec.id, str(spec.category))
        audiences = tuple(sorted(spec.audiences.keys())) if spec.audiences else ()
        is_entry = bool(spec.entryHint) or str(spec.category) == "start"

        nodes_pre[spec.id] = {
            "title": spec.title,
            "category": str(spec.category),
            "purpose": spec.purpose,
            "cluster": cluster,
            "isEntry": is_entry,
            "isLeafFlag": bool(spec.isLeafNode),
            "audiences": audiences,
        }

        for field_name, kind in (
            ("successors", "successor"),
            ("predecessors", "predecessor"),
            ("linkedSkills", "linkedRecipe"),
            ("knowledgeRefs", "knowledge"),
        ):
            for raw in getattr(spec, field_name, []) or []:
                if not isinstance(raw, str):
                    continue
                dst = _normalizeRef(raw)
                if dst and dst in ids and dst != spec.id:
                    edges_list.append(SkillEdge(src=spec.id, dst=dst, kind=kind))
                    out_count[spec.id] += 1
                    in_count[dst] += 1

        for raw in spec.sourceRefs or []:
            if not isinstance(raw, str):
                continue
            value = _normalizeRef(raw)
            if value.startswith("dartlab://skills/"):
                dst = value.removeprefix("dartlab://skills/")
                if dst and dst in ids and dst != spec.id:
                    edges_list.append(SkillEdge(src=spec.id, dst=dst, kind="source"))
                    out_count[spec.id] += 1
                    in_count[dst] += 1

    nodes_list: list[SkillNode] = []
    entry_ids: list[str] = []
    orphan_ids: list[str] = []

    for sid, meta in nodes_pre.items():
        in_d = in_count.get(sid, 0)
        out_d = out_count.get(sid, 0)
        is_entry = meta["isEntry"]
        is_leaf = meta["isLeafFlag"] or out_d == 0
        is_orphan = in_d == 0 and not is_entry

        nodes_list.append(
            SkillNode(
                id=sid,
                title=meta["title"],
                category=meta["category"],
                purpose=meta["purpose"],
                inDegree=in_d,
                outDegree=out_d,
                cluster=meta["cluster"],
                isEntry=is_entry,
                isLeaf=is_leaf,
                isOrphan=is_orphan,
                audiences=meta["audiences"],
            )
        )

        if is_entry:
            entry_ids.append(sid)
        if is_orphan:
            orphan_ids.append(sid)

    nodes_tuple = tuple(sorted(nodes_list, key=lambda n: n.id))
    edges_tuple = tuple(edges_list)
    entry_tuple = tuple(sorted(entry_ids))
    orphan_tuple = tuple(sorted(orphan_ids))

    cycles = detectCycles(edges_tuple)
    reachable = reachableFromEntries(edges_tuple, entry_tuple, maxHops=maxHops)
    unreachable = tuple(sorted(sid for sid in ids if sid not in reachable))

    return SkillGraph(
        nodes=nodes_tuple,
        edges=edges_tuple,
        entryNodes=entry_tuple,
        cycles=cycles,
        unreachableFromEntry=unreachable,
        orphanNodes=orphan_tuple,
    )


def detectCycles(edges: tuple[SkillEdge, ...]) -> tuple[tuple[str, ...], ...]:
    """3+ 노드 SCC 검출 (Tarjan).

    Description
    -----------
    2 노드 양방향 (A↔B) 은 *정상* 으로 제외 — dartlab 의 parent-child /
    cross-engine 양방향 인용 패턴. 3+ 노드 strongly connected component 만
    반환 — 추적 어려운 회귀 위험.

    Parameters
    ----------
    edges : tuple[SkillEdge, ...]
        SkillGraph 의 edges.

    Returns
    -------
    tuple[tuple[str, ...], ...]
        각 SCC 의 노드 id 튜플. 빈 튜플이면 cycle 없음.

    Raises
    ------
    없음
        검증/차단은 graphLint.py.

    Examples
    --------
    >>> edges = (SkillEdge('a', 'b', 'successor'),
    ...          SkillEdge('b', 'c', 'successor'),
    ...          SkillEdge('c', 'a', 'successor'))
    >>> cycles = detectCycles(edges)
    >>> len(cycles)
    1

    Notes
    -----
    Tarjan SCC O(V+E). 2-node 양방향 cycle 은 *정상 패턴* 으로 제외.

    Guide
    -----
    cycle 발견 시 graphLint.py 가 warning 또는 error 결정 (phase 별 정책).

    See Also
    --------
    buildSkillGraph : edges 빌드.
    """
    adjacency: dict[str, list[str]] = defaultdict(list)
    nodes_set: set[str] = set()
    for edge in edges:
        if edge.kind in ("successor", "linkedRecipe"):
            adjacency[edge.src].append(edge.dst)
            nodes_set.add(edge.src)
            nodes_set.add(edge.dst)

    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    sccs: list[tuple[str, ...]] = []

    def strongconnect(node: str) -> None:
        """Tarjan SCC 재귀 클로저 — node 에서 시작해 stack/lowlink 갱신 후 3+ 노드 SCC 발견 시 sccs 에 append."""
        indices[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)

        for successor in adjacency.get(node, []):
            if successor not in indices:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[successor])

        if lowlinks[node] == indices[node]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == node:
                    break
            if len(scc) >= 3:
                sccs.append(tuple(sorted(scc)))

    for n in sorted(nodes_set):
        if n not in indices:
            strongconnect(n)

    return tuple(sccs)


def reachableFromEntries(
    edges: tuple[SkillEdge, ...],
    entries: tuple[str, ...],
    *,
    maxHops: int = 6,
) -> set[str]:
    """entry 노드들에서 BFS — maxHops 안 도달 가능한 id 셋.

    Description
    -----------
    `successor`/`linkedRecipe` 엣지만 forward path 로 사용. `knowledge`/
    `source` 는 *참조* 결이라 진행 path 아님 — 제외.

    Parameters
    ----------
    edges : tuple[SkillEdge, ...]
        SkillGraph 의 edges.
    entries : tuple[str, ...]
        진입점 id 셋.
    maxHops : int, optional
        최대 hop. 기본 6.

    Returns
    -------
    set[str]
        entry 부터 maxHops 안 도달 가능한 모든 id.

    Raises
    ------
    없음

    Examples
    --------
    >>> edges = (SkillEdge('start.x', 'a', 'successor'),
    ...          SkillEdge('a', 'b', 'successor'))
    >>> reach = reachableFromEntries(edges, ('start.x',), maxHops=2)
    >>> 'b' in reach
    True

    Notes
    -----
    entry 노드 자체도 reachable 셋에 포함.

    Guide
    -----
    unreachable 노드는 *진입 path 없는* 상태 — 의도적 leaf 면 frontmatter
    `isLeafNode: true` 명시, 그 외엔 graphLint 가 warning.

    See Also
    --------
    buildSkillGraph : reachability 자동 계산.
    """
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.kind in ("successor", "linkedRecipe"):
            adjacency[edge.src].append(edge.dst)

    reached: set[str] = set(entries)
    frontier: deque[tuple[str, int]] = deque((sid, 0) for sid in entries)

    while frontier:
        node, depth = frontier.popleft()
        if depth >= maxHops:
            continue
        for nxt in adjacency.get(node, []):
            if nxt not in reached:
                reached.add(nxt)
                frontier.append((nxt, depth + 1))

    return reached


__all__ = [
    "SkillNode",
    "SkillEdge",
    "SkillGraph",
    "buildSkillGraph",
    "detectCycles",
    "reachableFromEntries",
]
