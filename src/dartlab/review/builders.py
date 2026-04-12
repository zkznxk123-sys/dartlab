"""review 블록 빌더 — calc* 결과(dict) → Block 리스트 변환.

analysis.financial 의 calc* 함수는 dict/숫자만 반환한다.
여기서 그 dict를 Block으로 조립한다.
"""

from __future__ import annotations

import polars as pl

from dartlab.review.blocks import (
    FlagBlock,
    HeadingBlock,
    MetricBlock,
    TableBlock,
    TextBlock,
)
from dartlab.review.catalog import getBlockMeta as _meta
from dartlab.review.narrate import (
    narrateCashFlow,
    narrateCashQuality,
    narrateConcentration,
    narrateDistress,
    narrateGrowth,
    narrateLeverage,
    narrateMargin,
    narrateROIC,
    narrateStrategy,
    narrateTechnicalVerdict,
    narrateValuation,
)
from dartlab.review.utils import unifyTableScale

# ── notes enrichment 렌더링 ──


def _notesDetailBlocks(data: dict, keyLabels: dict[str, str]) -> list:
    """notesDetail enrichment → TextBlock + TableBlock 리스트.

    calc 함수가 notesDetail 필드를 반환했을 때, 주석 테이블로 렌더링.
    notes accessor 는 원 단위로 노출되므로(`tableBuilder.buildTableDf`에서 정규화)
    추가 단위 변환 불필요.

    all-null row 제거 — parser 가 sub-row 헤더 (예: "OAT Nego", "Banker's Usance"
    등) 를 데이터 row 로 추출한 노이즈를 차단한다.
    """
    notesDetail = data.get("notesDetail")
    if not notesDetail:
        return []
    blocks: list = []
    for key, rows in notesDetail.items():
        if not rows:
            continue
        # all-null row (항목/snakeId 외 모든 값 None) 제거
        cleaned = []
        for row in rows:
            hasValue = any(
                v is not None and v != ""
                for k, v in row.items()
                if k not in ("항목", "snakeId", "account", "tag", "label")
            )
            if hasValue:
                cleaned.append(row)
        if not cleaned:
            continue
        label = keyLabels.get(key, key)
        try:
            blocks.append(TextBlock(f"▸ 주석: {label}", style="dim", indent="h2"))
            blocks.append(TableBlock("", pl.DataFrame(cleaned)))
        except (ValueError, TypeError):
            pass
    return blocks


# ── 수익구조 (revenue) 빌더 ──


def profileBlock(data: dict) -> list:
    """calcCompanyProfile 결과 → TextBlock."""
    if not data:
        return []
    parts = []
    if "sector" in data:
        parts.append(data["sector"])
    if "products" in data:
        parts.append(data["products"])
    if not parts:
        return []
    return [TextBlock(" | ".join(parts), style="dim", indent="h2")]


def segmentCompositionBlock(data: dict) -> list:
    """calcSegmentComposition 결과 → HeadingBlock + TableBlock."""
    if not data:
        return []
    segments = data.get("segments", [])
    if not segments:
        return []

    totalRev = data["totalRevenue"]
    hasOp = data.get("hasOpIncome", False)

    rows = []
    for seg in segments:
        rev = seg["revenue"]
        pct = rev / totalRev * 100 if totalRev else 0
        row = {"부문": seg["name"], "매출": rev, "비중": f"{pct:.0f}%"}
        if hasOp and seg.get("opIncome") is not None:
            row["영업이익"] = seg["opIncome"]
            margin = seg.get("opMargin")
            row["이익률"] = f"{margin:.1f}%" if margin is not None else "-"
        rows.append(row)

    valueCols = ["매출"]
    if hasOp:
        valueCols.append("영업이익")

    unified = unifyTableScale(rows, "부문", valueCols, unit="millions")
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("segmentComposition").label,
            level=2,
            helper="매출 비중 + 이익률로 수익 구조 편중을 본다",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(unified)))

    # 다년간 비중 변화 테이블
    history = data.get("compositionHistory")
    if history and len(history) >= 2:
        # {year, shares: {seg: pct}} → 부문×연도 테이블
        allSegs = []
        for h in history:
            for s in h["shares"]:
                if s not in allSegs:
                    allSegs.append(s)
        [h["year"] for h in history]
        histRows = []
        for seg in allSegs:
            row: dict = {"부문": seg}
            for h in history:
                row[h["year"]] = f"{h['shares'].get(seg, 0):.1f}%"
            histRows.append(row)
        blocks.append(TableBlock("비중 변화", pl.DataFrame(histRows)))

    return blocks


def segmentTrendBlock(data: dict) -> list:
    """calcSegmentTrend 결과 → HeadingBlock + TableBlock."""
    if not data:
        return []
    yearCols = data.get("yearCols", [])
    trendRows = data.get("rows", [])
    if not yearCols or not trendRows:
        return []

    rows = []
    for tr in trendRows:
        row: dict = {"부문": tr["name"]}
        for yc in yearCols:
            row[yc] = tr["values"].get(yc)
        if tr.get("yoy") is not None:
            row["YoY"] = f"{tr['yoy']:+.0f}%"
        else:
            row["YoY"] = "-"
        rows.append(row)

    unified = unifyTableScale(rows, "부문", yearCols, unit="millions")
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("segmentTrend").label,
            level=2,
            helper="부문별 성장/정체를 연도 비교로 식별",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(unified)))
    return blocks


def breakdownBlock(data: dict, sub: str) -> list:
    """calcBreakdown 결과 → HeadingBlock + TableBlock."""
    if not data:
        return []
    items = data.get("items", [])
    if not items:
        return []

    meta = _meta(sub)
    title = meta.label if meta else f"{sub}별 매출"

    rows = []
    for item in items:
        rows.append(
            {
                "구분": item["name"],
                "매출": item["value"],
                "비중": f"{item['pct']:.0f}%",
            }
        )

    unified = unifyTableScale(rows, "구분", ["매출"], unit="millions")
    blocks: list = []
    blocks.append(HeadingBlock(title, level=2))
    blocks.append(TableBlock("", pl.DataFrame(unified)))

    # 다년간 비중 변화
    history = data.get("breakdownHistory")
    if history and len(history) >= 2:
        allNames: list[str] = []
        for h in history:
            for n in h["shares"]:
                if n not in allNames:
                    allNames.append(n)
        histRows = []
        for name in allNames:
            row: dict = {"구분": name}
            for h in history:
                row[h["year"]] = f"{h['shares'].get(name, 0):.1f}%"
            histRows.append(row)
        blocks.append(TableBlock("비중 변화", pl.DataFrame(histRows)))

    return blocks


def revenueGrowthBlock(data: dict) -> list:
    """calcRevenueGrowth 결과 → MetricBlock + 분기 매출 TableBlock."""
    if not data:
        return []

    blocks: list = []
    metrics = []
    yoy = data.get("yoy")
    cagr = data.get("cagr3y")
    if yoy is not None:
        metrics.append(("매출 YoY", f"{yoy:+.1f}%"))
    if cagr is not None:
        metrics.append(("3Y CAGR", f"{cagr:+.1f}%"))

    # 분기 매출 테이블 (최근 8분기)
    quarterly = data.get("quarterlySelect")
    qTable = _quarterlyRevenueTable(quarterly)

    if not metrics and qTable is None:
        return []

    blocks.append(
        HeadingBlock(
            _meta("growth").label,
            level=2,
            helper="YoY vs 3Y CAGR 방향이 다르면 추세 전환 의심",
        )
    )

    narration = narrateGrowth(yoy, cagr)
    if narration:
        blocks.append(TextBlock(narration))

    if metrics:
        blocks.append(MetricBlock(metrics))
    if qTable is not None:
        blocks.append(qTable)

    return blocks


_MAX_QUARTERS = 8


def _quarterlyRevenueTable(selectResult) -> TableBlock | None:
    """SelectResult → 최근 N분기 매출 TableBlock."""
    if selectResult is None:
        return None

    df = selectResult.df
    if df is None or df.is_empty():
        return None

    # 기간 컬럼만 추출 (Q 포함)
    periodCols = [c for c in df.columns if "Q" in c]
    periodCols = sorted(periodCols, reverse=True)[:_MAX_QUARTERS]
    if not periodCols:
        return None

    labelCol = "항목" if "항목" in df.columns else df.columns[0]
    keepCols = [labelCol] + periodCols

    rows = []
    for row in df.select(keepCols).iter_rows(named=True):
        label = row[labelCol]
        rowDict = {"": label}
        for pc in periodCols:
            rowDict[pc] = row.get(pc)
        rows.append(rowDict)

    if not rows:
        return None

    unified = unifyTableScale(rows, "", periodCols, unit=_unitForCurrency())
    return TableBlock("분기별 매출", pl.DataFrame(unified))


def concentrationBlock(data: dict) -> list:
    """calcConcentration 결과 → MetricBlock."""
    if not data:
        return []

    metrics = []
    metrics.append(("HHI", f"{data['hhi']:,.0f} ({data['hhiLabel']})"))
    metrics.append(("1위 부문 비중", f"{data['topPct']:.0f}%"))
    if data.get("domesticPct") is not None:
        metrics.append(("내수 비중", f"{data['domesticPct']:.0f}%"))

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("concentration").label,
            level=2,
            helper="HHI > 5000 고집중, > 2500 중간 집중",
        )
    )

    narration = narrateConcentration(data)
    if narration:
        blocks.append(TextBlock(narration))

    blocks.append(MetricBlock(metrics))

    # HHI 시계열
    hhiHistory = data.get("hhiHistory")
    hhiDir = data.get("hhiDirection")
    if hhiHistory and len(hhiHistory) >= 2:
        hhiRows = [{"연도": h["year"], "HHI": f"{h['hhi']:,.0f}"} for h in hhiHistory]
        blocks.append(TableBlock("HHI 추이", pl.DataFrame(hhiRows)))
        if hhiDir:
            blocks.append(TextBlock(f"방향: {hhiDir}", style="dim", indent="h2"))

    return blocks


def revenueQualityBlock(data: dict) -> list:
    """calcRevenueQuality 결과 → MetricBlock."""
    if not data:
        return []

    metrics = []
    cc = data.get("cashConversion")
    if cc is not None:
        metrics.append(("영업CF/순이익", f"{cc:.0f}% ({data['cashConversionLabel']})"))
    gm = data.get("grossMargin")
    if gm is not None:
        metrics.append(("매출총이익률", f"{gm:.1f}%"))

    gmDir = data.get("grossMarginDirection", "안정")
    if gmDir and gmDir != "안정":
        metrics.append(("총이익률 방향", gmDir))

    if not metrics:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("revenueQuality").label,
            level=2,
            helper="영업CF/순이익 80%+ 양호, 총이익률 하락 추세 주의",
        )
    )
    blocks.append(MetricBlock(metrics))
    return blocks


def growthContributionBlock(data: dict) -> list:
    """calcGrowthContribution 결과 → MetricBlock + TextBlock."""
    if not data:
        return []

    totalPct = data.get("totalGrowthPct")
    contributions = data.get("contributions", [])
    driver = data.get("driver", "")

    if not contributions:
        return []

    period = data.get("period", "")

    blocks: list = []
    periodSuffix = f" ({period})" if period else ""
    blocks.append(
        HeadingBlock(
            f"{_meta('growthContribution').label}{periodSuffix}",
            level=2,
            helper="어느 부문이 전체 성장을 이끌었는가",
        )
    )

    metrics = []
    if totalPct is not None:
        metrics.append(("전체 매출 변화", f"{totalPct:+.1f}%"))
    for c in contributions[:5]:
        sign = "+" if c["amount"] > 0 else ""
        metrics.append((c["name"], f"기여 {sign}{c['pct']:.0f}%"))
    blocks.append(MetricBlock(metrics))

    if driver:
        blocks.append(TextBlock(driver, style="dim", indent="h2"))

    return blocks


def revenueFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcFlags 결과 → FlagBlock."""
    if not flags:
        return []
    warnings = [f for f, k in flags if k == "warning"]
    opportunities = [f for f, k in flags if k == "opportunity"]
    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks


# ── 자금구조 (capital) 빌더 ──


def fundingSourcesBlock(data: dict) -> list:
    """calcFundingSources 결과 → 조달원 비중 테이블 + 시계열."""
    if not data:
        return []

    latest = data.get("latest")
    if not latest:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("fundingSources").label,
            level=2,
            helper="내부유보 = 사업으로 번 돈, 금융차입 = 이자 붙는 빚, 영업조달 = 자연 발생 자금",
        )
    )

    # 최신 비중 메트릭
    fmtAmt = _fmtAmtShort(latest["totalAssets"])
    metrics = [("총자산", fmtAmt)]
    metrics.append(("내부유보 (이익잉여금)", f"{_fmtAmtShort(latest['retained'])} ({latest['retainedPct']:.0f}%)"))
    metrics.append(("외부-주주 (자본금+잉여금)", f"{_fmtAmtShort(latest['paidIn'])} ({latest['paidInPct']:.0f}%)"))
    metrics.append(("외부-금융차입", f"{_fmtAmtShort(latest['finDebt'])} ({latest['finDebtPct']:.0f}%)"))
    if latest["opFundingPct"] > 0.5:
        metrics.append(
            ("영업조달 (매입채무·선수금 등)", f"{_fmtAmtShort(latest['opFunding'])} ({latest['opFundingPct']:.0f}%)")
        )
    blocks.append(MetricBlock(metrics))

    # 시계열 테이블 (행=항목, 열=기간)
    history = data.get("history", [])
    if len(history) >= 2:
        cols = {"": ["내부유보", "주주자본", "금융차입", "영업조달"]}
        for h in history:
            cols[h["period"]] = [
                f"{h['retainedPct']:.0f}%",
                f"{h['paidInPct']:.0f}%",
                f"{h['finDebtPct']:.0f}%",
                f"{h['opFundingPct']:.0f}%",
            ]
        blocks.append(TableBlock("조달원 비중 추이", pl.DataFrame(cols)))

    # 보충 지표 (순차입금/EBITDA, 암묵적 차입금리)
    suppMetrics = []
    ndEbitda = data.get("netDebtEbitda")
    if ndEbitda is not None:
        if ndEbitda == 0:
            suppMetrics.append(("순차입금/EBITDA", "순현금 (차입 없음)"))
        else:
            suppMetrics.append(("순차입금/EBITDA", f"{ndEbitda:.1f}배"))
    impliedRate = data.get("impliedBorrowingRate")
    if impliedRate is not None:
        suppMetrics.append(("암묵적 차입금리", f"{impliedRate:.1f}%"))
    if suppMetrics:
        blocks.append(MetricBlock(suppMetrics))

    # 진단 + 비중 변화 방향
    diagnosis = data.get("diagnosis", "")
    leverageTrend = data.get("leverageTrend")
    diagParts = [p for p in [diagnosis, leverageTrend] if p]
    if diagParts:
        blocks.append(TextBlock(" | ".join(diagParts), style="dim", indent="h2"))

    blocks.extend(_notesDetailBlocks(data, {"borrowings": "차입금 상세"}))

    return blocks


import contextvars

_review_currency: contextvars.ContextVar[str] = contextvars.ContextVar("review_currency", default="KRW")


def _unitForCurrency() -> str:
    """현재 통화에 맞는 unifyTableScale unit 반환."""
    return "usd" if _review_currency.get() == "USD" else "won"


def _fmtAmtShort(value) -> str:
    """금액 간략 포맷 (KRW: 조/억, USD: B/M)."""
    if value is None or value == 0:
        return "-"
    absVal = abs(value)
    sign = "-" if value < 0 else ""
    if _review_currency.get() == "USD":
        if absVal >= 1_000_000_000:
            return f"{sign}${absVal / 1_000_000_000:.1f}B"
        if absVal >= 1_000_000:
            return f"{sign}${absVal / 1_000_000:.0f}M"
        return f"{sign}${absVal:,.0f}"
    if absVal >= 1_0000_0000_0000:
        return f"{sign}{absVal / 1_0000_0000_0000:.1f}조"
    if absVal >= 1_0000_0000:
        return f"{sign}{absVal / 1_0000_0000:.0f}억"
    return f"{sign}{absVal:,.0f}"


def capitalOverviewBlock(data: dict) -> list:
    """calcCapitalOverview 결과 → MetricBlock."""
    if not data:
        return []
    metrics = data.get("metrics", [])
    if not metrics:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("capitalOverview").label,
            level=2,
            helper="부채비율 100% 이하 안정, 순현금이면 재무 여유",
        )
    )
    blocks.append(MetricBlock(metrics))
    return blocks


def capitalTimelineBlock(data: dict) -> list:
    """calcCapitalTimeline 결과 → TableBlock."""
    if not data:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("capitalTimeline").label,
            level=2,
            helper="이익잉여금 = 사업으로 번 돈, 자본금+잉여금 = 외부 조달",
        )
    )
    for label, tableRows, cols in data.get("tables", []):
        if tableRows and cols:
            unified = unifyTableScale(tableRows, "", cols, unit=_unitForCurrency())
            blocks.append(TableBlock(label, pl.DataFrame(unified)))
    if len(blocks) <= 1:
        return []
    return blocks


def debtTimelineBlock(data: dict) -> list:
    """calcDebtTimeline 결과 → TableBlock."""
    if not data:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("debtTimeline").label,
            level=2,
            helper="영업부채 = 자연 발생, 금융부채 = 이자 붙는 차입",
        )
    )
    for label, tableRows, cols in data.get("tables", []):
        if tableRows and cols:
            unified = unifyTableScale(tableRows, "", cols, unit=_unitForCurrency())
            blocks.append(TableBlock(label, pl.DataFrame(unified)))
    if len(blocks) <= 1:
        return []
    return blocks


def interestBurdenBlock(data: dict) -> list:
    """calcInterestBurden 결과 → MetricBlock."""
    if not data:
        return []
    metrics = data.get("metrics", [])
    if not metrics:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("interestBurden").label,
            level=2,
            helper="이자보상배율 3배 이상 안정, 1.5배 이하 주의",
        )
    )
    blocks.append(MetricBlock(metrics))
    return blocks


def liquidityBlock(data: dict) -> list:
    """calcLiquidity 결과 → MetricBlock."""
    if not data:
        return []
    metrics = data.get("metrics", [])
    if not metrics:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("liquidity").label,
            level=2,
            helper="유동비율 100% 이하 → 단기 지급 리스크",
        )
    )
    blocks.append(MetricBlock(metrics))
    return blocks


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


def distressBlock(data: dict) -> list:
    """calcDistressIndicators 결과 → MetricBlock."""
    if not data:
        return []
    metrics = data.get("metrics", [])
    if not metrics:
        return []
    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("distressIndicators").label,
            level=2,
            helper="Altman Z > 2.99 안전, Piotroski F ≥ 7 건전",
        )
    )
    blocks.append(MetricBlock(metrics))
    return blocks


def capitalFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcCapitalFlags 결과 → FlagBlock."""
    if not flags:
        return []
    warnings = [f for f, k in flags if k == "warning"]
    opportunities = [f for f, k in flags if k == "opportunity"]
    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks


