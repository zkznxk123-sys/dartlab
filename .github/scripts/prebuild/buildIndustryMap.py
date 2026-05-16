"""산업지도 시각화용 JSON 아티팩트 생성.

landing/static/map/에 3단계 레벨별 JSON을 생성한다:
- atlas.json: L1 — 34개 산업 + 산업간 플로우
- industries/{id}.json: L2 — 산업별 공정 + 노드 + 내부 엣지
- companies/{stockCode}.json: L3 — 회사 egograph (1홉 이웃)

사용법::

    uv run python .github/scripts/prebuild/buildIndustryMap.py
    uv run python .github/scripts/prebuild/buildIndustryMap.py --companies 100  # 상위 N개만
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dartlab.gather.krx.listing import getKrxList  # noqa: E402
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


def buildIndustryDetail(industryId: str, scanMetrics: dict[str, dict] | None = None) -> dict:
    """L2: 산업 내부 공정 + 노드 + 엣지."""
    nodes = loadNodes()
    edges = loadEdges()
    ind_def = getIndustry(industryId)
    if not ind_def:
        return {}
    if scanMetrics is None:
        scanMetrics = {}

    members = [n for n in nodes if n.industry == industryId]
    memberCodes = {n.stockCode for n in members}

    # 공정별 그룹화, 매출 정렬
    stages: dict[str, list[dict]] = defaultdict(list)
    for n in sorted(members, key=lambda x: x.revenue or 0, reverse=True):
        m = scanMetrics.get(n.stockCode, {})
        stages[n.stage or "unclassified"].append(
            {
                "stockCode": n.stockCode,
                "corpName": n.corpName,
                "stage": n.stage,
                "role": n.role,
                "stream": n.stream,
                "revenue": round((n.revenue or 0) / 1e8),  # 억
                "confidence": n.confidence,
                "source": n.source,
                "roe": _roundOrNone(m.get("roe")),
                "opMargin": _roundOrNone(m.get("opMargin")),
                "debtRatio": _roundOrNone(m.get("debtRatio")),
                "revCagr": _roundOrNone(m.get("revCagr")),
                "profGrade": m.get("profGrade") or "",
                "debtGrade": m.get("debtGrade") or "",
                "growthGrade": m.get("growthGrade") or "",
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


def _loadInsiderMetrics() -> dict[str, dict]:
    """scan/insider 에서 전 종목 소유구조 로드.

    Returns
    -------
    dict[str, dict]
        stockCode → {"holderPct", "holderChange", "treasuryShares", "stability"}
    """
    from dartlab.scan.insider import scanInsider

    metrics: dict[str, dict] = {}
    try:
        df = scanInsider()
        for r in df.iter_rows(named=True):
            code = r["stockCode"]
            metrics[code] = {
                "holderPct": r.get("holderPct"),
                "holderChange": r.get("holderChange"),
                "stability": r.get("stability") or "",
            }
    except Exception as e:
        print(f"  ⚠ insider 로드 실패: {e}")
    return metrics


def _loadScanMetrics() -> dict[str, dict]:
    """scan 엔진에서 전 종목 재무 지표를 한 번 로드하여 stockCode→dict 매핑 반환.

    Returns
    -------
    dict[str, dict]
        stockCode → {"roe": float|None, "opMargin": float|None,
                     "debtRatio": float|None, "icr": float|None,
                     "revCagr": float|None, "profGrade": str,
                     "debtGrade": str, "growthGrade": str}
    """
    from dartlab.scan import debt, growth, profitability

    metrics: dict[str, dict] = {}

    try:
        pdf = profitability()
        for r in pdf.iter_rows(named=True):
            code = r["종목코드"]
            metrics.setdefault(code, {})
            metrics[code]["roe"] = r.get("ROE")
            metrics[code]["opMargin"] = r.get("영업이익률")
            metrics[code]["profGrade"] = r.get("등급") or ""
    except Exception as e:
        print(f"  ⚠ profitability 로드 실패: {e}")

    try:
        ddf = debt()
        for r in ddf.iter_rows(named=True):
            code = r["종목코드"]
            metrics.setdefault(code, {})
            metrics[code]["debtRatio"] = r.get("부채비율")
            metrics[code]["icr"] = r.get("ICR")
            metrics[code]["debtGrade"] = r.get("위험등급") or ""
    except Exception as e:
        print(f"  ⚠ debt 로드 실패: {e}")

    try:
        gdf = growth()
        for r in gdf.iter_rows(named=True):
            code = r["종목코드"]
            metrics.setdefault(code, {})
            metrics[code]["revCagr"] = r.get("매출CAGR")
            metrics[code]["growthGrade"] = r.get("등급") or ""
    except Exception as e:
        print(f"  ⚠ growth 로드 실패: {e}")

    # ── 추가 7축 (등급 문자열만 — ecosystem.json 경량화) ──

    # governance (지배구조 A~E)
    try:
        from dartlab.scan.governance import scanGovernance

        gov = scanGovernance()
        for r in gov.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["govGrade"] = r.get("등급") or r.get("grade") or ""
    except Exception as e:
        print(f"  ⚠ governance 로드 실패: {e}")

    # cashflow (8종 패턴)
    try:
        from dartlab.scan.financial.cashflow import scanCashflow

        cf = scanCashflow()
        for r in cf.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["cfPattern"] = r.get("패턴") or r.get("pattern") or ""
    except Exception as e:
        print(f"  ⚠ cashflow 로드 실패: {e}")

    # audit (감사 리스크)
    try:
        from dartlab.scan.audit import scanAudit

        aud = scanAudit()
        for r in aud.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["auditRisk"] = r.get("위험등급") or r.get("riskGrade") or ""
    except Exception as e:
        print(f"  ⚠ audit 로드 실패: {e}")

    # quality (이익의 질)
    try:
        from dartlab.scan.financial.quality import scanQuality

        qual = scanQuality()
        for r in qual.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["qualGrade"] = r.get("등급") or r.get("grade") or ""
    except Exception as e:
        print(f"  ⚠ quality 로드 실패: {e}")

    # liquidity (유동성)
    try:
        from dartlab.scan.financial.liquidity import scanLiquidity

        liq = scanLiquidity()
        for r in liq.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["liqGrade"] = r.get("등급") or r.get("grade") or ""
    except Exception as e:
        print(f"  ⚠ liquidity 로드 실패: {e}")

    # capital (주주환원 분류)
    try:
        from dartlab.scan.capital import scanCapital

        cap = scanCapital()
        for r in cap.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            metrics[code]["capClass"] = r.get("환원분류") or r.get("returnClass") or ""
    except Exception as e:
        print(f"  ⚠ capital 로드 실패: {e}")

    # workforce (직원수)
    try:
        from dartlab.scan.workforce import scanWorkforce

        wf = scanWorkforce()
        for r in wf.iter_rows(named=True):
            code = r.get("종목코드") or r.get("stockCode")
            if not code:
                continue
            metrics.setdefault(code, {})
            emp = r.get("직원수") or r.get("empCount")
            if emp is not None:
                try:
                    metrics[code]["empCount"] = int(float(str(emp).replace(",", "")))
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        print(f"  ⚠ workforce 로드 실패: {e}")

    return metrics


def _roundOrNone(v, digits: int = 1):
    """숫자를 반올림하되 None/파싱불가 시 None 반환.

    scan 엔진의 float/str 혼재 값을 ecosystem.json 에 주입할 때
    안전하게 float 변환 + 반올림.

    Parameters
    ----------
    v : Any
        변환 대상. None, str("12.3"), float 모두 수용.
    digits : int
        소수점 자릿수. 기본 1.

    Returns
    -------
    float | None
        반올림된 값. 변환 불가 시 None.
    """
    if v is None:
        return None
    try:
        return round(float(v), digits)
    except (TypeError, ValueError):
        return None


def _computeLayout(nodes, taxonomy, atlasFlows=None, edges=None) -> dict[str, tuple[float, float]]:
    """관계 기반 2단계 hierarchical layout.

    L1 (산업 배치): atlasFlows를 가중치로 networkx Kamada-Kawai + PageRank 허브 중앙.
        강하게 연결된 산업끼리 가깝고, 허브 산업이 중심.
    L2 (산업 내 회사): 산업 중심 주변 golden spiral 배치 (매출 큰 순 = 안쪽).

    Parameters
    ----------
    nodes : list
        전종목 IndustryNode
    taxonomy : dict
        industry 분류
    atlasFlows : list[dict] | None
        atlas.json flows ({fromIndustry, toIndustry, edgeCount, amount})
        None이면 nodes 엣지로부터 집계 (fallback)

    Returns
    -------
    dict
        stockCode → (x, y) 좌표
    """
    import math

    import networkx as nx

    # 1. 산업별 그룹핑
    byIndustry: dict[str, list] = {}
    for n in nodes:
        byIndustry.setdefault(n.industry, []).append(n)

    allInds = list(byIndustry.keys())

    # 2. 산업 간 그래프 (flows 기반)
    G = nx.Graph()
    G.add_nodes_from(allInds)
    if atlasFlows:
        for f in atlasFlows:
            src = f.get("fromIndustry")
            dst = f.get("toIndustry")
            if src == dst or src not in byIndustry or dst not in byIndustry:
                continue
            # 가중치: amount 우선, 없으면 edgeCount
            w = f.get("amount") or (f.get("edgeCount", 1) * 1e9)
            # log 스케일로 편향 방지
            w = math.log1p(w / 1e9)
            if G.has_edge(src, dst):
                G[src][dst]["weight"] += w
            else:
                G.add_edge(src, dst, weight=w)

    # 3. PageRank로 허브 산업 식별
    if G.number_of_edges() > 0:
        pr = nx.pagerank(G, weight="weight")
    else:
        pr = {k: 0 for k in allInds}

    # 4. Kamada-Kawai 레이아웃 (flows 반영)
    if G.number_of_edges() > 0:
        try:
            pos = nx.kamada_kawai_layout(G, weight="weight", scale=5000)
        except Exception:
            pos = nx.spring_layout(G, weight="weight", k=2.0, iterations=200, seed=42, scale=5000)
    else:
        pos = nx.circular_layout(G, scale=5000)

    # 5. 중심점 스케일 보정 + 허브 중앙 정렬
    # pos는 단위원 기준 좌표. 허브 상위 3개의 중심을 (0,0)으로 시프트
    topHubs = sorted(pr, key=pr.get, reverse=True)[:3]
    if topHubs:
        hubCx = sum(pos[h][0] for h in topHubs) / len(topHubs)
        hubCy = sum(pos[h][1] for h in topHubs) / len(topHubs)
        for k in pos:
            pos[k] = (pos[k][0] - hubCx, pos[k][1] - hubCy)

    centers: dict[str, tuple[float, float]] = {k: (float(v[0]), float(v[1])) for k, v in pos.items()}

    # 6. 산업 간 최소 거리 보정 (회사 수 √ 기반 spread)
    indSpreads: dict[str, float] = {}
    for ind_id in allInds:
        cnt = len(byIndustry[ind_id])
        indSpreads[ind_id] = max(200, min(900, 45 * math.sqrt(cnt)))

    # 충돌 밀어내기: 최소 거리 = 양쪽 spread 합 + 200
    for _ in range(80):
        moved = False
        for a in range(len(allInds)):
            for b in range(a + 1, len(allInds)):
                ka, kb = allInds[a], allInds[b]
                ax, ay = centers[ka]
                bx, by = centers[kb]
                dx, dy = bx - ax, by - ay
                dist = math.sqrt(dx * dx + dy * dy) or 1
                minDist = indSpreads[ka] + indSpreads[kb] + 200
                if dist < minDist:
                    push = (minDist - dist) / 2 + 20
                    ux, uy = dx / dist, dy / dist
                    centers[ka] = (ax - ux * push, ay - uy * push)
                    centers[kb] = (bx + ux * push, by + uy * push)
                    moved = True
        if not moved:
            break

    # 7. 산업 내 노드: IndustryDrilldown 알고리즘 재현
    # stage별 격자 중심점 → stage 내부는 spring_layout (관련 회사끼리 가깝게)
    golden = math.pi * (3 - math.sqrt(5))
    coords: dict[str, tuple[float, float]] = {}

    # 산업별 내부 엣지 인덱싱
    internalEdges: dict[str, list[tuple[str, str, float]]] = {}
    if edges:
        nodeInd = {n.stockCode: n.industry for n in nodes}
        for e in edges:
            indA = nodeInd.get(e.fromCode)
            indB = nodeInd.get(e.toCode)
            if indA and indA == indB:
                w = (e.amount or 1e6) * (e.confidence or 0.5)
                w = math.log1p(w / 1e6)
                internalEdges.setdefault(indA, []).append((e.fromCode, e.toCode, w))

    for ind_id, members in byIndustry.items():
        cx, cy = centers[ind_id]
        spread = indSpreads[ind_id]
        indInternalEdges = internalEdges.get(ind_id, [])

        # stage별 그룹핑 → 초기 위치 anchor
        stageGroups: dict[str, list] = {}
        for m in members:
            stage = m.stage or "_unclassified"
            stageGroups.setdefault(stage, []).append(m)

        stageKeys = list(stageGroups.keys())
        cols = max(1, int(math.ceil(math.sqrt(len(stageKeys)))))
        rows = max(1, int(math.ceil(len(stageKeys) / cols)))

        # stage 중심점: 산업 중심 주변 격자 (initial position anchor)
        stageCenters: dict[str, tuple[float, float]] = {}
        for i, sk in enumerate(stageKeys):
            col = i % cols
            row = i // cols
            dx = (col - (cols - 1) / 2) * (spread * 0.7 / max(1, cols))
            dy = (row - (rows - 1) / 2) * (spread * 0.7 / max(1, rows))
            stageCenters[sk] = (cx + dx, cy + dy)

        # 전체 산업 노드를 하나의 spring_layout으로 (stage 초기 위치 + 전체 엣지)
        if len(members) >= 5 and len(indInternalEdges) >= 2:
            try:
                subG = nx.Graph()
                # 모든 회사 추가 (stage 중심 주변 random jitter로 초기 위치)
                initPos: dict[str, tuple[float, float]] = {}
                import random

                rng = random.Random(42)
                for m in members:
                    subG.add_node(m.stockCode)
                    scx, scy = stageCenters[m.stage or "_unclassified"]
                    # stage 중심 주변 약간의 랜덤 (spring_layout의 초기점 역할)
                    initPos[m.stockCode] = (
                        scx - cx + rng.uniform(-30, 30),
                        scy - cy + rng.uniform(-30, 30),
                    )
                # 모든 산업 내부 엣지 (stage 무관)
                for f, t, w in indInternalEdges:
                    if subG.has_node(f) and subG.has_node(t):
                        if subG.has_edge(f, t):
                            subG[f][t]["weight"] += w
                        else:
                            subG.add_edge(f, t, weight=w)

                # 초기 위치를 pos로 전달 → spring_layout이 starting point로 사용
                subPos = nx.spring_layout(
                    subG,
                    pos=initPos,
                    weight="weight",
                    k=spread / math.sqrt(len(members)) * 0.8,
                    iterations=50,  # 초기 위치 유지 위해 낮게
                    seed=42,
                    scale=spread * 0.9,
                )
                # 산업 중심점으로 평행이동
                avgX = sum(float(p[0]) for p in subPos.values()) / len(subPos)
                avgY = sum(float(p[1]) for p in subPos.values()) / len(subPos)
                for code, (px, py) in subPos.items():
                    coords[code] = (float(cx + px - avgX), float(cy + py - avgY))
                continue
            except Exception:
                pass

        # Fallback: stage 격자 + stage별 golden spiral
        for sk, stageMembers in stageGroups.items():
            scx, scy = stageCenters[sk]
            stageSpread = max(60, min(400, spread * 0.3))
            ranked = sorted(stageMembers, key=lambda x: x.revenue or 0, reverse=True)
            for j, n in enumerate(ranked):
                if j == 0:
                    coords[n.stockCode] = (scx, scy)
                else:
                    angle = golden * j
                    dist = stageSpread * math.sqrt(j) / math.sqrt(max(1, len(ranked)))
                    coords[n.stockCode] = (scx + dist * math.cos(angle), scy + dist * math.sin(angle))

    return coords


def _buildTimeline(outDir, companies):
    """companies/{code}.json의 financials5y에서 연도별 매출/OPM 추출 → timeline.json."""

    compDir = outDir / "companies"
    timeline: dict[str, dict[str, dict]] = {}  # year → stockCode → {revenue, opMargin}
    industryMap: dict[str, str] = {}  # stockCode → industry
    allYears: set[str] = set()

    for n in companies:
        code = n.stockCode
        fpath = compDir / f"{code}.json"
        if not fpath.exists():
            continue
        try:
            d = json.load(open(fpath, encoding="utf-8"))
        except Exception:
            continue

        industryMap[code] = n.industry
        for f in d.get("financials5y", []):
            year = str(f.get("year", ""))
            if not year:
                continue
            allYears.add(year)
            if year not in timeline:
                timeline[year] = {}
            sales = f.get("sales") or 0
            op = f.get("operating_profit")
            opMargin = round(op / sales * 100, 1) if sales and op else None
            timeline[year][code] = {
                "revenue": round(sales),
                "opMargin": opMargin,
            }

    # 산업별 집계
    sortedYears = sorted(allYears)
    industryTotals: dict[str, dict[str, dict]] = {}
    for year in sortedYears:
        industryTotals[year] = {}
        byInd: dict[str, list] = {}
        for code, data in timeline.get(year, {}).items():
            ind = industryMap.get(code, "unknown")
            byInd.setdefault(ind, []).append(data)
        for ind, entries in byInd.items():
            totalRev = sum(e["revenue"] for e in entries)
            opms = [e["opMargin"] for e in entries if e["opMargin"] is not None]
            industryTotals[year][ind] = {
                "totalRevenue": round(totalRev),
                "count": len(entries),
                "avgOpm": round(sum(opms) / len(opms), 1) if opms else None,
            }

    result = {
        "periods": sortedYears,
        "data": timeline,
        "industryTotals": industryTotals,
    }
    (outDir / "timeline.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"  - {len(sortedYears)}개 연도 × {sum(len(v) for v in timeline.values())}건")


def buildEcosystem(
    scanMetrics: dict[str, dict] | None = None,
    yoyDeltas: dict[str, dict] | None = None,
    insiderMetrics: dict[str, dict] | None = None,
    atlasFlows: list[dict] | None = None,
) -> dict:
    """전체 생태계 한 파일 — Cosmograph용 (nodes + links).

    전 상장사 노드 + 공급망 엣지를 flat 배열로. 산업별 색상 + scan 재무 지표 + YoY delta 포함.
    """
    nodes = loadNodes()
    edges = loadEdges()
    taxonomy = loadTaxonomy()
    if scanMetrics is None:
        scanMetrics = _loadScanMetrics()
    if yoyDeltas is None:
        yoyDeltas = {}
    if insiderMetrics is None:
        insiderMetrics = {}

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

    # 좌표 사전 계산 (관계 기반 — 산업 간 + 산업 내부 force-directed)
    coords = _computeLayout(nodes, taxonomy, atlasFlows=atlasFlows, edges=edges)

    # KRX 시장구분 (KOSPI/KOSDAQ/KONEX) 매핑 — ecosystem.json 노드 보강용
    try:
        krxList = getKrxList()
        marketByCode = {
            r["short_code"]: r["marketName"]
            for r in krxList.iter_rows(named=True)
            if r.get("short_code") and r.get("marketName")
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[map] KRX list 로드 실패 — market 필드 비움: {exc}", file=sys.stderr)
        marketByCode = {}

    # 노드 (Cosmograph 포맷)
    nodeList = []
    for n in nodes:
        rev_log = 1.0 if not n.revenue else max(1.0, min(20.0, 1.0 + (n.revenue / 1e11)))  # log-ish
        rank, share = industryRanks.get(n.industry, {}).get(n.stockCode, (0, 0.0))
        m = scanMetrics.get(n.stockCode, {})
        d = yoyDeltas.get(n.stockCode, {})
        ins = insiderMetrics.get(n.stockCode, {})
        nodeList.append(
            {
                "id": n.stockCode,
                "label": n.corpName,
                "market": marketByCode.get(n.stockCode, ""),
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
                # scan 엔진 재무 지표 (색상/정렬 기준)
                "roe": _roundOrNone(m.get("roe")),
                "opMargin": _roundOrNone(m.get("opMargin")),
                "debtRatio": _roundOrNone(m.get("debtRatio")),
                "icr": _roundOrNone(m.get("icr")),
                "revCagr": _roundOrNone(m.get("revCagr")),
                "profGrade": m.get("profGrade") or "",
                "debtGrade": m.get("debtGrade") or "",
                "growthGrade": m.get("growthGrade") or "",
                # YoY delta (전년 대비 변화)
                "roeDelta": d.get("roeDelta"),
                "opMarginDelta": d.get("opMarginDelta"),
                "debtRatioDelta": d.get("debtRatioDelta"),
                "revenueYoyPct": d.get("revenueYoyPct"),
                "deltaYear": d.get("asOfYear"),
                # insider 소유구조
                "holderPct": _roundOrNone(ins.get("holderPct")),
                "holderChange": _roundOrNone(ins.get("holderChange")),
                "stability": ins.get("stability") or "",
                # scan 7축 등급 (문자열만)
                "govGrade": m.get("govGrade") or "",
                "cfPattern": m.get("cfPattern") or "",
                "auditRisk": m.get("auditRisk") or "",
                "qualGrade": m.get("qualGrade") or "",
                "liqGrade": m.get("liqGrade") or "",
                "capClass": m.get("capClass") or "",
                "empCount": m.get("empCount"),
                "size": rev_log,
                "color": ind_color.get(n.industry, "#9ca3af"),
                "x": round(coords.get(n.stockCode, (0, 0))[0], 1),
                "y": round(coords.get(n.stockCode, (0, 0))[1], 1),
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

    # 산업별 convex hull 계산 (클러스터 배경 영역)
    def _convexHull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Graham scan으로 convex hull 계산."""

        pts = sorted(set(points))
        if len(pts) <= 2:
            return pts

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        upper = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return lower[:-1] + upper[:-1]

    indHulls: dict[str, list] = {}
    # nodeList에서 산업별 좌표 수집
    indPoints: dict[str, list[tuple[float, float]]] = {}
    for nd in nodeList:
        ind = nd["industry"]
        if nd.get("x") is not None and nd.get("y") is not None:
            indPoints.setdefault(ind, []).append((nd["x"], nd["y"]))
    for ind_id, pts in indPoints.items():
        if len(pts) >= 3:
            hull = _convexHull(pts)
            # padding: hull 확장 (중심에서 바깥으로 15% 확장)
            cx = sum(p[0] for p in hull) / len(hull)
            cy = sum(p[1] for p in hull) / len(hull)
            expanded = []
            for px, py in hull:
                dx, dy = px - cx, py - cy
                expanded.append([round(px + dx * 0.15, 1), round(py + dy * 0.15, 1)])
            indHulls[ind_id] = expanded

    # 산업 메타 — semantic zoom용 centroid + 집계
    # 각 산업 = 소속 회사의 평균 위치 (줌 전환 시 공간 일치)
    industries = []
    nodeByCode = {nd["id"]: nd for nd in nodeList}
    for ind_id, ind_def in taxonomy.items():
        memberNodes = [nd for nd in nodeList if nd["industry"] == ind_id]
        count = len(memberNodes)
        if count == 0:
            continue

        xs = [nd["x"] for nd in memberNodes]
        ys = [nd["y"] for nd in memberNodes]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        # radius: 회사 분산 기반 (줌 아웃 시 산업 버블 크기)
        maxDist = max(((nd["x"] - cx) ** 2 + (nd["y"] - cy) ** 2) ** 0.5 for nd in memberNodes)
        radius = max(80, maxDist * 1.1)

        totalRev = sum(nd["revenue"] for nd in memberNodes)

        entry = {
            "id": ind_id,
            "name": ind_def.name,
            "color": ind_color[ind_id],
            "count": count,
            "x": round(cx, 1),
            "y": round(cy, 1),
            "radius": round(radius, 1),
            "totalRevenue": round(totalRev),
        }
        if ind_id in indHulls:
            entry["hull"] = indHulls[ind_id]
        industries.append(entry)
    industries.sort(key=lambda x: x["count"], reverse=True)

    # 산업간 flow 집계 (회사간 엣지 → industry_pair)
    flowMap: dict[tuple[str, str], dict] = {}
    for e in edges:
        indA = nodeByCode.get(e.fromCode, {}).get("industry") if e.fromCode in nodeByCode else None
        indB = nodeByCode.get(e.toCode, {}).get("industry") if e.toCode in nodeByCode else None
        if not indA or not indB or indA == indB:
            continue
        key = (indA, indB)
        if key not in flowMap:
            flowMap[key] = {"edgeCount": 0, "amount": 0.0}
        flowMap[key]["edgeCount"] += 1
        flowMap[key]["amount"] += e.amount or 0

    industryFlows = [
        {
            "fromIndustry": src,
            "toIndustry": dst,
            "edgeCount": data["edgeCount"],
            "amount": round(data["amount"]),
        }
        for (src, dst), data in flowMap.items()
    ]
    # 중요도 순으로 상위 flow만 (너무 많으면 스파게티)
    industryFlows.sort(key=lambda f: f["amount"] or f["edgeCount"], reverse=True)
    industryFlows = industryFlows[:80]

    return {
        "version": "2026-04-14",
        "industries": industries,
        "industryFlows": industryFlows,
        "nodes": nodeList,
        "links": linkList,
    }


