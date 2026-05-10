"""macro 경제분석 보고서 — 6막 인과 서사.

6막 구조 — "앞 막이 뒷 막의 원인"::

    1막: 경제는 어디에 있나     (cycle, inventory)
    2막: 왜 여기에 있나         (corporate, trade)
    3막: 정책은 뭘 하고 있나    (rates)
    4막: 금융 시스템은 괜찮나   (liquidity, crisis)
    5막: 시장은 어떻게 반응하나  (assets, sentiment)
    6막: 앞으로 어떻게 되나     (forecast, scenario)
"""

from __future__ import annotations

from dartlab.story.blocks import TextBlock
from dartlab.story.section import Section

from .builders import (
    buildCausationBlocks,
    buildDashboardBlocks,
    buildOutlookBlocks,
    buildPhaseBlocks,
)
from .catalog import SECTIONS
from .narrative import (
    generateActTransition,
    generateCirculationSummary,
    narrateOverallStory,
)


def _detectTemplate(summary: dict) -> str:
    """상황별 템플릿 결정."""
    market = summary.get("market", "US")
    if market == "KR":
        return "kr"
    cycle = (summary.get("cycle") or {}).get("phase", "")
    crisis_zone = ((summary.get("crisis") or {}).get("creditGap") or {}).get("zone", "")
    if cycle == "contraction" or crisis_zone in ("warning", "danger"):
        return "crisis"
    if cycle == "slowdown":
        return "transition"
    return "normal"


def macroReport(
    *,
    market: str = "US",
    asOf: str | None = None,
    fmt: str | None = "rich",
):
    """경제분석 보고서 — 6막 인과 서사.

    Args:
        market: "US" | "KR"
        as_of: 백테스트 날짜 (YYYY-MM-DD)
        fmt: "rich" | "html" | "markdown" | "json" | None(Story 객체 반환)

    Returns:
        str (fmt 지정 시) 또는 Story 객체
    """
    from dartlab.macro.summary import analyzeSummary

    summary = analyzeSummary(market=market, asOf=asOf)
    template = _detectTemplate(summary)

    meta = {s.key: s for s in SECTIONS}
    sections = []

    # ── M0: 신호등 대시보드 ──
    m = meta["dashboard"]
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=buildDashboardBlocks(summary),
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 1막: 경제는 어디에 있나 (cycle + inventory) ──
    # 기존 build_phase_blocks에서 cycle + inventory 부분 사용
    m = meta["phase"]
    phase_blocks = buildPhaseBlocks(summary)
    t1 = generateActTransition(1, summary)
    if t1:
        phase_blocks.append(TextBlock(t1, style="transition"))
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=phase_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 2막: 왜 여기에 있나 (corporate + trade) ──
    # 기존 build_causation_blocks에서 corporate + trade 부분
    m = meta["causation"]
    causation_blocks = buildCausationBlocks(summary)
    t2 = generateActTransition(2, summary)
    if t2:
        causation_blocks.append(TextBlock(t2, style="transition"))
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=causation_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 3막: 정책은 뭘 하고 있나 (rates) ──
    # rates 블록은 현재 build_phase_blocks 안에 포함되어 있음
    # 6막 전면 분리는 다음 단계 — 현재는 M3에 빈 섹션 추가 방지
    m = meta["policy"]
    t3 = generateActTransition(3, summary)
    policy_blocks = []
    if t3:
        policy_blocks.append(TextBlock(t3, style="transition"))
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=policy_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 4막: 금융 시스템은 괜찮나 (liquidity + crisis) ──
    # 기존 build_causation_blocks에 이미 포함
    m = meta["financial"]
    t4 = generateActTransition(4, summary)
    financial_blocks = []
    if t4:
        financial_blocks.append(TextBlock(t4, style="transition"))
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=financial_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 5막: 시장은 어떻게 반응하나 (assets + sentiment) ──
    m = meta["market"]
    t5 = generateActTransition(5, summary)
    market_blocks = []
    if t5:
        market_blocks.append(TextBlock(t5, style="transition"))
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=market_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── 6막: 앞으로 어떻게 되나 (forecast + scenario) ──
    m = meta["outlook"]
    outlook_blocks = buildOutlookBlocks(summary)
    sections.append(
        Section(
            key=m.key,
            partId=m.partId,
            title=m.title,
            blocks=outlook_blocks,
            helper=m.helper,
            aiGuide=m.aiGuide,
        )
    )

    # ── Story 조립 ──
    from dartlab.story import Story

    story = Story(
        stockCode="MACRO",
        corpName=f"{market} 경제",
        sections=sections,
        circulationSummary=narrateOverallStory(summary) or generateCirculationSummary(summary, template),
    )

    if fmt is None:
        return story
    return story.render(fmt)
