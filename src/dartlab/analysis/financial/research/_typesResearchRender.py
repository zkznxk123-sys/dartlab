"""Research 리포트 렌더링 + 직렬화 함수 — types.py 에서 분리.

ResearchResult 의 rich rendering (Console / HTML) + summary 텍스트 + dict 직렬화를
모두 모듈 레벨 함수로 추출하여 types.py 의 dataclass 정의를 슬림하게 유지.

ResearchResult 의 ``__repr__`` / ``_repr_html_`` / ``summary`` / ``toDict`` 가
본 모듈 함수를 호출 (lazy import).
"""

from __future__ import annotations

from dataclasses import asdict

from dartlab.core.utils.fmt import fmtBig as _fmtBig
from dartlab.core.utils.fmt import fmtNum as _fmtNum
from dartlab.core.utils.fmt import fmtPrice as _fmtPrice


def _opinionColor(opinion: str) -> str:
    """투자의견 → rich 색상."""
    m = {"강력매수": "bold green", "매수": "green", "중립": "yellow", "매도": "red", "강력매도": "bold red"}
    return m.get(opinion, "white")


def _profileBadge(profile: str) -> tuple[str, str]:
    """프로파일 → (뱃지, 색상)."""
    m = {
        "premium": ("★", "bold green"),
        "growth": ("▲", "green"),
        "stable": ("●", "cyan"),
        "caution": ("▼", "yellow"),
        "distress": ("✗", "bold red"),
    }
    return m.get(profile, ("?", "white"))


def _assessColor(assessment: str) -> str:
    """평가 → 색상."""
    return {"high": "green", "good": "green", "moderate": "yellow", "neutral": "yellow"}.get(assessment, "red")


def _distressColor(level: str) -> str:
    """부실 수준 → 색상."""
    return {"safe": "green", "watch": "cyan", "warning": "yellow", "danger": "red", "critical": "bold red"}.get(
        level, "white"
    )


def _verdictColor(verdict: str) -> str:
    """밸류에이션 판정 → 색상."""
    return {"저평가": "green", "적정": "yellow", "고평가": "red"}.get(verdict, "white")