# ── 자산구조 (asset) 빌더 ──


def assetStructureBlock(data: dict) -> list:
    """calcAssetStructure 결과 → 영업/비영업 재분류 시계열."""
    if not data:
        return []

    history = data.get("history", [])
    if not history:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("assetStructure").label,
            level=2,
            helper="영업자산 = 사업에 투입된 자산, 비영업 = 현금/투자/금융자산",
        )
    )

    # 비중 시계열 테이블
    rows = ["총자산", "영업자산", "비영업자산", "순영업자산(NOA)", "순운전자본", "고정영업자산"]
    cols = {"": rows}
    for h in history:
        ta = h.get("totalAssets", 0)
        cols[h["period"]] = [
            _fmtAmtShort(ta),
            f"{_fmtAmtShort(h['opAssets'])} ({h['opAssetsPct']:.0f}%)",
            f"{_fmtAmtShort(h['nonOpAssets'])} ({h['nonOpAssetsPct']:.0f}%)",
            _fmtAmtShort(h["noa"]),
            _fmtAmtShort(h["wc"]),
            _fmtAmtShort(h["fixedOp"]),
        ]
    blocks.append(TableBlock("자산 재분류 추이", pl.DataFrame(cols)))

    # 세부 구성 시계열 (영업+비영업 주요 항목)
    detailRows = ["매출채권", "재고자산", "유형자산", "무형자산+영업권", "건설중인자산", "현금성자산", "투자자산"]
    detailCols = {"": detailRows}
    for h in history:
        intGw = h.get("intangibles", 0) + h.get("goodwill", 0)
        detailCols[h["period"]] = [
            _fmtAmtShort(h.get("receivables", 0)),
            _fmtAmtShort(h.get("inventory", 0)),
            _fmtAmtShort(h.get("ppe", 0)),
            _fmtAmtShort(intGw),
            _fmtAmtShort(h.get("cip", 0)),
            _fmtAmtShort(h.get("cash", 0)),
            _fmtAmtShort(h.get("investments", 0)),
        ]
    blocks.append(TableBlock("자산 구성 상세 추이", pl.DataFrame(detailCols)))

    # 진단
    diagnosis = data.get("diagnosis")
    if diagnosis:
        blocks.append(TextBlock(diagnosis, style="dim", indent="h2"))

    blocks.extend(
        _notesDetailBlocks(
            data, {"inventory": "재고자산 상세", "tangibleAsset": "유형자산 변동", "intangibleAsset": "무형자산 상세"}
        )
    )

    return blocks


def workingCapitalBlock(data: dict) -> list:
    """calcWorkingCapital 결과 → 운전자본 + CCC."""
    if not data:
        return []

    latest = data.get("latest")
    if not latest:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("workingCapital").label,
            level=2,
            helper="CCC = 재고회전일 + 매출채권회전일 - 매입채무회전일",
        )
    )

    metrics = [
        ("순운전자본", _fmtAmtShort(latest["wc"])),
    ]
    for label, key, suffix in [
        ("매출채권 회전일", "receivableDays", "일"),
        ("재고 회전일", "inventoryDays", "일"),
        ("매입채무 회전일", "payableDays", "일"),
        ("CCC", "ccc", "일"),
    ]:
        val = latest.get(key)
        if val is not None:
            metrics.append((label, f"{val:.0f}{suffix}"))
    blocks.append(MetricBlock(metrics))

    # CCC 시계열 (행=항목, 열=기간)
    history = data.get("history", [])
    if len(history) >= 2:
        hasData = any(h.get("ccc") is not None for h in history)
        if hasData:
            cols = {"": ["매출채권일", "재고일", "매입채무일", "CCC"]}
            for h in history:
                cols[h["period"]] = [
                    f"{h['receivableDays']:.0f}" if h.get("receivableDays") is not None else "-",
                    f"{h['inventoryDays']:.0f}" if h.get("inventoryDays") is not None else "-",
                    f"{h['payableDays']:.0f}" if h.get("payableDays") is not None else "-",
                    f"{h['ccc']:.0f}" if h.get("ccc") is not None else "-",
                ]
            blocks.append(TableBlock("CCC 추이", pl.DataFrame(cols)))

    return blocks


def capexBlock(data: dict) -> list:
    """calcCapexPattern 결과 → CAPEX/감가상각 + 건설중인자산."""
    if not data:
        return []

    latest = data.get("latest")
    if not latest:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("capexPattern").label,
            level=2,
            helper="CAPEX/감가상각 > 1 → 성장 투자, < 1 → 유지/수확",
        )
    )

    metrics = [
        ("CAPEX", _fmtAmtShort(latest["capex"])),
        ("감가상각", _fmtAmtShort(latest["depreciation"])),
    ]
    ratio = latest.get("capexToDepRatio")
    if ratio is not None:
        metrics.append(("CAPEX/감가상각", f"{ratio:.1f}배"))
    cip = latest.get("cip", 0)
    if cip > 0:
        metrics.append(("건설중인자산", f"{_fmtAmtShort(cip)} ({latest['cipPct']:.0f}%)"))
    blocks.append(MetricBlock(metrics))

    investType = latest.get("investmentType")
    if investType:
        blocks.append(TextBlock(investType, style="dim", indent="h2"))

    # 시계열 (행=항목, 열=기간)
    history = data.get("history", [])
    if len(history) >= 2:
        cols = {"": ["CAPEX", "감가상각", "CAPEX/감가상각", "건설중인자산"]}
        for h in history:
            r = h.get("capexToDepRatio")
            cols[h["period"]] = [
                _fmtAmtShort(h["capex"]),
                _fmtAmtShort(h["depreciation"]),
                f"{r:.1f}배" if r is not None else "-",
                _fmtAmtShort(h["cip"]),
            ]
        blocks.append(TableBlock("CAPEX 추이", pl.DataFrame(cols)))

    return blocks


def assetEfficiencyBlock(data: dict) -> list:
    """calcAssetEfficiency 결과 → 회전율 시계열."""
    if not data:
        return []

    history = data.get("history", [])
    if len(history) < 2:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("assetEfficiency").label,
            level=2,
            helper="회전율이 높을수록 같은 자산으로 매출을 더 뽑는다",
        )
    )

    cols = {"": ["총자산회전율", "유형자산회전율"]}
    for h in history:
        ta = h.get("totalAssetTurnover")
        ppe = h.get("ppeTurnover")
        cols[h["period"]] = [
            f"{ta:.2f}회" if ta is not None else "-",
            f"{ppe:.2f}회" if ppe is not None else "-",
        ]
    blocks.append(TableBlock("회전율 추이", pl.DataFrame(cols)))

    return blocks


def assetFlagsBlock(flags: list[str]) -> list:
    """calcAssetFlags 결과 → FlagBlock."""
    if not flags:
        return []
    return [FlagBlock(flags, kind="warning")]


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


# ── 2부: 재무비율 분석 빌더 ──


def _extractSeries(data: dict, field: str) -> list[dict]:
    """history 기반 calc 결과에서 [{"period": p, "value": v}, ...] 추출."""
    history = data.get("history", [])
    if not history:
        return data.get(field, [])
    return [{"period": h["period"], "value": h.get(field)} for h in history if h.get(field) is not None]


def _timelineTable(
    specs: list[tuple[list[dict], str]],
    rowLabels: list[str],
) -> dict[str, list[str]] | None:
    """[{period, value}, ...] 시계열 → 행=지표, 열=기간 dict.

    specs: [(series, fmt), ...] -- series는 buildTimeline 결과, fmt는 f-string 포맷.
    rowLabels: 각 행 라벨 (specs와 동일 순서).
    반환: polars DataFrame으로 변환 가능한 dict. 기간 데이터 없으면 None.
    """
    cols: dict[str, list[str]] = {"": rowLabels}
    for idx, (series, fmt) in enumerate(specs):
        for item in series:
            period = item["period"]
            if period not in cols:
                cols[period] = ["-"] * len(rowLabels)
            v = item["value"]
            cols[period][idx] = fmt.format(v) if v is not None else "-"
    if len(cols) <= 1:
        return None
    return cols


_POSITIVE_KEYWORDS = ("안정", "건전", "양호", "우량", "순현금", "충분", "개선", "고성장")


def _flagsBlock(flags: list[str]) -> list:
    """플래그 리스트 → FlagBlock. 긍정/경고 자동 분류."""
    if not flags:
        return []
    warnings = []
    opportunities = []
    for f in flags:
        if any(kw in f for kw in _POSITIVE_KEYWORDS):
            opportunities.append(f)
        else:
            warnings.append(f)
    result = []
    if warnings:
        result.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        result.append(FlagBlock(opportunities, kind="opportunity"))
    return result


def _enrichedFlagsBlock(flags: list[str], enrichedFlags: list[dict] | None = None) -> list:
    """플래그 + enrichedFlags → FlagBlock. 정밀도 메타 포함."""
    if not flags:
        return []
    # EnrichedFlag 변환
    efList = None
    if enrichedFlags:
        from dartlab.review.blocks import EnrichedFlag

        efList = [
            EnrichedFlag(
                code=ef.get("code", ""),
                message=ef.get("message", ""),
                precision=ef.get("precision"),
                baseRate=ef.get("baseRate", ""),
                reference=ef.get("reference", ""),
                sectorNote=ef.get("sectorNote", ""),
            )
            for ef in enrichedFlags
        ]
        # enrichedFlags의 메시지에 정밀도 주석 추가
        {ef.get("code") for ef in enrichedFlags}
        augmented = []
        for f in flags:
            matched = next((ef for ef in enrichedFlags if ef.get("message") == f), None)
            if matched and matched.get("precision") is not None:
                p = matched["precision"]
                ref = matched.get("reference", "")
                note = matched.get("sectorNote", "")
                suffix = f" (정밀도 {p:.0%}, {ref})"
                if note:
                    suffix += f" [{note}]"
                augmented.append(f + suffix)
            else:
                augmented.append(f)
        flags = augmented

    warnings = []
    opportunities = []
    for f in flags:
        if any(kw in f for kw in _POSITIVE_KEYWORDS):
            opportunities.append(f)
        else:
            warnings.append(f)
    result = []
    if warnings:
        result.append(FlagBlock(warnings, kind="warning", enrichedFlags=efList))
    if opportunities:
        result.append(FlagBlock(opportunities, kind="opportunity"))
    return result


# ── 2-1 수익성 ──


def marginTrendBlock(data: dict) -> list:
    """calcMarginTrend 결과 → 마진 시계열 테이블."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "grossMargin"), "{:.1f}%"),
            (_extractSeries(data, "operatingMargin"), "{:.1f}%"),
            (_extractSeries(data, "netMargin"), "{:.1f}%"),
        ],
        ["매출총이익률", "영업이익률", "순이익률"],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("marginTrend").label,
            level=2,
            helper="매출총이익률 안정 + 영업이익률 상승 = 원가 통제 + 판관비 효율",
        ),
    ]

    narration = narrateMargin(data)
    if narration:
        blocks.append(TextBlock(narration))

    blocks.append(TableBlock("마진 추이", pl.DataFrame(cols)))

    # 마진 시계열 차트
    history = data.get("history", [])
    if history:
        from dartlab.review.blocks import ChartBlock
        from dartlab.viz.generators import spec_margin_trend

        chart = spec_margin_trend(history)
        if chart:
            blocks.append(ChartBlock(spec=chart))
    return blocks


def returnTrendBlock(data: dict) -> list:
    """calcReturnTrend 결과 → ROE/ROA 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "roe"), "{:.1f}%"),
            (_extractSeries(data, "roa"), "{:.1f}%"),
            (_extractSeries(data, "leverage"), "{:.2f}배"),
        ],
        ["ROE", "ROA", "레버리지(ROE/ROA)"],
    )
    if cols is None:
        return []

    return [
        HeadingBlock(
            _meta("returnTrend").label,
            level=2,
            helper="ROE/ROA > 2 → 레버리지로 수익률 확대",
        ),
        TableBlock("수익률 추이", pl.DataFrame(cols)),
    ]


def dupontBlock(data: dict) -> list:
    """calcDupont 결과 → 듀퐁 분해 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "operatingMargin"), "{:.1f}%"),
            (_extractSeries(data, "assetTurnover"), "{:.2f}"),
            (_extractSeries(data, "leverage"), "{:.2f}"),
        ],
        ["영업이익률(%)", "자산회전율(회)", "재무레버리지(배)"],
    )
    if cols is None:
        return []

    return [
        HeadingBlock(
            _meta("dupont").label,
            level=2,
            helper="ROE = 순이익률 x 자산회전율 x 재무레버리지",
        ),
        TableBlock("듀퐁 분해", pl.DataFrame(cols)),
    ]


def profitabilityFlagsBlock(flags: list[str]) -> list:
    """calcProfitabilityFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


# ── 2-2 성장성 ──


def growthTrendBlock(data: dict) -> list:
    """calcGrowthTrend 결과 → 성장률 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "revenueYoy"), "{:+.1f}%"),
            (_extractSeries(data, "operatingIncomeYoy"), "{:+.1f}%"),
            (_extractSeries(data, "netIncomeYoy"), "{:+.1f}%"),
            (_extractSeries(data, "totalAssetsYoy"), "{:+.1f}%"),
        ],
        ["매출 성장률", "영업이익 성장률", "순이익 성장률", "자산 성장률"],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("growthTrend").label,
            level=2,
            helper="매출 성장 > 이익 성장이면 수익성 희석 가능",
        ),
        TableBlock("성장률 추이", pl.DataFrame(cols)),
    ]

    history = data.get("history", [])
    if history:
        from dartlab.review.blocks import ChartBlock
        from dartlab.viz.generators import spec_growth_yoy_bar

        chart = spec_growth_yoy_bar(history)
        if chart:
            blocks.append(ChartBlock(spec=chart))
    return blocks


def growthQualityBlock(data: dict) -> list:
    """calcGrowthQuality 결과 → CAGR + 성장 품질."""
    if not data:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("growthQuality").label,
            level=2,
            helper="CAGR로 단기 변동 너머의 중기 추세를 본다",
        )
    )

    periods = data.get("periods", 0)
    metrics = []
    revCagr = data.get("revenueCagr")
    opCagr = data.get("operatingProfitCagr")
    npCagr = data.get("netProfitCagr")
    quality = data.get("quality", "")

    if revCagr is not None:
        metrics.append((f"매출 CAGR ({periods}Y)", f"{revCagr:+.1f}%"))
    if opCagr is not None:
        metrics.append((f"영업이익 CAGR ({periods}Y)", f"{opCagr:+.1f}%"))
    if npCagr is not None:
        metrics.append((f"순이익 CAGR ({periods}Y)", f"{npCagr:+.1f}%"))
    if quality:
        metrics.append(("성장 품질", quality))

    if not metrics:
        return []
    blocks.append(MetricBlock(metrics))
    return blocks


def growthFlagsBlock(flags: list[str]) -> list:
    """calcGrowthFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


# ── 2-3 안정성 ──


def leverageTrendBlock(data: dict) -> list:
    """calcLeverageTrend 결과 → 레버리지 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "debtRatio"), "{:.0f}%"),
            (_extractSeries(data, "netDebtRatio"), "{:.0f}%"),
            (_extractSeries(data, "equityRatio"), "{:.0f}%"),
        ],
        ["부채비율", "순부채비율", "자기자본비율"],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("leverageTrend").label,
            level=2,
            helper="부채비율 200% 이상 위험, 50% 이하 매우 안정",
        ),
    ]

    narration = narrateLeverage(data)
    if narration:
        blocks.append(TextBlock(narration))

    blocks.append(TableBlock("레버리지 추이", pl.DataFrame(cols)))
    blocks.extend(_notesDetailBlocks(data, {"borrowings": "차입금 구성", "lease": "리스부채"}))

    history = data.get("history", [])
    if history:
        from dartlab.review.blocks import ChartBlock
        from dartlab.viz.generators import spec_leverage_trend

        chart = spec_leverage_trend(history)
        if chart:
            blocks.append(ChartBlock(spec=chart))
    return blocks


def coverageTrendBlock(data: dict) -> list:
    """calcCoverageTrend 결과 → 이자보상배율 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [(_extractSeries(data, "interestCoverage"), "{:.1f}배")],
        ["이자보상배율"],
    )
    if cols is None:
        return []

    return [
        HeadingBlock(
            _meta("coverageTrend").label,
            level=2,
            helper="이자보상배율 3배 이상 안정, 1배 미만 이자 지급 불능",
        ),
        TableBlock("이자보상 추이", pl.DataFrame(cols)),
    ]


def distressScoreBlock(data: dict) -> list:
    """calcDistressScore 결과 → Z-Score 시계열 + 등급."""
    if not data:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("distressScore").label,
            level=2,
            helper="Z > 2.99 안전, 1.81~2.99 회색, < 1.81 위험",
        )
    )

    narration = narrateDistress(data)
    if narration:
        blocks.append(TextBlock(narration))

    metrics = []
    latest = data.get("latestScore")
    zone = data.get("zone", "")
    if latest is not None:
        metrics.append(("최신 Z-Score", f"{latest:.2f}"))
    if zone:
        metrics.append(("판정", zone))
    if metrics:
        blocks.append(MetricBlock(metrics))

    cols = _timelineTable(
        [(_extractSeries(data, "altmanZScore"), "{:.2f}")],
        ["Altman Z-Score"],
    )
    if cols is not None:
        blocks.append(TableBlock("Z-Score 추이", pl.DataFrame(cols)))

    # 충당부채 주석은 위험/회색 구간일 때만 표시
    zone = data.get("zone", "")
    if zone in ("위험", "회색"):
        blocks.extend(_notesDetailBlocks(data, {"provisions": "충당부채 상세"}))

    return blocks


