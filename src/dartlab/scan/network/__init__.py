"""한국 상장사 관계 지도 — 출자/지분/인적 관계 그래프.

Public API:
    build_graph()        → data dict (전체 파이프라인)
    export_full(data)    → full JSON dict
    export_overview(data, full) → overview JSON dict
    export_ego(data, full, code) → ego JSON dict
"""

from __future__ import annotations

import time

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

from dartlab.scan.network.classifier import classifyBalanced
from dartlab.scan.network.cycles import detectCycles
from dartlab.scan.network.edges import (
    buildHolderEdges,
    buildInvestEdges,
    deduplicateEdges,
)
from dartlab.scan.network.export import (
    exportEgo,
    exportFull,
    exportOverview,
)
from dartlab.scan.network.scanner import (
    loadListing,
    scanInvested,
    scanMajorHolders,
)
from dartlab.scan.network.scanner import (
    scanAffiliateDocs as _scan_affiliate_docs_fn,
)


def buildGraph(*, verbose: bool = True) -> dict:
    """전체 파이프라인 실행 → data dict.

    Returns:
        dict with keys: listing_meta, code_to_name, code_to_group,
        invest_edges, corp_edges, person_edges, all_node_ids, cycles
    """
    t0 = time.perf_counter()

    def _say(msg: str) -> None:
        if verbose:
            _log.info(msg)

    _say("1. 상장사 목록...")
    nameToCode, codeToName, listing_codes, listing_meta = loadListing()

    _say("2. investedCompany 스캔...")
    raw_inv = scanInvested()
    investEdges = buildInvestEdges(raw_inv, nameToCode, codeToName)
    invest_deduped = deduplicateEdges(investEdges)
    invest_deduped = invest_deduped.filter(pl.col("from_code") != pl.col("to_code"))
    _say(f"   → {len(invest_deduped):,} edges")

    _say("3. majorHolder 스캔...")
    raw_mh = scanMajorHolders()
    corpEdges, personEdges = buildHolderEdges(raw_mh, nameToCode)
    _say(f"   → corp {len(corpEdges):,}, person {len(personEdges):,}")

    # 노드 수집
    allNodeIds: set[str] = set()
    listed_only = invest_deduped.filter(pl.col("is_listed") & pl.col("to_code").is_not_null())
    for row in listed_only.iter_rows(named=True):
        allNodeIds.add(row["from_code"])
        allNodeIds.add(row["to_code"])
    matched_corp = corpEdges.filter(pl.col("from_code").is_not_null())
    for row in matched_corp.iter_rows(named=True):
        allNodeIds.add(row["from_code"])
        allNodeIds.add(row["to_code"])
    allNodeIds = allNodeIds & listing_codes
    _say(f"   → {len(allNodeIds)} 상장사 노드")

    _say("4. docs ground truth...")
    docs_gt = _scan_affiliate_docs_fn(nameToCode, codeToName)
    _say(f"   → {len(docs_gt)} 종목 매핑")

    _say("5. 균형 분류...")
    codeToGroup = classifyBalanced(
        invest_deduped,
        corpEdges,
        personEdges,
        allNodeIds,
        codeToName,
        docs_gt,
        verbose=verbose,
    )

    _say("6. 순환출자 탐지...")
    cycles = detectCycles(invest_deduped, codeToName, maxLength=6)
    _say(f"   → {len(cycles)}개")

    elapsed = time.perf_counter() - t0
    _say(f"\n파이프라인 완료: {elapsed:.1f}초")

    return {
        "listing_meta": listing_meta,
        "code_to_name": codeToName,
        "code_to_group": codeToGroup,
        "invest_edges": invest_deduped,
        "corp_edges": corpEdges,
        "person_edges": personEdges,
        "all_node_ids": allNodeIds,
        "cycles": cycles,
    }


__all__ = [
    "build_graph",
    "export_full",
    "export_overview",
    "export_ego",
]