def buildIndustryStats(scanMetrics: dict[str, dict]) -> dict:
    """산업별 사전 집계 — `industryStats.json` 산출.

    각 산업에 대해:
    - 평균 ROE / 영업이익률 / 매출 CAGR / HHI (HHI 는 insights.json 에 기업별로 있음)
    - Top 5: 수익성 / 성장 / 위험신호
    - 공급 흐름: 어디로 보내고 어디서 받는지 Top 5 (atlas.flows 활용)

    Returns
    -------
    dict
        {industryId: {avgRoe, avgOpMargin, avgCagr, count,
                      topRoe, topGrowth, riskFlags,
                      supplyTo, supplyFrom}}
    """
    nodes = loadNodes()
    edges = loadEdges()
    taxonomy = loadTaxonomy()

    # 산업 → primary 노드 + scan 지표 결합
    byIndustry: dict[str, list[dict]] = {}
    for n in nodes:
        if not n.primary:
            continue
        m = scanMetrics.get(n.stockCode, {})
        byIndustry.setdefault(n.industry, []).append(
            {
                "stockCode": n.stockCode,
                "corpName": n.corpName,
                "revenue": n.revenue or 0,
                "roe": m.get("roe"),
                "opMargin": m.get("opMargin"),
                "debtRatio": m.get("debtRatio"),
                "revCagr": m.get("revCagr"),
                "profGrade": m.get("profGrade") or "",
                "debtGrade": m.get("debtGrade") or "",
                "growthGrade": m.get("growthGrade") or "",
            }
        )

    # 산업간 supplier flow (atlas.flows 와 동일 로직 — 모든 flow 보존)
    codeToIndustry = {n.stockCode: n.industry for n in nodes}
    flows: dict[tuple[str, str], dict] = {}
    for e in edges:
        if e.edgeType != "supplier":
            continue
        fi = codeToIndustry.get(e.fromCode)
        ti = codeToIndustry.get(e.toCode)
        if not fi or not ti or fi == ti:
            continue
        key = (fi, ti)
        if key not in flows:
            flows[key] = {"fromIndustry": fi, "toIndustry": ti, "edgeCount": 0, "amount": 0.0}
        flows[key]["edgeCount"] += 1
        flows[key]["amount"] += e.amount or 0

    # 산업별 in/out flow 집계
    flowsByFrom: dict[str, list[dict]] = {}
    flowsByTo: dict[str, list[dict]] = {}
    for f in flows.values():
        flowsByFrom.setdefault(f["fromIndustry"], []).append(f)
        flowsByTo.setdefault(f["toIndustry"], []).append(f)

    def _avg(vs: list) -> float | None:
        cleaned = [v for v in vs if v is not None]
        return round(sum(cleaned) / len(cleaned), 2) if cleaned else None

    def _distribution(vs: list) -> dict | None:
        """분포 통계 — p10/p25/median/p75/p90/mean/std/n.

        표본 < 3 이면 None 반환 (의미 없는 분포).
        """
        cleaned = sorted(v for v in vs if v is not None)
        n = len(cleaned)
        if n < 3:
            return None

        def _quantile(q: float) -> float:
            """linear interpolation quantile."""
            if n == 1:
                return cleaned[0]
            pos = q * (n - 1)
            lo = int(pos)
            hi = min(lo + 1, n - 1)
            frac = pos - lo
            return cleaned[lo] * (1 - frac) + cleaned[hi] * frac

        mean = sum(cleaned) / n
        variance = sum((v - mean) ** 2 for v in cleaned) / n
        std = variance**0.5
        return {
            "n": n,
            "p10": round(_quantile(0.10), 2),
            "p25": round(_quantile(0.25), 2),
            "median": round(_quantile(0.50), 2),
            "p75": round(_quantile(0.75), 2),
            "p90": round(_quantile(0.90), 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
        }

    def _industryNameOf(iid: str) -> str:
        return taxonomy[iid].name if iid in taxonomy else iid

    out: dict = {}
    for indId, members in byIndustry.items():
        # 평균 (None 제외)
        avgRoe = _avg([m["roe"] for m in members])
        avgOp = _avg([m["opMargin"] for m in members])
        avgCagr = _avg([m["revCagr"] for m in members])

        # Top 5 — None 제외 정렬
        sortedRoe = sorted([m for m in members if m["roe"] is not None], key=lambda x: x["roe"], reverse=True)[:5]
        sortedGrowth = sorted(
            [m for m in members if m["revCagr"] is not None], key=lambda x: x["revCagr"], reverse=True
        )[:5]
        # 위험: 부채 등급 위험/주의 + ROE 음수
        risks = [m for m in members if m.get("debtGrade") == "위험" or (m.get("roe") is not None and m["roe"] < 0)]
        risks.sort(key=lambda x: (x.get("debtRatio") or 0), reverse=True)
        riskFlags = risks[:5]

        # supply flows
        supplyTo = sorted(flowsByFrom.get(indId, []), key=lambda x: x["amount"], reverse=True)[:5]
        supplyFrom = sorted(flowsByTo.get(indId, []), key=lambda x: x["amount"], reverse=True)[:5]

        # 분포 통계 (업종 정규화용)
        distribution = {
            "roe": _distribution([m["roe"] for m in members]),
            "opMargin": _distribution([m["opMargin"] for m in members]),
            "debtRatio": _distribution([m["debtRatio"] for m in members]),
            "revCagr": _distribution([m["revCagr"] for m in members]),
        }

        out[indId] = {
            "name": _industryNameOf(indId),
            "count": len(members),
            "distribution": distribution,
            "avgRoe": avgRoe,
            "avgOpMargin": avgOp,
            "avgCagr": avgCagr,
            "topRoe": [
                {"stockCode": m["stockCode"], "corpName": m["corpName"], "roe": m["roe"], "revenue": m["revenue"]}
                for m in sortedRoe
            ],
            "topGrowth": [
                {
                    "stockCode": m["stockCode"],
                    "corpName": m["corpName"],
                    "revCagr": m["revCagr"],
                    "revenue": m["revenue"],
                }
                for m in sortedGrowth
            ],
            "riskFlags": [
                {
                    "stockCode": m["stockCode"],
                    "corpName": m["corpName"],
                    "debtRatio": m["debtRatio"],
                    "debtGrade": m["debtGrade"],
                    "roe": m["roe"],
                }
                for m in riskFlags
            ],
            "supplyTo": [
                {**f, "fromName": _industryNameOf(f["fromIndustry"]), "toName": _industryNameOf(f["toIndustry"])}
                for f in supplyTo
            ],
            "supplyFrom": [
                {**f, "fromName": _industryNameOf(f["fromIndustry"]), "toName": _industryNameOf(f["toIndustry"])}
                for f in supplyFrom
            ],
        }

    return out


def buildMovers(
    scanMetrics: dict[str, dict],
    yoyDeltas: dict[str, dict],
    indStats: dict,
) -> dict:
    """변화 감지 — 급변 회사 Top N.

    카테고리
    --------
    - **profitImprove**: ROE 개선 상위 (Δ > 0, |z| ≥ 1.5 in industry)
    - **profitDecline**: ROE 악화 상위 (Δ < 0, |z| ≥ 1.5)
    - **revenueSpike**: 매출 YoY 급증 상위 (> +30%)
    - **revenueDrop**: 매출 YoY 급락 상위 (< -20%)
    - **debtStress**: 부채비율 급증 (+20%p 이상 AND 최종 > 150%)
    - **extremeWarning**: |ROE Δ| > 100%p 등 극단 이상치 — 검증 필요

    각 항목은 "왜 급변인가" 1줄 노트 포함 (재분류/회계이슈 주의).
    """
    nodes = loadNodes()
    taxonomy = loadTaxonomy()
    codeMeta = {n.stockCode: n for n in nodes if n.primary}

    def _entry(code: str, extras: dict) -> dict | None:
        n = codeMeta.get(code)
        if not n:
            return None
        ind = taxonomy[n.industry].name if n.industry in taxonomy else n.industry
        m = scanMetrics.get(code, {})
        d = yoyDeltas.get(code, {})
        return {
            "stockCode": code,
            "corpName": n.corpName,
            "industry": n.industry,
            "industryName": ind,
            "revenue": n.revenue or 0,
            "roe": m.get("roe"),
            "opMargin": m.get("opMargin"),
            "debtRatio": m.get("debtRatio"),
            "roeDelta": d.get("roeDelta"),
            "opMarginDelta": d.get("opMarginDelta"),
            "debtRatioDelta": d.get("debtRatioDelta"),
            "revenueYoyPct": d.get("revenueYoyPct"),
            "asOfYear": d.get("asOfYear"),
            **extras,
        }

    # 산업별 ROE 분포로 industry-aware z-score 계산
    def _roe_zscore(code: str) -> float | None:
        n = codeMeta.get(code)
        if not n:
            return None
        roe = scanMetrics.get(code, {}).get("roe")
        if roe is None:
            return None
        dist = indStats.get(n.industry, {}).get("distribution", {}).get("roe")
        if not dist or not dist.get("std"):
            return None
        return (roe - dist["mean"]) / dist["std"]

    profit_improve = []
    profit_decline = []
    revenue_spike = []
    revenue_drop = []
    debt_stress = []
    extreme_warn = []

    for code, d in yoyDeltas.items():
        m = scanMetrics.get(code, {})
        # Extreme (검증 필요)
        if d.get("roeDelta") is not None and abs(d["roeDelta"]) > 100:
            e = _entry(
                code,
                {
                    "signal": f"ROE Δ{d['roeDelta']:+.1f}%p — 극단 변화",
                    "note": "1회성 이익/자본잠식/재분류 가능성. 원본 공시 검증 필요.",
                },
            )
            if e:
                extreme_warn.append(e)
            continue  # 정상 카테고리엔 넣지 않음

        # Revenue YoY
        rev_yoy = d.get("revenueYoyPct")
        if rev_yoy is not None:
            if rev_yoy >= 30:
                e = _entry(
                    code,
                    {
                        "signal": f"매출 YoY +{rev_yoy:.1f}% — 고성장",
                        "note": f"{d.get('priorYear')}→{d.get('asOfYear')} 매출 급증. 신제품/시장 확대 가능성.",
                    },
                )
                if e:
                    revenue_spike.append(e)
            elif rev_yoy <= -20:
                e = _entry(
                    code,
                    {
                        "signal": f"매출 YoY {rev_yoy:+.1f}% — 급락",
                        "note": f"{d.get('priorYear')}→{d.get('asOfYear')} 매출 급감. 수요 둔화/고객사 이탈 의심.",
                    },
                )
                if e:
                    revenue_drop.append(e)

        # ROE 개선/악화 (industry-aware z-score)
        roe_d = d.get("roeDelta")
        if roe_d is not None:
            z = _roe_zscore(code)
            if z is not None and abs(z) >= 1.5:
                if roe_d > 0:
                    e = _entry(
                        code,
                        {
                            "signal": f"ROE Δ{roe_d:+.1f}%p · 산업 z={z:+.1f}σ",
                            "note": "수익성 개선. 원인은 본업 회복/일회성 여부 확인.",
                        },
                    )
                    if e:
                        profit_improve.append(e)
                elif roe_d < 0:
                    e = _entry(
                        code,
                        {
                            "signal": f"ROE Δ{roe_d:+.1f}%p · 산업 z={z:+.1f}σ",
                            "note": "수익성 악화. 마진 압박/일회성 손실 가능성.",
                        },
                    )
                    if e:
                        profit_decline.append(e)

        # 부채 스트레스
        debt_d = d.get("debtRatioDelta")
        debt_now = m.get("debtRatio")
        if debt_d is not None and debt_now is not None and debt_d >= 20 and debt_now > 150:
            e = _entry(
                code,
                {
                    "signal": f"부채비율 {debt_now:.0f}% (+{debt_d:.0f}%p)",
                    "note": "부채 급증 + 높은 절대값. 재무 스트레스 신호.",
                },
            )
            if e:
                debt_stress.append(e)

    def _top_by(arr: list, key: str, reverse=True, n=20) -> list:
        arr.sort(key=lambda x: abs(x.get(key) or 0), reverse=reverse)
        return arr[:n]

    return {
        "asOf": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "categories": {
            "profitImprove": {
                "title": "수익성 개선 (ROE)",
                "description": "산업 평균 대비 유의미하게 ROE 가 개선된 기업 (industry z-score ≥ 1.5σ, Δ > 0).",
                "entries": _top_by(profit_improve, "roeDelta"),
            },
            "profitDecline": {
                "title": "수익성 악화 (ROE)",
                "description": "산업 평균 대비 유의미하게 ROE 가 악화된 기업. 마진 압박 또는 1회성 손실 의심.",
                "entries": _top_by(profit_decline, "roeDelta"),
            },
            "revenueSpike": {
                "title": "매출 급증 (YoY +30% 이상)",
                "description": "전년 대비 매출이 크게 성장한 기업. 신제품/시장 확대 가능성.",
                "entries": _top_by(revenue_spike, "revenueYoyPct"),
            },
            "revenueDrop": {
                "title": "매출 급락 (YoY -20% 이하)",
                "description": "전년 대비 매출이 크게 감소한 기업. 수요 둔화/고객사 이탈 의심.",
                "entries": _top_by(revenue_drop, "revenueYoyPct"),
            },
            "debtStress": {
                "title": "부채 스트레스",
                "description": "부채비율이 +20%p 이상 증가하고 현재 150%+ 인 기업. 재무 리스크 조기 신호.",
                "entries": _top_by(debt_stress, "debtRatioDelta"),
            },
            "extremeWarning": {
                "title": "⚠ 극단 변화 — 검증 필요",
                "description": "ROE 변화 |100%p| 초과. 재분류·자본잠식·1회성 이익 등 회계 이슈 가능성. 수동 검증 권장.",
                "entries": _top_by(extreme_warn, "roeDelta"),
            },
        },
        "disclaimer": "규칙 기반 스캐너. 재분류/합병/분할상장 노이즈 구분 불가. 투자 판단 전 원본 공시 확인 필수.",
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
    parser.add_argument(
        "--companies",
        type=int,
        default=0,
        help="상위 N개사만 enrich (0 = 전 종목, 기본). 빠른 개발 빌드 시 500 등 지정",
    )
    parser.add_argument("--all-industries", action="store_true", help="모든 산업 상세 생성")
    args = parser.parse_args()

    _ensureDir(OUT_DIR)
    _ensureDir(OUT_DIR / "industries")
    _ensureDir(OUT_DIR / "companies")

    # scan 재무 지표 — 한 번만 로드 후 전 파일 공유
    print("[Scan] 재무 지표 로드 중 (profitability + debt + growth)...")
    scanMetrics = _loadScanMetrics()
    print(f"  - scan 커버: {len(scanMetrics)}종목")

    # insider 소유구조
    print("[Insider] 소유구조 로드 중 (holderPct + stability)...")
    insiderMetrics = _loadInsiderMetrics()
    print(f"  - insider 커버: {len(insiderMetrics)}종목")

    # YoY delta 사전 계산 (전년 대비 변화)
    print("[Delta] YoY 재무 변화 계산 중...")
    from dartlab.industry.build.delta import computeYoyDelta

    yoyDeltas = computeYoyDelta()
    print(f"  - YoY delta 커버: {len(yoyDeltas)}종목")

    # L1 Atlas (먼저 — ecosystem 레이아웃이 flows 사용)
    print("[L1] atlas.json 생성...")
    atlas = buildAtlas()
    (OUT_DIR / "atlas.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  - {len(atlas['industries'])}개 산업, {len(atlas['flows'])}개 플로우")

    # 생태계 (Cosmograph용) — flows 기반 관계 레이아웃
    print("[Ecosystem] ecosystem.json 생성...")
    eco = buildEcosystem(scanMetrics, yoyDeltas, insiderMetrics, atlasFlows=atlas.get("flows", []))
    (OUT_DIR / "ecosystem.json").write_text(json.dumps(eco, ensure_ascii=False), encoding="utf-8")
    print(f"  - {len(eco['nodes'])} 노드, {len(eco['links'])} 엣지, {len(eco['industries'])} 산업")

    # L2 Industries
    print("[L2] 산업 상세...")
    taxonomy = loadTaxonomy()
    for ind_id in taxonomy:
        detail = buildIndustryDetail(ind_id, scanMetrics)
        (OUT_DIR / "industries" / f"{ind_id}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"  - {len(taxonomy)}개 산업 JSON 생성")

    # L3 Companies enrichment (AI insights, blog, 재무, 공급망 인사이트, 2-hop)
    # --companies 0 (기본) = 전 종목 enrich. 양수면 상위 N개만
    from dartlab.industry.build.enrichCompany import _loadBlogIndex, enrichCompanyData

    nodes = loadNodes()
    edges = loadEdges()
    blogIndex = _loadBlogIndex()
    print(f"  - 블로그 인덱스: {sum(len(v) for v in blogIndex.values())}건, {len(blogIndex)}사 커버")

    # 2-hop 공급망 사전 계산
    from dartlab.industry.build.hop2 import computeHop2

    print("  - 2-hop 공급망 사전 계산...")
    hop2Data = computeHop2()
    print(f"    · {len(hop2Data)} 종목 × hop2 (허브는 1.5-hop 제한)")

    sortedCompanies = sorted(nodes, key=lambda n: n.revenue or 0, reverse=True)
    if args.companies > 0:
        topCompanies = sortedCompanies[: args.companies]
        print(f"[L3] 상위 {len(topCompanies)}개사 enrich egograph (개발용 제한)...")
    else:
        topCompanies = sortedCompanies
        print(f"[L3] 전 종목 {len(topCompanies)}사 enrich egograph...")
    enrichedCount = 0
    for n in topCompanies:
        ego = buildCompanyEgograph(n.stockCode)
        if not ego:
            continue
        try:
            enriched = enrichCompanyData(n.stockCode, ego, edges, nodes, blogIndex, hop2Data)
            if enriched.get("aiInsight") or enriched.get("blogPosts") or enriched.get("financials5y"):
                enrichedCount += 1
        except Exception as e:
            print(f"  ⚠ enrich 실패 ({n.stockCode}): {e}")
            enriched = ego

        (OUT_DIR / "companies" / f"{n.stockCode}.json").write_text(
            json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"  - {len(topCompanies)}개사 생성 (enrich: {enrichedCount}사)")

    # 타임라인 (연도별 산업 변화)
    print("[타임라인] timeline.json 생성...")
    _buildTimeline(OUT_DIR, topCompanies)

    # 산업 통계 (사용자 가치 인사이트)
    print("[산업 통계] industryStats.json")
    indStats = buildIndustryStats(scanMetrics)
    (OUT_DIR / "industryStats.json").write_text(json.dumps(indStats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  - {len(indStats)}개 산업 (avgRoe + topN + supply flows)")

    # Movers — 급변 회사 Top N (변화 감지)
    print("[변화 감지] movers.json")
    movers = buildMovers(scanMetrics, yoyDeltas, indStats)
    (OUT_DIR / "movers.json").write_text(json.dumps(movers, ensure_ascii=False, indent=2), encoding="utf-8")
    cat_counts = {k: len(v["entries"]) for k, v in movers["categories"].items()}
    print(f"  - {sum(cat_counts.values())}건 (카테고리별: {cat_counts})")

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

    # RSS + iCal feeds (변화 감지 구독)
    print("[피드] RSS + iCal 생성")
    try:
        subprocess.run(
            ["python", "-X", "utf8", str(Path(__file__).parent / "buildFeeds.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        print("  - feed/movers.xml · feed/industry/*.xml · feed/calendar.ics")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ 피드 생성 실패: {e.stderr}")

    # 메타데이터: 빌드 시각 + 데이터 소스별 최신성
    print("[메타] meta.json")
    meta = _buildMeta()
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  - buildId={meta['buildId']}, dart={meta['dataAsOf'].get('dart', '?')}")

    print(f"\n완료: {OUT_DIR}")

    # HF 업로드 — HF_TOKEN 있을 때만. landing 빌드가 여기서 pull 해 가는 구조.
    _uploadToHf()


def _uploadToHf() -> None:
    """생성된 map JSON 을 HF dataset 에 업로드 (SSoT). HF_TOKEN 없으면 스킵."""
    import os

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[map] HF_TOKEN 없음 → HF 업로드 스킵 (로컬 파일만 생성)")
        return

    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    cfg = DATA_RELEASES["industryMap"]
    dirPath = cfg["dir"]

    fileCount = sum(1 for p in OUT_DIR.rglob("*") if p.is_file())
    print(f"[map] HF 업로드: {fileCount}개 파일 → {HF_REPO}/{dirPath}/")

    api = HfApi(token=token)
    api.upload_folder(
        repo_id=HF_REPO,
        repo_type="dataset",
        folder_path=str(OUT_DIR),
        path_in_repo=dirPath,
        commit_message=f"map: auto-rebuild {fileCount} files",
    )
    print("[map] HF 업로드 완료")


def _buildMeta() -> dict:
    """meta.json — 빌드·데이터 신선도.

    각 소스(dart / finance / scan / reviews)의 최근 갱신 시각을 포함.
    프런트는 이 값으로 우상단 배지("DART 3h · Finance 2Q25 · Reviews 1d")를 표시.
    """

    def _mtime_iso(path: Path) -> str | None:
        if not path.exists():
            return None
        ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _latest_mtime(dir_path: Path, pattern: str = "*") -> str | None:
        if not dir_path.exists():
            return None
        files = list(dir_path.rglob(pattern))
        if not files:
            return None
        latest = max(f.stat().st_mtime for f in files if f.is_file())
        return datetime.fromtimestamp(latest, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    data_dir = ROOT / "data" / "dart"
    blog_dir = ROOT / "blog" / "05-company-reports"

    # finance parquet 가장 최근 갱신
    finance_mtime = _latest_mtime(data_dir / "scan", "*.parquet")
    # docs parquet (공시 원문)
    docs_mtime = _latest_mtime(data_dir / "docs", "*.parquet")
    # 블로그 분석글 최근 갱신
    reviews_mtime = _latest_mtime(blog_dir, "index.md")
    # taxonomy/nodes (산업 분류)
    taxonomy_mtime = _mtime_iso(ROOT / "src/dartlab/industry/taxonomy.json")

    # git sha (있으면)
    commit_sha = None
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=5,
        )
        if r.returncode == 0:
            commit_sha = r.stdout.strip()
    except Exception:
        pass

    # 산출물 크기
    sizes = {}
    for name in ["ecosystem.json", "atlas.json", "insights.json", "industryStats.json", "search-index.json"]:
        p = OUT_DIR / name
        if p.exists():
            sizes[name] = p.stat().st_size
    companies_dir = OUT_DIR / "companies"
    if companies_dir.exists():
        sizes["companies/"] = sum(f.stat().st_size for f in companies_dir.iterdir() if f.is_file())

    return {
        "schemaVersion": 1,
        "buildId": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "buildTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commitSha": commit_sha,
        "dataAsOf": {
            "dart": docs_mtime,
            "finance": finance_mtime,
            "reviews": reviews_mtime,
            "taxonomy": taxonomy_mtime,
        },
        "sizes": sizes,
        "counts": {
            # industryStats 등 이미 산출된 파일 라인 카운트는 프런트에서 fetch 시 확인
        },
    }


if __name__ == "__main__":
    main()