def scenarioSensitivityBlock(data: dict | None) -> list:
    """calcScenarioSensitivity 결과 → shock별 지표 변화 + 해석."""
    if not data:
        return []

    base = data.get("baseCase", {})
    shocks = data.get("shocks", {})
    if not shocks:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("scenarioSensitivity").label,
            level=2,
            helper="핵심 가정이 무너지면 어떻게 되는가 — 3가지 하방 shock",
        ),
    ]

    # Base case metrics
    base_metrics = []
    if base.get("opm") is not None:
        base_metrics.append(("현재 OPM", f"{base['opm']:.1f}%"))
    if base.get("roe") is not None:
        base_metrics.append(("현재 ROE", f"{base['roe']:.1f}%"))
    if base.get("interestCoverage") is not None:
        base_metrics.append(("이자보상배율", f"{base['interestCoverage']:.1f}x"))
    if base_metrics:
        blocks.append(MetricBlock(base_metrics))

    # Shock table
    rows = []
    shock_labels = {
        "opm_minus_5pp": "OPM -5%p",
        "revenue_minus_15pct": "매출 -15%",
        "interest_plus_2pp": "금리 +2%p",
    }
    for key, label in shock_labels.items():
        s = shocks.get(key)
        if not s:
            continue
        row: dict = {"시나리오": label}
        if s.get("roe") is not None:
            row["ROE"] = f"{s['roe']:.1f}%"
        if s.get("interestCoverage") is not None:
            row["이자보상"] = f"{s['interestCoverage']:.1f}x"
        row["판정"] = s.get("verdict", "")
        rows.append(row)

    if rows:
        blocks.append(TableBlock("하방 시나리오 영향", pl.DataFrame(rows)))

    # breakdown point
    bp = data.get("breakdownPoint")
    if bp and bp.get("value") is not None:
        safety = bp.get("safetyMargin")
        txt = f"**손익분기점**: OPM {bp['value']:.1f}% ({bp['meaning']})"
        if safety is not None:
            txt += f" — 현재 안전마진 {safety:.1f}%p"
        blocks.append(TextBlock(txt))

    # 인과 연쇄 narrate — OPM shock에서 파생 지표 변화 자동 문장
    opm_shock = shocks.get("opm_minus_5pp", {})
    if opm_shock and base:
        from dartlab.review.narrate import narrateCausalChain

        metrics = {}
        if base.get("opm") is not None and opm_shock.get("opm") is not None:
            metrics["opm_delta"] = opm_shock["opm"] - base["opm"]
        if base.get("roe") is not None and opm_shock.get("roe") is not None:
            base_roe = base["roe"]
            metrics["debt_delta_pp"] = opm_shock["roe"] - base_roe  # ROE 변화를 proxy로
        chain = narrateCausalChain(metrics)
        if chain:
            blocks.append(TextBlock(chain))

    return blocks


def criticalAssumptionsBlock(data: dict | None) -> list:
    """calcScenarioSensitivity 결과 → 핵심 가정 목록."""
    if not data:
        return []
    assumptions = data.get("criticalAssumptions", [])
    if not assumptions:
        return []

    return [
        HeadingBlock(
            _meta("criticalAssumptions").label,
            level=2,
            helper="이 보고서의 결론을 지탱하는 가정. 하나라도 무너지면 재평가 필요.",
        ),
        TextBlock("\n".join(f"- {a}" for a in assumptions)),
    ]


def stabilityFlagsBlock(data) -> list:
    """calcStabilityFlags 결과 → FlagBlock."""
    if isinstance(data, dict):
        return _enrichedFlagsBlock(data.get("flags", []), data.get("enrichedFlags"))
    flags = data if isinstance(data, list) else []
    return _flagsBlock(flags)


# ── 2-4 효율성 ──


def turnoverTrendBlock(data: dict) -> list:
    """calcTurnoverTrend 결과 → 회전율 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "totalAssetTurnover"), "{:.2f}회"),
            (_extractSeries(data, "receivablesTurnover"), "{:.2f}회"),
            (_extractSeries(data, "inventoryTurnover"), "{:.2f}회"),
        ],
        ["총자산회전율", "매출채권회전율", "재고회전율"],
    )
    if cols is None:
        return []

    return [
        HeadingBlock(
            _meta("turnoverTrend").label,
            level=2,
            helper="회전율 상승 = 같은 자산으로 매출을 더 뽑는다",
        ),
        TableBlock("회전율 추이", pl.DataFrame(cols)),
    ]


def cccTrendBlock(data: dict) -> list:
    """calcCccTrend 결과 → CCC 구성요소 시계열."""
    if not data:
        return []

    cols = _timelineTable(
        [
            (_extractSeries(data, "dso"), "{:.0f}일"),
            (_extractSeries(data, "dio"), "{:.0f}일"),
            (_extractSeries(data, "dpo"), "{:.0f}일"),
            (_extractSeries(data, "ccc"), "{:.0f}일"),
        ],
        ["DSO(매출채권일)", "DIO(재고일)", "DPO(매입채무일)", "CCC"],
    )
    if cols is None:
        return []

    return [
        HeadingBlock(
            _meta("cccTrend").label,
            level=2,
            helper="CCC = DSO + DIO - DPO, 마이너스면 운전자본 유리",
        ),
        TableBlock("CCC 추이", pl.DataFrame(cols)),
    ]


def efficiencyFlagsBlock(flags: list[str]) -> list:
    """calcEfficiencyFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


# ── 2-5 종합 평가 ──


def scorecardBlock(data: dict) -> list:
    """calcScorecard 결과 → 5영역 등급 테이블."""
    if not data:
        return []

    items = data.get("items", [])
    if not items:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("scorecard").label,
            level=2,
            helper="F 등급 영역을 최우선으로 개선 검토",
        )
    )

    rows = []
    for item in items:
        rows.append({"영역": item["area"], "등급": item["grade"]})
    blocks.append(TableBlock("", pl.DataFrame(rows)))

    profile = data.get("profile", "")
    if profile:
        blocks.append(TextBlock(f"재무 프로필: {profile}", style="dim", indent="h2"))

    return blocks


def piotroskiBlock(data: dict) -> list:
    """calcPiotroskiDetail 결과 → 9개 항목 상세."""
    if not data:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("piotroski").label,
            level=2,
            helper="9점 만점, 7+ 건전, 3- 심각",
        )
    )

    total = data.get("total", 0)
    interp = data.get("interpretation", "")
    interpKor = {"strong": "건전", "moderate": "보통", "weak": "취약"}.get(interp, interp)
    blocks.append(MetricBlock([("F-Score", f"{total}/9 ({interpKor})")]))

    items = data.get("items", [])
    if items:
        rows = []
        for item in items:
            rows.append(
                {
                    "항목": item["signal"],
                    "충족": "O" if item["pass"] else "X",
                }
            )
        blocks.append(TableBlock("", pl.DataFrame(rows)))

    return blocks


def summaryFlagsBlock(flags: list[str]) -> list:
    """calcSummaryFlags 결과 → FlagBlock."""
    if not flags:
        return []
    return [FlagBlock(flags, kind="warning")]


# ── 3부: 심화 분석 ──


def _historyTable(
    data: dict | None,
    fields: list[tuple[str, str, str]],
) -> dict[str, list[str]] | None:
    """history 기반 시계열 → 행=지표, 열=기간 dict.

    fields: [(key, rowLabel, fmt), ...] -- history item의 key, 행 라벨, 포맷.
    """
    if not data:
        return None
    history = data.get("history", [])
    if not history:
        return None

    rowLabels = [f[1] for f in fields]
    cols: dict[str, list[str]] = {"": rowLabels}
    for h in history:
        period = h["period"]
        vals = []
        for key, _, fmt in fields:
            v = h.get(key)
            if v is None:
                vals.append("-")
            elif fmt == "amt":
                vals.append(_fmtAmtShort(v))
            else:
                vals.append(fmt.format(v))
        cols[period] = vals
    return cols if len(cols) > 1 else None


# ── 3-1 이익품질 ──


def accrualAnalysisBlock(data: dict) -> list:
    """calcAccrualAnalysis 결과 → 발생액 시계열."""
    cols = _historyTable(
        data,
        [
            ("sloanAccrualRatio", "Sloan 발생액비율", "{:.2f}"),
            ("accrualToRevenue", "발생액/매출(%)", "{:.1f}%"),
            ("ocfToNi", "영업CF/순이익(%)", "{:.0f}%"),
        ],
    )
    if cols is None:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("accrualAnalysis").label,
            level=2,
            helper="발생액비율 0.10 이상 = 이익 현금화 부족",
        ),
        TableBlock("발생액 추이", pl.DataFrame(cols)),
    ]
    blocks.extend(_notesDetailBlocks(data, {"receivables": "매출채권 상세"}))
    return blocks


def earningsPersistenceBlock(data: dict) -> list:
    """calcEarningsPersistence 결과 → 이익 지속성."""
    if not data:
        return []

    cols = _historyTable(
        data,
        [
            ("operatingIncome", "영업이익", "amt"),
            ("nonOperatingIncome", "영업외손익", "amt"),
            ("nonOpRatio", "영업외비중(%)", "{:.1f}%"),
        ],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("earningsPersistence").label,
            level=2,
            helper="영업외비중 30%+ = 일회성 이익 의존",
        ),
        TableBlock("이익 구성 추이", pl.DataFrame(cols)),
    ]

    cv = data.get("earningsVolatility")
    if cv is not None:
        blocks.append(MetricBlock([("이익 변동계수(CV)", f"{cv:.2f}")]))

    return blocks


def beneishMScoreBlock(data: dict) -> list:
    """calcBeneishTimeline 결과 → M-Score 시계열."""
    cols = _historyTable(
        data,
        [
            ("mScore", "M-Score", "{:.2f}"),
        ],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("beneishMScore").label,
            level=2,
            helper="M-Score > -1.78 임계값 초과 = 이익 조작 가능성",
        ),
        TableBlock("M-Score 추이", pl.DataFrame(cols)),
    ]

    threshold = data.get("threshold")
    if threshold is not None:
        blocks.append(TextBlock(f"임계값: {threshold}", style="dim", indent="h2"))

    return blocks


def earningsQualityFlagsBlock(data) -> list:
    """calcEarningsQualityFlags 결과 → FlagBlock."""
    if isinstance(data, dict):
        return _enrichedFlagsBlock(data.get("flags", []), data.get("enrichedFlags"))
    # 하위호환: list[str] 직접 전달
    return _flagsBlock(data if isinstance(data, list) else [])


# ── 3-2 비용구조 ──


def costBreakdownBlock(data: dict) -> list:
    """calcCostBreakdown 결과 → 비용 비중 시계열."""
    cols = _historyTable(
        data,
        [
            ("costOfSalesRatio", "매출원가율(%)", "{:.1f}%"),
            ("sgaRatio", "판관비율(%)", "{:.1f}%"),
            ("operatingCostRatio", "영업비용률(%)", "{:.1f}%"),
        ],
    )
    if cols is None:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("costBreakdown").label,
            level=2,
            helper="원가율+판관비율 = 영업비용률, 100에서 빼면 영업이익률",
        ),
        TableBlock("비용 비중 추이", pl.DataFrame(cols)),
    ]
    blocks.extend(_notesDetailBlocks(data, {"costByNature": "비용 성격별 분류"}))
    return blocks


def operatingLeverageBlock(data: dict) -> list:
    """calcOperatingLeverage 결과 → DOL 시계열."""
    cols = _historyTable(
        data,
        [
            ("dol", "DOL", "{:.1f}"),
            ("contributionProxy", "매출총이익/영업이익", "{:.1f}"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("operatingLeverage").label,
            level=2,
            helper="DOL > 3 = 매출 변동에 이익이 크게 반응",
        ),
        TableBlock("영업레버리지 추이", pl.DataFrame(cols)),
    ]


def breakevenEstimateBlock(data: dict) -> list:
    """calcBreakevenEstimate 결과 → BEP 시계열."""
    cols = _historyTable(
        data,
        [
            ("revenue", "실제 매출", "amt"),
            ("bepRevenue", "BEP 매출", "amt"),
            ("marginOfSafety", "안전마진(%)", "{:.1f}%"),
            ("variableCostRatio", "변동비율", "{:.2f}"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("breakevenEstimate").label,
            level=2,
            helper="안전마진 10% 미만 = 손익분기점 근접",
        ),
        TableBlock("손익분기점 추이", pl.DataFrame(cols)),
    ]


def costStructureFlagsBlock(flags: list[str]) -> list:
    """calcCostStructureFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


# ── 3-3 자본배분 ──


def dividendPolicyBlock(data: dict) -> list:
    """calcDividendPolicy 결과 → 배당 정책 시계열."""
    if not data:
        return []

    cols = _historyTable(
        data,
        [
            ("dividendsPaid", "배당금", "amt"),
            ("payoutRatio", "배당성향(%)", "{:.1f}%"),
            ("dividendGrowth", "배당성장률(%)", "{:+.1f}%"),
        ],
    )
    if cols is None:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("dividendPolicy").label,
            level=2,
            helper="배당성향 100%+ = 이익 초과 배당",
        ),
        TableBlock("배당 추이", pl.DataFrame(cols)),
    ]

    consecutive = data.get("consecutiveYears", 0)
    if consecutive > 0:
        blocks.append(MetricBlock([("연속 배당", f"{consecutive}년")]))

    return blocks


def shareholderReturnBlock(data: dict) -> list:
    """calcShareholderReturn 결과 → 주주환원 시계열."""
    cols = _historyTable(
        data,
        [
            ("dividendsPaid", "배당금", "amt"),
            ("treasuryStockPurchase", "자사주 매입", "amt"),
            ("totalReturn", "총환원", "amt"),
            ("fcf", "FCF", "amt"),
            ("returnToFcf", "환원/FCF(%)", "{:.0f}%"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("shareholderReturn").label,
            level=2,
            helper="환원/FCF 100%+ = FCF 초과 환원, 지속 불가",
        ),
        TableBlock("주주환원 추이", pl.DataFrame(cols)),
    ]


def reinvestmentBlock(data: dict) -> list:
    """calcReinvestment 결과 → 재투자 시계열."""
    cols = _historyTable(
        data,
        [
            ("capex", "CAPEX", "amt"),
            ("capexToRevenue", "CAPEX/매출(%)", "{:.1f}%"),
            ("retentionRate", "유보율(%)", "{:.1f}%"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("reinvestment").label,
            level=2,
            helper="유보율 = 1 - 배당성향, 재투자 여력",
        ),
        TableBlock("재투자 추이", pl.DataFrame(cols)),
    ]


def fcfUsageBlock(data: dict) -> list:
    """calcFcfUsage 결과 → FCF 사용처 시계열."""
    cols = _historyTable(
        data,
        [
            ("fcf", "FCF", "amt"),
            ("dividendsPaid", "배당", "amt"),
            ("debtRepaid", "부채상환", "amt"),
            ("residual", "잔여", "amt"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("fcfUsage").label,
            level=2,
            helper="잔여 = FCF - 배당 - 부채상환 (현금 축적 또는 투자)",
        ),
        TableBlock("FCF 사용처 추이", pl.DataFrame(cols)),
    ]


def treasuryStockStatusBlock(data: dict | None) -> list:
    """calcTreasuryStockStatus 결과 → 자사주 현황 테이블."""
    if not data:
        return []
    rows = data.get("rows", [])
    if not rows:
        return []

    table_rows = []
    for r in rows:
        row: dict = {"구분": r.get("method", "")}
        if r.get("acquired") is not None:
            row["취득"] = f"{r['acquired']:,.0f}"
        if r.get("disposed") is not None:
            row["처분"] = f"{r['disposed']:,.0f}"
        if r.get("retired") is not None:
            row["소각"] = f"{r['retired']:,.0f}"
        if r.get("endShares") is not None:
            row["잔량"] = f"{r['endShares']:,.0f}"
        table_rows.append(row)

    if not table_rows:
        return []

    source = data.get("source", "")
    helper = "자사주 취득/처분/소각 현황"
    if source == "XBRL":
        helper += " (EDGAR XBRL 기반)"

    return [
        HeadingBlock(_meta("treasuryStockStatus").label, level=2, helper=helper),
        TableBlock("자사주 현황", pl.DataFrame(table_rows)),
    ]


def capitalAllocationFlagsBlock(flags: list[str]) -> list:
    """calcCapitalAllocationFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


def dividendSustainabilityBlock(divData: dict | None, shData: dict | None) -> list:
    """배당 지속성 — 성향 5Y 평균 + FCF 커버리지 + 변동성.

    두 calc 결과(calcDividendPolicy, calcShareholderReturn)를 조합해 파생 지표를 만든다.
    엔진은 history만 반환, review가 조합/요약.
    """
    if not divData and not shData:
        return []

    divHist = (divData or {}).get("history", []) or []
    shHist = (shData or {}).get("history", []) or []

    if not divHist and not shHist:
        return []

    payouts = [h.get("payoutRatio") for h in divHist if h.get("payoutRatio") is not None]
    returnToFcfs = [h.get("returnToFcf") for h in shHist if h.get("returnToFcf") is not None]

    avgPayout = sum(payouts) / len(payouts) if payouts else None
    avgFcfCover = sum(returnToFcfs) / len(returnToFcfs) if returnToFcfs else None

    payoutVol = None
    if len(payouts) >= 2:
        mean = sum(payouts) / len(payouts)
        var = sum((p - mean) ** 2 for p in payouts) / len(payouts)
        payoutVol = var**0.5

    metrics: list[tuple[str, str]] = []
    if avgPayout is not None:
        metrics.append(("5Y 평균 배당성향", f"{avgPayout:.1f}%"))
    if avgFcfCover is not None:
        verdict = "지속 가능" if avgFcfCover <= 80 else "여유 부족" if avgFcfCover <= 100 else "FCF 초과"
        metrics.append(("5Y 평균 환원/FCF", f"{avgFcfCover:.0f}% ({verdict})"))
    if payoutVol is not None:
        metrics.append(("성향 변동성(σ)", f"{payoutVol:.1f}%p"))

    consecutive = (divData or {}).get("consecutiveYears")
    if consecutive and consecutive > 0:
        metrics.append(("연속 배당", f"{consecutive}년"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("dividendSustainability").label,
            level=2,
            helper="환원/FCF 80% 이하 = 여유, 100% 초과 = FCF 초과 환원",
        ),
        MetricBlock(metrics),
    ]


def totalShareholderReturnBlock(shData: dict | None) -> list:
    """총 주주환원율 — 배당+자사주 합산 5Y 추이 + 평균."""
    if not shData:
        return []
    hist = shData.get("history", []) or []
    if not hist:
        return []

    cols = _historyTable(
        shData,
        [
            ("dividendsPaid", "배당", "amt"),
            ("treasuryStockPurchase", "자사주", "amt"),
            ("totalReturn", "총환원", "amt"),
            ("returnToFcf", "환원/FCF(%)", "{:.0f}%"),
        ],
    )
    if cols is None:
        return []

    # 5Y 총환원율 평균 (배당+자사주)
    rates = [h.get("returnToFcf") for h in hist if h.get("returnToFcf") is not None]
    avg = sum(rates) / len(rates) if rates else None

    blocks: list = [
        HeadingBlock(
            _meta("totalShareholderReturn").label,
            level=2,
            helper="FCF 대비 총환원율 — 배당만이 아닌 자사주까지 포함한 실질 환원",
        ),
        TableBlock("총 주주환원 추이", pl.DataFrame(cols)),
    ]
    if avg is not None:
        blocks.append(MetricBlock([("5Y 평균 총환원/FCF", f"{avg:.0f}%")]))
    return blocks


# ── 3-4 투자효율 ──


def roicTimelineBlock(data: dict) -> list:
    """calcRoicTimeline 결과 → ROIC/WACC/Spread 시계열."""
    cols = _historyTable(
        data,
        [
            ("roic", "ROIC(%)", "{:.1f}%"),
            ("waccEstimate", "WACC 추정(%)", "{:.1f}%"),
            ("spread", "Spread(%p)", "{:+.1f}%p"),
        ],
    )
    if cols is None:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("roicTimeline").label,
            level=2,
            helper="Spread > 0 = 가치 창출, < 0 = 가치 파괴",
        ),
    ]
    narration = narrateROIC(data)
    if narration:
        blocks.append(TextBlock(narration))
    blocks.append(TableBlock("ROIC vs WACC 추이", pl.DataFrame(cols)))
    return blocks


