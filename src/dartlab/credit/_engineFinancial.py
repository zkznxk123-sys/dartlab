"""Track B (금융업) 전용 평가 — engine.py 에서 분리."""

from __future__ import annotations

from dartlab.credit._engineConfig import _WEIGHTS
from dartlab.credit.features.sectorThresholds import getSectorLabel
from dartlab.credit.scoring.creditScorecard import (
    axisScore,
    creditOutlook,
    gradeCategory,
    isInvestmentGrade,
    scoreMetric,
    weightedScore,
)


def _evaluateFinancial(company, *, detail: bool = False, basePeriod: str | None = None, sector=None) -> dict | None:
    """금융업(은행/보험/증권) 전용 5축 평가.

    D/EBITDA, FFO/Debt를 사용하지 않고
    자본비율, ROA, NIM, 충당금 비율로 평가.
    """
    from dartlab.credit._enginePostAdjust import (
        _applyPostAdjustments,
        _applyTimeSeriesSmoothing,
        _normalizeMetricsForOutput,
    )
    from dartlab.credit.scoring.metrics import calcFinancialMetrics

    metrics = calcFinancialMetrics(company, basePeriod=basePeriod)
    if metrics is None or not metrics.get("history"):
        return None

    from dartlab.credit.features.sectorThresholds import financialTrackBThresholds

    thresholds = financialTrackBThresholds()
    latest = metrics["history"][0]

    # ── 축1: 자본적정성 ──
    ax1 = [
        ("자기자본비율", scoreMetric(latest.get("equityRatio"), thresholds["equity_ratio"])),
    ]
    s1 = axisScore(ax1)

    # ── 축2: 수익성 ──
    ax2 = [
        ("ROA", scoreMetric(latest.get("roa"), thresholds["roa"])),
        ("NIM대리", scoreMetric(latest.get("nimProxy"), thresholds["nim_proxy"])),
    ]
    s2 = axisScore(ax2)

    # ── 축3: 자산건전성 ──
    ax3 = [
        ("충당금비율", scoreMetric(latest.get("provisionRatio"), thresholds["provision_ratio"])),
    ]
    s3 = axisScore(ax3)
    if s3 is None:
        # 자산건전성 데이터 없을 때: 대형 금융지주는 양호 추정, 소형은 중립
        ta = latest.get("totalAssets") or 0
        s3 = 12.0 if ta > 100e12 else 20.0 if ta > 10e12 else 25.0

    # ── 축4: 유동성 ──
    ax4 = [
        ("현금/자산", scoreMetric(latest.get("cashToAsset"), thresholds["cash_to_asset"])),
        ("유동비율", scoreMetric(latest.get("currentRatio"), thresholds["current_ratio"])),
    ]
    s4 = axisScore(ax4)
    if s4 is None:
        s4 = 25.0

    # ── 축5: 사업안정성 ──
    biz = metrics.get("businessStability", {})
    ax5 = []
    revCV = biz.get("revenueCV")
    if revCV is not None:
        ax5.append(("영업안정성", min(revCV, 100)))
    totalAssets = biz.get("totalAssets")
    if totalAssets and totalAssets > 50e12:
        ax5.append(("규모", 0.0))
    elif totalAssets and totalAssets > 10e12:
        ax5.append(("규모", 15.0))
    else:
        ax5.append(("규모", 35.0))
    s5 = axisScore(ax5) if ax5 else 25.0

    # ── 가중평균 ──
    w = _WEIGHTS["financial"]
    axes = [
        {"name": "자본적정성", "score": s1, "weight": w[0], "metrics": ax1},
        {"name": "수익성", "score": s2, "weight": w[1], "metrics": ax2},
        {"name": "자산건전성", "score": s3, "weight": w[2], "metrics": ax3},
        {"name": "유동성", "score": s4, "weight": w[3], "metrics": ax4},
        {"name": "사업안정성", "score": s5, "weight": w[4], "metrics": ax5},
    ]

    for a in axes:
        score = a.get("score") or 0
        weight = a.get("weight", 0)
        a["contribution"] = round(score * weight, 2)

    currentScore = weightedScore([{"score": a["score"], "weight": a["weight"]} for a in axes])

    historicalScores = []
    for h in metrics["history"][1:3]:
        scores = []
        er = scoreMetric(h.get("equityRatio"), thresholds["equity_ratio"])
        roa = scoreMetric(h.get("roa"), thresholds["roa"])
        if er is not None:
            scores.append(er)
        if roa is not None:
            scores.append(roa)
        if scores:
            historicalScores.append(sum(scores) / len(scores))

    overall = _applyTimeSeriesSmoothing(currentScore, historicalScores)

    grade, gradeDesc, pdEstimate, overall, chsResult, notchAdj, divExpl = _applyPostAdjustments(
        company, overall, latest, metrics, axes, False, False, None
    )

    sectorLabel = f"{getSectorLabel(sector)} (Track B 금융전용)"

    result = {
        "grade": f"dCR-{grade}",
        "gradeRaw": grade,
        "gradeDescription": gradeDesc,
        "gradeCategory": gradeCategory(grade),
        "investmentGrade": isInvestmentGrade(grade),
        "score": overall,
        "healthScore": round(100 - overall, 2),
        "currentScore": currentScore,
        "pdEstimate": pdEstimate,
        "eCR": None,
        "outlook": creditOutlook([currentScore] + historicalScores),
        "sector": sectorLabel,
        "captiveFinance": False,
        "holding": False,
        "latestPeriod": latest.get("period"),
        "chsAdjustment": chsResult,
        "notchAdjustment": notchAdj if notchAdj["totalNotch"] != 0 else None,
        "divergenceExplanation": divExpl,
        "methodologyVersion": "v4.0-TrackB",
        "axes": [
            {
                "name": a["name"],
                "score": a["score"],
                "weight": round(a["weight"] * 100),
                "contribution": a.get("contribution", 0),
                "metrics": _normalizeMetricsForOutput(a["metrics"]),
            }
            for a in axes
        ],
    }

    if detail:
        result["metricsHistory"] = metrics["history"]
        result["businessStability"] = metrics.get("businessStability")

    return result
