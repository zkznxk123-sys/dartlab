"""ResearchResult summary 텍스트 + dict 직렬화."""

from __future__ import annotations

from dataclasses import asdict

from dartlab.core.utils.fmt import fmtBig as _fmtBig
from dartlab.core.utils.fmt import fmtNum as _fmtNum
from dartlab.core.utils.fmt import fmtPrice as _fmtPrice


def _renderSectorKpis(result, console) -> None:
    """Sector KPIs 패널."""
    if not result.sectorKpis:
        return
    from rich.panel import Panel
    from rich.table import Table

    st = Table(show_header=True, box=None, padding=(0, 2))
    st.add_column("KPI")
    st.add_column("값", justify="right")
    st.add_column("벤치마크", justify="right", style="dim")
    st.add_column("평가")
    for kpi in result.sectorKpis.kpis:
        val = f"{kpi.value}{kpi.unit}" if kpi.value is not None else "-"
        bench = f"{kpi.benchmark}{kpi.unit}" if kpi.benchmark is not None else "-"
        badge = {"good": "[green]✓[/]", "bad": "[red]✗[/]", "neutral": "[yellow]~[/]"}.get(kpi.assessment, "")
        st.add_row(kpi.label, val, bench, badge)
    console.print(Panel(st, title=f"[bold]섹터 KPI — {result.sectorKpis.sectorName}[/bold]", border_style="yellow"))


def summary(result) -> str:
    """plain text 전체 출력 (rich 없는 환경용).

    Capabilities:
        - rich 미설치 환경 (서버 로그·노트북 fallback) 에서도 리포트 본문 출력.

    Guide:
        meta → executive → thesis → narrative → valuation → risk → market 순 plain text.

    When:
        rich import 실패 또는 console 미지원 환경.

    How:
        '-' × 50 구분선 + key/value lines.append → "\n".join.

    Requires:
        result 가 ResearchResult 호환 dataclass (meta·executive·thesis 등 속성).

    Raises:
        없음. None 필드 가드 처리.

    Returns:
        str
            리포트 전체를 plain text로 포맷한 문자열.

    Example:
        >>> summary(result)
        "==================================================\n  Acme Corp 종합 기업분석 리포트\n..."

    See Also:
        - toDict : dict 직렬화 버전.

    AIContext:
        rich 미가용 환경 자동 fallback. 본문 톤 그대로 유지.
    """
    sep = "-" * 50
    lines: list[str] = []
    name = result.meta.corpName or result.meta.stockCode

    lines.append(f"{'=' * 50}")
    lines.append(f"  {name} 종합 기업분석 리포트")
    lines.append(f"{'=' * 50}")
    lines.append(f"  생성일: {result.meta.generatedAt[:10] if result.meta.generatedAt else '-'}")
    lines.append(f"  커버리지: {result.meta.coverageScore:.0%}")
    if result.meta.warnings:
        lines.append(f"  ! {', '.join(result.meta.warnings)}")

    ex = result.executive
    lines.append(f"\n{sep}")
    lines.append("  Executive Summary")
    lines.append(sep)
    if ex.opinion:
        lines.append(f"  투자의견: {ex.opinion}  |  프로파일: {ex.profile}")
    if ex.currentPrice is not None:
        p = f"  현재가: {ex.currentPrice:,.0f}"
        if ex.targetPrice:
            p += f"  ->  목표가: {ex.targetPrice:,.0f}"
        if ex.upside is not None:
            p += f"  ({ex.upside:+.1%})"
        lines.append(p)

    th = result.thesis
    lines.append(f"\n{sep}")
    lines.append("  Investment Thesis")
    lines.append(sep)
    if th.summaryNarrative:
        lines.append(f"  {th.summaryNarrative}")
    for b in th.bullCase:
        lines.append(f"  + {b}")
    for b in th.bearCase:
        lines.append(f"  - {b}")
    lines.append(f"  확신도: {th.confidence:.0%}")

    if result.narrativeAnalysis and result.narrativeAnalysis.paragraphs:
        lines.append(f"\n{sep}")
        lines.append("  Deep Analysis")
        lines.append(sep)
        for p in result.narrativeAnalysis.paragraphs:
            lines.append(f"  [{p.dimension}] {p.body}")
        if result.narrativeAnalysis.crossReferences:
            for cr in result.narrativeAnalysis.crossReferences:
                lines.append(f"  * {cr}")
        if result.narrativeAnalysis.forwardImplications:
            for fi in result.narrativeAnalysis.forwardImplications:
                lines.append(f"  -> {fi}")

    if result.valuationAnalysis:
        va = result.valuationAnalysis
        lines.append(f"\n{sep}")
        lines.append("  Valuation")
        lines.append(sep)
        if va.dcfPerShare is not None:
            lines.append(f"  DCF: {va.dcfPerShare:,.0f}원")
        if va.ddmPerShare is not None:
            lines.append(f"  DDM: {va.ddmPerShare:,.0f}원")
        if va.relativePerShare is not None:
            lines.append(f"  상대가치: {va.relativePerShare:,.0f}원")
        if va.fairValueRange:
            lo, hi = va.fairValueRange
            lines.append(f"  적정범위: {lo:,.0f} ~ {hi:,.0f}원 ({va.verdict})")

    if result.riskAnalysis and result.riskAnalysis.distress:
        d = result.riskAnalysis.distress
        lines.append(f"\n{sep}")
        lines.append(f"  Risk: {d.level} (신용 {d.creditGrade})")
        lines.append(sep)
        for rf in d.riskFactors[:3]:
            lines.append(f"  ▸ {rf}")

    if result.marketData:
        md = result.marketData
        lines.append(f"\n{sep}")
        lines.append("  Market Data")
        lines.append(sep)
        parts = []
        if md.marketCap and md.marketCap > 0:
            parts.append(f"시총 {_fmtBig(md.marketCap)}")
        if md.per is not None:
            parts.append(f"PER {md.per:.1f}")
        if md.pbr is not None:
            parts.append(f"PBR {md.pbr:.2f}")
        if parts:
            lines.append(f"  {' | '.join(parts)}")

    lines.append(f"\n{'=' * 50}")
    lines.append(f"  {result.DISCLAIMER}")
    lines.append(f"{'=' * 50}")
    return "\n".join(lines)


def toDict(result) -> dict:
    """전체 리포트를 dict로 변환.

    Requires:
        result 가 dataclass 인스턴스 (asdict 호환).

    Raises:
        없음. dataclass 가 아니면 TypeError 전파.

    Example:
        >>> toDict(result)
        {"meta": {...}, "executive": {...}, ...}

    Returns:
        dict
            dataclass 전체를 재귀적으로 dict로 변환한 결과.
    """
    return asdict(result)