def investmentIntensityBlock(data: dict) -> list:
    """calcInvestmentIntensity 결과 → 투자 강도 시계열."""
    cols = _historyTable(
        data,
        [
            ("capexToRevenue", "CAPEX/매출(%)", "{:.1f}%"),
            ("tangibleRatio", "유형자산/총자산(%)", "{:.1f}%"),
            ("intangibleRatio", "무형자산/총자산(%)", "{:.1f}%"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("investmentIntensity").label,
            level=2,
            helper="무형자산비율 급등 = 대규모 인수 또는 영업권 증가",
        ),
        TableBlock("투자 강도 추이", pl.DataFrame(cols)),
    ]


def evaTimelineBlock(data: dict) -> list:
    """calcEvaTimeline 결과 → EVA 시계열."""
    cols = _historyTable(
        data,
        [
            ("nopat", "NOPAT", "amt"),
            ("investedCapital", "투하자본", "amt"),
            ("waccEstimate", "WACC(%)", "{:.1f}%"),
            ("eva", "EVA", "amt"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("evaTimeline").label,
            level=2,
            helper="EVA > 0 = 자본비용 이상 수익 창출",
        ),
        TableBlock("EVA 추이", pl.DataFrame(cols)),
    ]


def investmentFlagsBlock(flags: list[str]) -> list:
    """calcInvestmentFlags 결과 → FlagBlock."""
    return _flagsBlock(flags)


# ── 3-5 재무정합성 ──


def isCfDivergenceBlock(data: dict) -> list:
    """calcIsCfDivergence 결과 → IS-CF 괴리 시계열."""
    cols = _historyTable(
        data,
        [
            ("netIncome", "순이익", "amt"),
            ("ocf", "영업CF", "amt"),
            ("divergence", "괴리율(%)", "{:+.0f}%"),
            ("direction", "방향", "{}"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("isCfDivergence").label,
            level=2,
            helper="괴리 > 50% = 순이익 대비 현금흐름 극심한 차이",
        ),
        TableBlock("IS-CF 괴리 추이", pl.DataFrame(cols)),
    ]


def isBsDivergenceBlock(data: dict) -> list:
    """calcIsBsDivergence 결과 → IS-BS 괴리 시계열."""
    cols = _historyTable(
        data,
        [
            ("revenueGrowth", "매출성장(%)", "{:+.1f}%"),
            ("receivableGrowth", "매출채권성장(%)", "{:+.1f}%"),
            ("inventoryGrowth", "재고성장(%)", "{:+.1f}%"),
            ("revRecGap", "채권-매출 갭(%p)", "{:+.1f}%p"),
            ("revInvGap", "재고-매출 갭(%p)", "{:+.1f}%p"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("isBsDivergence").label,
            level=2,
            helper="채권/재고 성장이 매출보다 20%p+ 빠르면 의심",
        ),
        TableBlock("IS-BS 괴리 추이", pl.DataFrame(cols)),
    ]


def anomalyScoreBlock(data: dict) -> list:
    """calcAnomalyScore 결과 → 이상 점수 시계열."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("anomalyScore").label,
            level=2,
            helper="70점 이상 = 재무제표 신뢰성 주의",
        ),
    ]

    # 점수 시계열
    cols: dict[str, list[str]] = {"": ["종합 점수"]}
    for h in history:
        cols[h["period"]] = [f"{h['score']:.0f}"]
    blocks.append(TableBlock("이상 점수 추이", pl.DataFrame(cols)))

    # 최신 구성요소
    h0 = history[0]
    components = h0.get("components", {})
    if components:
        metrics = [(k, f"{v:.1f}") for k, v in components.items()]
        blocks.append(MetricBlock(metrics))

    return blocks


def effectiveTaxRateBlock(data: dict) -> list:
    """calcEffectiveTaxRate 결과 → 유효세율 시계열."""
    cols = _historyTable(
        data,
        [
            ("effectiveTaxRate", "유효세율(%)", "{:.1f}%"),
            ("statutoryRate", "법정세율(%)", "{:.0f}%"),
            ("taxGap", "세율갭(%p)", "{:+.1f}%p"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("effectiveTaxRate").label,
            level=2,
            helper="유효세율 < 10% 극저, > 35% 고세율",
        ),
        TableBlock("유효세율 추이", pl.DataFrame(cols)),
    ]


def deferredTaxBlock(data: dict) -> list:
    """calcDeferredTax 결과 → 이연법인세 시계열."""
    cols = _historyTable(
        data,
        [
            ("deferredTaxAsset", "이연법인세자산", "amt"),
            ("deferredTaxLiability", "이연법인세부채", "amt"),
            ("netDeferredTax", "순이연법인세", "amt"),
            ("dtaToTotalAssets", "DTA/총자산(%)", "{:.2f}%"),
        ],
    )
    if cols is None:
        return []
    return [
        HeadingBlock(
            _meta("deferredTax").label,
            level=2,
            helper="이연법인세자산 급증 = 미래 과세소득 가정 검토",
        ),
        TableBlock("이연법인세 추이", pl.DataFrame(cols)),
    ]


def crossStatementFlagsBlock(flags: list[str]) -> list:
    """교차검증+세금 플래그 통합 -> FlagBlock."""
    return _flagsBlock(flags)


# ── 4부: 가치평가 빌더 ──


def dcfValuationBlock(data: dict) -> list:
    """calcDcf 결과 -> HeadingBlock + MetricBlock + TableBlock."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("dcfValuation").label,
            level=2,
            helper="FCF 기반 기업가치 추정 -- 할인율과 성장률 가정 확인 필수",
        ),
    ]
    metrics = []
    if data.get("perShareValue") is not None:
        metrics.append(("적정가", f"{data['perShareValue']:,.0f}"))
    if data.get("currentPrice") is not None:
        metrics.append(("현재가", f"{data['currentPrice']:,.0f}"))
    if data.get("marginOfSafety") is not None:
        metrics.append(("안전마진", f"{data['marginOfSafety']:.1f}%"))
    metrics.append(("할인율", f"{data.get('discountRate', 0):.1f}%"))
    metrics.append(("영구성장률", f"{data.get('terminalGrowth', 0):.1f}%"))
    if metrics:
        blocks.append(MetricBlock(metrics))

    # FCF 추정 테이블
    projections = data.get("fcfProjections", [])
    if projections:
        rows = [{"연차": f"Y{i + 1}", "FCF(조원)": round(v / 1e12, 1)} for i, v in enumerate(projections)]
        blocks.append(TableBlock("FCF 추정", pl.DataFrame(rows)))

    for w in data.get("warnings", []):
        blocks.append(TextBlock(f"-- {w}", style="dim"))
    return blocks


def ddmValuationBlock(data: dict) -> list:
    """calcDdm 결과 -> MetricBlock."""
    if not data:
        return []
    if data.get("modelUsed") == "N/A":
        return [
            HeadingBlock(_meta("ddmValuation").label, level=2),
            TextBlock("DDM 적용 불가 (무배당 또는 데이터 부족)", style="dim"),
        ]

    blocks: list = [
        HeadingBlock(
            _meta("ddmValuation").label,
            level=2,
            helper="배당 기반 가치 -- 배당 지속성이 핵심 가정",
        ),
    ]
    metrics: list[tuple[str, str]] = []
    if data.get("intrinsicValue") is not None:
        metrics.append(("적정가", f"{data['intrinsicValue']:,.0f}"))
    if data.get("dividendPerShare") is not None:
        metrics.append(("주당배당금", f"{data['dividendPerShare']:,.0f}"))
    if data.get("dividendGrowth") is not None:
        metrics.append(("배당성장률", f"{data['dividendGrowth']:.1f}%"))
    if data.get("payoutRatio") is not None:
        metrics.append(("배당성향", f"{data['payoutRatio']:.1f}%"))
    if metrics:
        blocks.append(MetricBlock(metrics))
    return blocks


def relativeValuationBlock(data: dict) -> list:
    """calcRelativeValuation 결과 -> TableBlock."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("relativeValuation").label,
            level=2,
            helper="섹터 배수 대비 현재 배수 비교 -- 업종 평균과 괴리 확인",
        ),
    ]

    implied = data.get("impliedValues", {})
    sectorMults = data.get("sectorMultiples", {})
    currentMults = data.get("currentMultiples", {})
    premium = data.get("premiumDiscount", {})

    rows = []
    for key in ["PER", "PBR", "EV/EBITDA", "PSR", "PEG"]:
        iv = implied.get(key)
        if iv is None:
            continue
        row = {
            "지표": key,
            "섹터배수": f"{sectorMults.get(key, 0):.1f}" if sectorMults.get(key) else "-",
            "현재배수": f"{currentMults.get(key, 0):.1f}" if currentMults.get(key) else "-",
            "적정가": f"{iv:,.0f}",
        }
        pd = premium.get(key)
        row["할증/할인"] = f"{pd:+.1f}%" if pd is not None else "-"
        rows.append(row)

    if rows:
        blocks.append(TableBlock("", pl.DataFrame(rows)))

    consensus = data.get("consensusValue")
    if consensus:
        blocks.append(MetricBlock([("종합 적정가", f"{consensus:,.0f}")]))
    return blocks


def residualIncomeBlock(data: dict) -> list:
    """calcResidualIncome 결과 -> MetricBlock."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("residualIncome").label,
            level=2,
            helper="BPS + 초과이익 현가 -- 자기자본비용 대비 초과수익 평가",
        ),
    ]
    metrics: list[tuple[str, str]] = []
    if data.get("bps"):
        metrics.append(("BPS", f"{data['bps']:,.0f}원"))
    metrics.append(("자기자본비용", f"{data.get('coe', 0):.1f}%"))
    if data.get("intrinsicValue") is not None:
        metrics.append(("적정가", f"{data['intrinsicValue']:,.0f}원"))
    if data.get("upside") is not None:
        metrics.append(("업사이드", f"{data['upside']:+.1f}%"))
    if metrics:
        blocks.append(MetricBlock(metrics))
    return blocks


def priceTargetBlock(data: dict) -> list:
    """calcPriceTarget 결과 -> MetricBlock + TableBlock(시나리오)."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("priceTarget").label,
            level=2,
            helper="5개 거시 시나리오 x DCF + Monte Carlo 분포",
        ),
    ]
    metrics: list[tuple[str, str]] = [("가중 목표가", f"{data.get('weightedTarget', 0):,.0f}원")]
    if data.get("currentPrice"):
        metrics.append(("현재가", f"{data['currentPrice']:,.0f}원"))
    if data.get("upside") is not None:
        metrics.append(("업사이드", f"{data['upside']:+.1f}%"))
    metrics.append(("투자 신호", data.get("signal", "-")))
    metrics.append(("신뢰도", data.get("confidence", "-")))
    blocks.append(MetricBlock(metrics))

    # 시나리오 테이블
    scenarios = data.get("scenarios", [])
    if scenarios:
        rows = []
        for s in scenarios:
            rows.append(
                {
                    "시나리오": s["name"],
                    "확률": f"{s['probability'] * 100:.0f}%",
                    "목표가(원)": f"{s['perShareValue']:,.0f}",
                }
            )
        blocks.append(TableBlock("시나리오별 목표가", pl.DataFrame(rows)))

    # Monte Carlo 백분위
    pctls = data.get("percentiles", {})
    if pctls:
        rows = [{"백분위": k, "주가(원)": f"{v:,.0f}"} for k, v in sorted(pctls.items())]
        blocks.append(TableBlock("Monte Carlo 분포", pl.DataFrame(rows)))
    return blocks


def reverseImpliedBlock(data: dict) -> list:
    """calcReverseImplied 결과 -> MetricBlock."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("reverseImplied").label,
            level=2,
            helper="현재 시가총액이 내재하는 매출 성장률 -- 시장 기대와 엔진 예측 비교",
        ),
    ]
    metrics: list[tuple[str, str]] = [
        ("내재성장률", f"{data.get('impliedGrowthRate', 0):.1f}%"),
        ("최근 매출", f"{data.get('latestRevenue', 0) / 1e8:,.0f}억"),
        ("가정 WACC", f"{data.get('assumedWacc', 0):.1f}%"),
    ]
    signal = data.get("signal")
    if signal:
        metrics.append(("신호", signal))
    blocks.append(MetricBlock(metrics))
    return blocks


def sensitivityBlock(data: dict) -> list:
    """calcSensitivity 결과 -> TableBlock(그리드)."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("sensitivity").label,
            level=2,
            helper="WACC x 영구성장률 조합별 적정가 변화",
        ),
    ]

    grid = data.get("grid", [])
    if not grid:
        return blocks

    # 피벗: 행=WACC, 열=성장률
    waccVals = sorted({g["wacc"] for g in grid})
    growthVals = sorted({g["terminalGrowth"] for g in grid})

    lookup = {(g["wacc"], g["terminalGrowth"]): g.get("perShareValue") for g in grid}

    rows = []
    for wacc in waccVals:
        row: dict = {"WACC": f"{wacc:.1f}%"}
        for tg in growthVals:
            val = lookup.get((wacc, tg))
            colName = f"g={tg:.1f}%"
            row[colName] = f"{val:,.0f}원" if val is not None else "-"
        rows.append(row)

    if rows:
        blocks.append(TableBlock("WACC x 성장률 민감도 (주당 적정가)", pl.DataFrame(rows)))

    baseVal = data.get("baseValue")
    if baseVal is not None:
        blocks.append(MetricBlock([("기준 적정가", f"{baseVal:,.0f}원")]))

    # heatmap ChartBlock
    if grid:
        from dartlab.review.blocks import ChartBlock
        from dartlab.viz.generators import spec_sensitivity_heatmap

        hm_grid = [{"wacc": g["wacc"], "g": g.get("terminalGrowth", 0), "fairValue": g.get("perShareValue")} for g in grid]
        hm = spec_sensitivity_heatmap(hm_grid)
        if hm:
            blocks.append(ChartBlock(spec=hm))

        # 자동 문장: 편차 범위
        vals = [g.get("perShareValue") for g in grid if g.get("perShareValue") is not None]
        if vals and baseVal:
            min_v, max_v = min(vals), max(vals)
            pct_range = (max_v - min_v) / baseVal * 100 if baseVal > 0 else 0
            label = "높음" if pct_range > 80 else "보통" if pct_range > 40 else "낮음"
            blocks.append(TextBlock(f"가정 민감도: 적정가 편차 {pct_range:.0f}% ({label}) — 가정 변화에 가치가 크게 흔들리{'면 주의' if label == '높음' else '지 않음'}"))
    return blocks


def valuationSynthesisBlock(data: dict, priceTargetData: dict | None = None) -> list:
    """calcValuationSynthesis 결과 -> MetricBlock + TextBlock.

    priceTargetData 인자를 받아 두 모델 (synthesis 보수적 vs priceTarget 시나리오
    가중) 차이를 narration 으로 자동 추가하여 사용자 혼란을 해소한다.
    """
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("valuationSynthesis").label,
            level=2,
            helper="DCF + DDM + 상대가치 종합 -- 모델 간 범위와 판정",
        ),
    ]

    narration = narrateValuation(data)
    if narration:
        blocks.append(TextBlock(narration))

    fvr = data.get("fairValueRange")
    metrics: list[tuple[str, str]] = []
    if fvr:
        metrics.append(("적정가 범위", f"{fvr[0]:,.0f}원 ~ {fvr[1]:,.0f}원"))
    if data.get("currentPrice"):
        metrics.append(("현재가", f"{data['currentPrice']:,.0f}원"))
    metrics.append(("판정", data.get("verdict", "-")))
    blocks.append(MetricBlock(metrics))

    # 모델별 추정치
    estimates = data.get("estimates", [])
    if estimates:
        rows = [{"모델": e["method"], "적정가(원)": f"{e['value']:,.0f}"} for e in estimates]
        blocks.append(TableBlock("모델별 적정가", pl.DataFrame(rows)))

    # 두 모델 통합 narration
    if priceTargetData:
        synthFair = data.get("weightedFairValue")
        ptFair = priceTargetData.get("weightedTarget")
        data.get("currentPrice") or priceTargetData.get("currentPrice")
        if synthFair and ptFair and synthFair > 0 and ptFair > 0:
            divergence = abs(ptFair - synthFair) / synthFair * 100
            ratio = ptFair / synthFair
            if divergence > 30:
                if ptFair > synthFair:
                    direction = (
                        f"시장 기대가 모델 평균보다 **{ratio:.1f}배 낙관적**. "
                        f"확률가중 목표가 ({ptFair:,.0f}원) 가 모델 종합 적정가 ({synthFair:,.0f}원) 를 크게 상회"
                    )
                else:
                    direction = (
                        f"시장 기대가 모델 평균보다 **{1 / ratio:.1f}배 보수적**. "
                        f"확률가중 목표가 ({ptFair:,.0f}원) 가 모델 종합 적정가 ({synthFair:,.0f}원) 보다 낮음"
                    )
                blocks.append(
                    TextBlock(
                        f"두 모델 차이 {divergence:.0f}%: {direction}. "
                        f"종합 적정가는 DCF/DDM/RIM/상대가치 모델 평균(보수적), "
                        f"확률가중 목표가는 5개 거시 시나리오 시뮬레이션(시장 기대 기반)."
                    )
                )
            else:
                blocks.append(
                    TextBlock(
                        f"두 모델 수렴 (차이 {divergence:.0f}%): "
                        f"종합 적정가 {synthFair:,.0f}원 vs 확률가중 목표가 {ptFair:,.0f}원. "
                        f"보수적 모델 평균과 시장 기대 시나리오가 일치 — 신뢰도 높음."
                    )
                )

    return blocks


def valuationFlagsBlock(flags: list[dict]) -> list:
    """calcValuationFlags 결과 -> FlagBlock."""
    if not flags:
        return []
    flagTexts = []
    for f in flags:
        prefix = {"warning": "[!]", "opportunity": "[+]", "info": "[i]"}.get(f.get("signal", ""), "")
        flagTexts.append(f"{prefix} {f.get('label', '')}")
    return _flagsBlock(flagTexts)


# ── 5-1 지배구조 ──


def ownershipTrendBlock(data: dict) -> list:
    """calcOwnershipTrend 결과 -> 지분 추이 테이블 + 주주 구성."""
    if not data:
        return []
    blocks: list = []

    history = data.get("history", [])
    if history:
        rows = []
        for h in history:
            row: dict = {"연도": h["year"]}
            row["지분율(%)"] = h["ratio"]
            row["변동(%p)"] = h.get("change")
            rows.append(row)
        blocks.append(
            HeadingBlock(
                _meta("ownershipTrend").label,
                level=2,
                helper="연도별 최대주주 지분율 추이",
            )
        )
        blocks.append(TableBlock("", pl.DataFrame(rows)))

    holders = data.get("latestHolders", [])
    if holders:
        hRows = []
        for h in holders[:5]:
            hRows.append(
                {
                    "성명": h.get("name", ""),
                    "관계": h.get("relate", ""),
                    "지분율(%)": h.get("ratio"),
                }
            )
        blocks.append(TableBlock("최근 주요 주주", pl.DataFrame(hRows)))

    return blocks


def boardCompositionBlock(data: dict) -> list:
    """calcBoardComposition 결과 -> 이사회 구성 메트릭."""
    if not data:
        return []
    metrics = [
        ("전체 임원", f"{data['totalCount']}명"),
        ("사내이사", f"{data['registeredCount']}명"),
        ("사외이사", f"{data['outsideCount']}명"),
    ]
    outsideRatio = data.get("outsideRatio")
    if outsideRatio is not None:
        metrics.append(("사외이사비율", f"{outsideRatio:.1f}%"))
    return [
        HeadingBlock(
            _meta("boardComposition").label,
            level=2,
            helper="사외이사비율로 이사회 독립성을 판단한다",
        ),
        MetricBlock(metrics),
    ]


def auditOpinionTrendBlock(data: dict) -> list:
    """calcAuditOpinionTrend 결과 -> 감사의견 시계열."""
    if not data:
        return []
    history = data.get("history", [])
    if not history:
        return []
    rows = []
    for h in history:
        row: dict = {"연도": h["year"], "감사의견": h.get("opinion", "")}
        auditor = h.get("auditor", "")
        if auditor:
            row["감사인"] = auditor
        if h.get("auditorChanged"):
            row["변경"] = "Y"
        rows.append(row)
    return [
        HeadingBlock(
            _meta("auditOpinionTrend").label,
            level=2,
            helper="감사의견과 감사인 변경을 추적한다",
        ),
        TableBlock("", pl.DataFrame(rows)),
    ]


def governanceFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcGovernanceFlags 결과 -> FlagBlock."""
    return _tupleFlags(flags)


