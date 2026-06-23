"""story 블록 빌더 — cashflow 도메인 (debt-honesty P3-3 god-split). 공유 imports·상수·헬퍼는 _shared."""

from __future__ import annotations

from dartlab.story.builders._shared import (
    FlagBlock,
    HeadingBlock,
    MetricBlock,
    TableBlock,
    TextBlock,
    _fmtAmtShort,
    _meta,
    _unitForCurrency,
    narrateCashFlow,
    narrateCashQuality,
    pl,
    unifyTableScale,
)


def cashFlowBlock(data: dict) -> list:
    """calcCashFlowStructure 결과 → TableBlock + TextBlock + MetricBlock."""
    if not data:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("cashFlowStructure").label,
            level=2,
            helper="영업CF(+)/투자CF(-)/재무CF(-) → 건전한 패턴",
        )
    )
    tableRows = data.get("tableRows")
    cols = data.get("cols")
    if tableRows and cols:
        unified = unifyTableScale(tableRows, "", cols, unit=_unitForCurrency())
        blocks.append(TableBlock("", pl.DataFrame(unified)))
    pattern = data.get("pattern")
    if pattern:
        blocks.append(TextBlock(f"CF 패턴: {pattern}", style="dim", indent="h2"))
    metrics = data.get("metrics")
    if metrics:
        blocks.append(MetricBlock(metrics))
    if len(blocks) <= 1:
        return []
    return blocks


# ── 1-4 현금흐름 빌더 ──


def cashFlowOverviewBlock(data: dict) -> list:
    """calcCashFlowOverview 결과 → CF 3구간 + FCF 시계열 테이블."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("cashFlowOverview").label,
            level=2,
            helper="영업CF(+)/투자CF(-)/재무CF(-) = 건전한 패턴",
        )
    )

    narration = narrateCashFlow(data, fmtAmt=_fmtAmtShort)
    if narration:
        blocks.append(TextBlock(narration))

    rows = ["영업CF", "투자CF", "재무CF", "CAPEX", "FCF"]
    cols = {"": rows}
    for h in history:
        cols[h["period"]] = [
            _fmtAmtShort(h["ocf"]),
            _fmtAmtShort(h["icf"]),
            _fmtAmtShort(h["fcfFinancing"]),
            _fmtAmtShort(h["capex"]),
            _fmtAmtShort(h["fcf"]),
        ]
    blocks.append(TableBlock("현금흐름 추이", pl.DataFrame(cols)))

    # CF 패턴 시계열
    patternRows = ["CF 패턴"]
    patternCols = {"": patternRows}
    for h in history:
        pat = h.get("pattern")
        label = pat.split(" — ")[0] if pat else "-"
        patternCols[h["period"]] = [label]
    blocks.append(TableBlock("CF 패턴 추이", pl.DataFrame(patternCols)))

    return blocks


def cashQualityBlock(data: dict) -> list:
    """calcCashQuality 결과 → 영업CF/순이익, 영업CF 마진 시계열."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("cashQuality").label,
            level=2,
            helper="영업CF/순이익 > 100%이면 이익이 현금으로 회수됨",
        )
    )

    narration = narrateCashQuality(data)
    if narration:
        blocks.append(TextBlock(narration))

    rows = ["영업CF", "당기순이익", "영업CF/순이익", "영업CF 마진"]
    cols = {"": rows}
    for h in history:
        ratio = h.get("ocfToNi")
        margin = h.get("ocfMargin")
        cols[h["period"]] = [
            _fmtAmtShort(h["ocf"]),
            _fmtAmtShort(h["netIncome"]),
            f"{ratio:.0f}%" if ratio is not None else "-",
            f"{margin:.1f}%" if margin is not None else "-",
        ]
    blocks.append(TableBlock("현금 품질 추이", pl.DataFrame(cols)))

    return blocks


def cashFlowFlagsBlock(flags: list[str]) -> list:
    """calcCashFlowFlags 결과 → FlagBlock."""
    if not flags:
        return []
    return [FlagBlock(flags, kind="warning")]


# ── OCF 분해 빌더 ──


def ocfDecompositionBlock(data: dict) -> list:
    """calcOcfDecomposition → HeadingBlock + TableBlock."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []

    rows = []
    for h in history:
        rows.append(
            {
                "기간": h["period"],
                "순이익": h.get("ni"),
                "감가상각(추정)": h.get("depEstimate"),
                "운전자본효과": h.get("wcEffect"),
                "영업CF": h.get("ocf"),
                "잔차": h.get("residual"),
            }
        )

    unified = unifyTableScale(rows, "기간", ["순이익", "감가상각(추정)", "운전자본효과", "영업CF", "잔차"], unit="won")

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("ocfDecomposition").label,
            level=2,
            helper="OCF ≈ NI + 감가상각 + 운전자본. 잔차가 크면 비경상 항목",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(unified)))
    return blocks


def cashFlowGradeBlock(data: dict) -> list:
    """calcCashFlowGrade 결과 → eCR 시계열."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []

    rows = []
    for h in history:
        rows.append(
            {
                "기간": h["period"],
                "eCR": h.get("eCR", "?"),
                "OCF/매출": f"{h['ocfToSales']:.1f}%" if h.get("ocfToSales") is not None else "-",
                "FCF양수": "O" if h.get("fcfPositive") else "X",
                "OCF/Debt": f"{h['ocfToDebt']:.0f}%" if h.get("ocfToDebt") is not None else "-",
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("cashFlowGrade").label,
            level=2,
            helper="eCR-1(최상): OCF/매출>15% + FCF양수 + OCF/Debt>30%",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
    return blocks