def _richPrint(result, console) -> None:
    """rich Console에 전체 리포트 출력."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    name = result.meta.corpName or result.meta.stockCode
    ex = result.executive

    # ── 1. Header ──
    header = Text()
    header.append(f"{name}\n", style="bold white")
    header.append(f"생성일 {result.meta.generatedAt[:10] if result.meta.generatedAt else '-'}  ")
    header.append("커버리지 ")
    score = result.meta.coverageScore
    filled = int(score * 15)
    header.append("█" * filled, style="green")
    header.append("░" * (15 - filled), style="dim")
    header.append(f" {score:.0%}")
    if result.meta.warnings:
        header.append(f"\n⚠ {', '.join(result.meta.warnings)}", style="yellow")
    console.print(Panel(header, title="[bold]Research Report[/bold]", border_style="blue"))

    # ── 2. Executive Summary ──
    execTable = Table(show_header=False, box=None, padding=(0, 2))
    execTable.add_column(style="dim", width=10)
    execTable.add_column()
    if ex.opinion:
        badge, bcolor = _profileBadge(ex.profile)
        execTable.add_row(
            "투자의견", f"[{_opinionColor(ex.opinion)}]{ex.opinion}[/]  [{bcolor}]{badge} {ex.profile}[/]"
        )
    if ex.currentPrice is not None:
        priceText = f"{ex.currentPrice:,.0f}"
        if ex.targetPrice:
            priceText += f"  →  [bold]{ex.targetPrice:,.0f}[/bold]"
        if ex.upside is not None:
            color = "green" if ex.upside > 0 else "red"
            priceText += f"  [{color}]({ex.upside:+.1%})[/{color}]"
        execTable.add_row("가격", priceText)
    if ex.grades:
        gradeText = Text()
        for k, v in ex.grades.items():
            color = "green" if v in ("A", "B") else "yellow" if v == "C" else "red"
            gradeText.append(f" {k}=", style="dim")
            gradeText.append(v, style=f"bold {color}")
        execTable.add_row("등급", gradeText)
    if ex.keyMetrics:
        metricText = " | ".join(f"{m['label']} {m['value']}{m.get('unit', '')}" for m in ex.keyMetrics)
        execTable.add_row("핵심지표", metricText)
    console.print(Panel(execTable, title="[bold]Executive Summary[/bold]", border_style="cyan"))

    # ── 3. Investment Thesis ──
    _renderThesis(result, console)

    # ── 3.5 Narrative Analysis ──
    _renderNarrative(result, console)

    # ── 4. Valuation ──
    _renderValuation(result, console)

    # ── 5. Quant + Earnings Quality ──
    _renderQuantAndQuality(result, console)

    # ── 6. Risk Analysis ──
    _renderRisk(result, console)

    # ── 7. Forecast ──
    _renderForecast(result, console)

    # ── 8. Peer ──
    _renderPeer(result, console)

    # ── 9. Market Data ──
    _renderMarket(result, console)

    # ── 10. Financial Trends ──
    _renderFinancial(result, console)

    # ── 11. Sector KPIs ──
    _renderSectorKpis(result, console)

    # ── 12. Overview ──
    if result.overview and result.overview.description:
        from rich.panel import Panel

        console.print(Panel(result.overview.description[:300], title="[bold]Overview[/bold]", border_style="dim"))

    # ── 13. Disclaimer ──
    console.print(f"\n[dim italic]{result.DISCLAIMER}[/]")


def _renderThesis(result, console) -> None:
    """Investment Thesis 패널."""
    from rich.panel import Panel
    from rich.text import Text

    th = result.thesis
    thText = Text()
    if th.summaryNarrative:
        thText.append(f"{th.summaryNarrative}\n\n", style="bold")
    if th.bullCase:
        thText.append("Bull Case\n", style="bold green")
        for b in th.bullCase:
            thText.append(f"  + {b}\n", style="green")
    if th.bearCase:
        thText.append("Bear Case\n", style="bold red")
        for b in th.bearCase:
            thText.append(f"  - {b}\n", style="red")
    if th.catalysts:
        thText.append("촉매\n", style="bold yellow")
        for c in th.catalysts:
            thText.append(f"  ▸ {c}\n", style="yellow")
    if th.monitoringPoints:
        thText.append("모니터링\n", style="bold dim")
        for m in th.monitoringPoints:
            thText.append(f"  ◦ {m}\n", style="dim")
    thText.append(f"\n확신도 {th.confidence:.0%}", style="bold")
    console.print(Panel(thText, title="[bold]Investment Thesis[/bold]", border_style="green"))


def _renderNarrative(result, console) -> None:
    """Narrative Analysis 패널."""
    na = result.narrativeAnalysis
    if na is None or not na.paragraphs:
        return
    from rich.panel import Panel
    from rich.text import Text

    nt = Text()
    severityStyle = {
        "positive": "green",
        "negative": "red",
        "warning": "yellow",
        "neutral": "dim",
    }
    for p in na.paragraphs:
        color = severityStyle.get(p.severity, "white")
        icon = {"positive": "▲", "negative": "▼", "warning": "⚠", "neutral": "●"}.get(p.severity, "●")
        nt.append(f"{icon} {p.title}\n", style=f"bold {color}")
        nt.append(f"  {p.body}\n\n")
    if na.crossReferences:
        nt.append("교차분석\n", style="bold cyan")
        for cr in na.crossReferences:
            nt.append(f"  ◆ {cr}\n", style="cyan")
        nt.append("\n")
    if na.forwardImplications:
        nt.append("전망 시사점\n", style="bold magenta")
        for fi in na.forwardImplications:
            nt.append(f"  → {fi}\n", style="magenta")
    console.print(Panel(nt, title="[bold]Deep Analysis[/bold]", border_style="bright_blue"))


def _renderValuation(result, console) -> None:
    """Valuation 패널."""
    va = result.valuationAnalysis
    if va is None:
        return
    if va.dcfPerShare is None and va.ddmPerShare is None and va.relativePerShare is None and va.fairValueRange is None:
        return
    from rich.panel import Panel
    from rich.table import Table

    vt = Table(show_header=True, box=None, padding=(0, 2))
    vt.add_column("방법론")
    vt.add_column("적정가", justify="right")
    vt.add_column("비고")
    if va.dcfPerShare is not None:
        mos = f"안전마진 {va.dcfMos:.0f}%" if va.dcfMos is not None else ""
        vt.add_row("DCF", _fmtPrice(va.dcfPerShare), mos)
    if va.ddmPerShare is not None:
        vt.add_row("DDM (배당)", _fmtPrice(va.ddmPerShare), "")
    if va.relativePerShare is not None:
        vt.add_row("상대가치", _fmtPrice(va.relativePerShare), "섹터 배수 기반")
    if va.fairValueRange:
        lo, hi = va.fairValueRange
        color = _verdictColor(va.verdict)
        vt.add_row(
            "[bold]종합[/bold]",
            f"[bold]{lo:,.0f} ~ {hi:,.0f}원[/bold]",
            f"[{color}]{va.verdict}[/{color}]",
        )
    for m in va.methodology:
        vt.add_row("", "", f"[dim]{m}[/dim]")
    for w in va.warnings:
        vt.add_row("", "", f"[yellow]⚠ {w}[/yellow]")
    console.print(Panel(vt, title="[bold]Valuation[/bold]", border_style="magenta"))


def _renderQuantAndQuality(result, console) -> None:
    """Quant Scores + Earnings Quality 패널 (side by side)."""
    from rich.columns import Columns
    from rich.panel import Panel
    from rich.table import Table

    panels = []
    if result.quantScores:
        qt = Table(show_header=False, box=None, padding=(0, 1))
        qt.add_column(style="dim", width=12)
        qt.add_column()
        qs = result.quantScores
        if qs.piotroski:
            p = qs.piotroski
            bar = "[green]●[/]" * p.total + "[dim]○[/]" * (9 - p.total)
            qt.add_row("Piotroski", f"{bar}  {p.total}/9 ({p.interpretation})")
        if qs.magicFormula:
            mf = qs.magicFormula
            parts = []
            if mf.roic is not None:
                parts.append(f"ROIC {mf.roic:.1f}%")
            if mf.earningsYield is not None:
                parts.append(f"EY {mf.earningsYield:.1f}%")
            qt.add_row("Magic Formula", " | ".join(parts) if parts else "-")
        if qs.qmj and qs.qmj.composite is not None:
            q = qs.qmj
            qt.add_row(
                "QMJ",
                f"{q.composite:.2f}  (P{q.profitability:.1f} G{q.growth:.1f} S{q.safety:.1f})",
            )
        if qs.lynchFairValue:
            lv = qs.lynchFairValue
            sig = {
                "undervalued": "[green]저평가[/]",
                "overvalued": "[red]고평가[/]",
                "fair": "[yellow]적정[/]",
            }.get(lv.signal or "", "")
            parts = []
            if lv.fairValue is not None:
                parts.append(f"적정 {lv.fairValue:,.0f}")
            if lv.pegRatio is not None:
                parts.append(f"PEG {lv.pegRatio:.2f}")
            parts.append(sig)
            qt.add_row("Lynch", " ".join(parts))
        if qs.buffettOwnerEarnings is not None:
            qt.add_row("Buffett OE", _fmtBig(qs.buffettOwnerEarnings))
        if qs.dupont:
            qt.add_row("DuPont", f"주도: [bold]{qs.dupont.driver}[/bold]")
        panels.append(Panel(qt, title="[bold]Quant Scores[/bold]", border_style="magenta"))

    if result.earningsQuality:
        eq = result.earningsQuality
        et = Table(show_header=False, box=None, padding=(0, 1))
        et.add_column(style="dim", width=10)
        et.add_column()
        et.add_row("평가", f"[{_assessColor(eq.assessment)}]{eq.assessment}[/]")
        if eq.cfToNi is not None:
            et.add_row("CF/NI", _fmtNum(eq.cfToNi, precision=2))
        if eq.accrualRatio is not None:
            et.add_row("Accrual", _fmtNum(eq.accrualRatio, precision=4))
        if eq.ccc is not None:
            et.add_row("CCC", f"{eq.ccc:.0f}일")
        if eq.beneishMScore is not None:
            color = "green" if eq.beneishMScore < -2.22 else "red"
            et.add_row("Beneish M", f"[{color}]{eq.beneishMScore:.2f}[/]")
        panels.append(Panel(et, title="[bold]이익의 질[/bold]", border_style="magenta"))

    if panels:
        console.print(Columns(panels, equal=True, expand=True))


def _renderRisk(result, console) -> None:
    """Risk Analysis 패널."""
    ra = result.riskAnalysis
    if ra is None:
        return
    from rich.panel import Panel
    from rich.text import Text

    riskText = Text()
    if ra.distress:
        d = ra.distress
        color = _distressColor(d.level)
        riskText.append("부실 위험: ", style="dim")
        riskText.append(f"{d.level.upper()}", style=f"bold {color}")
        riskText.append(f"  (종합 {d.overall:.0f}/100, 신용 {d.creditGrade})\n")
        if d.cashRunwayMonths is not None:
            riskText.append(f"현금소진 예상: {d.cashRunwayMonths:.0f}개월\n", style="yellow")
        for rf in d.riskFactors[:3]:
            riskText.append(f"  ▸ {rf}\n", style="dim")
    if ra.anomalies and ra.anomalies.items:
        a = ra.anomalies
        riskText.append("\n이상치: ", style="dim")
        riskText.append(f"Critical {a.criticalCount}", style="bold red")
        riskText.append(f" / Warning {a.warningCount}\n", style="yellow")
        for item in a.items[:4]:
            sev = item.get("severity", "")
            color = "red" if sev in ("critical", "danger") else "yellow"
            riskText.append(f"  ● {item.get('text', '')}\n", style=color)
    if ra.riskNarrative:
        riskText.append(f"\n{ra.riskNarrative}", style="italic")
    console.print(Panel(riskText, title="[bold]Risk Analysis[/bold]", border_style="red"))


def _renderForecast(result, console) -> None:
    """Forecast 패널."""
    fc = result.forecast
    if fc is None:
        return
    from rich.panel import Panel
    from rich.table import Table

    ft = Table(show_header=True, box=None, padding=(0, 1))
    ft.add_column("연도", style="dim")
    ft.add_column("매출", justify="right")
    ft.add_column("영업이익", justify="right")
    ft.add_column("EPS", justify="right")
    for rc in fc.revenueConsensus:
        rev = rc.get("revenueEst")
        op = rc.get("operatingProfitEst")
        ft.add_row(
            str(rc.get("fiscalYear", "?")),
            _fmtBig(rev * 1e8 if rev else None),
            _fmtBig(op * 1e8 if op else None),
            _fmtNum(rc.get("epsEst"), "원", precision=0) if rc.get("epsEst") else "-",
        )
    if fc.selfForecast:
        sf = fc.selfForecast
        method = sf.get("method", "")
        gr = sf.get("growthRate")
        conf = sf.get("confidence", "")
        if gr is not None:
            ft.add_row("", f"[dim]자체예측 성장 {gr:.1f}% ({method}, {conf})[/dim]", "", "")
    if fc.scenarioSummary:
        sc = fc.scenarioSummary
        base = sc.get("base")
        bull = sc.get("bull")
        bear = sc.get("bear")
        if base is not None:
            ft.add_row(
                "",
                f"[dim]시나리오 Base {_fmtPrice(base)} / Bull {_fmtPrice(bull)} / Bear {_fmtPrice(bear)}[/dim]",
                "",
                "",
            )
    console.print(Panel(ft, title="[bold]Forecast[/bold]", border_style="blue"))


def _renderPeer(result, console) -> None:
    """Peer Comparison 패널."""
    pa = result.peerAnalysis
    if pa is None:
        return
    hasCompanyData = any(v is not None for v in pa.companyMultiples.values())
    if not hasCompanyData and not pa.sectorMultiples:
        return
    from rich.panel import Panel
    from rich.table import Table

    pt = Table(show_header=True, box=None, padding=(0, 2))
    pt.add_column("배수")
    pt.add_column("기업", justify="right")
    pt.add_column("섹터", justify="right", style="dim")
    pt.add_column("할인/할증", justify="right")
    for key in ["PER", "PBR", "EV/EBITDA"]:
        cv = pa.companyMultiples.get(key)
        sv = pa.sectorMultiples.get(key)
        pd = pa.premiumDiscount.get(key)
        cvText = f"{cv:.1f}배" if cv is not None else "-"
        svText = f"{sv:.1f}배" if sv is not None else "-"
        if pd is not None:
            color = "green" if pd < 0 else "red"
            pdText = f"[{color}]{pd:+.0f}%[/{color}]"
        else:
            pdText = "-"
        pt.add_row(key, cvText, svText, pdText)
    if pa.peerNarrative:
        pt.add_row("", f"[dim]{pa.peerNarrative}[/dim]", "", "")
    console.print(Panel(pt, title=f"[bold]Peer — {pa.sectorName}[/bold]", border_style="yellow"))


def _renderMarket(result, console) -> None:
    """Market Data 패널."""
    md = result.marketData
    if md is None:
        return
    hasData = (md.marketCap and md.marketCap > 0) or md.per is not None or md.pbr is not None
    if not hasData:
        return
    from rich.panel import Panel
    from rich.table import Table

    mt = Table(show_header=False, box=None, padding=(0, 1))
    mt.add_column(style="dim", width=10)
    mt.add_column()
    if md.marketCap and md.marketCap > 0:
        mt.add_row("시가총액", _fmtBig(md.marketCap))
    if md.per is not None:
        mt.add_row("PER", _fmtNum(md.per, "배"))
    if md.pbr is not None:
        mt.add_row("PBR", _fmtNum(md.pbr, "배", precision=2))
    if md.dividendYield is not None:
        mt.add_row("배당률", _fmtNum(md.dividendYield, "%"))
    if md.high52w and md.low52w and md.high52w > 0:
        mt.add_row("52주", f"{md.low52w:,.0f} ~ {md.high52w:,.0f}")
    if md.foreignHoldingRatio is not None:
        mt.add_row("외인보유", _fmtNum(md.foreignHoldingRatio, "%"))
    if md.analystCount and md.analystCount > 0:
        mt.add_row("애널리스트", f"{md.analystCount}명")
    if md.baseRate is not None:
        mt.add_row("기준금리", _fmtNum(md.baseRate, "%"))
    console.print(Panel(mt, title="[bold]Market Data[/bold]", border_style="blue"))


def _renderFinancial(result, console) -> None:
    """Financial Trends — 수익성·DuPont·효율성 종합 테이블."""
    if not result.financial or not result.financial.periods:
        return
    from rich.panel import Panel
    from rich.table import Table

    fa = result.financial
    periods = fa.periods

    # ── 1) 수익성 추이 ──
    ft = Table(show_header=True, box=None, padding=(0, 2), title="수익성 추이")
    ft.add_column("지표", style="dim")
    for p in periods:
        ft.add_column(p, justify="right")
    if fa.marginTrends.get("grossMargin"):
        ft.add_row("매출총이익률", *[_fmtNum(v, "%") for v in fa.marginTrends["grossMargin"]])
    if fa.marginTrends.get("operatingMargin"):
        ft.add_row("영업이익률", *[_fmtNum(v, "%") for v in fa.marginTrends["operatingMargin"]])
    if fa.marginTrends.get("netMargin"):
        ft.add_row("순이익률", *[_fmtNum(v, "%") for v in fa.marginTrends["netMargin"]])
    if fa.marginTrends.get("costOfSalesRatio"):
        ft.add_row("원가율", *[_fmtNum(v, "%") for v in fa.marginTrends["costOfSalesRatio"]])
    if fa.marginTrends.get("sgaRatio"):
        ft.add_row("판관비율", *[_fmtNum(v, "%") for v in fa.marginTrends["sgaRatio"]])

    # ── 2) DuPont 분해 ──
    if fa.dupont and fa.dupont.roe:
        dp = fa.dupont
        ft.add_row("")  # separator
        ft.add_row(
            "[bold]ROE[/bold]",
            *[_fmtNum(v * 100 if v else None, "%") for v in dp.roe],
        )
        ft.add_row(
            "  순이익률",
            *[_fmtNum(v * 100 if v else None, "%") for v in dp.netMargin],
        )
        ft.add_row(
            "  자산회전율",
            *[_fmtNum(v, "배", precision=2) for v in dp.assetTurnover],
        )
        ft.add_row(
            "  레버리지",
            *[_fmtNum(v, "배") for v in dp.equityMultiplier],
        )

    # ── 3) 효율성 추이 ──
    if fa.marginTrends.get("dso") or fa.marginTrends.get("ccc"):
        ft.add_row("")  # separator
        if fa.marginTrends.get("dso"):
            ft.add_row("매출채권회전일", *[_fmtNum(v, "일", precision=0) for v in fa.marginTrends["dso"]])
        if fa.marginTrends.get("dio"):
            ft.add_row("재고자산회전일", *[_fmtNum(v, "일", precision=0) for v in fa.marginTrends["dio"]])
        if fa.marginTrends.get("dpo"):
            ft.add_row("매입채무회전일", *[_fmtNum(v, "일", precision=0) for v in fa.marginTrends["dpo"]])
        if fa.marginTrends.get("ccc"):
            ft.add_row("[bold]CCC[/bold]", *[_fmtNum(v, "일", precision=0) for v in fa.marginTrends["ccc"]])

    # ── 4) 성장률 ──
    if fa.marginTrends.get("salesGrowth"):
        ft.add_row("")
        ft.add_row("매출 성장률", *[_fmtNum(v, "%") for v in fa.marginTrends["salesGrowth"]])
    if fa.marginTrends.get("opGrowth"):
        ft.add_row("영업이익 성장률", *[_fmtNum(v, "%") for v in fa.marginTrends["opGrowth"]])

    # ── 5) 규모 (억 단위) ──
    if fa.marginTrends.get("sales"):
        ft.add_row("")
        ft.add_row("매출", *[_fmtBig(v) for v in fa.marginTrends["sales"]])
    if fa.marginTrends.get("operatingProfit"):
        ft.add_row("영업이익", *[_fmtBig(v) for v in fa.marginTrends["operatingProfit"]])
    if fa.marginTrends.get("netProfit"):
        ft.add_row("순이익", *[_fmtBig(v) for v in fa.marginTrends["netProfit"]])

    console.print(Panel(ft, title="[bold]Financial Analysis[/bold]", border_style="cyan"))

    # ── 6) BS 요약 ──
    if fa.bsSummary and fa.bsSummary.get("totalAssets"):
        bt = Table(show_header=True, box=None, padding=(0, 2), title="재무상태표 요약")
        bt.add_column("지표", style="dim")
        for p in periods:
            bt.add_column(p, justify="right")
        bsLabels = {
            "totalAssets": "자산총계",
            "currentAssets": "유동자산",
            "nonCurrentAssets": "비유동자산",
            "totalLiabilities": "부채총계",
            "totalEquity": "자본총계",
            "cashAndEquivalents": "현금및현금성자산",
            "retainedEarnings": "이익잉여금",
            "debtRatio": "부채비율",
            "currentRatio": "유동비율",
        }
        for key, label in bsLabels.items():
            vals = fa.bsSummary.get(key)
            if not vals:
                continue
            if key in ("debtRatio", "currentRatio"):
                bt.add_row(label, *[_fmtNum(v, "%", precision=1) for v in vals])
            else:
                bt.add_row(label, *[_fmtBig(v) for v in vals])
        console.print(Panel(bt, title="[bold]Balance Sheet Summary[/bold]", border_style="cyan"))

    # ── 7) CF 요약 ──
    if fa.cfSummary and fa.cfSummary.get("operatingCf"):
        ct = Table(show_header=True, box=None, padding=(0, 2), title="현금흐름표 요약")
        ct.add_column("지표", style="dim")
        for p in periods:
            ct.add_column(p, justify="right")
        cfLabels = {
            "operatingCf": "영업CF",
            "investingCf": "투자CF",
            "financingCf": "재무CF",
            "capex": "CAPEX",
            "fcf": "FCF",
        }
        for key, label in cfLabels.items():
            vals = fa.cfSummary.get(key)
            if not vals:
                continue
            ct.add_row(label, *[_fmtBig(v) for v in vals])
        console.print(Panel(ct, title="[bold]Cash Flow Summary[/bold]", border_style="cyan"))

    # ── 8) 3표 연결 지표 ──
    if fa.crossStatementMetrics and fa.crossStatementMetrics.get("ocfToNetIncome"):
        xt = Table(show_header=True, box=None, padding=(0, 2), title="3표 연결 지표")
        xt.add_column("지표", style="dim")
        for p in periods:
            xt.add_column(p, justify="right")
        xLabels = {
            "ocfToNetIncome": "OCF/NI",
            "capexToDepreciation": "CAPEX/감가상각",
            "retainedEarningsGrowth": "이익잉여금 증가율",
        }
        for key, label in xLabels.items():
            vals = fa.crossStatementMetrics.get(key)
            if not vals:
                continue
            if key == "retainedEarningsGrowth":
                xt.add_row(label, *[_fmtNum(v, "%", precision=1) for v in vals])
            else:
                xt.add_row(label, *[_fmtNum(v, "배", precision=2) for v in vals])
        console.print(Panel(xt, title="[bold]Cross-Statement Metrics[/bold]", border_style="cyan"))


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

    Returns
    -------
    str
        리포트 전체를 plain text로 포맷한 문자열.
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

    Returns
    -------
    dict
        dataclass 전체를 재귀적으로 dict로 변환한 결과.
    """
    return asdict(result)