def executivePayDivergenceBlock(data: dict | None) -> list:
    """임원보수 5Y CAGR vs 매출/순이익 CAGR 괴리 시각화."""
    if not data:
        return []

    cagr = data.get("cagr", {}) or {}
    divergence = data.get("divergence")

    metrics: list[tuple[str, str]] = []
    if cagr.get("execPay") is not None:
        metrics.append(("임원보수 5Y CAGR", f"{cagr['execPay']:+.1f}%"))
    if cagr.get("revenue") is not None:
        metrics.append(("매출 5Y CAGR", f"{cagr['revenue']:+.1f}%"))
    if cagr.get("netIncome") is not None:
        metrics.append(("순이익 5Y CAGR", f"{cagr['netIncome']:+.1f}%"))
    if divergence is not None:
        verdict = "주의 (보수↑ > 매출↑)" if divergence > 5 else "정렬" if abs(divergence) <= 5 else "억제"
        metrics.append(("괴리 (보수 - 매출)", f"{divergence:+.1f}%p ({verdict})"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("executivePayDivergence").label,
            level=2,
            helper="보수 증가율이 매출/순이익 증가율을 크게 상회하면 대리인 비용 신호",
        ),
        MetricBlock(metrics),
    ]


def independentDirectorQualityBlock(data: dict | None) -> list:
    """외부이사 독립성 — 구성 + 독립성 플래그."""
    if not data:
        return []

    latest = data.get("latest", {}) or {}
    flags = data.get("flags", []) or []

    metrics: list[tuple[str, str]] = []
    if latest.get("total"):
        metrics.append(("전체 임원", f"{latest['total']}명"))
    if latest.get("outside") is not None:
        metrics.append(("외부이사", f"{latest['outside']}명"))
    if latest.get("ratio") is not None:
        metrics.append(("외부이사 비율", f"{latest['ratio']:.0f}%"))

    if not metrics and not flags:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("independentDirectorQuality").label,
            level=2,
            helper="외부이사 비율 33% 이상 = 독립성 기준. 25% 미만 = 취약.",
        ),
    ]
    if metrics:
        blocks.append(MetricBlock(metrics))
    if flags:
        blocks.append(FlagBlock("warning", "\n".join(flags)))
    return blocks


# ── 5-2 공시변화 ──


def disclosureChangeSummaryBlock(data: dict) -> list:
    """calcDisclosureChangeSummary 결과 -> 요약 메트릭 + 상위 변화 테이블."""
    if not data:
        return []
    blocks: list = []

    metrics = [
        ("변화 건수", f"{data['totalChanges']}건"),
        ("변화 topic", f"{data['changedTopics']}/{data['totalTopics']}"),
        ("무변화 topic", f"{data['unchangedTopics']}"),
    ]
    blocks.append(
        HeadingBlock(
            _meta("disclosureChangeSummary").label,
            level=2,
            helper="전체 topic 변화 현황",
        )
    )
    blocks.append(MetricBlock(metrics))

    topChanged = data.get("topChanged", [])
    if topChanged:
        rows = [
            {"topic": t["topic"], "변화횟수": t["changedCount"], "변화율": f"{t['changeRate']:.0%}"}
            for t in topChanged[:5]
        ]
        blocks.append(TableBlock("변화율 상위 topic", pl.DataFrame(rows)))

    return blocks


def keyTopicChangesBlock(data: dict) -> list:
    """calcKeyTopicChanges 결과 -> 핵심 topic 변화 테이블."""
    if not data:
        return []
    keyTopics = data.get("keyTopics", [])
    if not keyTopics:
        return []
    rows = [
        {
            "topic": kt["topic"],
            "기간수": kt["totalPeriods"],
            "변화": kt["changedCount"],
            "변화율": f"{kt['changeRate']:.0%}",
        }
        for kt in keyTopics
    ]
    return [
        HeadingBlock(
            _meta("keyTopicChanges").label,
            level=2,
            helper="핵심 공시 topic의 변화 이력",
        ),
        TableBlock("", pl.DataFrame(rows)),
    ]


def changeIntensityBlock(data: dict) -> list:
    """calcChangeIntensity 결과 -> 변화 크기 테이블."""
    if not data:
        return []
    topByDelta = data.get("topByDelta", [])
    if not topByDelta:
        return []
    rows = [{"topic": t["topic"], "변화량(bytes)": t["totalDeltaBytes"]} for t in topByDelta[:5]]
    return [
        HeadingBlock(
            _meta("changeIntensity").label,
            level=2,
            helper="바이트 기준 변화량 상위 topic",
        ),
        TableBlock("", pl.DataFrame(rows)),
    ]


def disclosureDeltaFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcDisclosureDeltaFlags 결과 -> FlagBlock."""
    return _tupleFlags(flags)


# ── 5-3 비교분석 ──


def peerPositionBlock(data: dict | None) -> list:
    """calcPeerPosition 결과 → 시장 내 위치 + 교차 관점 + 레이더 차트."""
    if not data:
        return []

    from dartlab.review.blocks import ChartBlock
    from dartlab.viz.generators import spec_peer_radar

    blocks: list = [HeadingBlock(_meta("peerPosition").label, level=2, helper="전종목 횡단 비교 — 4축 백분위 + 교차 관점")]

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
        radar = spec_peer_radar(data)
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


def riskReturnPositionBlock(data: dict) -> list:
    """calcRiskReturnPosition 결과 -> 사분면 메트릭."""
    if not data:
        return []
    metrics = [
        ("ROE", f"{data['roe']:.1f}% (상위 {100 - data['roePercentile']:.0f}%)"),
        ("부채비율", f"{data['debtRatio']:.1f}% (상위 {100 - data['debtRatioPercentile']:.0f}%)"),
        ("포지션", data["quadrant"]),
        ("평가", data["assessment"]),
    ]
    return [
        HeadingBlock(
            _meta("riskReturnPosition").label,
            level=2,
            helper="ROE(수익) x 부채비율(위험) 사분면 위치",
        ),
        MetricBlock(metrics),
    ]


def peerBenchmarkFlagsBlock(flags: list[tuple[str, str]]) -> list:
    """calcPeerBenchmarkFlags 결과 -> FlagBlock."""
    return _tupleFlags(flags)


def _tupleFlags(flags: list[tuple[str, str]]) -> list:
    """(message, kind) 튜플 리스트 -> FlagBlock(s)."""
    if not flags:
        return []
    warnings = [f for f, k in flags if k == "warning"]
    opportunities = [f for f, k in flags if k == "opportunity"]
    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks


# ── 6-1 매출전망 빌더 ──


def _fmtEstimate(value: float | None, currency: str = "KRW") -> str:
    """추정치 포맷팅 (억원/M 단위)."""
    if value is None:
        return "-"
    if currency == "KRW":
        return f"{value / 1e8:,.0f}억(E)"
    return f"${value / 1e6:,.0f}M(E)"


def revenueForecastBlock(data: dict) -> list:
    """calcRevenueForecast -> 시나리오 테이블 + 신뢰도."""
    if not data:
        return []

    # 예측 불가 판정 시 경고만 표시
    if not data.get("forecastable", True):
        reason = data.get("unforecastableReason", "")
        return [
            HeadingBlock(
                _meta("revenueForecast").label,
                level=2,
                helper="7-소스 앙상블 매출 예측 -- 모든 수치는 추정치",
            ),
            TextBlock(f"이 기업은 현재 정량 예측이 불가능합니다: {reason}"),
        ]

    cur = data.get("currency", "KRW")
    blocks: list = [
        HeadingBlock(
            _meta("revenueForecast").label,
            level=2,
            helper="7-소스 앙상블 매출 예측 -- 모든 수치는 추정치",
        ),
    ]

    # 신뢰도 + 방법론 요약
    metrics = [
        ("방법", data.get("method", "")),
        ("신뢰도", data.get("confidence", "")),
    ]
    lifecycle = data.get("lifecycle", "")
    if lifecycle:
        metrics.append(("라이프사이클", lifecycle))
    blocks.append(MetricBlock(metrics))

    # 시나리오 테이블
    scenarios = data.get("scenarios", {})
    if scenarios:
        rows = []
        for label in ("bull", "base", "bear"):
            sc = scenarios.get(label)
            if not sc:
                continue
            proj = sc.get("projected", [])
            gr = sc.get("growthRates", [])
            prob = sc.get("probability", 0)
            row = {"시나리오": f"{label.title()} ({prob:.0f}%)"}
            for i, (p, g) in enumerate(zip(proj, gr)):
                row[f"+{i + 1}년"] = f"{_fmtEstimate(p, cur)} ({g:+.1f}%)"
            rows.append(row)
        if rows:
            blocks.append(TableBlock("[추정] 시나리오별 매출 전망", pl.DataFrame(rows)))
    else:
        # 시나리오 없이 기본 전망만
        projected = data.get("projected", [])
        growthRates = data.get("growthRates", [])
        if projected:
            rows = []
            for i, (p, g) in enumerate(zip(projected, growthRates)):
                rows.append({"연차": f"+{i + 1}년", "매출": _fmtEstimate(p, cur), "성장률": f"{g:+.1f}%"})
            blocks.append(TableBlock("[추정] 매출 전망", pl.DataFrame(rows)))

    blocks.append(TextBlock(data.get("disclaimer", ""), style="dim"))

    # scenario band chart
    scenarios = data.get("scenarios", {})
    if scenarios:
        from dartlab.review.blocks import ChartBlock
        from dartlab.viz.generators import spec_revenue_scenario_band

        # historical: calc가 반환하는 과거 매출 시계열 (list[float])
        hist_vals = data.get("historical", []) or []
        history_dicts = [{"period": f"Y-{len(hist_vals) - i}", "revenue": v} for i, v in enumerate(hist_vals) if v is not None] if hist_vals else []
        forecasts = {}
        for key in ("base", "bull", "bear"):
            sc = scenarios.get(key, {})
            if sc and sc.get("projected"):
                forecasts[key] = sc["projected"]
                if not forecasts.get("periods"):
                    forecasts["periods"] = [f"+{i + 1}Y" for i in range(len(sc["projected"]))]

        if history_dicts or forecasts:
            band_spec = spec_revenue_scenario_band(history_dicts, forecasts if forecasts else None)
            if band_spec:
                blocks.append(ChartBlock(spec=band_spec))

    return blocks


def segmentForecastBlock(data: dict) -> list:
    """calcSegmentForecast -> 세그먼트별 성장 테이블."""
    if not data:
        return []
    segments = data.get("segments", [])
    if not segments:
        return []

    data.get("currency", "KRW")
    blocks: list = [
        HeadingBlock(
            _meta("segmentForecast").label,
            level=2,
            helper="부문별 개별 매출 성장 전망",
        ),
    ]

    rows = []
    for seg in segments:
        gr = seg.get("growthRates", [])
        row = {
            "부문": seg.get("name", ""),
            "매출비중": f"{seg.get('shareOfRevenue', 0):.1f}%",
            "방법": seg.get("method", ""),
        }
        for i, g in enumerate(gr):
            row[f"+{i + 1}년"] = f"{g:+.1f}%"
        rows.append(row)
    if rows:
        blocks.append(TableBlock("[추정] 세그먼트별 성장률", pl.DataFrame(rows)))

    return blocks


def proFormaHighlightsBlock(data: dict) -> list:
    """calcProFormaHighlights -> IS 요약 전망 테이블."""
    if not data:
        return []
    years = data.get("years", [])
    if not years:
        return []

    cur = data.get("currency", "KRW")
    blocks: list = [
        HeadingBlock(
            _meta("proFormaHighlights").label,
            level=2,
            helper="매출 성장 경로에 따른 IS/CF 핵심 전망",
        ),
    ]

    # WACC + 성장률
    metrics = [("WACC", f"{data.get('wacc', 0):.1f}%")]
    grPath = data.get("revenueGrowthPath", [])
    if grPath:
        metrics.append(("성장률 경로", " -> ".join(f"{g:+.1f}%" for g in grPath)))
    blocks.append(MetricBlock(metrics))

    # 전망 테이블
    rows = []
    for yr in years:
        rows.append(
            {
                "연차": f"+{yr['yearOffset']}년",
                "매출": _fmtEstimate(yr.get("revenue"), cur),
                "영업이익": _fmtEstimate(yr.get("operatingIncome"), cur),
                "순이익": _fmtEstimate(yr.get("netIncome"), cur),
                "FCF": _fmtEstimate(yr.get("fcf"), cur),
            }
        )
    blocks.append(TableBlock("[추정] Pro-Forma IS 요약", pl.DataFrame(rows)))

    for w in data.get("warnings", []):
        blocks.append(TextBlock(f"-- {w}", style="dim"))
    return blocks


def scenarioImpactBlock(data: dict) -> list:
    """calcScenarioImpact -> 매크로 시나리오 비교 그리드."""
    if not data:
        return []
    scenarios = data.get("scenarios", {})
    if not scenarios:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("scenarioImpact").label,
            level=2,
            helper="거시경제 시나리오별 매출/마진 영향 비교",
        ),
    ]

    rows = []
    for name, sc in scenarios.items():
        rows.append(
            {
                "시나리오": sc.get("label", name),
                "매출변화": f"{sc.get('revenueChangePct', 0):+.1f}%",
                "마진변화": f"{sc.get('marginChangeBps', 0):+.0f}bps",
            }
        )
    blocks.append(TableBlock("[추정] 매크로 시나리오 영향", pl.DataFrame(rows)))
    return blocks


def forecastMethodologyBlock(data: dict) -> list:
    """calcForecastMethodology -> 소스 가중치 + 가정."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("forecastMethodology").label,
            level=2,
            helper="예측 방법론 투명성 공개",
        ),
    ]

    # 소스 가중치
    weights = data.get("sourceWeights", {})
    if weights:
        metrics = [(src, f"{w:.0%}") for src, w in weights.items()]
        blocks.append(MetricBlock(metrics))

    # 가정
    assumptions = data.get("assumptions", [])
    if assumptions:
        for a in assumptions:
            blocks.append(TextBlock(f"- {a}", style="dim"))

    # 경고
    for w in data.get("warnings", []):
        blocks.append(TextBlock(f"-- {w}", style="dim"))

    return blocks


def historicalRatiosBlock(data: dict) -> list:
    """calcHistoricalRatios -> 과거 구조 비율."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("historicalRatios").label,
            level=2,
            helper="Pro-Forma의 기반이 되는 과거 재무 비율",
        ),
    ]

    metrics = [
        ("매출총이익률", f"{data.get('grossMargin', 0):.1f}%"),
        ("판관비율", f"{data.get('sgaRatio', 0):.1f}%"),
        ("유효세율", f"{data.get('effectiveTaxRate', 0):.1f}%"),
        ("CAPEX/매출", f"{data.get('capexToRevenue', 0):.1f}%"),
        ("NWC/매출", f"{data.get('nwcToRevenue', 0):.1f}%"),
        ("배당성향", f"{data.get('dividendPayout', 0):.1f}%"),
        ("사용 연수", f"{data.get('yearsUsed', 0)}년"),
        ("신뢰도", data.get("confidence", "")),
    ]
    blocks.append(MetricBlock(metrics))

    for w in data.get("warnings", []):
        blocks.append(TextBlock(f"-- {w}", style="dim"))
    return blocks


def forecastFlagsBlock(data: dict) -> list:
    """calcForecastFlags -> FlagBlock."""
    if not data:
        return []
    flags = data.get("flags", [])
    if not flags:
        return []
    messages = [msg for _, msg in flags]
    return [FlagBlock(messages, kind="warning")]


def calibrationReportBlock(data: dict) -> list:
    """calcCalibrationReport -> Brier Score + bin 테이블."""
    if not data:
        return []
    blocks: list = [
        HeadingBlock(
            _meta("calibrationReport").label,
            level=2,
            helper="과거 예측 확률의 실제 적중률 검증 (Brier Score)",
        ),
    ]
    metrics = [
        ("Brier Score", f"{data['brierScore']:.4f}"),
        ("평가 건수", str(data.get("nRecords", 0))),
    ]
    blocks.append(MetricBlock(metrics))

    bins = data.get("bins", [])
    if bins:
        import polars as pl

        rows = [
            {
                "구간": f"{b['binLower']:.0%}~{b['binUpper']:.0%}",
                "평균 예측": f"{b['meanPredicted']:.1%}",
                "실제 적중": f"{b['meanActual']:.1%}",
                "괴리": f"{b['gap']:.1%}",
                "건수": str(b["count"]),
            }
            for b in bins
        ]
        blocks.append(TableBlock("확률 구간별 적중률", pl.DataFrame(rows)))

    return blocks


# ── Penman 분해 빌더 ──


def penmanDecompositionBlock(data: dict) -> list:
    """calcPenmanDecomposition → HeadingBlock + TableBlock."""
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
                "RNOA": f"{h['rnoa']:.1f}%" if h.get("rnoa") is not None else "-",
                "FLEV": f"{h['flev']:.2f}" if h.get("flev") is not None else "-",
                "NBC": f"{h['nbc']:.1f}%" if h.get("nbc") is not None else "-",
                "SPREAD": f"{h['spread']:.1f}%p" if h.get("spread") is not None else "-",
                "레버리지효과": f"{h['leverageEffect']:.1f}%p" if h.get("leverageEffect") is not None else "-",
                "ROCE": f"{h['roce']:.1f}%" if h.get("roce") is not None else "-",
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("penmanDecomposition").label,
            level=2,
            helper="RNOA > NBC이면 차입이 주주에게 유리 (양의 SPREAD)",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
    return blocks


# ── ROIC Tree 빌더 ──


def roicTreeBlock(data: dict) -> list:
    """calcRoicTree → HeadingBlock + TableBlock + TextBlock(driver)."""
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
                "ROIC": f"{h['roic']:.1f}%" if h.get("roic") is not None else "-",
                "영업마진": f"{h['operatingMargin']:.1f}%" if h.get("operatingMargin") is not None else "-",
                "자본회전": f"{h['capitalTurnover']:.2f}x" if h.get("capitalTurnover") is not None else "-",
                "매출총이익률": f"{h['grossMargin']:.1f}%" if h.get("grossMargin") is not None else "-",
                "판관비율": f"{h['sgaRatio']:.1f}%" if h.get("sgaRatio") is not None else "-",
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("roicTree").label,
            level=2,
            helper="ROIC = 영업마진 × 자본회전. 어느 쪽이 ROIC를 결정하는가",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))

    latest = history[-1]
    drivers = []
    if latest.get("marginDriver"):
        drivers.append(f"마진 드라이버: {latest['marginDriver']}")
    if latest.get("turnoverDriver"):
        drivers.append(f"회전 드라이버: {latest['turnoverDriver']}")
    if drivers:
        blocks.append(TextBlock(" | ".join(drivers), style="dim"))

    return blocks


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


# ── Richardson 3계층 발생액 빌더 ──


def richardsonAccrualBlock(data: dict) -> list:
    """calcRichardsonAccrual → HeadingBlock + TableBlock."""
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
                "WCACC": h.get("wcacc"),
                "LTOACC": h.get("ltoacc"),
                "FINACC": h.get("finacc"),
                "총발생액": h.get("totalAccrual"),
                "신뢰도": h.get("reliabilityScore", "-"),
            }
        )

    valueCols = ["WCACC", "LTOACC", "FINACC", "총발생액"]
    unified = unifyTableScale(rows, "기간", valueCols, unit="millions")

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("richardsonAccrual").label,
            level=2,
            helper="LTOACC 비중이 높을수록 이익 지속성 낮음 (신뢰도↓)",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(unified)))
    return blocks


# ── 영업외손익 분해 빌더 ──


def nonOperatingBreakdownBlock(data: dict) -> list:
    """calcNonOperatingBreakdown → HeadingBlock + TableBlock."""
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
                "영업이익": h.get("opIncome"),
                "금융수익": h.get("finIncome"),
                "금융비용": h.get("finCost"),
                "지분법": h.get("associateIncome"),
                "기타수익": h.get("otherIncome"),
                "기타비용": h.get("otherExpense"),
                "영업외비율": f"{h['nonOpRatio']:.0f}%" if h.get("nonOpRatio") is not None else "-",
            }
        )

    valueCols = ["영업이익", "금융수익", "금융비용", "지분법", "기타수익", "기타비용"]
    unified = unifyTableScale(rows, "기간", valueCols, unit="millions")

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("nonOperatingBreakdown").label,
            level=2,
            helper="영업외 > 30%이면 영업만으로 기업 판단 불가",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(unified)))
    blocks.extend(_notesDetailBlocks(data, {"affiliates": "관계기업 투자"}))
    return blocks


# ── CAGR 비교 빌더 ──


def cagrComparisonBlock(data: dict) -> list:
    """calcCagrComparison → HeadingBlock + TableBlock."""
    if not data:
        return []
    comparisons = data.get("comparisons", [])
    if not comparisons:
        return []

    rows = []
    for c in comparisons:
        rows.append(
            {
                "비교": c["label"],
                c["item1"]: f"{c['cagr1']:+.1f}%" if c.get("cagr1") is not None else "-",
                c["item2"]: f"{c['cagr2']:+.1f}%" if c.get("cagr2") is not None else "-",
                "갭": f"{c['gap']:+.1f}%p" if c.get("gap") is not None else "-",
                "시그널": c.get("signal", "-"),
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("cagrComparison").label,
            level=2,
            helper="매출 vs 이익 CAGR 갭 → 마진 방향, 자산 vs 매출 갭 → 효율 방향",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
    return blocks


# ── BS-CF 정합성 빌더 ──


def articulationCheckBlock(data: dict) -> list:
    """calcArticulationCheck → HeadingBlock + TableBlock."""
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
                "PPE오차": f"{h['ppeError']:.1f}%" if h.get("ppeError") is not None else "-",
                "현금오차": f"{h['cashError']:.1f}%" if h.get("cashError") is not None else "-",
                "자본오차": f"{h['equityError']:.1f}%" if h.get("equityError") is not None else "-",
                "최대오차": f"{h['maxErrorPct']:.1f}%" if h.get("maxErrorPct") is not None else "-",
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("articulationCheck").label,
            level=2,
            helper="오차 > 10%이면 연결범위 변동/환율효과/재분류 의심",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
    return blocks


# ── 3-6 신용평가 빌더 ──


def creditMetricsBlock(data: dict) -> list:
    """calcCreditMetrics 결과 → 핵심 지표 시계열 테이블."""
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
                "EBITDA/이자": f"{h['ebitdaInterestCoverage']:.1f}x"
                if h.get("ebitdaInterestCoverage") is not None
                else "-",
                "Debt/EBITDA": f"{h['debtToEbitda']:.1f}x" if h.get("debtToEbitda") is not None else "-",
                "FFO/Debt": f"{h['ffoToDebt']:.0f}%" if h.get("ffoToDebt") is not None else "-",
                "부채비율": f"{h['debtRatio']:.0f}%" if h.get("debtRatio") is not None else "-",
                "유동비율": f"{h['currentRatio']:.0f}%" if h.get("currentRatio") is not None else "-",
                "OCF/매출": f"{h['ocfToSales']:.1f}%" if h.get("ocfToSales") is not None else "-",
            }
        )

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("creditMetrics").label,
            level=2,
            helper="ICR>10 AA급 | Debt/EBITDA<1.5 A급 | FFO/Debt>40% 양호",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
    return blocks


def creditScoreBlock(data: dict) -> list:
    """calcCreditScore 결과 → 등급 종합 메트릭."""
    if not data:
        return []

    grade = data.get("grade", "?")
    desc = data.get("gradeDescription", "")
    score = data.get("score", 0)
    pd_est = data.get("pdEstimate", 0)
    ecr = data.get("eCR", "?")
    outlook = data.get("outlook", "N/A")
    sector = data.get("sector", "")
    inv = "투자적격" if data.get("investmentGrade") else "투기등급"

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("creditScore").label,
            level=2,
            helper=f"등급 {grade} ({desc}) | {inv} | PD {pd_est:.2f}%",
        )
    )
    blocks.append(
        MetricBlock(
            [
                ("신용등급", f"{grade} ({desc})"),
                ("종합 점수", f"{score:.1f}/100"),
                ("부도확률(1Y)", f"{pd_est:.2f}%"),
                ("현금흐름등급", ecr),
                ("등급 전망", outlook),
                ("업종", sector),
            ]
        )
    )

    # 5축 상세
    axes = data.get("axes", [])
    if axes:
        axisRows = []
        for a in axes:
            axisRows.append(
                {
                    "축": a.get("name", ""),
                    "점수": f"{a['score']:.1f}" if a.get("score") is not None else "-",
                    "비중": f"{a.get('weight', 0)}%",
                    "지표수": str(len(a.get("metrics", []))),
                }
            )
        blocks.append(TableBlock("5축 가중평균 상세", pl.DataFrame(axisRows)))

    return blocks


def creditHistoryBlock(data: dict) -> list:
    """calcCreditHistory 결과 → 등급 시계열."""
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
                "등급": h.get("grade", "?"),
                "점수": f"{h['score']:.1f}" if h.get("score") is not None else "-",
                "PD": f"{h['pdEstimate']:.2f}%" if h.get("pdEstimate") is not None else "-",
            }
        )

    stable = "안정적" if data.get("stable") else "변동 있음"

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("creditHistory").label,
            level=2,
            helper=f"등급 안정성: {stable}",
        )
    )
    blocks.append(TableBlock("", pl.DataFrame(rows)))
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


def creditPeerPositionBlock(data: dict) -> list:
    """calcCreditPeerPosition 결과 → 업종 내 위치."""
    if not data:
        return []

    metrics = data.get("metrics", {})
    if not metrics:
        return []

    blocks: list = []
    blocks.append(
        HeadingBlock(
            _meta("creditPeerPosition").label,
            level=2,
        )
    )
    metricList = []
    for k, v in metrics.items():
        if v is not None:
            metricList.append((k, f"{v:.1f}"))
    if metricList:
        blocks.append(MetricBlock(metricList))
    return blocks


def creditFlagsBlock(data: dict) -> list:
    """calcCreditFlags 결과 → 경고/기회 플래그."""
    if not data:
        return []
    flagList = data.get("flags", [])
    if not flagList:
        return []

    warnings = [f"{f['signal']}: {f['detail']}" for f in flagList if f.get("type") == "warning"]
    opportunities = [f"{f['signal']}: {f['detail']}" for f in flagList if f.get("type") == "opportunity"]

    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks


def creditNarrativeBlock(data: dict) -> list:
    """calcCreditNarrative 결과 → 7축 신용 서사 (severity별)."""
    if not data:
        return []

    axes = data.get("axes", [])
    if not axes:
        return []

    grade = data.get("grade", "?")
    grade_desc = data.get("gradeDescription", "")

    blocks: list = [
        HeadingBlock(
            _meta("creditNarrative").label,
            level=2,
            helper=f"등급 {grade} ({grade_desc}) — 7축 서사",
        ),
    ]

    severity_label = {
        "strong": "🟢 우수",
        "adequate": "🟡 양호",
        "weak": "🟠 주의",
        "critical": "🔴 위험",
    }

    for axis in axes:
        label = severity_label.get(axis.get("severity", ""), "")
        title = f"{axis.get('axisName', '?')} {label}".strip()
        summary = axis.get("summary", "")
        details = axis.get("details", [])

        text = f"**{title}** — {summary}"
        if details:
            details_text = " · ".join(d for d in details[:3] if d)
            if details_text:
                text += f"\n  {details_text}"
        blocks.append(TextBlock(text))

    return blocks


def creditAuditBlock(data: dict) -> list:
    """calcCreditAudit 결과 → 외부 신평사 대조."""
    if not data:
        return []

    external = data.get("externalGrades", {})
    notch_diffs = data.get("notchDifferences", {})
    avg_diff = data.get("avgNotchDiff", 0.0)
    agreements = data.get("agreements", [])
    disagreements = data.get("disagreements", [])

    if not external:
        # 외부 등급 데이터 없으면 블록 생략
        return []

    dcr_grade = data.get("dcrGrade", "?")

    blocks: list = [
        HeadingBlock(
            _meta("creditAudit").label,
            level=2,
            helper=f"dCR {dcr_grade} vs 신평사 평균 notch 차이 {avg_diff:+.1f}",
        ),
    ]

    # 외부 등급 비교 테이블
    rows = []
    for agency, grade in external.items():
        diff = notch_diffs.get(agency, 0)
        rows.append(
            {
                "신평사": agency,
                "등급": grade,
                "notch 차이": f"{diff:+d}" if diff != 99 else "비교불가",
            }
        )
    if rows:
        blocks.append(TableBlock("외부 신평사 대조", pl.DataFrame(rows)))

    # 동의/비동의 근거
    if agreements:
        blocks.append(TextBlock("**동의 근거**:\n" + "\n".join(f"- {a}" for a in agreements[:3])))
    if disagreements:
        blocks.append(TextBlock("**비동의 근거**:\n" + "\n".join(f"- {d}" for d in disagreements[:3])))

    return blocks


# ── 시장분석 (technicalAnalysis) 빌더 ──


def technicalVerdictBlock(data: dict) -> list:
    """calcTechnicalVerdict 결과 → 기술적 종합 판단."""
    if not data:
        return []

    verdict = data.get("verdict", "")
    score = data.get("score", 0)
    rsi = data.get("rsi")
    adx = data.get("adx")
    above20 = data.get("aboveSma20")
    above60 = data.get("aboveSma60")
    bbPos = data.get("bbPosition")

    metrics = [("종합 판단", f"{verdict} (score {score:+d})")]
    if rsi is not None:
        rsiLabel = "과매수" if rsi >= 70 else "과매도" if rsi <= 30 else "중립"
        metrics.append(("RSI (14)", f"{rsi:.1f} ({rsiLabel})"))
    if adx is not None:
        adxLabel = "강한 추세" if adx >= 25 else "추세 약함"
        metrics.append(("ADX (14)", f"{adx:.1f} ({adxLabel})"))
    if above20 is not None:
        metrics.append(("SMA 20일", "위" if above20 else "아래"))
    if above60 is not None:
        metrics.append(("SMA 60일", "위" if above60 else "아래"))
    if bbPos is not None:
        metrics.append(("BB 위치", f"{bbPos:.0f}%"))

    blocks: list = [
        HeadingBlock(
            _meta("technicalVerdict").label,
            level=2,
            helper="카테고리 간 우선순위 없음 — audit 통과한 독립 분해. 미래 예측 아님.",
        ),
        MetricBlock(metrics),
    ]

    # ── 카테고리 서브섹션 (Phase 5 verdict 강화, audit 통과 라벨만) ──
    categories = data.get("categories") or {}
    # 12년 audit 통과: trend 만 (momentum/volatility 12년 전라벨 fail → drop)
    cat_ko = {"trend": "추세"}
    for key, ko in cat_ko.items():
        cat = categories.get(key)
        if not cat:
            continue
        cat_metrics = [
            ("점수", f"{cat['score']:.0f}/100"),
            ("라벨", cat["label"]),
        ]
        inds = cat.get("indicators", {})
        for ik, iv in inds.items():
            if isinstance(iv, bool):
                cat_metrics.append((ik, "예" if iv else "아니오"))
            elif isinstance(iv, float):
                cat_metrics.append((ik, f"{iv:.1f}"))
            elif isinstance(iv, (list, dict)):
                continue  # 중첩 구조 skip
            else:
                cat_metrics.append((ik, str(iv)))
        blocks.append(HeadingBlock(f"{ko} ({key})", level=3))
        blocks.append(MetricBlock(cat_metrics))

    # narrate (Phase 5 E)
    narrative = narrateTechnicalVerdict(data)
    if narrative:
        blocks.append(TextBlock(narrative))

    return blocks


def technicalSignalsBlock(data: dict) -> list:
    """calcTechnicalSignals 결과 → 최근 매매 신호."""
    if not data:
        return []

    summary = data.get("signalSummary", {})
    bullish = summary.get("bullish", 0)
    bearish = summary.get("bearish", 0)

    blocks: list = [
        HeadingBlock(
            _meta("technicalSignals").label,
            level=2,
            helper="최근 20거래일 기준 매매 신호 집계",
        ),
        MetricBlock(
            [
                ("매수 신호", f"{bullish}건"),
                ("매도 신호", f"{bearish}건"),
            ]
        ),
    ]

    # 신호별 상세
    signals = data.get("signals", {})
    signalNames = {
        "goldenCross": "골든/데드크로스",
        "rsiSignal": "RSI 신호",
        "macdSignal": "MACD 신호",
        "bollingerSignal": "볼린저 신호",
    }
    sigMetrics = []
    for key, label in signalNames.items():
        val = signals.get(key, 0)
        if val > 0:
            sigMetrics.append((label, f"매수 {val}건"))
        elif val < 0:
            sigMetrics.append((label, f"매도 {abs(val)}건"))
    if sigMetrics:
        blocks.append(MetricBlock(sigMetrics))

    # 최근 이벤트 테이블
    events = data.get("recentEvents", [])
    if events:
        eventNames = {
            "goldenCross": "골든/데드크로스",
            "rsiSignal": "RSI",
            "macdSignal": "MACD",
            "bollingerSignal": "볼린저",
        }
        rows = {
            "날짜": [e.get("date", "") for e in events],
            "신호": [eventNames.get(e.get("type", ""), e.get("type", "")) for e in events],
            "방향": [e.get("direction", "") for e in events],
        }
        blocks.append(TableBlock("최근 신호 이벤트", pl.DataFrame(rows)))

    return blocks


def quantModuleBlock(key: str, data: dict | None) -> list:
    """quant 서사 모듈 1개 → Block (analysis calc 패턴).

    각 calc*Narrative 함수가 독립으로 반환한 dict 를 review 블록으로 변환.
    analysis 의 개별 calc → builder 패턴과 동일.
    """
    if not data:
        return []
    narrative = data.get("narrative", "")
    if not narrative or narrative.endswith("데이터 없음.") or narrative.endswith("데이터 부족."):
        return []
    label = _meta(key).label if _has_meta(key) else key
    return [
        HeadingBlock(label, level=3),
        TextBlock(narrative),
    ]


def _has_meta(key: str) -> bool:
    """catalog 에 해당 key 의 BlockMeta 가 있는지."""
    try:
        _meta(key)
        return True
    except (KeyError, AttributeError):
        return False


def strategySnapshotBlock(data: dict) -> list:
    """calcStrategySnapshot 결과 → 8 검증 스타일 진입 진단 카드.

    Strategy DSL 의 review 6막 (전망) 진입점. 시총 의존 0.
    """
    if not data:
        return []

    style_labels = {
        "trendFollow": "추세추종",
        "meanReversion": "평균회귀",
        "breakout": "돌파",
        "dipBuy": "눌림목매수",
        "eventDriven": "이벤트드리븐",
        "flowFollow": "수급추종(KR)",
        "lowVolDefensive": "저변동방어",
        "seasonalKR": "한국캘린더(KR)",
    }

    rows_label = []
    rows_sharpe = []
    rows_mdd = []
    rows_dsr = []
    rows_entry = []
    rows_exit = []
    rows_trades = []
    rows_verdict = []
    for key, label in style_labels.items():
        snap = data.get(key)
        if snap is None or snap.get("status") != "ok":
            continue
        sharpe = snap.get("sharpe", 0.0)
        rows_label.append(label)
        rows_sharpe.append(f"{sharpe:+.2f}")
        rows_mdd.append(f"{snap.get('mdd', 0.0) * 100:+.1f}%")
        rows_dsr.append(f"{snap.get('dsr', 0.0):.2f}")
        rows_entry.append("●" if snap.get("entry_today") else "—")
        rows_exit.append("●" if snap.get("exit_today") else "—")
        rows_trades.append(str(snap.get("trades", 0)))
        # 판정
        if sharpe >= 1.2:
            rows_verdict.append("강함")
        elif sharpe >= 0.6:
            rows_verdict.append("양호")
        elif sharpe >= 0.2:
            rows_verdict.append("보통")
        elif sharpe > -1e-6:
            rows_verdict.append("약함")
        else:
            rows_verdict.append("부정")

    if not rows_label:
        return []

    table = pl.DataFrame(
        {
            "스타일": rows_label,
            "Sharpe": rows_sharpe,
            "MDD": rows_mdd,
            "DSR": rows_dsr,
            "오늘진입": rows_entry,
            "오늘청산": rows_exit,
            "Trades": rows_trades,
            "판정": rows_verdict,
        }
    )

    # 활성 진입 신호 narrate (1줄)
    active_styles = [style_labels[k] for k, v in data.items() if v.get("entry_today") and v.get("status") == "ok"]
    helper = (
        "8 검증 스타일 백테스트 결과 + 오늘 시점 진입/청산 진단. "
        "Sharpe ≥ 1.2 강함, ≥ 0.6 양호, < 0.2 약함. DSR (Bailey-Lopez) 가 우연성 검증."
    )
    if active_styles:
        helper += f"\n오늘 진입 신호 활성 스타일: {', '.join(active_styles)}"

    blocks: list = [
        HeadingBlock(
            "전략별 진입 진단",
            level=2,
            helper=helper,
        ),
        TableBlock("스타일 백테스트 매트릭스", table),
    ]

    # 학술 출처 + 5년 결과 + 오늘 신호 narrate (Phase 4 R5)
    narrative = narrateStrategy(data)
    if narrative:
        blocks.append(TextBlock(narrative))

    return blocks


def marketBetaBlock(data: dict) -> list:
    """calcMarketBeta 결과 → 시장 베타 + CAPM."""
    if not data:
        return []

    metrics = []
    beta = data.get("value")
    if beta is not None:
        metrics.append(("베타 (β)", f"{beta:.3f}"))
    alpha = data.get("alpha")
    if alpha is not None:
        metrics.append(("연간 알파", f"{alpha:+.2f}%"))
    r2 = data.get("rSquared")
    if r2 is not None:
        metrics.append(("R²", f"{r2:.4f}"))
    capm = data.get("capm")
    if capm is not None:
        metrics.append(("CAPM 기대수익률", f"{capm:.1f}%"))
    rs = data.get("relativeStrength")
    if rs is not None:
        rsLabel = "상대 강세" if rs > 0 else "상대 약세"
        metrics.append(("상대강도 (RSI 차이)", f"{rs:+.1f} ({rsLabel})"))

    if not metrics:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("marketBeta").label,
            level=2,
            helper="β < 1 시장보다 안정, β > 1 시장보다 변동 큼. α > 0이면 시장 초과 수익",
        ),
        MetricBlock(metrics),
    ]

    interp = data.get("interpretation")
    if interp:
        blocks.append(TextBlock(interp, style="dim", indent="h2"))

    return blocks


def fundamentalDivergenceBlock(data: dict) -> list:
    """calcFundamentalDivergence 결과 → 재무-시장 괴리 진단."""
    if not data:
        return []

    metrics = []
    fg = data.get("financialGrade")
    tv = data.get("technicalVerdict")
    div = data.get("divergence")

    if fg:
        metrics.append(("재무 등급", fg))
    if tv:
        ts = data.get("technicalScore", 0)
        metrics.append(("기술적 판단", f"{tv} (score {ts:+d})"))
    if div:
        metrics.append(("교차검증", div))

    if not metrics:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("fundamentalDivergence").label,
            level=2,
            helper="재무 분석과 시장 반응이 일치하면 신뢰도 ↑, 괴리하면 원인 분석 필요",
        ),
        MetricBlock(metrics),
    ]

    diagnosis = data.get("diagnosis")
    if diagnosis:
        blocks.append(TextBlock(diagnosis, indent="h2"))

    return blocks


def marketRiskBlock(data: dict) -> list:
    """calcMarketRisk 결과 → 안정성 섹션에 배치되는 시장 리스크."""
    if not data:
        return []

    metrics = []
    beta = data.get("beta")
    if beta is not None:
        metrics.append(("시장 베타", f"{beta:.3f}"))
    atrPct = data.get("atrPercent")
    volGrade = data.get("volatilityGrade")
    if atrPct is not None:
        metrics.append(("일일 변동성 (ATR%)", f"{atrPct:.1f}%"))
    if volGrade:
        metrics.append(("변동성 등급", volGrade))
    rs = data.get("relativeStrength")
    if rs is not None:
        metrics.append(("시장 대비 상대강도", f"{rs:+.1f}"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("marketRisk").label,
            level=2,
            helper="β > 1.5 고위험, ATR% > 5% 고변동. 상대강도 양수면 시장보다 강함",
        ),
        MetricBlock(metrics),
    ]


def marketAnalysisFlagsBlock(data) -> list:
    """calcMarketAnalysisFlags 결과 → FlagBlock."""
    flags = data if isinstance(data, list) else []
    return _flagsBlock(flags)


# ── 매크로 블록 ──


def macroPositionBlock(data: dict) -> list:
    """calcMacroEnvironment 결과 → 경제 사이클 + 기업 포지션."""
    if not data:
        return []

    phase_label = data.get("phaseLabel", "미정")
    confidence = data.get("confidence", "low")
    position_label = data.get("positionLabel", "중립")
    cyclicality = data.get("cyclicality", "moderate")
    signals = data.get("signals", [])

    metrics = [
        ("경제 국면", f"{phase_label} ({confidence})"),
        ("업종 경기민감도", cyclicality),
        ("현재 포지션", position_label),
    ]

    blocks: list = [
        HeadingBlock(
            _meta("macroEnvironment").label,
            level=2,
            helper="경제 사이클 4국면(침체/회복/확장/둔화) 판별 + 업종별 투자 전략",
        ),
        MetricBlock(metrics),
    ]

    if signals:
        blocks.append(TextBlock("판별 근거: " + " | ".join(signals[:4])))

    implication = data.get("implication")
    if implication:
        blocks.append(TextBlock(f"시사점: {implication}"))

    return blocks


def assetSignalsBlock(data: dict) -> list:
    """calcAssetSignals 결과 → 5대 자산 해석."""
    if not data:
        return []

    assets = data.get("assets", [])
    if not assets:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("assetSignals").label,
            level=2,
            helper="금리·환율·금·VIX 현재 상태와 해석",
        ),
    ]

    for a in assets:
        line = f"{a['label']}: {a['interpretation']}"
        relevance = a.get("companyRelevance")
        if relevance:
            line += f" → {relevance}"
        blocks.append(TextBlock(line))

    return blocks


def macroEnvironmentBlock(summary: dict) -> list:
    """macro 종합 결과 → 경제 환경 신호등."""
    if not summary:
        return []

    overall_label = summary.get("overallLabel", "")
    score = summary.get("score", 0)
    reasons = summary.get("reasons", []) or []
    contributions = summary.get("contributions", {}) or {}
    allocation = summary.get("allocation") or {}

    if not overall_label:
        return []

    metrics = [
        ("종합 판정", f"{overall_label} (score {score:+.1f})"),
    ]
    if reasons:
        metrics.append(("핵심 근거", ", ".join(reasons[:3])))

    contrib_parts = []
    for axis, val in sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True):
        if val != 0:
            contrib_parts.append(f"{axis} {val:+.1f}")
    if contrib_parts:
        metrics.append(("축별 기여", ", ".join(contrib_parts[:5])))

    if allocation:
        eq = allocation.get("equity", 0)
        bd = allocation.get("bond", 0)
        gd = allocation.get("gold", 0)
        cs = allocation.get("cash", 0)
        metrics.append(("자산배분", f"주식 {eq}% / 채권 {bd}% / 금 {gd}% / 현금 {cs}%"))
        regime = allocation.get("regime", "")
        if regime:
            metrics.append(("투자 국면", regime))

    from dartlab.review.narrate import narrateMacroEnvironment

    blocks: list = [
        HeadingBlock(
            _meta("macroEnvironment").label,
            level=2,
            helper="매크로 11축 종합 판정 — 경제 환경이 투자에 우호적인가",
        ),
        MetricBlock(metrics),
    ]
    narrative = narrateMacroEnvironment(summary)
    if narrative:
        blocks.append(TextBlock(narrative))
    return blocks


def macroCycleBlock(data: dict) -> list:
    """dartlab.macro("사이클") 결과 → 경기 사이클 + 전환 시퀀스 + 섹터 전략."""
    if not data:
        return []

    phase = data.get("phase", "")
    phase_label = data.get("phaseLabel", "")
    confidence = data.get("confidence", "")
    signals = data.get("signals", []) or []
    sector_strategy = data.get("sectorStrategy", {}) or {}
    transition = data.get("transition") or {}

    if not phase:
        return []

    metrics = [
        ("경기 국면", f"{phase_label or phase}"),
        ("판정 신뢰도", confidence or "?"),
    ]
    if signals:
        metrics.append(("핵심 신호", ", ".join(signals[:3])))

    if transition:
        t_from = transition.get("from", "")
        t_to = transition.get("to", "")
        progress = transition.get("progress")
        if t_from and t_to:
            prog_str = f" ({progress:.0%})" if isinstance(progress, (int, float)) else ""
            metrics.append(("전환 시퀀스", f"{t_from} → {t_to}{prog_str}"))
        triggered = transition.get("triggered", [])
        pending = transition.get("pending", [])
        if triggered:
            metrics.append(("확인된 신호", ", ".join(triggered[:3])))
        if pending:
            metrics.append(("대기 신호", ", ".join(pending[:3])))

    sector_lines = []
    for k_label, k in [
        ("경기민감 (high)", "high"),
        ("중간민감 (moderate)", "moderate"),
        ("방어주 (defensive)", "defensive"),
        ("저민감 (low)", "low"),
    ]:
        v = sector_strategy.get(k)
        if v:
            sector_lines.append((k_label, v))

    blocks: list = [
        HeadingBlock(
            _meta("macroCycle").label,
            level=2,
            helper="회복/확장/둔화/침체 4국면 + 전환 시퀀스 + 섹터별 전략",
        ),
        MetricBlock(metrics),
    ]
    if sector_lines:
        blocks.append(MetricBlock(sector_lines))

    # Bridgewater 4 Quadrant (Growth × Inflation)
    quadrant = data.get("quadrant")
    if isinstance(quadrant, dict):
        q_label = quadrant.get("quadrantLabel", "")
        q_growth = "성장↑" if quadrant.get("growth") == "rising" else "성장↓"
        q_infl = "인플레↑" if quadrant.get("inflation") == "rising" else "인플레↓"
        q_conf = quadrant.get("confidence", "")
        q_lines = [
            ("매크로 체제", f"{q_label} ({q_growth}, {q_infl})"),
            ("체제 신뢰도", q_conf),
        ]
        asset_impl = quadrant.get("assetImplication", {})
        if asset_impl:
            ow = [k for k, v in asset_impl.items() if v == "overweight"]
            uw = [k for k, v in asset_impl.items() if v == "underweight"]
            if ow:
                q_lines.append(("Overweight", ", ".join(ow)))
            if uw:
                q_lines.append(("Underweight", ", ".join(uw)))
        blocks.append(MetricBlock(q_lines))

    return blocks


def macroRatesBlock(data: dict) -> list:
    """macro 금리 결과 → 금리 환경."""
    if not data:
        return []

    outlook = data.get("outlook") or {}
    expectation = data.get("expectation") or {}
    yield_curve = data.get("yieldCurve") or {}
    real_rate = data.get("realRateRegime", "")

    direction = outlook.get("direction", "")
    if not direction:
        return []

    _DIR_LABELS = {"cut": "인하 기대", "hold": "동결", "hike": "인상 가능"}
    metrics: list[tuple[str, str]] = [
        ("금리 방향", _DIR_LABELS.get(direction, direction)),
    ]

    spread_2y_ff = expectation.get("spread2yFf")
    if spread_2y_ff is not None:
        metrics.append(("2Y-FF 스프레드", f"{spread_2y_ff:+.2f}%p"))

    slope = yield_curve.get("slope")
    if slope is not None:
        shape = "정상" if slope > 0 else "역전"
        metrics.append(("수익률곡선", f"{shape} (Slope {slope:+.2f}%p)"))

    if real_rate:
        if isinstance(real_rate, dict):
            metrics.append(("실질금리 국면", real_rate.get("regimeLabel", "")))
        else:
            metrics.append(("실질금리 국면", str(real_rate)))

    # ACM Term Premium
    tp = data.get("termPremium")
    if isinstance(tp, dict):
        tp_val = tp.get("value")
        tp_label = tp.get("zoneLabel", "")
        if tp_val is not None:
            metrics.append(("텀프리미엄", f"{tp_val:+.2f}%p ({tp_label})"))

    # Cochrane-Piazzesi Bond Risk Premium
    cp = data.get("bondRiskPremium")
    if isinstance(cp, dict):
        cp_val = cp.get("cpFactor")
        cp_label = cp.get("zoneLabel", "")
        if cp_val is not None:
            metrics.append(("CP 팩터", f"{cp_val:+.2f} ({cp_label})"))

    return [
        HeadingBlock(
            _meta("macroRates").label,
            level=2,
            helper="금리 방향 + 수익률곡선 + 텀프리미엄 + 채권 리스크프리미엄",
        ),
        MetricBlock(metrics),
    ]


def macroLiquidityBlock(data: dict) -> list:
    """macro 유동성 결과 → 유동성 환경."""
    if not data:
        return []

    regime = data.get("regime", "")
    if not regime:
        return []

    _REGIME_LABELS = {"abundant": "풍부", "normal": "보통", "tight": "긴축"}
    metrics: list[tuple[str, str]] = [
        ("유동성 국면", _REGIME_LABELS.get(regime, regime)),
    ]

    fci = data.get("fci")
    if isinstance(fci, dict):
        fci_val = fci.get("value")
        fci_label = fci.get("label", "")
        if fci_val is not None:
            metrics.append(("FCI", f"{fci_val:+.2f} ({fci_label})"))
    elif isinstance(fci, (int, float)):
        label = "완화" if fci < 0 else "긴축"
        metrics.append(("FCI", f"{fci:+.2f} ({label})"))

    nfci = data.get("nfci")
    if isinstance(nfci, dict):
        nfci_val = nfci.get("value")
        if nfci_val is not None:
            metrics.append(("NFCI", f"{nfci_val:+.2f}"))
    elif isinstance(nfci, (int, float)):
        metrics.append(("NFCI", f"{nfci:+.2f}"))

    capex = data.get("capexPressure")
    if isinstance(capex, dict):
        level = capex.get("level", "")
        if level:
            metrics.append(("설비투자 압력", level))

    return [
        HeadingBlock(
            _meta("macroLiquidity").label,
            level=2,
            helper="유동성 환경 + FCI → 기업 자금 접근성",
        ),
        MetricBlock(metrics),
    ]


def macroSentimentBlock(data: dict) -> list:
    """macro 심리 결과 → 시장 심리."""
    if not data:
        return []

    fg = data.get("fearGreed") or {}
    vix = data.get("vixRegime") or {}

    fg_score = fg.get("score")
    if fg_score is None:
        return []

    fg_label = fg.get("label", "")
    metrics: list[tuple[str, str]] = [
        ("공포탐욕", f"{fg_score:.0f} ({fg_label})"),
    ]

    vix_level = vix.get("level", "")
    vix_value = vix.get("value")
    if vix_level:
        vix_str = f"{vix_level}"
        if vix_value is not None:
            vix_str += f" ({vix_value:.1f})"
        metrics.append(("VIX 구간", vix_str))

    buy_signal = vix.get("buySignal")
    if buy_signal is not None:
        _BUY_LABELS = {0: "대기", 1: "1차 매수", 2: "2차 매수", 3: "3차 매수"}
        metrics.append(("분할매수 신호", f"{buy_signal}차 ({_BUY_LABELS.get(buy_signal, '')})"))

    # JLN Macro Uncertainty
    mu = data.get("macroUncertainty")
    if isinstance(mu, dict):
        mu_val = mu.get("value")
        mu_label = mu.get("zoneLabel", "")
        vs_vix = mu.get("vsVix", "")
        if mu_val is not None:
            metrics.append(("실물 불확실성", f"{mu_val:.3f} ({mu_label})"))
            if vs_vix == "divergent":
                metrics.append(("VIX-JLN 괴리", "금융과 실물 불확실성 방향 다름"))

    return [
        HeadingBlock(
            _meta("macroSentiment").label,
            level=2,
            helper="공포탐욕 + VIX + JLN 실물 불확실성 — 극단값에서 역투자 기회",
        ),
        MetricBlock(metrics),
    ]


def macroForecastBlock(data: dict | None) -> list:
    """macro 예측 결과 → 경기 전망."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    rp = data.get("recessionProb")
    if rp and rp.get("probability") is not None:
        prob = rp["probability"]
        if prob > 0.4:
            label = "경계"
        elif prob > 0.2:
            label = "주의"
        elif prob > 0.1:
            label = "보통"
        else:
            label = "낮음"
        metrics.append(("침체확률", f"{prob * 100:.0f}% ({label})"))

    lei = data.get("lei")
    if isinstance(lei, dict):
        signal = lei.get("signal", "")
        _LEI_LABELS = {
            "expansion": "확장 지속",
            "caution": "주의",
            "recession_warning": "침체 경고",
        }
        if signal:
            metrics.append(("LEI 신호", _LEI_LABELS.get(signal, signal)))

    sahm = data.get("sahmRule")
    if isinstance(sahm, dict):
        val = sahm.get("value")
        triggered = sahm.get("triggered", False)
        if val is not None:
            status = "트리거" if triggered else "정상"
            metrics.append(("Sahm Rule", f"{val:.2f}%p ({status})"))

    momentum = data.get("momentumSignal")
    if isinstance(momentum, dict):
        direction = momentum.get("direction", "")
        if direction:
            metrics.append(("성장 모멘텀", direction))

    # Growth-at-Risk (Adrian 2019)
    gar = data.get("growthAtRisk")
    if isinstance(gar, dict):
        gar5 = gar.get("currentGaR5")
        median = gar.get("median")
        tail = gar.get("tailRiskLabel", "")
        if gar5 is not None:
            metrics.append(("GaR 5th", f"{gar5:+.1f}% ({tail})"))
        if median is not None:
            metrics.append(("GaR 중위", f"{median:+.1f}%"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroForecast").label,
            level=2,
            helper="침체확률 + LEI + Sahm + Growth-at-Risk → 경기 방향 선행 지표",
        ),
        MetricBlock(metrics),
    ]


