"""순환출자 DFS 탐지."""

from __future__ import annotations

from collections import defaultdict

import polars as pl


def detectCycles(
    investEdges: pl.DataFrame,
    codeToName: dict[str, str],
    *,
    maxLength: int = 6,
) -> list[list[str]]:
    """상장사간 directed graph에서 순환출자 경로를 DFS로 탐지한다.

    investedCompany 엣지 중 상장사 간 경영참여/투자 관계를 방향 그래프로
    구성하고, 지정 길이 이하의 모든 순환 경로를 찾는다.

    Parameters
    ----------
    invest_edges : pl.DataFrame
        build_invest_edges 결과. 필수 컬럼: from_code, to_code, is_listed.
    code_to_name : dict[str, str]
        종목코드 → 회사명 매핑 (현재 내부 미사용, 호출자 편의용).
    max_length : int
        탐지할 순환 경로의 최대 노드 수 (기본 6).

    Returns
    -------
    list[list[str]]
        순환출자 경로 리스트. 각 경로는 종목코드 리스트이며
        마지막 원소 == 첫 원소 (순환 표시). 중복 경로는 제거된다.
        예: ``[["005930", "006400", "005930"]]``
    """
    adj: dict[str, list[str]] = defaultdict(list)
    listed = investEdges.filter(
        pl.col("is_listed") & pl.col("to_code").is_not_null() & (pl.col("from_code") != pl.col("to_code"))
    )
    for row in listed.iter_rows(named=True):
        adj[row["from_code"]].append(row["to_code"])

    cycles: list[list[str]] = []
    visited_global: set[str] = set()

    def dfs(node: str, path: list[str], pathSet: set[str]) -> None:
        """dfs — TODO 한국어 동작 설명."""
        if len(path) > maxLength:
            return
        for nb in adj.get(node, []):
            if nb == path[0] and len(path) >= 2:
                cycles.append(path + [nb])
            elif nb not in pathSet and nb not in visited_global:
                path.append(nb)
                pathSet.add(nb)
                dfs(nb, path, pathSet)
                path.pop()
                pathSet.discard(nb)

    for start in sorted(adj.keys()):
        if start in visited_global:
            continue
        dfs(start, [start], {start})
        visited_global.add(start)

    unique: list[list[str]] = []
    seen: set[frozenset[str]] = set()
    for cycle in cycles:
        key = frozenset(cycle[:-1])
        if key not in seen:
            seen.add(key)
            unique.append(cycle)
    return unique
