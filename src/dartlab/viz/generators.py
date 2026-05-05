"""Company → VizSpec(ChartSpec) 자동 생성기 8종.

기존 ``tools/chart.py``의 ``spec_*`` 함수를 통합.

사용법::

    from dartlab.viz.generators import spec_revenue_trend, auto_chart

    spec = spec_revenue_trend(company)   # → dict (ChartSpec)
    specs = auto_chart(company)          # → list[dict]
"""

from __future__ import annotations

from typing import Any

from dartlab.core.palette import COLORS

# ── 7영역 인사이트 상수 ──

_AREA_NAMES = ["performance", "profitability", "health", "cashflow", "governance", "risk", "opportunity"]
_AREA_LABELS = {
    "performance": "성과",
    "profitability": "수익성",
    "health": "건전성",
    "cashflow": "현금흐름",
    "governance": "지배구조",
    "risk": "리스크",
    "opportunity": "기회",
}
_GRADE_MAP = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 0}


def _safe_val(v: Any) -> float:
    """None → 0, 나머지 float 변환."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _meta(company: Any, source: str) -> dict:
    """ChartSpec meta 블록 생성."""
    return {
        "source": source,
        "stockCode": getattr(company, "stockCode", ""),
        "corpName": getattr(company, "corpName", ""),
    }


def _with_visual_context(spec: dict, *, purpose: str, evidenceIds: list[str] | None = None) -> dict:
    """Add optional visual-policy fields while preserving ChartSpec compatibility."""
    spec["purpose"] = purpose
    if evidenceIds:
        spec["evidenceIds"] = evidenceIds
    return spec


# ── spec 생성기 8종 ──


def spec_revenue_trend(company: Any, *, n_years: int = 5) -> dict | None:
    """IS 매출·영업이익·순이익 combo 차트 ChartSpec."""
    ann = getattr(company, "annual", None)
    if not ann:
        return None
    ann_data, ann_years = ann
    is_data = ann_data.get("IS", {})

    key_accounts = [
        ("매출액", ["sales", "revenue", "interest_income"]),
        ("영업이익", ["operating_income", "operating_profit"]),
        ("당기순이익", ["net_income", "profit_for_the_period", "profit_loss"]),
    ]
    chart_types = ["bar", "line", "line"]
    colors = [COLORS[2], COLORS[0], COLORS[3]]

    series = []
    for i, (label, candidates) in enumerate(key_accounts):
        vals = None
        for cand in candidates:
            if cand in is_data and any(v is not None for v in is_data[cand]):
                vals = is_data[cand]
                break
        if vals is None:
            continue
        recent = vals[-n_years:]
        series.append(
            {
                "name": label,
                "data": [_safe_val(v) for v in recent],
                "color": colors[i],
                "type": chart_types[i],
            }
        )

    if not series:
        return None
    return _with_visual_context(
        {
            "chartType": "combo",
            "title": f"{company.corpName} 손익 추이",
            "series": series,
            "categories": ann_years[-n_years:],
            "options": {"unit": "백만원"},
            "meta": _meta(company, "finance"),
        },
        purpose="trend",
        evidenceIds=["finance:IS"],
    )


def spec_cashflow_waterfall(company: Any) -> dict | None:
    """CF 워터폴 브릿지 ChartSpec."""
    ann = getattr(company, "annual", None)
    if not ann:
        return None
    ann_data, ann_years = ann
    cf_data = ann_data.get("CF", {})

    accts = {
        "cash_and_cash_equivalents_beginning": "기초현금",
        "operating_cashflow": "영업활동",
        "investing_cashflow": "투자활동",
        "financing_cashflow": "재무활동",
        "cash_and_cash_equivalents_ending": "기말현금",
    }
    vals = {}
    for key, label in accts.items():
        arr = cf_data.get(key, [])
        vals[label] = _safe_val(arr[-1]) if arr else 0.0

    if vals["기초현금"] == 0 and vals["영업활동"] == 0:
        return None

    labels = ["기초현금", "영업활동", "투자활동", "재무활동", "기말현금"]
    data = [vals[lb] for lb in labels]

    return _with_visual_context(
        {
            "chartType": "waterfall",
            "title": f"{company.corpName} 현금흐름 브릿지 ({ann_years[-1]})",
            "series": [{"name": "현금흐름", "data": data, "color": COLORS[2]}],
            "categories": labels,
            "options": {"unit": "백만원"},
            "meta": _meta(company, "finance"),
        },
        purpose="bridge",
        evidenceIds=["finance:CF"],
    )


def spec_balance_sheet(company: Any, *, n_years: int = 5) -> dict | None:
    """BS 유동/비유동 자산 stacked bar ChartSpec."""
    ann = getattr(company, "annual", None)
    if not ann:
        return None
    ann_data, ann_years = ann
    bs_data = ann_data.get("BS", {})

    accounts = [
        ("유동자산", "current_assets", COLORS[2]),
        ("비유동자산", "noncurrent_assets", COLORS[3]),
    ]
    series = []
    for label, key, color in accounts:
        arr = bs_data.get(key, [])
        if not arr:
            continue
        recent = arr[-n_years:]
        series.append(
            {
                "name": label,
                "data": [_safe_val(v) for v in recent],
                "color": color,
                "type": "bar",
                "stack": "assets",
            }
        )

    if not series:
        return None
    return _with_visual_context(
        {
            "chartType": "bar",
            "title": f"{company.corpName} 자산 구성",
            "series": series,
            "categories": ann_years[-n_years:],
            "options": {"unit": "백만원", "stacked": True},
            "meta": _meta(company, "finance"),
        },
        purpose="composition",
        evidenceIds=["finance:BS"],
    )


def spec_profitability(company: Any, *, n_years: int = 5) -> dict | None:
    """수익성 비율 라인 ChartSpec (ratioSeries 기반)."""
    rs = getattr(company, "ratioSeries", None)
    if rs is None:
        return None
    if isinstance(rs, tuple) and len(rs) == 2:
        ratio_dict = rs[0].get("RATIO", {})
        periods = rs[1]
    else:
        return None

    metrics = [
        ("ROE", "roe", COLORS[0]),
        ("영업이익률", "operatingMargin", COLORS[2]),
        ("순이익률", "netMargin", COLORS[3]),
    ]
    series = []
    for label, key, color in metrics:
        vals = ratio_dict.get(key, [])
        if not vals or not any(v is not None for v in vals):
            continue
        recent = vals[-n_years * 4 :]  # 분기별
        series.append(
            {
                "name": label,
                "data": [_safe_val(v) for v in recent],
                "color": color,
                "type": "line",
            }
        )

    if not series:
        return None
    return _with_visual_context(
        {
            "chartType": "line",
            "title": f"{company.corpName} 수익성 추이",
            "series": series,
            "categories": periods[-len(series[0]["data"]) :],
            "options": {"unit": "%"},
            "meta": _meta(company, "finance"),
        },
        purpose="trend",
        evidenceIds=["finance:ratioSeries"],
    )


def spec_dividend(company: Any) -> dict | None:
    """배당 시계열 combo ChartSpec."""
    div_df = None
    report = getattr(company, "report", None)
    if report is not None:
        div_obj = getattr(report, "dividend", None)
        if div_obj is not None:
            if hasattr(div_obj, "df"):
                div_df = div_obj.df
            elif hasattr(div_obj, "columns"):
                div_df = div_obj

    if div_df is None:
        div_df = getattr(company, "dividend", None)

    if div_df is None or not hasattr(div_df, "columns"):
        return None
    if "year" not in div_df.columns or "dps" not in div_df.columns:
        return None

    df = div_df.sort("year")
    years = [str(y) for y in df["year"].to_list()]
    dps_vals = [_safe_val(v) for v in df["dps"].to_list()]

    if not years or all(v == 0 for v in dps_vals):
        return None

    series: list[dict] = [{"name": "DPS(원)", "data": dps_vals, "color": COLORS[2], "type": "bar"}]

    if "dividendYield" in df.columns:
        series.append(
            {
                "name": "배당수익률(%)",
                "data": [_safe_val(v) for v in df["dividendYield"].to_list()],
                "color": COLORS[0],
                "type": "line",
            }
        )

    return _with_visual_context(
        {
            "chartType": "combo",
            "title": f"{company.corpName} 배당 분석",
            "series": series,
            "categories": years,
            "options": {"unit": "원", "secondaryY": ["배당수익률(%)"]},
            "meta": _meta(company, "finance"),
        },
        purpose="trend",
        evidenceIds=["report:dividend"],
    )


def spec_insight_radar(company: Any) -> dict | None:
    """7영역 인사이트 레이더 ChartSpec."""
    insights = getattr(company, "insights", None)
    if insights is None or not hasattr(insights, "performance"):
        return None

    grades = {}
    for name in _AREA_NAMES:
        area = getattr(insights, name, None)
        grades[name] = area.grade if area and hasattr(area, "grade") else "F"

    categories = [_AREA_LABELS.get(n, n) for n in _AREA_NAMES]
    data = [_GRADE_MAP.get(grades[n], 0) for n in _AREA_NAMES]

    return _with_visual_context(
        {
            "chartType": "radar",
            "title": f"{company.corpName} 투자 인사이트",
            "series": [{"name": company.corpName, "data": data, "color": COLORS[0]}],
            "categories": categories,
            "options": {"maxValue": 5},
            "meta": _meta(company, "insight"),
        },
        purpose="comparison",
        evidenceIds=["insight:grades"],
    )


def spec_ratio_sparklines(company: Any) -> dict | None:
    """비율 스파크라인 배열 ChartSpec."""
    from dartlab.analysis.financial.ratios import RATIO_CATEGORIES

    rs = getattr(company, "ratioSeries", None)
    if rs is None:
        return None
    if isinstance(rs, tuple) and len(rs) == 2:
        ratio_dict = rs[0].get("RATIO", {})
        periods = rs[1]
    else:
        return None

    sparklines = []
    for cat_name, fields in RATIO_CATEGORIES:
        cat_items = []
        for field_name in fields:
            vals = ratio_dict.get(field_name, [])
            if not vals:
                continue
            valid_count = sum(1 for v in vals if v is not None)
            if valid_count < 2:
                continue
            latest = next((v for v in reversed(vals) if v is not None), None)
            recent_valid = [v for v in vals[-8:] if v is not None]
            trend = (
                "up"
                if len(recent_valid) >= 2 and recent_valid[-1] > recent_valid[-2]
                else ("down" if len(recent_valid) >= 2 else "neutral")
            )
            cat_items.append(
                {
                    "field": field_name,
                    "values": [_safe_val(v) for v in vals[-20:]],
                    "latest": latest,
                    "trend": trend,
                }
            )
        if cat_items:
            sparklines.append({"category": cat_name, "metrics": cat_items[:3]})

    if not sparklines:
        return None
    return _with_visual_context(
        {
            "chartType": "sparkline",
            "title": f"{company.corpName} 비율 스파크라인",
            "series": sparklines,
            "categories": periods[-20:],
            "options": {},
            "meta": _meta(company, "finance"),
        },
        purpose="trend",
        evidenceIds=["finance:ratioSeries"],
    )


def spec_diff_heatmap(company: Any) -> dict | None:
    """diff 변화 밀도 히트맵 ChartSpec."""
    try:
        diff_df = company.diff()
    except (AttributeError, TypeError, OSError):
        return None
    if diff_df is None or not hasattr(diff_df, "shape") or diff_df.shape[0] == 0:
        return None

    change_rates: dict[str, float] = {}
    for row in diff_df.iter_rows(named=True):
        topic = row["topic"]
        rate = row.get("changeRate", 0) or 0
        change_rates[topic] = float(rate)

    sorted_topics = sorted(change_rates.items(), key=lambda x: x[1], reverse=True)[:30]
    heatmap_data = []
    for topic, rate in sorted_topics:
        intensity = "high" if rate >= 0.5 else ("medium" if rate >= 0.2 else "low")
        heatmap_data.append({"topic": topic, "changeRate": round(rate, 4), "intensity": intensity})

    return _with_visual_context(
        {
            "chartType": "heatmap",
            "title": f"{company.corpName} 공시 변화 밀도",
            "series": [{"name": "변화율", "data": heatmap_data}],
            "categories": [d["topic"] for d in heatmap_data],
            "options": {"colorScale": {"low": "#22c55e", "medium": "#f59e0b", "high": "#ea4647"}},
            "meta": _meta(company, "docs"),
        },
        purpose="evidence",
        evidenceIds=["docs:diff"],
    )


# ── 레지스트리 ──

# ── Phase A 신규 spec ──


def spec_peer_radar(peer_data: dict) -> dict | None:
    """4축(수익성/성장/품질/부채) 백분위 레이더 차트 spec.

    peer_data: calcPeerPosition 반환 dict.
    """
    axes = [
        ("수익성", peer_data.get("profitability_pct")),
        ("성장성", peer_data.get("growth_pct")),
        ("이익품질", peer_data.get("quality_pct")),
        ("안정성", 100 - peer_data.get("debt_pct", 50) if peer_data.get("debt_pct") is not None else None),
    ]
    vals = [v if v is not None else 50 for _, v in axes]
    labels = [a[0] for a in axes]

    return {
        "chartType": "radar",
        "title": "시장 내 위치 (백분위)",
        "series": [{"name": "백분위", "data": vals, "color": COLORS[0]}],
        "categories": labels,
        "options": {"unit": "%", "maxValue": 100},
        "purpose": "comparison",
        "evidenceIds": ["scan:peerPosition"],
        "meta": {
            "source": "scan/extended::calcPeerPosition",
            "statement": "PEER",
            "total_stocks": peer_data.get("total_stocks"),
        },
    }


def spec_sensitivity_heatmap(grid: list[dict]) -> dict | None:
    """DCF 민감도 히트맵 spec.

    grid: sensitivityAnalysis 반환 list[{wacc, g, fairValue}].
    """
    if not grid:
        return None
    waccs = sorted({r["wacc"] for r in grid})
    gs = sorted({r["g"] for r in grid})
    matrix = []
    for g_val in gs:
        row = []
        for w_val in waccs:
            fv = next((r["fairValue"] for r in grid if r["wacc"] == w_val and r["g"] == g_val), None)
            row.append(fv)
        matrix.append(row)

    return {
        "chartType": "heatmap",
        "title": "DCF 민감도 (WACC × 성장률)",
        "series": [{"name": f"{g:.1f}%", "data": row} for g, row in zip(gs, matrix, strict=False)],
        "categories": [f"{w:.1f}%" for w in waccs],
        "options": {"unit": "원", "yLabels": [f"{g:.1f}%" for g in gs]},
        "purpose": "valuation",
        "evidenceIds": ["valuation:sensitivity"],
        "meta": {"source": "core/finance/dcf::sensitivityAnalysis", "statement": "PRICE"},
    }


def spec_margin_trend(history: list[dict]) -> dict | None:
    """마진 3축(매출총이익/영업이익/순이익률) 시계열 line spec."""
    if not history:
        return None
    periods = [h.get("period", "") for h in history]
    return {
        "chartType": "line",
        "title": "마진 추이",
        "series": [
            {
                "name": "매출총이익률",
                "data": [h.get("grossMargin") for h in history],
                "color": COLORS[0],
                "type": "line",
            },
            {
                "name": "영업이익률",
                "data": [h.get("operatingMargin") for h in history],
                "color": COLORS[1],
                "type": "line",
            },
            {"name": "순이익률", "data": [h.get("netMargin") for h in history], "color": COLORS[2], "type": "line"},
        ],
        "categories": periods,
        "options": {"unit": "%"},
        "purpose": "trend",
        "evidenceIds": ["finance:IS"],
        "meta": {"source": "analysis/financial::calcMarginTrend", "statement": "IS"},
    }


def spec_leverage_trend(history: list[dict]) -> dict | None:
    """부채비율 시계열 line spec."""
    if not history:
        return None
    return {
        "chartType": "line",
        "title": "레버리지 추이",
        "series": [
            {"name": "부채비율", "data": [h.get("debtRatio") for h in history], "color": COLORS[3], "type": "line"}
        ],
        "categories": [h.get("period", "") for h in history],
        "options": {"unit": "%"},
        "purpose": "risk",
        "evidenceIds": ["finance:BS"],
        "meta": {"source": "analysis/financial::calcLeverage", "statement": "BS"},
    }


def spec_growth_yoy_bar(history: list[dict]) -> dict | None:
    """매출/영업이익/순이익 YoY bar chart spec."""
    if not history:
        return None
    return {
        "chartType": "bar",
        "title": "성장률 YoY",
        "series": [
            {"name": "매출 YoY", "data": [h.get("revenueYoY") for h in history], "color": COLORS[0], "type": "bar"},
            {"name": "영업이익 YoY", "data": [h.get("opYoY") for h in history], "color": COLORS[1], "type": "bar"},
        ],
        "categories": [h.get("period", "") for h in history],
        "options": {"unit": "%"},
        "purpose": "trend",
        "evidenceIds": ["finance:IS"],
        "meta": {"source": "analysis/financial::calcRevenueGrowth", "statement": "IS"},
    }


def spec_revenue_scenario_band(history: list[dict], forecasts: dict | None) -> dict | None:
    """매출 과거 실적 + Base/Bull/Bear 전망 밴드 spec."""
    if not history:
        return None
    periods = [h.get("period", "") for h in history]
    actuals = [h.get("revenue") for h in history]

    series: list[dict] = [{"name": "실적", "data": actuals, "color": COLORS[0], "type": "line"}]
    categories = periods

    if forecasts:
        fwd_periods = forecasts.get("periods", [])
        categories = periods + fwd_periods
        actuals_ext = actuals + [None] * len(fwd_periods)
        series[0]["data"] = actuals_ext

        for key, label, color in [
            ("base", "Base", COLORS[1]),
            ("bull", "Bull", COLORS[4]),
            ("bear", "Bear", COLORS[3]),
        ]:
            vals = forecasts.get(key, [])
            if vals:
                series.append({"name": label, "data": [None] * len(periods) + vals, "color": color, "type": "line"})

    return {
        "chartType": "line",
        "title": "매출 전망 시나리오 밴드",
        "series": series,
        "categories": categories,
        "options": {"unit": "원"},
        "purpose": "valuation",
        "evidenceIds": ["forecast:revenue"],
        "meta": {"source": "analysis/forecast", "statement": "IS"},
    }


SPEC_GENERATORS = {
    "revenue_trend": spec_revenue_trend,
    "cashflow": spec_cashflow_waterfall,
    "balance_sheet": spec_balance_sheet,
    "profitability": spec_profitability,
    "dividend": spec_dividend,
    "insight_radar": spec_insight_radar,
    "ratio_sparklines": spec_ratio_sparklines,
    "diff_heatmap": spec_diff_heatmap,
}


def auto_chart(company: Any) -> list[dict]:
    """사용 가능한 모든 ChartSpec 리스트를 자동 생성.

    데이터가 없는 차트는 건너뛴다.
    """
    specs = []
    for gen in [
        spec_revenue_trend,
        spec_balance_sheet,
        spec_profitability,
        spec_cashflow_waterfall,
        spec_dividend,
        spec_insight_radar,
        spec_ratio_sparklines,
        spec_diff_heatmap,
    ]:
        try:
            s = gen(company)
            if s is not None:
                specs.append(s)
        except (AttributeError, KeyError, OSError, TypeError, ValueError):
            continue
    return specs