def macroCorporateBlock(data: dict | None) -> list:
    """macro 기업집계 결과 → 시장 전체 이익사이클."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    ec = data.get("earningsCycle")
    if ec:
        direction = ec.get("currentDirection", "")
        label = ec.get("currentLabel", direction)
        yoy = ec.get("latestYoY")
        yoy_str = f" (YoY {yoy:+.1f}%)" if yoy is not None else ""
        if label:
            metrics.append(("이익사이클", f"{label}{yoy_str}"))

    pr = data.get("ponziRatio")
    if pr:
        ratio = pr.get("currentRatio")
        if ratio is not None:
            metrics.append(("Ponzi 비율", f"{ratio:.1%} (ICR<1 기업 비중)"))

    lc = data.get("leverageCycle")
    if lc:
        median = lc.get("currentMedian")
        if median is not None:
            metrics.append(("레버리지 중간값", f"{median:.1f}%"))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroCorporate").label,
            level=2,
            helper="전종목 재무제표 집계 — 시장 전체의 이익 건강도",
        ),
        MetricBlock(metrics),
    ]


def macroTradeBlock(data: dict | None) -> list:
    """macro 교역 결과 → 교역조건 (KR만)."""
    if not data:
        return []

    metrics: list[tuple[str, str]] = []

    tot = data.get("termsOfTrade")
    if tot:
        direction = tot.get("direction", "")
        _DIR_LABELS = {"improving": "개선", "stable": "안정", "deteriorating": "악화"}
        if direction:
            metrics.append(("교역조건", _DIR_LABELS.get(direction, direction)))

    ep = data.get("exportProfit")
    if isinstance(ep, dict):
        signal = ep.get("signal", "")
        if signal:
            metrics.append(("수출이익 함의", signal))

    lrs = data.get("leadingRelativeStrength")
    if isinstance(lrs, dict):
        direction = lrs.get("direction", "")
        if direction:
            metrics.append(("양국 선행지수", direction))

    if not metrics:
        return []

    return [
        HeadingBlock(
            _meta("macroTrade").label,
            level=2,
            helper="교역조건 + 수출이익 선행 — 한국 수출기업 영향",
        ),
        MetricBlock(metrics),
    ]


def macroFlagsBlock(summary: dict) -> list:
    """macro 종합에서 경고/기회 플래그 집계."""
    if not summary:
        return []

    warnings: list[str] = []
    opportunities: list[str] = []

    crisis = summary.get("crisis")
    if isinstance(crisis, dict):
        cg = crisis.get("creditGap")
        if cg and cg.get("zone") in ("warning", "danger"):
            warnings.append(f"Credit-to-GDP gap {cg.get('zoneLabel', '경계')}")
        ghs = crisis.get("ghsScore")
        if isinstance(ghs, dict) and ghs.get("score", 0) > 50:
            warnings.append(f"GHS 위기 점수 {ghs['score']:.0f}")
        minsky = crisis.get("minskyPhase")
        if isinstance(minsky, dict) and minsky.get("phase") in ("overtrading", "discredit", "revulsion"):
            warnings.append(f"Minsky {minsky.get('phaseLabel', minsky['phase'])}")
        # Excess Bond Premium (Gilchrist 2012)
        ebp = crisis.get("excessBondPremium")
        if isinstance(ebp, dict) and ebp.get("recessionSignal"):
            warnings.append(f"EBP {ebp.get('ebp', 0):.2f} — 침체 12개월 신호")
        elif isinstance(ebp, dict) and ebp.get("zone") == "stress":
            warnings.append(f"EBP {ebp.get('ebp', 0):.2f} — 신용 스트레스")
        # Verdad Credit Cycle
        cc = crisis.get("creditCycle")
        if isinstance(cc, dict):
            cc_phase = cc.get("phase")
            if cc_phase == "trough":
                opportunities.append("신용사이클 저점 — 역발상 매수 기회")
            elif cc_phase == "peak":
                warnings.append("신용사이클 정점 — 리스크 축소 시작")

    corporate = summary.get("corporate")
    if isinstance(corporate, dict):
        pr = corporate.get("ponziRatio")
        if pr and pr.get("currentRatio", 0) > 0.3:
            warnings.append(f"Ponzi비율 {pr['currentRatio']:.0%} — 금융 취약")

    sentiment = summary.get("sentiment")
    if isinstance(sentiment, dict):
        fg = sentiment.get("fearGreed")
        if fg and fg.get("score") is not None:
            s = fg["score"]
            if s < 25:
                opportunities.append(f"극단공포 ({s:.0f}) — 역투자 기회")
            elif s > 75:
                warnings.append(f"극단탐욕 ({s:.0f}) — 과열 경계")

    forecast = summary.get("forecast")
    if isinstance(forecast, dict):
        rp = forecast.get("recessionProb")
        if rp and rp.get("probability", 0) > 0.3:
            warnings.append(f"침체확률 {rp['probability'] * 100:.0f}%")

    overall = summary.get("overall", "")
    score = summary.get("score", 0)
    if overall == "favorable" and score >= 2.0:
        cycle = summary.get("cycle", {})
        phase = cycle.get("phaseLabel", "")
        opportunities.append(f"사이클 {phase} + 종합 우호 — 위험자산 긍정")

    if not warnings and not opportunities:
        return []

    blocks: list = []
    if warnings:
        blocks.append(FlagBlock(warnings, kind="warning"))
    if opportunities:
        blocks.append(FlagBlock(opportunities, kind="opportunity"))
    return blocks


def sectorKpiBlock(data: dict | None) -> list:
    """sectorKpi 결과 → 업종별 KPI 블록. 업종에 따라 다른 내용."""
    if not data:
        return []
    sector = data.get("sector", "")
    kpis = data.get("kpis", {})
    if not kpis:
        return []

    sector_labels = {"construction": "건설", "semiconductor": "반도체", "gaming": "게임·엔터", "pharma": "제약·바이오"}

    blocks: list = [
        HeadingBlock(
            f"업종 특수 KPI ({sector_labels.get(sector, sector)})",
            level=2,
            helper="범용 14축에 없는 이 업종만의 핵심 지표",
        ),
    ]

    from dartlab.review.narrate import narrateSectorContext

    context = narrateSectorContext(sector, kpis)
    if context:
        blocks.append(TextBlock(context))

    for key, val in kpis.items():
        if not val or not isinstance(val, dict):
            continue

        # 공통 패턴: history가 있으면 표, 아니면 metric
        history = val.get("history", [])
        if history and isinstance(history, list) and len(history) > 0 and isinstance(history[0], dict):
            cols_dict: dict[str, list] = {}
            for h in history:
                for k, v in h.items():
                    if k == "period":
                        continue
                    if k not in cols_dict:
                        cols_dict[k] = []
                    cols_dict[k].append(str(v) if v is not None else "-")
            if cols_dict:
                periods_list = [str(h.get("period", "")) for h in history]
                rows = [{"": k, **dict(zip(periods_list, vals))} for k, vals in cols_dict.items()]
                if rows:
                    blocks.append(TableBlock(key, pl.DataFrame(rows)))

        # simple metrics
        metrics = []
        for k, v in val.items():
            if k in ("history", "note", "products"):
                continue
            if isinstance(v, (int, float)):
                metrics.append((k, f"{v:.1f}" if isinstance(v, float) else str(v)))
            elif isinstance(v, str) and v:
                metrics.append((k, v))
        if metrics:
            blocks.append(MetricBlock(metrics[:8]))

        # note
        note = val.get("note")
        if note:
            blocks.append(TextBlock(f"_{note}_"))

    return blocks


# ── 개선 시나리오 (How축) ──


def improvementLeversBlock(data: dict | None) -> list:
    """calcImprovementLevers 결과 → 개선 레버 순위 + narrate."""
    if not data:
        return []
    levers = data.get("levers", [])
    if not levers:
        return []

    from dartlab.review.narrate import narrateImprovementLevers

    blocks: list = [HeadingBlock(_meta("improvementLevers").label, level=2, helper="영향도 순 개선 경로 — 가장 효과 큰 것부터")]

    narration = narrateImprovementLevers(data)
    if narration:
        blocks.append(TextBlock(narration))

    rows = []
    for lv in levers[:5]:
        row: dict = {"레버": lv["name"], "난이도": lv.get("difficulty", ""), "기간": lv.get("timeframe", "")}
        impact = lv.get("impact", {})
        if impact.get("opm") is not None:
            row["OPM"] = f"{impact['opm']:.1f}%"
        if impact.get("roe") is not None:
            row["ROE"] = f"{impact['roe']:.1f}%"
        if impact.get("fcf_change_pct") is not None:
            row["FCF 변화"] = f"{impact['fcf_change_pct']:+.0f}%"
        if impact.get("interestCoverage") is not None:
            row["이자보상"] = f"{impact['interestCoverage']:.1f}x"
        rows.append(row)

    if rows:
        blocks.append(TableBlock("개선 레버 영향도", pl.DataFrame(rows)))
    return blocks


def gradeUpgradePathBlock(data: dict | None) -> list:
    """calcGradeImprovement 결과 → 신용등급 상향 경로."""
    if not data:
        return []

    from dartlab.review.narrate import narrateGradeUpgrade

    blocks: list = [HeadingBlock(_meta("gradeUpgradePath").label, level=2, helper="dCR 한 노치 상향에 필요한 구체적 변화")]

    narration = narrateGradeUpgrade(data)
    if narration:
        blocks.append(TextBlock(narration))

    metrics = [("현재 등급", data.get("currentGrade", "")), ("목표 등급", data.get("targetGrade", ""))]
    if data.get("weakestAxis"):
        metrics.append(("가장 약한 축", data["weakestAxis"]))
    blocks.append(MetricBlock(metrics))

    improvements = data.get("improvements", [])
    if improvements:
        rows = [{"축": imp["axis"], "지표": imp["metric"], "현재": f"{imp['current']:.1f}", "목표": f"{imp['target']:.1f}", "변화": imp["change"]} for imp in improvements]
        blocks.append(TableBlock("등급 상향 경로", pl.DataFrame(rows)))
    return blocks


def technicalActionTargetsBlock(data: dict | None) -> list:
    """calcActionableTargets 결과 → 기술적 행동 목표."""
    if not data:
        return []

    from dartlab.review.narrate import narrateTechnicalAction

    blocks: list = [HeadingBlock(_meta("technicalActionTargets").label, level=2, helper="기술적 관점의 진입/청산 가격 목표")]

    narration = narrateTechnicalAction(data)
    if narration:
        blocks.append(TextBlock(narration))

    metrics = [("현재가", f"{data['currentPrice']:,}"), ("기술적 판정", data.get("technicalVerdict", ""))]
    if data.get("support"):
        metrics.append(("지지선", f"{data['support']:,}"))
    if data.get("resistance"):
        metrics.append(("저항선", f"{data['resistance']:,}"))
    blocks.append(MetricBlock(metrics))

    targets = data.get("targets", [])
    if targets:
        rows = [{"신호": t["signal"], "트리거 가격": f"{t['triggerPrice']:,}", "행동": t["action"], "신뢰도": t["confidence"]} for t in targets]
        blocks.append(TableBlock("행동 목표", pl.DataFrame(rows)))
    return blocks


def cyclicalActionPlanBlock(data: dict | None) -> list:
    """calcCyclicalAction 결과 → 사이클 대응 행동 계획."""
    if not data:
        return []

    from dartlab.review.narrate import narrateCyclicalAction

    blocks: list = [HeadingBlock(_meta("cyclicalActionPlan").label, level=2, helper="사이클 위치에 따른 지금 해야 할 것")]

    narration = narrateCyclicalAction(data)
    if narration:
        blocks.append(TextBlock(narration))

    blocks.append(MetricBlock([("사이클 국면", data.get("phaseLabel", ""))]))

    actions = data.get("actions", [])
    if actions:
        rows = [{"우선순위": a["priority"], "행동": a["action"], "이유": a["reason"], "긴급도": a.get("urgency", "")} for a in actions]
        blocks.append(TableBlock("행동 계획", pl.DataFrame(rows)))

    precedent = data.get("historicalPrecedent")
    if precedent:
        blocks.append(TextBlock(f"**역사적 선례**: {precedent}"))
    return blocks


def damodaran3testBlock(company) -> list:
    """Damodaran 3-test 결과 → 스토리 검증 블록."""
    try:
        from dartlab.review.narrative.validators import damodaranTest

        result = damodaranTest(company)
    except (ImportError, AttributeError, ValueError):
        return []

    blocks: list = [
        HeadingBlock(
            _meta("damodaran3test").label,
            level=2,
            helper="Damodaran: 모든 스토리는 History/Experience/Common Sense 3시험을 통과해야 한다",
        ),
    ]

    for test in [result.historyTest, result.experienceTest, result.commonSenseTest]:
        if test is None:
            continue
        icon = "✓" if test.passed else "✗"
        blocks.append(TextBlock(f"**{icon} {test.name}**: {test.detail}"))

    blocks.append(MetricBlock([("통과", f"{result.passCount}/{result.totalCount}")]))
    if result.passCount < 3:
        blocks.append(FlagBlock("warning", "3-test 일부 미통과 — 스토리 재검토 권고"))

    return blocks


def thesisReportBlocks(company, hypothesis: str | None) -> list:
    """AI 주도 논제 검증 — 가설→증거→판정 서사.

    블록을 기계적으로 쪼개지 않고 AI 응답 텍스트를 서사 단위로 3~4 블록에 배치.
    review의 '균질 블록' 원칙의 예외 — thesis는 서사 주도.
    """
    if not hypothesis:
        return [
            HeadingBlock(_meta("thesisStatement").label, level=2),
            FlagBlock(
                "warning",
                "hypothesis 파라미터가 필요합니다. 예: c.review(type='thesis', hypothesis='...')",
            ),
        ]

    blocks: list = [
        HeadingBlock(_meta("thesisStatement").label, level=2, helper="사용자 가설"),
        TextBlock(f"**가설**: {hypothesis}"),
    ]

    # AI 호출 (선택적 — 실패 시 스켈레톤만 반환)
    try:
        ask = getattr(company, "ask", None)
        if ask is None:
            blocks.append(FlagBlock("warning", "AI 엔진이 이 Company에 연결되지 않았습니다."))
            return blocks

        prompt = (
            f"다음 가설을 이 기업의 재무/공시 데이터로 검증하라:\n\n"
            f"가설: {hypothesis}\n\n"
            f"응답 형식:\n"
            f"## 지지 증거\n- 수치/팩트 (출처 명시)\n\n"
            f"## 반박 증거\n- 수치/팩트 (출처 명시)\n\n"
            f"## 판정\n지지/반박/미결 중 하나 + 신뢰도 (low/medium/high)"
        )
        response = ask(prompt)
        text = str(response) if response is not None else ""

        if text:
            blocks.append(HeadingBlock(_meta("evidenceFor").label, level=2))
            blocks.append(TextBlock(text))
    except (AttributeError, ValueError, RuntimeError) as e:
        blocks.append(FlagBlock("warning", f"AI 검증 실패: {e}"))

    return blocks


def companyCyclePositionBlock(crisisData: dict | None) -> list:
    """현재 매크로 환경의 역사적 유사 에포크 표시.

    crisis dict 내부의 historicalContext → historicalEvents 리스트를 표로 전개.
    '지금과 비슷했던 과거'와 '그때 어떻게 흘러갔는지'를 나란히 놓는다.
    """
    if not crisisData:
        return []

    hc = crisisData.get("historicalContext") or {}
    events = hc.get("historicalEvents") or []
    scenario = hc.get("suggestedScenario")
    reason = hc.get("suggestedScenarioReason")
    overall = hc.get("overallAssessment") or crisisData.get("verdict")

    if not events and not scenario and not overall:
        return []

    blocks: list = [
        HeadingBlock(
            _meta("companyCyclePosition").label,
            level=2,
            helper="지금과 비슷했던 과거 에포크. 역사가 반복되는 건 아니지만 운율은 맞는다.",
        ),
    ]

    if overall:
        blocks.append(TextBlock(str(overall)))

    if events:
        rows = []
        for e in events[:5]:
            if isinstance(e, dict):
                rows.append(
                    {
                        "사건": e.get("eventName", ""),
                        "시점": e.get("eventDate", ""),
                        "유사도": e.get("similarity", ""),
                        "맥락": e.get("context", ""),
                        "귀결": e.get("outcome", ""),
                    }
                )
        if rows:
            blocks.append(TableBlock("유사 역사적 에포크", pl.DataFrame(rows)))

    if scenario:
        blocks.append(TextBlock(f"**다음 장 추정 시나리오**: {scenario}" + (f" — {reason}" if reason else "")))

    return blocks


def valuationBandBlock(data: dict) -> list:
    """calcValuationBand 결과 → PER/PBR 밴드."""
    if not data:
        return []

    bands = data.get("bands", {})
    overall = data.get("overallZone", "적정")

    if not bands:
        return []

    metrics = []
    for key, band in bands.items():
        m = band["metric"]
        metrics.append((f"{m} 현재", f"{band['current']:.1f}x"))
        metrics.append((f"{m} 평균", f"{band['mean']:.1f}x (±{band['std']:.1f})"))
        metrics.append((f"{m} 백분위", f"{band['percentile']:.0f}%"))
        metrics.append((f"{m} 판정", band["zoneLabel"]))

    metrics.append(("종합", overall))

    return [
        HeadingBlock(
            _meta("valuationBand").label,
            level=2,
            helper="과거 PER/PBR 정규분포에서 현재 위치. -1σ 이하=저평가, +1σ 이상=고평가",
        ),
        MetricBlock(metrics),
    ]
