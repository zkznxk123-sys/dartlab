"""엣지 빌더 — docs + scan/network에서 공급-수요·계열 관계 추출.

데이터 소스:
1. scan/network — 투자관계(investedCompany), 계열사(affiliateGroup)
2. docs parquet — 거래처(rawMaterial 텍스트), 특수관계자거래
3. 추후: AI/사람 검수

Company 객체를 로드하지 않고 parquet/report를 직접 스캔한다.
"""

from __future__ import annotations

import logging
import re

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

# section_title → 공급/수요 분류 패턴
_SUPPLIER_TITLE = re.compile(r"원재료|원자재|부자재|매입처|공급처|거래처|생산설비")
_CUSTOMER_TITLE = re.compile(r"매출처|판매처|수주처|주요.*고객")
_RELATED_PARTY = re.compile(r"대주주.*거래|특수관계자|계열회사")

# 법인명 추출 패턴 — ㈜, (주), 주식회사 앞뒤로 회사명
_CORP_PATTERN = re.compile(
    r"㈜\s*([가-힣A-Za-z0-9]+)|([가-힣A-Za-z0-9]+)\s*㈜|\(주\)\s*([가-힣A-Za-z0-9]+)|주식회사\s+([가-힣A-Za-z0-9]+)"
)


def _extractCorpNames(content: str) -> list[str]:
    """본문에서 법인명 패턴(㈜, (주), 주식회사)을 추출."""
    names: list[str] = []
    for m in _CORP_PATTERN.finditer(content):
        name = m.group(1) or m.group(2) or m.group(3) or m.group(4)
        if name and len(name) >= 2:
            names.append(name)
    return names


