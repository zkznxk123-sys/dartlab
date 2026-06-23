"""story 블록 빌더 — peer 도메인 (debt-honesty P3-3 god-split). 공유 imports·상수·헬퍼는 _shared."""

from __future__ import annotations

from dartlab.story.builders._shared import (
    HeadingBlock,
    MetricBlock,
    TableBlock,
    TextBlock,
    _meta,
    _tupleFlags,
    pl,
)

# ── 5-3 비교분석 ──


def peerPositionBlock(data: dict | None) -> list:
    """calcPeerPosition 결과 → 시장 내 위치 + 교차 관점 + 레이더 차트."""
    if not data:
        return []

    from dartlab.story.blocks import ChartBlock
    from dartlab.viz.generators import specPeerRadar

    blocks: list = [
        HeadingBlock(_meta("peerPosition").label, level=2, helper="전종목 횡단 비교 — 4축 백분위 + 교차 관점")
    ]

    total = data.get("total_stocks", 0)
    metrics: list[tuple[str, str]] = []
    for key, label in [
        ("profitability_pct", "수익성 백분위"),
        ("growth_pct", "성장성 백분위"),
        ("quality_pct", "이익품질 백분위"),
        ("debt_pct", "부채 백분위"),
    ]:
        v = data.get(key)
        if v is not None:
            metrics.append((label, f"상위 {100 - v:.0f}% ({v:.0f}%ile, {total}개사 중)"))

    if data.get("op_margin") is not None:
        metrics.append(("영업이익률", f"{data['op_margin']:.1f}%"))
    if data.get("roe") is not None:
        metrics.append(("ROE", f"{data['roe']:.1f}%"))
    if data.get("debt_ratio") is not None:
        metrics.append(("부채비율", f"{data['debt_ratio']:.1f}%"))

    if metrics:
        blocks.append(MetricBlock(metrics))

    # 교차 관점
    crossViews = data.get("crossViews", [])
    if crossViews:
        for cv in crossViews:
            blocks.append(TextBlock(f"**{cv['view']}**: {cv['basis']}"))

    # narrative 요약
    narrative = data.get("narrative", "")
    if narrative and not narrative.endswith("데이터 부족."):
        blocks.append(TextBlock(narrative))

    # radar chart
    try:
        radar = specPeerRadar(data)
        if radar:
            blocks.append(ChartBlock(spec=radar))
    except (KeyError, TypeError, ValueError):
        pass

    return blocks


def peerRankingBlock(data: dict) -> list:
    """calcPeerRanking 결과 -> 백분위 순위 테이블."""
    if not data:
        return []
    rankings = data.get("rankings", [])
    if not rankings:
        return []
    rows = [
        {
            "지표": r["label"],
            "값": r["value"],
            "백분위": f"{r['percentile']:.0f}%",
            "순위": f"{r['rank']}/{r['total']}",
        }
        for r in rankings
    ]
    return [
        HeadingBlock(
            _meta("peerRanking").label,
            level=2,
            helper="전종목 대비 핵심 비율 위치 (백분위가 높을수록 상위)",
        ),
        TableBlock("", pl.DataFrame(rows)),
    ]


def peerBenchmarkFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcPeerBenchmarkFlags 결과 -> FlagBlock."""
    return _tupleFlags(flags)
