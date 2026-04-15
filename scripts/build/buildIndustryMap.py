"""산업지도 시각화용 JSON 아티팩트 생성.

landing/static/map/에 3단계 레벨별 JSON을 생성한다:
- atlas.json: L1 — 34개 산업 + 산업간 플로우
- industries/{id}.json: L2 — 산업별 공정 + 노드 + 내부 엣지
- companies/{stockCode}.json: L3 — 회사 egograph (1홉 이웃)

사용법::

    uv run python scripts/build/buildIndustryMap.py
    uv run python scripts/build/buildIndustryMap.py --companies 100  # 상위 N개만
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dartlab.industry.build.pipeline import loadEdges, loadNodes  # noqa: E402
from dartlab.industry.taxonomy import getIndustry, loadTaxonomy  # noqa: E402

OUT_DIR = ROOT / "landing" / "static" / "map"


def _ensureDir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def buildAtlas() -> dict:
    """L1: 34개 산업 + 산업간 supplier 플로우."""
    nodes = loadNodes()
    edges = loadEdges()
    taxonomy = loadTaxonomy()

    # 산업별 집계
    industriesAgg: dict[str, dict] = {}
    for ind_id, ind_def in taxonomy.items():
        members = [n for n in nodes if n.industry == ind_id]
        totalRev = sum(n.revenue or 0 for n in members) / 1e8  # 억
        staged = [n for n in members if n.stage]

        stageMix: dict[str, int] = defaultdict(int)
        for n in staged:
            stageMix[n.stage] += 1

        industriesAgg[ind_id] = {
            "id": ind_id,
            "name": ind_def.name,
            "revenue": round(totalRev),
            "nodeCount": len(members),
            "stagedCount": len(staged),
            "stageMix": dict(stageMix),
            "stages": [{"key": s.key, "name": s.name, "role": s.role, "stream": s.stream} for s in ind_def.stages],
        }

    # 산업 간 플로우 (supplier 엣지 집계)
    flows: dict[tuple[str, str], dict] = {}
    codeToIndustry: dict[str, str] = {n.stockCode: n.industry for n in nodes}
    for e in edges:
        if e.edgeType != "supplier":
            continue
        fromInd = codeToIndustry.get(e.fromCode)
        toInd = codeToIndustry.get(e.toCode)
        if not fromInd or not toInd or fromInd == toInd:
            continue
        key = (fromInd, toInd)
        if key not in flows:
            flows[key] = {"fromIndustry": fromInd, "toIndustry": toInd, "edgeCount": 0, "amount": 0.0}
        flows[key]["edgeCount"] += 1
        flows[key]["amount"] += e.amount or 0

    flowList = sorted(flows.values(), key=lambda f: (f["amount"], f["edgeCount"]), reverse=True)[:50]

    return {
        "version": "2026-04-14",
        "industries": list(industriesAgg.values()),
        "flows": flowList,
    }


def buildIndustryDetail(industryId: str) -> dict:
    """L2: 산업 내부 공정 + 노드 + 엣지."""
    nodes = loadNodes()
    edges = loadEdges()
    ind_def = getIndustry(industryId)
    if not ind_def:
        return {}

    members = [n for n in nodes if n.industry == industryId]
    memberCodes = {n.stockCode for n in members}

    # 공정별 그룹화, 매출 정렬
    stages: dict[str, list[dict]] = defaultdict(list)
    for n in sorted(members, key=lambda x: x.revenue or 0, reverse=True):
        stages[n.stage or "unclassified"].append(
            {
                "stockCode": n.stockCode,
                "corpName": n.corpName,
                "stage": n.stage,
                "revenue": round((n.revenue or 0) / 1e8),  # 억
                "confidence": n.confidence,
                "source": n.source,
            }
        )

    # 내부 엣지 (양 끝이 같은 산업 소속)
    internalEdges = [
        {
            "from": e.fromCode,
            "to": e.toCode,
            "type": e.edgeType,
            "amount": e.amount,
            "ratio": e.ratio,
            "product": e.product,
            "confidence": e.confidence,
            "source": e.source,
        }
        for e in edges
        if e.fromCode in memberCodes and e.toCode in memberCodes
    ]

    totalRev = sum(n.revenue or 0 for n in members) / 1e8
    return {
        "industryId": industryId,
        "name": ind_def.name,
        "totalRevenue": round(totalRev),
        "nodeCount": len(members),
        "stages": [
            {
                "key": s.key,
                "name": s.name,
                "role": s.role,
                "stream": s.stream,
                "nodes": stages.get(s.key, []),
            }
            for s in ind_def.stages
        ],
        "unclassified": stages.get("unclassified", []),
        "edges": internalEdges,
    }


def buildCompanyEgograph(stockCode: str) -> dict:
    """L3: 회사 egograph (1홉 이웃)."""
    nodes = loadNodes()
    edges = loadEdges()

    ego = next((n for n in nodes if n.stockCode == stockCode), None)
    if not ego:
        return {}

    # 1홉 이웃
    neighbors: dict[str, dict] = {}
    egoEdges: list[dict] = []
    for e in edges:
        if e.fromCode == stockCode:
            neighbor = e.toCode
            direction = "out"
        elif e.toCode == stockCode:
            neighbor = e.fromCode
            direction = "in"
        else:
            continue

        n = next((x for x in nodes if x.stockCode == neighbor), None)
        if not n:
            continue

        if neighbor not in neighbors:
            neighbors[neighbor] = {
                "stockCode": n.stockCode,
                "corpName": n.corpName,
                "industry": n.industry,
                "stage": n.stage,
                "revenue": round((n.revenue or 0) / 1e8),
            }

        egoEdges.append(
            {
                "from": e.fromCode,
                "to": e.toCode,
                "direction": direction,
                "type": e.edgeType,
                "amount": e.amount,
                "ratio": e.ratio,
                "product": e.product,
                "confidence": e.confidence,
                "source": e.source,
                "evidence": e.evidence,
            }
        )

    return {
        "ego": {
            "stockCode": ego.stockCode,
            "corpName": ego.corpName,
            "industry": ego.industry,
            "stage": ego.stage,
            "role": ego.role,
            "stream": ego.stream,
            "revenue": round((ego.revenue or 0) / 1e8),
            "confidence": ego.confidence,
            "source": ego.source,
        },
        "neighbors": list(neighbors.values()),
        "edges": egoEdges,
    }


def buildEcosystem() -> dict:
    """전체 생태계 한 파일 — Cosmograph용 (nodes + links).

    2,664 노드 + 18,418 엣지를 flat 배열로. 산업별 색상 포함.
    """
    nodes = loadNodes()
    edges = loadEdges()
    taxonomy = loadTaxonomy()

    # 산업별 색상 팔레트 (34개)
    palette = [
        "#0ea5e9",
        "#f97316",
        "#10b981",
        "#8b5cf6",
        "#ec4899",
        "#eab308",
        "#06b6d4",
        "#14b8a6",
        "#f59e0b",
        "#ef4444",
        "#22c55e",
        "#6366f1",
        "#d946ef",
        "#84cc16",
        "#f43f5e",
        "#0891b2",
        "#7c3aed",
        "#a855f7",
        "#db2777",
        "#e11d48",
        "#16a34a",
        "#0d9488",
        "#2563eb",
        "#9333ea",
        "#c026d3",
        "#dc2626",
        "#ea580c",
        "#ca8a04",
        "#65a30d",
        "#059669",
        "#0284c7",
        "#4f46e5",
        "#9ca3af",
        "#6b7280",
    ]
    ind_color: dict[str, str] = {}
    for i, ind_id in enumerate(taxonomy.keys()):
        ind_color[ind_id] = palette[i % len(palette)]

    # 산업별 순위/점유율 사전계산
    # {industry: {stockCode: (rank, sharePct)}}
    industryRanks: dict[str, dict[str, tuple[int, float]]] = {}
    industryRevTotals: dict[str, float] = {}
    byIndustry: dict[str, list] = {}
    for n in nodes:
        byIndustry.setdefault(n.industry, []).append(n)
    for ind_id, members in byIndustry.items():
        total = sum(m.revenue or 0 for m in members)
        industryRevTotals[ind_id] = total
        ranked = sorted(members, key=lambda x: x.revenue or 0, reverse=True)
        ranks: dict[str, tuple[int, float]] = {}
        for i, m in enumerate(ranked, start=1):
            share = ((m.revenue or 0) / total * 100) if total > 0 else 0.0
            ranks[m.stockCode] = (i, share)
        industryRanks[ind_id] = ranks

    # stage key → stageName lookup (taxonomy 기반)
    def _stageNameOf(industryId: str, stageKey: str) -> str:
        if not stageKey or industryId not in taxonomy:
            return ""
        for s in taxonomy[industryId].stages:
            if s.key == stageKey:
                return s.name
        return stageKey

    # 노드 (Cosmograph 포맷)
    nodeList = []
    for n in nodes:
        rev_log = 1.0 if not n.revenue else max(1.0, min(20.0, 1.0 + (n.revenue / 1e11)))  # log-ish
        rank, share = industryRanks.get(n.industry, {}).get(n.stockCode, (0, 0.0))
        nodeList.append(
            {
                "id": n.stockCode,
                "label": n.corpName,
                "industry": n.industry,
                "industryName": taxonomy[n.industry].name if n.industry in taxonomy else n.industry,
                "stage": n.stage or "",
                "stageName": _stageNameOf(n.industry, n.stage or ""),
                "role": n.role or "",
                "stream": n.stream or "",
                "confidence": round(n.confidence, 2) if n.confidence else 0.0,
                "source": n.source or "",
                "revenue": n.revenue or 0,
                "industryRank": rank,
                "industryPeerCount": len(byIndustry.get(n.industry, [])),
                "marketShare": round(share, 2),
                "size": rev_log,
                "color": ind_color.get(n.industry, "#9ca3af"),
            }
        )

    # 엣지 (source/target ID 기반)
    linkList = []
    for e in edges:
        linkList.append(
            {
                "source": e.fromCode,
                "target": e.toCode,
                "type": e.edgeType,
                "amount": e.amount,
                "ratio": e.ratio,
                "product": e.product,
                "confidence": e.confidence,
                "source_tag": e.source,
            }
        )

    # 산업 메타 (필터 사이드바용)
    industries = []
    for ind_id, ind_def in taxonomy.items():
        count = sum(1 for n in nodes if n.industry == ind_id)
        industries.append(
            {
                "id": ind_id,
                "name": ind_def.name,
                "color": ind_color[ind_id],
                "count": count,
            }
        )
    industries.sort(key=lambda x: x["count"], reverse=True)

    return {
        "version": "2026-04-14",
        "industries": industries,
        "nodes": nodeList,
        "links": linkList,
    }


def buildSearchIndex() -> list[dict]:
    """회사명/코드 검색 인덱스."""
    nodes = loadNodes()
    return [
        {
            "stockCode": n.stockCode,
            "corpName": n.corpName,
            "industry": n.industry,
            "stage": n.stage,
            "revenue": round((n.revenue or 0) / 1e8),
        }
        for n in sorted(nodes, key=lambda x: x.revenue or 0, reverse=True)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", type=int, default=500, help="상위 N개사만 생성")
    parser.add_argument("--all-industries", action="store_true", help="모든 산업 상세 생성")
    args = parser.parse_args()

    _ensureDir(OUT_DIR)
    _ensureDir(OUT_DIR / "industries")
    _ensureDir(OUT_DIR / "companies")

    # 생태계 (Cosmograph용)
    print("[Ecosystem] ecosystem.json 생성...")
    eco = buildEcosystem()
    (OUT_DIR / "ecosystem.json").write_text(json.dumps(eco, ensure_ascii=False), encoding="utf-8")
    print(f"  - {len(eco['nodes'])} 노드, {len(eco['links'])} 엣지, {len(eco['industries'])} 산업")

    # L1 Atlas
    print("[L1] atlas.json 생성...")
    atlas = buildAtlas()
    (OUT_DIR / "atlas.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  - {len(atlas['industries'])}개 산업, {len(atlas['flows'])}개 플로우")

    # L2 Industries
    print("[L2] 산업 상세...")
    taxonomy = loadTaxonomy()
    for ind_id in taxonomy:
        detail = buildIndustryDetail(ind_id)
        (OUT_DIR / "industries" / f"{ind_id}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"  - {len(taxonomy)}개 산업 JSON 생성")

    # L3 Companies (상위 N개) + enrichment (AI insights, blog, 재무, 공급망 인사이트)
    print(f"[L3] 상위 {args.companies}개사 enrich egograph...")
    from dartlab.industry.build.enrichCompany import _loadBlogIndex, enrichCompanyData

    nodes = loadNodes()
    edges = loadEdges()
    blogIndex = _loadBlogIndex()
    print(f"  - 블로그 인덱스: {sum(len(v) for v in blogIndex.values())}건, {len(blogIndex)}사 커버")

    topCompanies = sorted(nodes, key=lambda n: n.revenue or 0, reverse=True)[: args.companies]
    enrichedCount = 0
    for n in topCompanies:
        ego = buildCompanyEgograph(n.stockCode)
        if not ego:
            continue
        try:
            enriched = enrichCompanyData(n.stockCode, ego, edges, nodes, blogIndex)
            if enriched.get("aiInsight") or enriched.get("blogPosts") or enriched.get("financials5y"):
                enrichedCount += 1
        except Exception as e:
            print(f"  ⚠ enrich 실패 ({n.stockCode}): {e}")
            enriched = ego

        (OUT_DIR / "companies" / f"{n.stockCode}.json").write_text(
            json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"  - {len(topCompanies)}개사 생성 (enrich: {enrichedCount}사)")

    # Search index
    print("[검색] search-index.json")
    searchIdx = buildSearchIndex()
    (OUT_DIR / "search-index.json").write_text(json.dumps(searchIdx, ensure_ascii=False), encoding="utf-8")
    print(f"  - {len(searchIdx)}개 종목")

    # Insight rankings (공급망 집중도/분산/허브/위험)
    print("[인사이트 랭킹] insights.json")
    import subprocess

    try:
        subprocess.run(
            ["python", "-X", "utf8", str(Path(__file__).parent / "buildInsightRankings.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        print("  - insights.json 생성")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ 인사이트 랭킹 생성 실패: {e.stderr}")

    print(f"\n완료: {OUT_DIR}")


if __name__ == "__main__":
    main()