def extractDocsEdges(nodes: list[IndustryNode]) -> list[IndustryEdge]:
    """docs parquet에서 거래처 관계를 추출.

    2가지 방법으로 상장사를 찾는다:
    1. 본문에서 ㈜/주식회사 패턴으로 법인명 추출 → KindList 매칭
    2. KindList 상장사명이 본문에 직접 나오는 경우 (3글자 이상)
    """
    edges: list[IndustryEdge] = []
    nodeIdx = _buildNodeIndex(nodes)
    c2n, n2c = _listingLookup()

    # 매칭할 상장사명 집합 (3글자 이상 — 노이즈 방지)
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
            isRelated = bool(_RELATED_PARTY.search(title))
            if not isSupplier and not isCustomer and not isRelated:
                continue

            # 방법 1: ㈜ 패턴으로 법인명 추출
            corpNames = _extractCorpNames(content)

            # 방법 2: 상장사명 직접 매칭
            foundCodes: set[str] = set()
            for corpName in corpNames:
                targetCode = n2c.get(corpName)
                if targetCode and targetCode != code:
                    foundCodes.add(targetCode)

            for targetName, targetCode in targetNames.items():
                if targetCode == code or targetCode in foundCodes:
                    continue
                if targetName in content:
                    foundCodes.add(targetCode)

            # 엣지 생성
            for targetCode in foundCodes:
                targetName = c2n.get(targetCode, "")
                edgeType = "supplier" if isSupplier else "customer" if isCustomer else "affiliate"
                confidence = 0.7 if isSupplier else 0.6

                if isSupplier:
                    edges.append(
                        IndustryEdge(
                            fromCode=targetCode,
                            fromName=targetName,
                            toCode=code,
                            toName=c2n.get(code, ""),
                            edgeType="supplier",
                            industry=node.industry,
                            confidence=confidence,
                            source="docs",
                            evidence=f"{title}",
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
                            confidence=confidence,
                            source="docs",
                            evidence=f"{title}",
                        )
                    )
                elif isRelated:
                    edges.append(
                        IndustryEdge(
                            fromCode=code,
                            fromName=c2n.get(code, ""),
                            toCode=targetCode,
                            toName=targetName,
                            edgeType="affiliate",
                            industry=node.industry,
                            confidence=0.5,
                            source="docs",
                            evidence=f"{title}",
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


# ── 3. docs 원재료 테이블 파싱 (강력한 한방) ──


def extractRawMaterialEdges(nodes: list[IndustryNode]) -> list[IndustryEdge]:
    """docs "원재료 및 생산설비" 섹션의 마크다운 테이블에서 supplier 엣지 추출.

    구조화된 데이터: 부문 / 품목 / 매입액 / 비중 / 매입처
    → 공급사 실명 + 제품 + 거래 비중이 포함된 정밀 엣지.
    """
    from dartlab.industry.build.stage3_docs import _docsDir
    from dartlab.industry.build.table_parser import (
        extractCorpNames,
        extractTables,
        findTableByHeaders,
        normalizeCorpName,
        parseAmount,
        parsePercent,
        tableToRowDictsWithHeaderRow,
    )

    edges: list[IndustryEdge] = []
    nodeIdx = _buildNodeIndex(nodes)
    c2n, n2c = _listingLookup()

    # 정규화된 회사명 → 종목코드 매핑 (㈜ 등 제거)
    n2cNorm = {normalizeCorpName(name): code for name, code in n2c.items() if len(name) >= 2}

    docsDir = _docsDir()
    if not docsDir.exists():
        return edges

    processed = 0
    matched = 0

    for code, node in nodeIdx.items():
        pqPath = docsDir / f"{code}.parquet"
        if not pqPath.exists():
            continue

        try:
            # 원재료 섹션만 — 최신 사업보고서(사업 or 12월)
            df = (
                pl.scan_parquet(str(pqPath))
                .filter(pl.col("section_title").str.contains("원재료"))
                .filter(pl.col("section_content").is_not_null())
                .select(["section_title", "section_content", "report_type"])
                .collect()
            )
        except (pl.exceptions.PolarsError, OSError):
            continue

        if df.height == 0:
            continue

        # 최신 사업보고서 우선
        latest = df.filter(pl.col("report_type").str.contains("사업보고서|12")).sort("report_type", descending=True)
        if latest.height == 0:
            latest = df

        processed += 1
        row = latest.row(0, named=True)
        content = row.get("section_content") or ""

        tables = extractTables(content)
        found = findTableByHeaders(tables, ["매입처"])
        if not found:
            continue

        table, hi = found
        rows = tableToRowDictsWithHeaderRow(table, hi, inheritColumns=["부문", "부 문"])

        for r in rows:
            supplierCol = next((k for k in r.keys() if "매입처" in k), None)
            if not supplierCol:
                continue
            supplierText = r[supplierCol]
            if not supplierText:
                continue
            supNames = extractCorpNames(supplierText)
            if not supNames:
                continue

            bumun = r.get("부 문", "").strip()
            # 소계/총계/※ 행 제외
            if any(skip in bumun for skip in ["소 계", "소계", "총 계", "총계", "※"]):
                continue

            product = r.get("품 목", "").strip()
            amount = parseAmount(r.get("매입액", ""))
            ratio = parsePercent(r.get("비중", ""))

            for supName in supNames:
                # 정규화 매칭
                normName = normalizeCorpName(supName)
                supCode = n2c.get(supName) or n2cNorm.get(normName)
                if not supCode or supCode == code:
                    continue

                matched += 1
                edges.append(
                    IndustryEdge(
                        fromCode=supCode,
                        fromName=c2n.get(supCode, supName),
                        toCode=code,
                        toName=c2n.get(code, ""),
                        edgeType="supplier",
                        industry=node.industry,
                        confidence=0.9,  # 테이블 직접 매칭 — 높은 신뢰도
                        source="docs_table",
                        evidence=f"{bumun} {product}".strip(),
                        product=product,
                        amount=amount,
                        ratio=ratio,
                    )
                )

    logger.info("원재료 테이블 엣지: %d사 스캔, %d건 매칭", processed, matched)
    return edges


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

    # 2. docs (텍스트 기반)
    if not skipDocs:
        try:
            docsEdges = extractDocsEdges(nodes)
            edges.extend(docsEdges)
            logger.info("docs 엣지: %d건", len(docsEdges))
        except Exception as e:
            logger.warning("docs 엣지 실패: %s", e)

        # 3. docs 원재료 테이블 (구조화 파싱)
        try:
            tableEdges = extractRawMaterialEdges(nodes)
            edges.extend(tableEdges)
            logger.info("원재료 테이블 엣지: %d건", len(tableEdges))
        except Exception as e:
            logger.warning("원재료 테이블 엣지 실패: %s", e)

    # 중복 제거 (from+to+type 기준, 테이블 우선)
    seen: set[tuple[str, str, str]] = set()
    unique: list[IndustryEdge] = []
    # source 우선순위: docs_table > docs > network
    priority = {"docs_table": 0, "docs": 1, "network": 2}
    edges.sort(key=lambda e: priority.get(e.source, 3))
    for e in edges:
        key = (e.fromCode, e.toCode, e.edgeType)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique
