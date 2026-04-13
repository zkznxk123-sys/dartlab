"""엣지 빌더 — docs + scan/network에서 공급-수요·계열 관계 추출.

데이터 소스:
1. scan/network — 투자관계(investedCompany), 계열사(affiliateGroup)
2. docs parquet — 거래처(rawMaterial 텍스트), 특수관계자거래
3. 추후: AI/사람 검수

Company 객체를 로드하지 않고 parquet/report를 직접 스캔한다.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import polars as pl

from dartlab.industry.types import IndustryEdge, IndustryNode

logger = logging.getLogger(__name__)


def _listingLookup() -> tuple[dict[str, str], dict[str, str]]:
    """종목코드→회사명, 회사명→종목코드 매핑."""
    try:
        from dartlab.gather.listing import getKindList

        df = getKindList()
        c2n = dict(zip(df["종목코드"].to_list(), df["회사명"].to_list()))
        n2c = dict(zip(df["회사명"].to_list(), df["종목코드"].to_list()))
        return c2n, n2c
    except Exception:
        return {}, {}


def _buildNodeIndex(nodes: list[IndustryNode]) -> dict[str, IndustryNode]:
    """stockCode → primary node."""
    idx: dict[str, IndustryNode] = {}
    for n in nodes:
        if n.primary and n.stockCode not in idx:
            idx[n.stockCode] = n
    return idx


# ── 1. scan/network에서 계열사/투자 관계 ──


def extractNetworkEdges(nodes: list[IndustryNode]) -> list[IndustryEdge]:
    """scan/network의 investedCompany 데이터에서 계열·투자 엣지 추출.

    상장사 간 투자 관계만 추출 (비상장 제외).
    """
    edges: list[IndustryEdge] = []
    nodeIdx = _buildNodeIndex(nodes)
    c2n, n2c = _listingLookup()

    try:
        from dartlab.scan.network.scanner import load_listing, scan_invested

        raw = scan_invested()
        if raw is None or raw.height == 0:
            return edges

        name_to_code, code_to_name, listing_codes, _ = load_listing()

        from dartlab.scan.network.edges import build_invest_edges

        investDf = build_invest_edges(raw, name_to_code, code_to_name)
    except Exception as e:
        logger.warning("network 엣지 추출 실패: %s", e)
        return edges

    for row in investDf.iter_rows(named=True):
        fromCode = row.get("from_code", "")
        toCode = row.get("to_code")
        purpose = row.get("purpose", "")
        ownershipPct = row.get("ownership_pct")

        if not fromCode or not toCode:
            continue

        # 양쪽 다 상장사인 것만
        if fromCode not in nodeIdx or toCode not in nodeIdx:
            continue

        fromNode = nodeIdx[fromCode]
        toNode = nodeIdx[toCode]

        edgeType = "affiliate"
        if purpose == "경영참여":
            edgeType = "affiliate"
        elif purpose == "단순투자":
            edgeType = "investor"

        evidence = f"지분 {ownershipPct:.1f}%" if ownershipPct else ""
        if purpose:
            evidence = f"{purpose} {evidence}".strip()

        edges.append(
            IndustryEdge(
                fromCode=fromCode,
                fromName=c2n.get(fromCode, ""),
                toCode=toCode,
                toName=c2n.get(toCode, ""),
                edgeType=edgeType,
                industry=fromNode.industry,
                confidence=0.9 if purpose == "경영참여" else 0.6,
                source="network",
                evidence=evidence,
            )
        )

    # 중복 제거 (같은 from-to 쌍)
    seen: set[tuple[str, str]] = set()
    unique: list[IndustryEdge] = []
    for e in edges:
        key = (e.fromCode, e.toCode)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


# ── 2. docs에서 거래처 관계 (rawMaterial/relatedPartyTx) ──

# 상장사명 매칭 패턴 — 회사명이 텍스트에 나오면 거래 관계로 추정
_SUPPLIER_TITLE = re.compile(r"원재료|원자재|부자재|매입처|공급처|거래처")
_CUSTOMER_TITLE = re.compile(r"매출처|판매처|수주처|주요.*고객")


def extractDocsEdges(nodes: list[IndustryNode]) -> list[IndustryEdge]:
    """docs parquet에서 거래처 관계를 추출.

    rawMaterial/거래처 섹션 텍스트에서 상장사명이 언급되면 supplier/customer 엣지로 생성.
    """
    edges: list[IndustryEdge] = []
    nodeIdx = _buildNodeIndex(nodes)
    c2n, n2c = _listingLookup()

    # 매칭할 상장사명 집합 (3글자 이상만 — 노이즈 방지)
    targetNames = {name: code for name, code in n2c.items() if len(name) >= 3}

    try:
        from dartlab.industry.build.stage3_docs import _docsDir

        docsDir = _docsDir()
        if not docsDir.exists():
            return edges
    except Exception:
        return edges

    processed = 0
    for code, node in nodeIdx.items():
        pqPath = docsDir / f"{code}.parquet"
        if not pqPath.exists():
            continue

        try:
            df = (
                pl.scan_parquet(str(pqPath))
                .select(["section_title", "section_content"])
                .filter(pl.col("section_content").is_not_null())
                .filter(pl.col("section_content").str.len_chars() > 20)
                .collect()
            )
        except (pl.exceptions.PolarsError, OSError):
            continue

        for row in df.iter_rows(named=True):
            title = row.get("section_title") or ""
            content = row.get("section_content") or ""

            isSupplier = bool(_SUPPLIER_TITLE.search(title))
            isCustomer = bool(_CUSTOMER_TITLE.search(title))
            if not isSupplier and not isCustomer:
                continue

            # 텍스트에서 상장사명 검색
            for targetName, targetCode in targetNames.items():
                if targetCode == code:
                    continue  # 자기 자신 제외
                if targetName in content:
                    if isSupplier:
                        edges.append(
                            IndustryEdge(
                                fromCode=targetCode,
                                fromName=targetName,
                                toCode=code,
                                toName=c2n.get(code, ""),
                                edgeType="supplier",
                                industry=node.industry,
                                confidence=0.6,
                                source="docs",
                                evidence=f"{title} 섹션에서 '{targetName}' 언급",
                            )
                        )
                    elif isCustomer:
                        edges.append(
                            IndustryEdge(
                                fromCode=code,
                                fromName=c2n.get(code, ""),
                                toCode=targetCode,
                                toName=targetName,
                                edgeType="customer",
                                industry=node.industry,
                                confidence=0.6,
                                source="docs",
                                evidence=f"{title} 섹션에서 '{targetName}' 언급",
                            )
                        )

        processed += 1

    logger.info("docs 엣지: %d사 스캔, %d건 추출", processed, len(edges))

    # 중복 제거
    seen: set[tuple[str, str, str]] = set()
    unique: list[IndustryEdge] = []
    for e in edges:
        key = (e.fromCode, e.toCode, e.edgeType)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


# ── 통합 ──


def buildAllEdges(nodes: list[IndustryNode], *, skipDocs: bool = False) -> list[IndustryEdge]:
    """모든 소스에서 엣지를 수집하여 통합."""
    edges: list[IndustryEdge] = []

    # 1. scan/network
    try:
        networkEdges = extractNetworkEdges(nodes)
        edges.extend(networkEdges)
        logger.info("network 엣지: %d건", len(networkEdges))
    except Exception as e:
        logger.warning("network 엣지 실패: %s", e)

    # 2. docs
    if not skipDocs:
        try:
            docsEdges = extractDocsEdges(nodes)
            edges.extend(docsEdges)
            logger.info("docs 엣지: %d건", len(docsEdges))
        except Exception as e:
            logger.warning("docs 엣지 실패: %s", e)

    return edges
