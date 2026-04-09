"""CompanyGraph 빌더 — Company × 14축 calc → 인과 그래프.

review의 6막 인과 연결을 명시적 그래프로 끌어올린다.
calc 결과의 dict 키에서 노드를 추출하고, 6막 간 인과를 엣지로 연결.

빌드 < 2초 (calc 캐시 재사용), 메모리 < 50MB.
"""

from __future__ import annotations

import logging
from typing import Any

from dartlab.analysis.graph.schema import (
    CompanyGraph,
    Edge,
    EdgeType,
    Node,
    NodeType,
)

log = logging.getLogger(__name__)

# calc 실패 시 잡아야 하는 예외
_SAFE = (
    KeyError,
    TypeError,
    ValueError,
    IndexError,
    AttributeError,
    ZeroDivisionError,
    FileNotFoundError,
    OSError,
    RuntimeError,
    ArithmeticError,
    StopIteration,
    ImportError,
)


def _safe(fn: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except _SAFE:
        return None


def _nid(type_: str, label: str, period: str = "") -> str:
    """노드 ID 생성."""
    if period:
        return f"{type_}:{label}:{period}"
    return f"{type_}:{label}"


def _addMetricNode(
    g: CompanyGraph,
    label: str,
    value: Any,
    period: str,
    unit: str = "",
) -> str:
    """메트릭 노드 추가 + ID 반환."""
    nid = _nid("metric", label, period)
    g.addNode(
        Node(
            id=nid,
            type=NodeType.METRIC,
            label=label,
            value=value,
            period=period,
            unit=unit,
        )
    )
    return nid


def _addCauses(g: CompanyGraph, source_id: str, target_id: str, label: str = "") -> None:
    g.addEdge(Edge(source=source_id, target=target_id, type=EdgeType.CAUSES, label=label))


def _addPartOf(g: CompanyGraph, part_id: str, whole_id: str, label: str = "") -> None:
    g.addEdge(Edge(source=part_id, target=whole_id, type=EdgeType.PART_OF, label=label))


def _addDerived(g: CompanyGraph, base_id: str, derived_id: str, label: str = "") -> None:
    g.addEdge(Edge(source=base_id, target=derived_id, type=EdgeType.DERIVED, label=label))


def _addAnomaly(g: CompanyGraph, source_id: str, target_id: str, label: str = "") -> None:
    g.addEdge(Edge(source=source_id, target=target_id, type=EdgeType.ANOMALY, label=label))


# ── 1막: 수익구조 ─────────────────────────────────────────


def _buildAct1(g: CompanyGraph, company: Any, bp: str | None) -> None:
    """매출 구성 → 부문별 partOf + 성장 causes."""
    try:
        from dartlab.analysis.financial.revenue import (
            calcRevenueGrowth,
            calcSegmentComposition,
        )
    except ImportError:
        return

    seg = _safe(calcSegmentComposition, company, basePeriod=bp)
    if seg and isinstance(seg, dict):
        segments = seg.get("segments") or []
        total_rev = seg.get("totalRevenue")
        if total_rev:
            rev_id = _addMetricNode(g, "매출액", total_rev, bp or "", "억원")
            for s in segments[:10]:
                name = s.get("name", "?")
                rev = s.get("revenue")
                share = s.get("share")
                sid = _nid("segment", name)
                g.addNode(Node(id=sid, type=NodeType.SEGMENT, label=name, value=rev))
                _addPartOf(g, sid, rev_id, label=f"{share}%" if share else "")

    growth = _safe(calcRevenueGrowth, company, basePeriod=bp)
    if growth and isinstance(growth, dict):
        yoy = growth.get("yoy")
        if isinstance(yoy, dict):
            for period, rate in list(yoy.items())[:5]:
                gid = _addMetricNode(g, "매출성장률", rate, period, "%")
                rev_id = _nid("metric", "매출액", period)
                if rev_id in g.nodes:
                    _addDerived(g, rev_id, gid)


# ── 2막: 수익성 ──────────────────────────────────────────


def _buildAct2(g: CompanyGraph, company: Any, bp: str | None) -> None:
    """마진 추이 → causes 체인."""
    try:
        from dartlab.analysis.financial.profitability import calcMarginTrend
    except ImportError:
        return

    margin = _safe(calcMarginTrend, company, basePeriod=bp)
    if not margin or not isinstance(margin, dict):
        return
    history = margin.get("history") or []
    for row in history[:5]:
        period = row.get("period", "")
        if not period:
            continue
        op_margin = row.get("operatingMargin")
        net_margin = row.get("netMargin")
        gross_margin = row.get("grossMargin")

        if gross_margin is not None:
            gm_id = _addMetricNode(g, "매출총이익률", gross_margin, period, "%")
        if op_margin is not None:
            om_id = _addMetricNode(g, "영업이익률", op_margin, period, "%")
            if gross_margin is not None:
                _addCauses(g, gm_id, om_id, "매출총이익 → 판관비 차감")
        if net_margin is not None:
            nm_id = _addMetricNode(g, "순이익률", net_margin, period, "%")
            if op_margin is not None:
                _addCauses(g, om_id, nm_id, "영업이익 → 영업외/세금 차감")


# ── 3막: 현금흐름 ─────────────────────────────────────────


def _buildAct3(g: CompanyGraph, company: Any, bp: str | None) -> None:
    """현금흐름 → 이익에서 현금 전환 causes."""
    try:
        from dartlab.analysis.financial.cashflow import calcCashFlowOverview
    except ImportError:
        return

    cf = _safe(calcCashFlowOverview, company, basePeriod=bp)
    if not cf or not isinstance(cf, dict):
        return
    for row in (cf.get("history") or [])[:5]:
        period = row.get("period", "")
        if not period:
            continue
        ocf = row.get("ocf")
        fcf = row.get("fcf")
        capex = row.get("capex")
        if ocf is not None:
            ocf_id = _addMetricNode(g, "영업CF", ocf, period, "억원")
            # 2막 순이익 → 3막 OCF
            ni_id = _nid("metric", "순이익률", period)
            if ni_id in g.nodes:
                _addCauses(g, ni_id, ocf_id, "이익 → 현금 전환")
        if fcf is not None:
            fcf_id = _addMetricNode(g, "FCF", fcf, period, "억원")
            if ocf is not None:
                _addDerived(g, ocf_id, fcf_id, "OCF - CAPEX")
        if capex is not None:
            capex_id = _addMetricNode(g, "CAPEX", abs(capex), period, "억원")
            if ocf is not None and fcf is not None:
                _addCauses(g, capex_id, fcf_id, "CAPEX 차감")


# ── 4막: 안정성 ──────────────────────────────────────────


def _buildAct4(g: CompanyGraph, company: Any, bp: str | None) -> None:
    """부채/Z-Score → 3막 FCF에서 감당 가능한지 causes."""
    try:
        from dartlab.analysis.financial.stability import calcDistressScore, calcLeverageTrend
    except ImportError:
        return

    lev = _safe(calcLeverageTrend, company, basePeriod=bp)
    if lev and isinstance(lev, dict):
        for row in (lev.get("history") or [])[:5]:
            period = row.get("period", "")
            dr = row.get("debtRatio")
            if period and dr is not None:
                dr_id = _addMetricNode(g, "부채비율", dr, period, "%")
                # 3막 FCF → 4막 부채 감당
                fcf_id = _nid("metric", "FCF", period)
                if fcf_id in g.nodes:
                    _addCauses(g, fcf_id, dr_id, "FCF로 부채 상환 가능 여부")

    distress = _safe(calcDistressScore, company, basePeriod=bp)
    if distress and isinstance(distress, dict):
        for row in (distress.get("history") or [])[:5]:
            period = row.get("period", "")
            zscore = row.get("zScore")
            if period and zscore is not None:
                zid = _addMetricNode(g, "Z-Score", zscore, period, "")
                if zscore < 1.8:
                    _addAnomaly(g, zid, zid, f"Z-Score {zscore:.1f} < 1.8 위험")


# ── 5막: 자본배분 ─────────────────────────────────────────


def _buildAct5(g: CompanyGraph, company: Any, bp: str | None) -> None:
    """ROIC + 배당 → 가치 창출/파괴 causes."""
    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
    except ImportError:
        return

    roic = _safe(calcRoicTimeline, company, basePeriod=bp)
    if roic and isinstance(roic, dict):
        for row in (roic.get("history") or [])[:5]:
            period = row.get("period", "")
            r = row.get("roic")
            wacc = row.get("wacc")
            if period and r is not None:
                rid = _addMetricNode(g, "ROIC", r, period, "%")
                if wacc is not None:
                    wid = _addMetricNode(g, "WACC", wacc, period, "%")
                    if r > wacc:
                        _addCauses(g, rid, wid, f"ROIC {r:.1f}% > WACC {wacc:.1f}% → 가치 창출")
                    else:
                        _addAnomaly(g, rid, wid, f"ROIC {r:.1f}% < WACC {wacc:.1f}% → 가치 파괴")


# ── 6막 전환 엣지 (막 간 인과) ────────────────────────────


def _buildActTransitions(g: CompanyGraph) -> None:
    """6막 간 인과 연결 — 가장 최근 기간에서 대표 엣지 1개씩."""
    # 1→2: 매출 → 마진
    for n in g.findNodes(type=NodeType.METRIC, label="매출액"):
        om = g.getNode(_nid("metric", "영업이익률", n.period))
        if om:
            _addCauses(g, n.id, om.id, "매출 규모 → 마진 수준")
            break
    # 4→5: 부채 → ROIC
    for n in g.findNodes(type=NodeType.METRIC, label="부채비율"):
        roic = g.getNode(_nid("metric", "ROIC", n.period))
        if roic:
            _addCauses(g, n.id, roic.id, "자본 구조 → 투자 수익")
            break


# ── 메인 빌더 ─────────────────────────────────────────────


def buildGraph(company: Any, *, basePeriod: str | None = None) -> CompanyGraph:
    """Company → CompanyGraph.

    14축 calc 캐시 재사용 → 빌드 < 2초.
    메모리 < 50MB (dict-of-dicts, Polars 비사용).
    """
    stockCode = getattr(company, "stockCode", None) or getattr(company, "ticker", "") or ""
    corpName = getattr(company, "corpName", "") or ""
    g = CompanyGraph(stockCode=stockCode, corpName=corpName)

    # basePeriod 해석
    bp = basePeriod
    if bp is None:
        try:
            from dartlab.analysis.financial._helpers import resolveBasePeriod

            pr = resolveBasePeriod(company, None, maxYears=5, maxQuarters=8)
            bp = pr.basePeriod if pr else None
        except _SAFE:
            pass

    # 6막 빌드
    _buildAct1(g, company, bp)
    _buildAct2(g, company, bp)
    _buildAct3(g, company, bp)
    _buildAct4(g, company, bp)
    _buildAct5(g, company, bp)
    _buildActTransitions(g)

    log.debug("buildGraph: %s", g.summary())
    return g
