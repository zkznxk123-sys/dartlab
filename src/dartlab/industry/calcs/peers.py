"""industry.peers — 동종업종 peer 추출.

종목코드로부터 (1) 그 회사의 industry id 를 찾고 (2) 같은 산업의 다른 노드들을
매출 순으로 정렬해 top N 을 반환한다. landing 의 PeerMatrix 와 viz 의
``spec_peer_matrix`` 가 받는 형태.

본 단계의 metric 은 nodes.json 에 이미 있는 ``revenue`` (매출 원) 와 ``stage``
(밸류체인 위치) 만 채운다. PER · PBR · ROE 등은 quant/analysis 엔진에서 lookup
이 추가로 필요 — 후속 phase 에서 채울 자리 (Phase 5-2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PeerRow:
    """단일 peer 행 — spec_peer_matrix(rows=...) 가 받는 형태."""

    stockCode: str
    corpName: str
    stage: str = ""
    industry: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    isSelf: bool = False

    def asDict(self) -> dict[str, Any]:
        """dataclass → dict 직렬화 (values 는 얕은 복사)."""
        return {
            "stockCode": self.stockCode,
            "corpName": self.corpName,
            "stage": self.stage,
            "industry": self.industry,
            "values": dict(self.values),
            "isSelf": self.isSelf,
        }


def _findIndustryFor(stockCode: str) -> tuple[str | None, list[Any]]:
    """nodes.json 에서 stockCode 가 속한 industry 와 같은 산업의 모든 노드.

    nodes 가 없으면 (None, []).
    """
    try:
        from dartlab.industry.build.pipeline import loadNodes
    except (AttributeError, ImportError):
        return None, []
    try:
        nodes = loadNodes()
    except (FileNotFoundError, OSError, RuntimeError):
        return None, []
    if not nodes:
        return None, []
    self_node = next((n for n in nodes if n.stockCode == stockCode), None)
    if self_node is None:
        return None, []
    industry = self_node.industry
    same = [n for n in nodes if n.industry == industry]
    return industry, same


def _baseValues(node: Any) -> dict[str, Any]:
    """node 가 가진 즉시 가용한 metric — 매출 + 공정.

    PER/ROE 등 외부 data 는 채우지 않는다 (None 으로 두면 PeerMatrixTable 이
    "—" 표시).
    """
    rev = getattr(node, "revenue", None)
    return {
        "매출(억)": round(rev / 1e8, 0) if rev else None,
    }


def industryPeers(stockCode: str, *, n: int = 10) -> list[PeerRow]:
    """동종업종 peer 추출.

    Args:
        stockCode: 본 회사 6 자리 종목코드.
        n: 본 회사 포함 최대 peer 수 (매출 상위 n).

    Returns:
        list[PeerRow]. 첫 행은 본 회사 (isSelf=True). 산업이 없거나 단독
        종목이면 빈 list.
    """
    industry, nodes = _findIndustryFor(stockCode)
    if not industry or not nodes:
        return []
    nodes_sorted = sorted(nodes, key=lambda n: -(getattr(n, "revenue", 0) or 0))
    self_idx = next((i for i, n in enumerate(nodes_sorted) if n.stockCode == stockCode), -1)

    # 본 회사 + 매출 상위 n-1 (본 회사 중복 제외)
    pick: list[Any] = []
    if self_idx >= 0:
        pick.append(nodes_sorted[self_idx])
    for nd in nodes_sorted:
        if len(pick) >= n:
            break
        if nd.stockCode == stockCode:
            continue
        pick.append(nd)

    return [
        PeerRow(
            stockCode=nd.stockCode,
            corpName=nd.corpName,
            stage=getattr(nd, "stage", "") or "",
            industry=industry,
            values=_baseValues(nd),
            isSelf=(nd.stockCode == stockCode),
        )
        for nd in pick
    ]


def industryPeerMetricKeys(rows: list[PeerRow]) -> list[str]:
    """rows 에 실제로 채워진 metric 키 목록 (열 라벨)."""
    seen: list[str] = []
    for r in rows:
        for k in r.values.keys():
            if k not in seen:
                seen.append(k)
    return seen
