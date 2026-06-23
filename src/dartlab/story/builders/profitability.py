"""story 블록 빌더 — profitability 도메인 (debt-honesty P3-3 god-split). 공유 imports·상수·헬퍼는 _shared."""

from __future__ import annotations

from dartlab.story.builders._shared import (
    HeadingBlock,
    MetricBlock,
    TableBlock,
    TextBlock,
    _extractSeries,
    _flagsBlock,
    _historyTable,
    _meta,
    _timelineTable,
    narrateMargin,
    narrateROIC,
    pl,
)

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
        from dartlab.story.blocks import ChartBlock
        from dartlab.viz.generators import specMarginTrend

        chart = specMarginTrend(history)
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
    """calcReturnTrend 결과 → 듀퐁 분해 시계열."""
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
        from dartlab.story.blocks import ChartBlock
        from dartlab.viz.generators import specGrowthYoyBar

        chart = specGrowthYoyBar(history)
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
