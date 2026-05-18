"""analysis/* 함수 결과 → kind 별 View spec 변환 어댑터.

각 함수는 (company, ...) 받아 dict | list | None. 다양한 출력 shape 을
방어적으로 파싱해 View 의 kind 별 필드 (tiles/items/rows/gauge value/...) 채움.

원칙:
- 실패 (None / 빈 dict / 미존재 키) 시 빈 spec 반환 — 카드는 "데이터 없음" 표시.
- 함수 시그니처 변화에 대비 try/except — 절대 view build 자체를 중단시키지 않음.
"""

from __future__ import annotations

import importlib
from typing import Any

from dartlab.viz.data import normalize
from dartlab.viz.display.finance.accounts import extractSeries


def _safeCall(modulePath: str, fnName: str, company: Any, *args: Any, **kwargs: Any) -> Any:
    """analysis 모듈 함수 안전 호출 — import / call 실패 시 None."""
    try:
        mod = importlib.import_module(modulePath)
    except ImportError:
        return None
    fn = getattr(mod, fnName, None)
    if fn is None:
        return None
    try:
        return fn(company, *args, **kwargs)
    except Exception:  # noqa: BLE001
        return None


def _toFloat(v: Any) -> float | None:
    """안전 float 변환. 실패 시 None."""
    if v is None:
        return None
    try:
        f = float(v)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _drill(obj: Any, path: str) -> Any:
    """dot-path 로 dict/객체 안 값 추출. 실패 시 None."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif hasattr(cur, part):
            cur = getattr(cur, part)
        else:
            return None
    return cur


# ─────────────────────────────────────────────────────────────
# kpiTile / diffView — norm 의 마지막 2 기간 자동 추출.
# ─────────────────────────────────────────────────────────────


def buildKpiTilesFromNorm(norm: Any, periods: list[str], tilePlans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """norm + tilePlans → KpiTile dict list (P-DASH-V1 D11: sparkline + range bar).

    tilePlans 각 항목: {label, account?: str, ratio?: dict, unit, intent, subtitle?}.

    출력 tile 각 항목:
        - value/prev/unit/intent/subtitle (기존)
        - sparkline: list[float] — 최근 8 분기 데이터 (카드 우측 mini line).
        - rangeMin/rangeMax: 자체 5y range (카드 하단 percentile bar).
    """
    tiles: list[dict[str, Any]] = []
    for plan in tilePlans:
        label = plan.get("label", "")
        unit = plan.get("unit", "")
        intent = plan.get("intent", "primary")
        subtitle = plan.get("subtitle", "")
        data: list[float | None] = []
        if "account" in plan:
            data = extractSeries(norm, plan["account"], periods)
        elif "yoy" in plan:
            base = extractSeries(norm, plan["yoy"], periods)
            data = [None]
            for k in range(1, len(periods)):
                p, c = base[k - 1], base[k]
                if p is None or c is None or p == 0:
                    data.append(None)
                else:
                    data.append((c - p) / abs(p) * 100)
        elif "ratio" in plan:
            ratio = plan["ratio"]
            num_terms = ratio.get("num") or {}
            den_terms = ratio.get("den") or {}
            scale = float(ratio.get("scale", 100))
            num = _sumWeighted(norm, num_terms, periods)
            den = _sumWeighted(norm, den_terms, periods)
            data = [(n / d * scale) if (n is not None and d is not None and d != 0) else None for n, d in zip(num, den)]
        elif "compose" in plan:
            data = _sumWeighted(norm, plan["compose"], periods)
        last, prev = _lastTwo(data)

        # sparkline — 최근 8 기간 (또는 가능한 만큼).
        nonNone = [v for v in data if v is not None]
        sparkline = nonNone[-8:] if len(nonNone) >= 1 else []
        # 5y range — 최근 20 분기 또는 5 년 (annual) 의 min/max.
        rangeWindow = nonNone[-20:] if nonNone else []
        rangeMin = min(rangeWindow) if rangeWindow else None
        rangeMax = max(rangeWindow) if rangeWindow else None

        tile: dict[str, Any] = {
            "label": label,
            "value": last,
            "prev": prev,
            "unit": unit,
            "intent": intent,
            "subtitle": subtitle,
        }
        if sparkline:
            tile["sparkline"] = sparkline
        if rangeMin is not None:
            tile["rangeMin"] = rangeMin
        if rangeMax is not None:
            tile["rangeMax"] = rangeMax
        tiles.append(tile)
    return tiles


def _sumWeighted(norm: Any, terms: dict[str, int], periods: list[str]) -> list[float | None]:
    """compose / ratio 가산 — builder._sumWeighted 와 동일 로직 복제 (순환 import 회피)."""
    n = len(periods)
    if not terms:
        return [None] * n
    series_by_key = {k: extractSeries(norm, k, periods) for k in terms}
    out: list[float | None] = []
    for i in range(n):
        total = 0.0
        valid = False
        for k, sign in terms.items():
            v = series_by_key[k][i]
            if v is None:
                continue
            total += sign * float(v)
            valid = True
        out.append(total if valid else None)
    return out


def _lastTwo(arr: list[float | None]) -> tuple[float | None, float | None]:
    """마지막 2 개 비 None 값. (last, prev) — last 가 가장 최근."""
    last: float | None = None
    prev: float | None = None
    for v in reversed(arr):
        if v is None:
            continue
        if last is None:
            last = v
        else:
            prev = v
            break
    return last, prev


def buildDuPontRadar(norm: Any, periods: list[str]) -> dict[str, Any]:
    """DuPont 3-factor radar — 마지막 4 기간을 각 polygon 으로.

    axes: [순이익률 (%), 자산회전율 (회 ×100), 레버리지 (배 ×10)]
        scale 보정으로 3 축이 비슷한 magnitude → polar 가 한쪽에 쏠리지 않게.
    polygon: 마지막 4 기간 (당기·전기·1y 전·2y 전) — 시각적 시계열.

    Args:
        norm: 정규화 finance DataFrame.
        periods: 시간 라벨 list (마지막 = 최신).

    Returns:
        {categories: [axis label], series: [{key, label, color, data: [axis 값]}]}.
        data 모두 None 이면 호출자가 fallback.
    """
    if not periods:
        return {"categories": [], "series": []}

    npm = _sumWeighted(norm, {"netIncome": 1}, periods)
    rev = _sumWeighted(norm, {"revenue": 1}, periods)
    assets = _sumWeighted(norm, {"assets": 1}, periods)
    equity = _sumWeighted(norm, {"equity": 1}, periods)

    def _ratio(num: list[float | None], den: list[float | None], scale: float, i: int) -> float | None:
        n = num[i] if i < len(num) else None
        d = den[i] if i < len(den) else None
        if n is None or d is None or d == 0:
            return None
        return (n / d) * scale

    axesLabels = ["순이익률(%)", "자산회전(회×100)", "레버리지(배×10)"]

    sample = periods[-4:] if len(periods) >= 4 else periods
    palette = ["#dc2626", "#f97316", "#a78bfa", "#9ca3af"]
    series: list[dict[str, Any]] = []
    for offset, period in enumerate(sample):
        i = len(periods) - len(sample) + offset
        m = _ratio(npm, rev, 100, i)
        t = _ratio(rev, assets, 100, i)
        l = _ratio(assets, equity, 10, i)
        data = [m, t, l]
        if all(v is None for v in data):
            continue
        isCurrent = offset == len(sample) - 1
        series.append(
            {
                "key": f"p{offset}",
                "label": f"{period}{'(당기)' if isCurrent else ''}",
                "color": palette[len(sample) - 1 - offset]
                if (len(sample) - 1 - offset) < len(palette)
                else palette[-1],
                "data": data,
                "type": "radar",
                "unit": "",
            }
        )

    return {"categories": axesLabels, "series": series}


# ─────────────────────────────────────────────────────────────
# topList — analysis 함수가 list[str] 또는 list[dict] 반환.
# ─────────────────────────────────────────────────────────────


def buildTopListFromFlags(flags: Any) -> list[dict[str, Any]]:
    """analysis flags 함수 결과 (list[str] 또는 list[tuple] 또는 list[dict]) → TopListItem."""
    if not flags or not isinstance(flags, list):
        return []
    items: list[dict[str, Any]] = []
    for f in flags:
        if isinstance(f, str):
            items.append({"label": f, "value": None, "unit": "", "delta": None})
        elif isinstance(f, tuple) and len(f) >= 2:
            items.append({"label": str(f[0]), "description": str(f[1])})
        elif isinstance(f, dict):
            items.append(
                {
                    "label": str(f.get("label") or f.get("name") or f.get("key") or "?"),
                    "value": _toFloat(f.get("value") or f.get("score")),
                    "unit": f.get("unit", ""),
                    "delta": _toFloat(f.get("delta")),
                    "description": str(f.get("description", f.get("desc", ""))),
                }
            )
    return items


# ─────────────────────────────────────────────────────────────
# gauge — distress / Altman Z / Beneish M.
# ─────────────────────────────────────────────────────────────


def buildDistressGauge(company: Any) -> dict[str, Any]:
    """Altman Z' (private firm) gauge — norm 만으로 직접 계산.

    Z' = 0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5
      X1 = (currentAssets - currentLiabilities) / assets   (운전자본/자산)
      X2 = retainedEarnings / assets                       (잉여금/자산)
      X3 = operatingIncome / assets                        (영업이익/자산, EBIT proxy)
      X4 = equity / liabilities                            (장부자기자본/부채)
      X5 = revenue / assets                                (자산회전율)

    임계: Z' ≥ 2.9 안전 / 1.23~2.9 주의 / < 1.23 위험.
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 4, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if not periods:
        return {}
    p = periods[-1]
    ca = _toFloat(extractSeries(norm, "currentAssets", [p])[0]) or 0.0
    cl = _toFloat(extractSeries(norm, "currentLiabilities", [p])[0]) or 0.0
    ta = _toFloat(extractSeries(norm, "assets", [p])[0]) or 0.0
    re = _toFloat(extractSeries(norm, "retainedEarnings", [p])[0]) or 0.0
    oi = _toFloat(extractSeries(norm, "operatingIncome", [p])[0]) or 0.0
    eq = _toFloat(extractSeries(norm, "equity", [p])[0]) or 0.0
    tl = _toFloat(extractSeries(norm, "liabilities", [p])[0]) or 0.0
    rv = _toFloat(extractSeries(norm, "revenue", [p])[0]) or 0.0
    if ta <= 0 or tl <= 0:
        return {}
    x1 = (ca - cl) / ta
    x2 = re / ta
    x3 = oi / ta
    x4 = eq / tl
    x5 = rv / ta
    z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
    return {
        "value": round(z, 2),
        "minValue": 0.0,
        "maxValue": 6.0,
        "bands": [
            {"fromValue": 0.0, "toValue": 1.23, "label": "위험", "intent": "negative"},
            {"fromValue": 1.23, "toValue": 2.9, "label": "주의", "intent": "accent"},
            {"fromValue": 2.9, "toValue": 6.0, "label": "안전", "intent": "positive"},
        ],
        "unit": "",
        "subtitle": f"Altman Z' (private firm) · {p} · ≥2.9 안전 / 1.23~2.9 주의 / <1.23 위험",
    }


def buildScenarioSensitivity(company: Any) -> dict[str, Any]:
    """매출 변동 × 마진 변동 → 영업이익 변동 % heatmap (P-DASH-V1 D15).

    base = 최근 기간 매출·영업이익률. 3×3 matrix:
        rev shifts:  -10% / 0% / +10%
        margin shifts: -2pp / 0 / +2pp

    각 cell = (base 영업이익 대비 변동 영업이익 - 1) × 100 %.

    Returns: {cells, rowOrder, colOrder, tone}.
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 4, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if not periods:
        return {}
    p = periods[-1]
    rv = _toFloat(extractSeries(norm, "revenue", [p])[0]) or 0.0
    oi = _toFloat(extractSeries(norm, "operatingIncome", [p])[0]) or 0.0
    if rv <= 0 or oi <= 0:
        return {}
    baseMargin = oi / rv  # 0.xx
    revShifts = [("매출 -10%", -0.10), ("매출 0%", 0.0), ("매출 +10%", 0.10)]
    marginShifts = [("마진 -2pp", -0.02), ("마진 0", 0.0), ("마진 +2pp", 0.02)]
    cells: list[dict[str, Any]] = []
    for marginLabel, mShift in marginShifts:
        for revLabel, rShift in revShifts:
            newRev = rv * (1 + rShift)
            newMargin = baseMargin + mShift
            newOi = newRev * newMargin
            change = (newOi - oi) / oi * 100 if oi != 0 else 0.0
            cells.append(
                {
                    "row": marginLabel,
                    "col": revLabel,
                    "value": round(change, 1),
                    "unit": "%",
                }
            )
    return {
        "cells": cells,
        "rowOrder": [m for m, _ in marginShifts],
        "colOrder": [r for r, _ in revShifts],
        "tone": "diverging",
    }


def buildDistressDecomp(company: Any) -> dict[str, Any]:
    """Altman Z' 5 인자 분해 — distress gauge 의 "왜?" topList (P-DASH-V1 D13).

    각 인자 X1~X5 의 값 + 계수 가중 기여도 (점수에 얼마나 기여했는지).
    높은 절대 기여 인자가 분석 핵심.

    Returns:
        {items: [{label, value(인자값), unit, delta(가중 기여)}, ...]}
        기여도 절대값 내림차순 정렬.
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 4, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if not periods:
        return {}
    p = periods[-1]
    ca = _toFloat(extractSeries(norm, "currentAssets", [p])[0]) or 0.0
    cl = _toFloat(extractSeries(norm, "currentLiabilities", [p])[0]) or 0.0
    ta = _toFloat(extractSeries(norm, "assets", [p])[0]) or 0.0
    re = _toFloat(extractSeries(norm, "retainedEarnings", [p])[0]) or 0.0
    oi = _toFloat(extractSeries(norm, "operatingIncome", [p])[0]) or 0.0
    eq = _toFloat(extractSeries(norm, "equity", [p])[0]) or 0.0
    tl = _toFloat(extractSeries(norm, "liabilities", [p])[0]) or 0.0
    rv = _toFloat(extractSeries(norm, "revenue", [p])[0]) or 0.0
    if ta <= 0 or tl <= 0:
        return {}
    x1 = (ca - cl) / ta
    x2 = re / ta
    x3 = oi / ta
    x4 = eq / tl
    x5 = rv / ta
    factors = [
        ("X1 운전자본/자산", x1, 0.717),
        ("X2 잉여금/자산", x2, 0.847),
        ("X3 영업이익/자산", x3, 3.107),
        ("X4 자기자본/부채", x4, 0.420),
        ("X5 자산회전율", x5, 0.998),
    ]
    items = [
        {
            "label": label,
            "value": round(val, 3),
            "unit": "배",
            "delta": round(val * coef, 3),  # 가중 기여 (Z 에 대한)
            "description": f"× {coef} = {val * coef:.2f}",
        }
        for label, val, coef in factors
    ]
    items.sort(key=lambda x: abs(x.get("delta") or 0.0), reverse=True)
    return {"items": items, "direction": "desc"}


def buildBeneishGauge(company: Any) -> dict[str, Any]:
    """earningsQuality.calcBeneishMScore → gauge. -2.22 임계 (이상 = 위험)."""
    res = _safeCall("dartlab.analysis.financial.earningsQuality", "calcBeneishMScore", company)
    if not res:
        return {}
    score = _toFloat(_drill(res, "mScore") or _drill(res, "score") or _drill(res, "value"))
    if score is None:
        return {}
    return {
        "value": score,
        "minValue": -6.0,
        "maxValue": 1.0,
        "bands": [
            {"fromValue": -6.0, "toValue": -2.22, "label": "정상", "intent": "positive"},
            {"fromValue": -2.22, "toValue": 1.0, "label": "분식 의심", "intent": "negative"},
        ],
        "unit": "",
        "subtitle": "Beneish M-Score (> -2.22 분식 의심)",
    }


# ─────────────────────────────────────────────────────────────
# phaseIndicator — lifeCycle.calcLifeCycle.
# ─────────────────────────────────────────────────────────────

LIFE_CYCLE_PHASES = ["도입", "성장", "성숙Ⅰ", "성숙Ⅱ", "쇠퇴", "회복"]


def buildLifeCyclePhase(company: Any) -> dict[str, Any]:
    """CF 3축 부호 + 매출 성장률 + ROE 로 단계 추정 (Dickinson 모델 단순화).

    부호 패턴:
      CFO+ CFI- CFF+  → 도입 (성장 자금 확보)
      CFO+ CFI- CFF-  → 성장
      CFO+ CFI- CFF-  + 매출증가 둔화 → 성숙Ⅰ
      CFO+ CFI+ CFF-  → 성숙Ⅱ (자산 처분)
      CFO- CFI- CFF+  → 쇠퇴
      CFO+ CFI+ CFF+  → 회복 / 비정형
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 8, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if len(periods) < 2:
        return {}
    p = periods[-1]
    cfo = _toFloat(extractSeries(norm, "cfOperating", [p])[0])
    cfi = _toFloat(extractSeries(norm, "cfInvesting", [p])[0])
    cff = _toFloat(extractSeries(norm, "cfFinancing", [p])[0])
    if cfo is None or cfi is None or cff is None:
        return {}
    # 매출 성장률.
    rev_series = [_toFloat(v) for v in extractSeries(norm, "revenue", periods)]
    growth = None
    if len(rev_series) >= 2 and rev_series[-2] not in (None, 0):
        growth = (rev_series[-1] - rev_series[-2]) / abs(rev_series[-2]) * 100
    # 단계 결정.
    sgn = (1 if cfo > 0 else -1, 1 if cfi > 0 else -1, 1 if cff > 0 else -1)
    if sgn == (1, -1, 1):
        idx = 0  # 도입
    elif sgn == (1, -1, -1):
        idx = 1 if (growth is not None and growth >= 10) else 2  # 성장 / 성숙Ⅰ
    elif sgn == (1, 1, -1):
        idx = 3  # 성숙Ⅱ
    elif cfo < 0:
        idx = 4  # 쇠퇴
    else:
        idx = 5  # 회복
    # 신뢰도 — 부호 차원 명확도 (절대값 / 자산).
    ta = _toFloat(extractSeries(norm, "assets", [p])[0]) or 1.0
    magnitude = (abs(cfo) + abs(cfi) + abs(cff)) / (3 * abs(ta))
    confidence = min(1.0, magnitude * 4)
    sgn_str = ("+" if cfo > 0 else "-") + ("+" if cfi > 0 else "-") + ("+" if cff > 0 else "-")
    subtitle = f"CFO{sgn_str[0]} CFI{sgn_str[1]} CFF{sgn_str[2]}"
    if growth is not None:
        subtitle += f" · 매출 YoY {growth:+.1f}%"
    return {
        "phases": LIFE_CYCLE_PHASES,
        "current": idx,
        "confidence": confidence,
        "subtitle": subtitle,
    }


# ─────────────────────────────────────────────────────────────
# sankey — 자본배분 (CFO → CapEx + 배당 + 부채상환 + 잉여)
# ─────────────────────────────────────────────────────────────


def buildCashflowAllocationSankey(norm: Any, periods: list[str]) -> dict[str, Any]:
    """[DEPRECATED — P-DASH-V1 D6] norm 마지막 기간 CFO 분해 sankey.

    Sankey 는 자본배분 시각화 표준 아니다 (Wall Street Prep / Damodaran).
    대안: capitalAllocationBars (stacked over time) · capitalAllocationWaterfall (단년).
    본 함수는 backward-compat 용 — catalog 의 sankey 카드는 D6 에서 폐기됨.
    """
    if not periods:
        return {}
    last = periods[-1]
    cfo = extractSeries(norm, "cfOperating", [last])[0]
    capex_raw = extractSeries(norm, "capex", [last])[0]
    dividends_raw = extractSeries(norm, "dividendsPaid", [last])[0]
    cfo_v = _toFloat(cfo) or 0.0
    capex = abs(_toFloat(capex_raw) or 0.0)
    dividends = abs(_toFloat(dividends_raw) or 0.0)
    if cfo_v <= 0:
        return {}
    used = min(capex + dividends, cfo_v)
    surplus = max(cfo_v - used, 0.0)
    nodes = [{"name": "영업현금흐름"}, {"name": "설비투자"}, {"name": "배당"}, {"name": "잉여"}]
    links: list[dict[str, Any]] = []
    if capex > 0:
        links.append({"source": 0, "target": 1, "value": capex})
    if dividends > 0:
        links.append({"source": 0, "target": 2, "value": dividends})
    if surplus > 0:
        links.append({"source": 0, "target": 3, "value": surplus})
    if not links:
        return {}
    return {"nodes": nodes, "links": links}


# ─────────────────────────────────────────────────────────────
# 자본배분 — stacked bar over time + waterfall (sankey 대체).
# Wall Street Prep / Damodaran 정통 시각화.
# ─────────────────────────────────────────────────────────────


def buildCapitalAllocationBars(norm: Any, periods: list[str]) -> dict[str, Any]:
    """연도 × {CapEx · 배당 · 부채상환 · 잉여} stacked bar 시계열.

    Returns:
        {seriesPlan-like: [series with data list]}  builder 가 view.series 에 박음.

    Buckets:
        - capEx (음수→양수 변환, intent=negative): -capex
        - dividends (intent=accent): -dividendsPaid
        - debtRepay (intent=negative): -cfFinancing 중 부채 부분 (근사)
        - surplus (intent=positive): max(cfOperating - 사용처, 0)

    데이터 부족 시 빈 dict.
    """
    if not periods or len(periods) < 2:
        return {}

    capexSeries: list[float | None] = []
    divSeries: list[float | None] = []
    debtRepaySeries: list[float | None] = []
    surplusSeries: list[float | None] = []

    cfoVals = extractSeries(norm, "cfOperating", periods)
    capexVals = extractSeries(norm, "capex", periods)
    divVals = extractSeries(norm, "dividendsPaid", periods)
    cffVals = extractSeries(norm, "cfFinancing", periods)

    for i in range(len(periods)):
        cfo = _toFloat(cfoVals[i]) or 0.0
        capex = abs(_toFloat(capexVals[i]) or 0.0)
        div = abs(_toFloat(divVals[i]) or 0.0)
        cff = _toFloat(cffVals[i]) or 0.0
        # 부채상환 = 음수 재무CF − 배당 (배당도 재무CF 음수에 포함되어있을 가능성).
        debtRepay = max(-cff - div, 0.0) if cff < 0 else 0.0
        used = capex + div + debtRepay
        surplus = max(cfo - used, 0.0)
        capexSeries.append(capex if capex > 0 else None)
        divSeries.append(div if div > 0 else None)
        debtRepaySeries.append(debtRepay if debtRepay > 0 else None)
        surplusSeries.append(surplus if surplus > 0 else None)

    # 모든 시리즈가 None 일 가능성 — 데이터 0.
    nonNone = sum(1 for s in (capexSeries, divSeries, debtRepaySeries, surplusSeries) for v in s if v is not None)
    if nonNone == 0:
        return {}

    # ChartContainer + Bar stack 으로 그릴 series list 반환.
    # finance.py 의 색 코드 (COLORS) 직접 import 회피 — render 가 palette 적용.
    return {
        "series": [
            {
                "key": "capex",
                "label": "설비투자",
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "alloc",
                "data": capexSeries,
            },
            {
                "key": "dividends",
                "label": "배당",
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "alloc",
                "data": divSeries,
            },
            {
                "key": "debtRepay",
                "label": "부채상환",
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "alloc",
                "data": debtRepaySeries,
            },
            {
                "key": "surplus",
                "label": "잉여",
                "intent": "positive",
                "unit": "원",
                "type": "bar",
                "stack": "alloc",
                "data": surplusSeries,
            },
        ],
    }


def buildCapitalAllocationWaterfall(norm: Any, periods: list[str]) -> dict[str, Any]:
    """단년 자본배분 waterfall — 영업CF → -CapEx → -배당 → -부채상환 → ΔCash.

    Returns 마지막 기간 분해. 데이터 부족 시 빈 dict.

    series 1 개 — recharts BarChart 가 measure 메타로 absolute/relative 분리.
    """
    if not periods:
        return {}
    last = periods[-1]
    cfo = _toFloat(extractSeries(norm, "cfOperating", [last])[0]) or 0.0
    capex = abs(_toFloat(extractSeries(norm, "capex", [last])[0]) or 0.0)
    div = abs(_toFloat(extractSeries(norm, "dividendsPaid", [last])[0]) or 0.0)
    cff = _toFloat(extractSeries(norm, "cfFinancing", [last])[0]) or 0.0
    debtRepay = max(-cff - div, 0.0) if cff < 0 else 0.0
    surplus = cfo - capex - div - debtRepay

    if cfo <= 0:
        return {}

    # categories + points (measure 메타).
    categories = ["영업CF", "-설비투자", "-배당", "-부채상환", "잉여"]
    points = [
        {"value": cfo, "measure": "absolute"},
        {"value": -capex if capex > 0 else 0.0, "measure": "relative"},
        {"value": -div if div > 0 else 0.0, "measure": "relative"},
        {"value": -debtRepay if debtRepay > 0 else 0.0, "measure": "relative"},
        {"value": surplus, "measure": "total"},
    ]
    return {
        "categories": categories,
        "series": [
            {
                "key": "waterfall",
                "label": "자본배분 waterfall",
                "unit": "원",
                "type": "bar",
                "points": points,
                "data": [p["value"] for p in points],
            }
        ],
    }


# ─────────────────────────────────────────────────────────────
# scatter — peerBenchmark 4사분면.
# ─────────────────────────────────────────────────────────────


def buildPeerScatter(company: Any) -> dict[str, Any]:
    """norm 으로 회사의 최근 8 기간 (ROE, 부채비율) 점들 + 최근값 self 표시.

    동종 데이터 wiring 은 후속 (peerBenchmark). 현재는 회사 자체 시간축 산점도.
    각 기간이 하나의 점, 최근 기간이 self (별표).
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 12, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if len(periods) < 2:
        return {}
    points: list[dict[str, Any]] = []
    for p in periods:
        ni = _toFloat(extractSeries(norm, "netIncome", [p])[0])
        eq = _toFloat(extractSeries(norm, "equity", [p])[0])
        tl = _toFloat(extractSeries(norm, "liabilities", [p])[0])
        if ni is None or eq is None or tl is None or eq <= 0:
            continue
        roe = ni / eq * 100
        de = tl / eq * 100
        points.append({"x": roe, "y": de, "label": p, "self": p == periods[-1]})
    if not points:
        return {}
    # 참조선 = 시계열 중앙값.
    sorted_x = sorted(p["x"] for p in points)
    sorted_y = sorted(p["y"] for p in points)
    median_x = sorted_x[len(sorted_x) // 2]
    median_y = sorted_y[len(sorted_y) // 2]
    return {
        "points": points,
        "xLabel": "ROE",
        "yLabel": "부채비율",
        "xUnit": "%",
        "yUnit": "%",
        "xRef": round(median_x, 2),
        "yRef": round(median_y, 2),
    }


def buildPeerComparison(company: Any) -> dict[str, Any]:
    """norm 의 최근값 vs 회사 자체 5년 중앙값 (peer median 자리 대체).

    동종 wiring 후속. 현재는 회사 시계열의 분포 (자신과 자기 중앙값 비교).
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 12, "annual")
    except Exception:  # noqa: BLE001
        return {}
    if len(periods) < 3:
        return {}

    def _series(numTerms, denTerms, scale):
        out = []
        for p in periods:
            n = _sumWeighted(norm, numTerms, [p])[0] if numTerms else None
            d = _sumWeighted(norm, denTerms, [p])[0] if denTerms else None
            if n is None or d is None or d == 0:
                out.append(None)
            else:
                out.append(n / d * scale)
        return out

    def _percentile(vals: list[float], v: float) -> float:
        sorted_v = sorted(vals)
        if not sorted_v:
            return 50.0
        below = sum(1 for x in sorted_v if x < v)
        return round(below / len(sorted_v) * 100, 1)

    metrics = [
        ("매출총이익률", {"grossProfit": 1}, {"revenue": 1}, 100, "%", True),
        ("영업이익률", {"operatingIncome": 1}, {"revenue": 1}, 100, "%", True),
        ("ROE", {"netIncome": 1}, {"equity": 1}, 100, "%", True),
        ("ROA", {"netIncome": 1}, {"assets": 1}, 100, "%", True),
        ("부채비율", {"liabilities": 1}, {"equity": 1}, 100, "%", False),
        ("유동비율", {"currentAssets": 1}, {"currentLiabilities": 1}, 100, "%", True),
        ("자산회전율", {"revenue": 1}, {"assets": 1}, 1, "회", True),
        ("영업CF/매출", {"cfOperating": 1}, {"revenue": 1}, 100, "%", True),
    ]
    rows: list[dict[str, Any]] = []
    for label, num, den, scale, unit, higher in metrics:
        series = _series(num, den, scale)
        non_null = [v for v in series if v is not None]
        if len(non_null) < 2:
            continue
        latest = series[-1]
        if latest is None:
            continue
        sorted_v = sorted(non_null)
        median = sorted_v[len(sorted_v) // 2]
        p25 = sorted_v[len(sorted_v) // 4]
        p75 = sorted_v[(3 * len(sorted_v)) // 4]
        pct = _percentile(non_null, latest) if higher else (100 - _percentile(non_null, latest))
        rows.append(
            {
                "label": label,
                "self": round(latest, 2),
                "peerMedian": round(median, 2),
                "peerP25": round(p25, 2),
                "peerP75": round(p75, 2),
                "percentile": pct,
                "unit": unit,
                "higherIsBetter": higher,
            }
        )
    if not rows:
        return {}
    return {"rows": rows, "peerCount": len(periods)}


def buildAnomalyTopList(company: Any) -> list[dict[str, Any]]:
    """전년 대비 변동 큰 지표 top 5 — 변동 절대값 기준 정렬.

    경고성 (large change) + 정상 (small change) 모두 표시. 임계 기반 hard cut 폐기.
    """
    try:
        norm = normalize.normalize(company.rawFinance)
        from dartlab.viz.display.finance.periods import lastNPeriods

        periods = lastNPeriods(norm, 4, "annual")
    except Exception:  # noqa: BLE001
        return []
    if len(periods) < 2:
        return []

    def _ratio(num: dict, den: dict, p: str) -> float | None:
        n = _sumWeighted(norm, num, [p])[0]
        d = _sumWeighted(norm, den, [p])[0]
        if n is None or d is None or d == 0:
            return None
        return n / d

    last = periods[-1]
    prev = periods[-2]
    metrics = [
        ("DSO (매출채권 회수일수)", {"receivables": 365}, {"revenue": 1}, "일"),
        ("DIO (재고자산 회수일수)", {"inventories": 365}, {"costOfSales": 1}, "일"),
        ("매출원가율", {"costOfSales": 1}, {"revenue": 1}, "%"),
        ("판관비율", {"sga": 1}, {"revenue": 1}, "%"),
        ("영업CF/순이익", {"cfOperating": 1}, {"netIncome": 1}, "%"),
        ("부채자본비율", {"liabilities": 1}, {"equity": 1}, "%"),
        ("유동비율", {"currentAssets": 1}, {"currentLiabilities": 1}, "%"),
        ("재고/자산", {"inventories": 1}, {"assets": 1}, "%"),
    ]
    items: list[dict[str, Any]] = []
    for label, num, den, unit in metrics:
        l = _ratio(num, den, last)
        p = _ratio(num, den, prev)
        if l is None or p is None or p == 0:
            continue
        delta_pct = (l - p) / abs(p) * 100
        scale = 1 if unit == "일" else 100
        l_disp = l * scale
        p_disp = p * scale
        items.append(
            {
                "label": label,
                "value": round(l_disp, 1),
                "unit": unit,
                "delta": round(delta_pct, 1),
                "description": f"{p_disp:.1f} → {l_disp:.1f} {unit} ({delta_pct:+.1f}% YoY)",
                "_abs_delta": abs(delta_pct),
            }
        )
    # 변동 절대값 기준 top 5.
    items.sort(key=lambda x: x.pop("_abs_delta", 0), reverse=True)
    return items[:6]


_ACT_LABELS = ["1막 사업", "2막 수익", "3막 현금", "4막 안정", "5막 배분", "6막 미래"]


def buildNarrativeBridge(company: Any) -> dict[str, Any]:
    """Story view 6 막 전환 자연어 — `story.narrative.buildActTransitions` 5 줄 + 종합 1 줄.

    Returns:
        {transitions: [{from, to, text}, ...], summaryLine: str}.
        engine 호출 실패하면 빈 transitions 반환 (renderer 가 placeholder 표시).
    """
    transitions: list[dict[str, str]] = []
    summary = ""
    try:
        from dartlab.story import narrative as _narr

        blockMap = getattr(company, "_blockMap", None) or {}
        tdict = _narr.buildActTransitions(company, blockMap) or {}
        for i in range(1, 6):
            key = f"{i}→{i + 1}"
            text = tdict.get(key, "")
            if not text:
                continue
            transitions.append(
                {
                    "from": _ACT_LABELS[i - 1],
                    "to": _ACT_LABELS[i],
                    "text": text,
                }
            )
        try:
            threads = _narr.detectThreads(company, blockMap) or []
            summary = _narr.buildCirculationSummary(threads) or ""
        except (AttributeError, ValueError, TypeError):
            summary = ""
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return {"transitions": transitions, "summaryLine": summary}


def buildSnowflakeRadar(company: Any) -> dict[str, Any]:
    """Snowflake 5 차원 radar — Value/Future/Past/Health/Dividend 0~5 점.

    `analysis.financial.intrinsic.calcSnowflake5Score` 호출. 점수 dict →
    radar categories + 단일 polygon series.
    """
    try:
        from dartlab.analysis.financial import intrinsic as _intr

        scores = _intr.calcSnowflake5Score(company) or {}
    except (ImportError, AttributeError, ValueError, TypeError):
        scores = {}
    dims = ["value", "future", "past", "health", "dividend"]
    labels = {"value": "Value", "future": "Future", "past": "Past", "health": "Health", "dividend": "Dividend"}
    categories = [labels[d] for d in dims]
    data = [float(scores.get(d, 0) or 0) for d in dims]
    return {
        "categories": categories,
        "series": [
            {
                "key": "snowflake",
                "label": "Snowflake 5",
                "data": data,
                "unit": "점",
                "intent": "primary",
                "type": "line",
            }
        ],
    }


_GRADE_BUCKETS = [
    (90, "A+"),
    (80, "A"),
    (70, "B+"),
    (60, "B"),
    (50, "C+"),
    (40, "C"),
    (0, "D"),
]


def buildSnowflakeAlert(company: Any) -> dict[str, Any]:
    """Snowflake alert — 회계 기반 측정 한계 안내 1 줄.

    radar / scoreBadge 가 시장가 의존 metric 폐기 후 회계 대체임을 운영자에게 노출.
    """
    return {
        "transitions": [
            {
                "from": "측정 한계",
                "to": "회계 기반",
                "text": (
                    "시장가 의존 metric (PER/PBR/배당수익률) → 회계 대체로 정규화. "
                    "Owner Earnings Yield · 매출 CAGR3y · ROE+ROA+ROIC · Piotroski F-Score · 배당성향+RE 누적."
                ),
            },
            {
                "from": "정통 Simply Wall St",
                "to": "dartlab 회계 기반",
                "text": (
                    "Simply Wall St 의 시가총액 의존 5 차원과는 점수 분포 다름. "
                    "회계 정보만으로 가치/성장/안전 평가."
                ),
            },
        ],
        "summaryLine": "회계 기반 5 차원 — 시장가 부재 환경의 합성 평점",
    }


def buildSnowflakeKpi(company: Any, tilePlans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Snowflake 단일 차원 KPI — tilePlan.dim 별 0~5 점.

    intrinsic.calcSnowflake5Score 한 번 호출 + 각 tilePlan 의 dim 값 추출.
    """
    try:
        from dartlab.analysis.financial import intrinsic as _intr

        scores = _intr.calcSnowflake5Score(company) or {}
    except (ImportError, AttributeError, ValueError, TypeError):
        scores = {}
    tiles: list[dict[str, Any]] = []
    for plan in tilePlans or []:
        dim = plan.get("dim", "")
        val = scores.get(dim)
        if isinstance(val, (int, float)):
            value: float | None = float(val)
        else:
            value = None
        tiles.append(
            {
                "label": plan.get("label", dim),
                "value": value,
                "prev": None,
                "unit": plan.get("unit", "점"),
                "intent": plan.get("intent", "primary"),
                "sparkline": [],
            }
        )
    return tiles


def buildScoreBadge(company: Any) -> dict[str, Any]:
    """Snowflake 종합 평점 카드 — 5 차원 점수 × 20 평균 → grade + 한 줄 서사."""
    try:
        from dartlab.analysis.financial import intrinsic as _intr

        scores = _intr.calcSnowflake5Score(company) or {}
    except (ImportError, AttributeError, ValueError, TypeError):
        scores = {}
    dims = [
        ("value", "Value"),
        ("future", "Future"),
        ("past", "Past"),
        ("health", "Health"),
        ("dividend", "Dividend"),
    ]
    dimList = [{"key": k, "label": label, "score": float(scores.get(k, 0) or 0)} for k, label in dims]
    vals = [d["score"] for d in dimList if isinstance(d["score"], (int, float))]
    if vals:
        overall = sum(vals) / len(vals) * 20.0
    else:
        overall = 0.0
    grade = "D"
    for cut, g in _GRADE_BUCKETS:
        if overall >= cut:
            grade = g
            break
    parts = " · ".join(f"{d['label']} {d['score']:.1f}/5" for d in dimList)
    summaryLine = f"{parts} — 종합 {overall:.0f}점 ({grade})"
    return {
        "grade": grade,
        "overallScore": round(overall, 1),
        "dimensions": dimList,
        "summaryLine": summaryLine,
    }


# ─────────────────────────────────────────────────────────────
# 정통 깊이 강화 adapter 6 (2026-05-19) — analysis 엔진 시계열 wrapping.
# Penman ROE 분해 / ROIC-WACC spread / 세그먼트 매출 / 세그먼트 집중도 /
# Operating Leverage·Breakeven / Distress 5 모델 ensemble.
# ─────────────────────────────────────────────────────────────


def buildPenmanRoeBars(company: Any) -> dict[str, Any]:
    """calcPenmanDecomposition → RNOA + LeverageEffect stacked + ROCE line.

    ROCE = RNOA + FLEV × SPREAD. RNOA 가 영업 동력, leverageEffect (= FLEV × SPREAD)
    가 부채 효과. 두 stack 합산이 ROCE.
    """
    res = _safeCall("dartlab.analysis.financial._profitabilityDeep", "calcPenmanDecomposition", company)
    history = _drill(res, "history") if isinstance(res, dict) else None
    if not isinstance(history, list) or len(history) < 1:
        return {}
    periods: list[str] = []
    rnoa: list[float | None] = []
    levEffect: list[float | None] = []
    roce: list[float | None] = []
    for row in history:
        if not isinstance(row, dict):
            continue
        periods.append(str(row.get("period", "")))
        rnoa.append(_toFloat(row.get("rnoa")))
        levEffect.append(_toFloat(row.get("leverageEffect")))
        roce.append(_toFloat(row.get("roce")))
    if not periods:
        return {}
    return {
        "categories": periods,
        "series": [
            {
                "key": "rnoa",
                "label": "영업력 (RNOA)",
                "color": "var(--chart-2)",
                "intent": "primary",
                "unit": "%",
                "type": "bar",
                "stack": "roce",
                "data": rnoa,
            },
            {
                "key": "leverageEffect",
                "label": "레버리지 효과",
                "color": "var(--chart-4)",
                "intent": "accent",
                "unit": "%",
                "type": "bar",
                "stack": "roce",
                "data": levEffect,
            },
            {
                "key": "roce",
                "label": "ROCE 합산",
                "color": "var(--chart-1)",
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "data": roce,
            },
        ],
    }


def buildRoicWaccGap(company: Any) -> dict[str, Any]:
    """calcRoicTimeline → ROIC line + WACC 8% 가정 + spread bar (양수 가치창출 / 음수 자본파괴).

    spread = ROIC − WACC. WACC 단순 가정 (Damodaran 한국 평균 7~9% → 8%). 정밀 WACC
    필요 시 후속 PR (CAPM β·rf·equity risk premium 산출).
    """
    res = _safeCall("dartlab.analysis.financial._investmentAnalysisRoic", "calcRoicTimeline", company)
    history = _drill(res, "history") if isinstance(res, dict) else None
    if not isinstance(history, list) or len(history) < 1:
        return {}
    WACC = 8.0
    periods: list[str] = []
    roicList: list[float | None] = []
    waccList: list[float | None] = []
    spreadList: list[float | None] = []
    for row in history:
        if not isinstance(row, dict):
            continue
        period = row.get("period")
        if period is None:
            continue
        periods.append(str(period))
        roic = _toFloat(row.get("roic"))
        roicList.append(roic)
        waccList.append(WACC)
        spreadList.append(roic - WACC if roic is not None else None)
    if not periods:
        return {}
    return {
        "categories": periods,
        "series": [
            {
                "key": "roic",
                "label": "ROIC",
                "color": "var(--chart-1)",
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "data": roicList,
            },
            {
                "key": "wacc",
                "label": "WACC (≈8%)",
                "color": "var(--chart-4)",
                "intent": "neutral",
                "unit": "%",
                "type": "line",
                "data": waccList,
            },
            {
                "key": "spread",
                "label": "Spread (ROIC−WACC)",
                "color": "var(--chart-5)",
                "intent": "positive",
                "unit": "%p",
                "type": "bar",
                "data": spreadList,
            },
        ],
    }


def buildSegmentBreakdown(company: Any) -> dict[str, Any]:
    """calcSegmentTrend → 부문별 매출 stacked bar.

    top 6 부문만 (`_MAX_SEGMENTS` 정통). 영업이익률 별도 색 라인은 부문 ×
    line 폭증 — 매출 stack 만 노출하고 영업이익률 추세는 별도 카드.
    """
    res = _safeCall("dartlab.analysis.financial._revenueSegment", "calcSegmentTrend", company)
    if not isinstance(res, dict):
        return {}
    yearCols = res.get("yearCols") or []
    rows = res.get("rows") or []
    if not yearCols or not rows:
        return {}
    # period 역순 정렬 (yearCols 가 최신→과거 라 시각화는 과거→최신)
    periods = list(reversed(yearCols))
    palette = [f"var(--chart-{i})" for i in (2, 3, 5, 6, 7, 8)]
    series: list[dict[str, Any]] = []
    for idx, row in enumerate(rows[:6]):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or f"부문 {idx + 1}")
        values = row.get("values") or {}
        data = [_toFloat(values.get(p)) for p in periods]
        if all(v is None for v in data):
            continue
        series.append(
            {
                "key": f"seg{idx}",
                "label": name,
                "color": palette[idx % len(palette)],
                "intent": "primary" if idx == 0 else "accent",
                "unit": "원",
                "type": "bar",
                "stack": "segment",
                "data": data,
            }
        )
    if not series:
        return {}
    return {"categories": periods, "series": series}


def buildSegmentConcentration(company: Any) -> dict[str, Any]:
    """calcConcentration → HHI 시계열 line + 최대 부문 비중 line.

    HHI > 5000 = 고집중 (단일 사업 위험). topPct = 최대 부문 매출 비중.
    """
    res = _safeCall("dartlab.analysis.financial._revenueGrowth", "calcConcentration", company)
    if not isinstance(res, dict):
        return {}
    hhiHistory = res.get("hhiHistory") or []
    if not isinstance(hhiHistory, list) or len(hhiHistory) < 1:
        # fallback — 단일 시점만 있을 때
        hhi = _toFloat(res.get("hhi"))
        topPct = _toFloat(res.get("topPct"))
        if hhi is None and topPct is None:
            return {}
        return {
            "categories": ["최신"],
            "series": [
                {"key": "hhi", "label": "HHI 집중도", "color": "var(--chart-3)", "intent": "negative",
                 "unit": "", "type": "line", "data": [hhi]},
                {"key": "topPct", "label": "1위 부문 비중", "color": "var(--chart-2)", "intent": "accent",
                 "unit": "%", "type": "line", "axis": "right", "data": [topPct]},
            ],
        }
    periods: list[str] = []
    hhiList: list[float | None] = []
    topList: list[float | None] = []
    for row in hhiHistory:
        if not isinstance(row, dict):
            continue
        periods.append(str(row.get("period", "")))
        hhiList.append(_toFloat(row.get("hhi")))
        topList.append(_toFloat(row.get("topPct")))
    if not periods:
        return {}
    return {
        "categories": periods,
        "series": [
            {
                "key": "hhi",
                "label": "HHI 집중도",
                "color": "var(--chart-3)",
                "intent": "negative",
                "unit": "",
                "type": "line",
                "data": hhiList,
            },
            {
                "key": "topPct",
                "label": "1위 부문 비중",
                "color": "var(--chart-2)",
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "axis": "right",
                "data": topList,
            },
        ],
    }


def buildDolBreakeven(company: Any) -> dict[str, Any]:
    """calcOperatingLeverage + calcBreakevenEstimate → DOL bar + 안전마진 line.

    DOL (영업레버리지) 클수록 매출 변동에 영업이익 민감. 안전마진 = (매출 − BEP)/매출 ×100.
    """
    dol_res = _safeCall("dartlab.analysis.financial.costStructure", "calcOperatingLeverage", company)
    bep_res = _safeCall("dartlab.analysis.financial.costStructure", "calcBreakevenEstimate", company)
    dolHistory = _drill(dol_res, "history") if isinstance(dol_res, dict) else None
    bepHistory = _drill(bep_res, "history") if isinstance(bep_res, dict) else None
    if not isinstance(dolHistory, list):
        dolHistory = []
    if not isinstance(bepHistory, list):
        bepHistory = []
    if not dolHistory and not bepHistory:
        return {}
    periodSet: list[str] = []
    seen: set[str] = set()
    for row in dolHistory:
        if isinstance(row, dict):
            p = str(row.get("period", ""))
            if p and p not in seen:
                periodSet.append(p)
                seen.add(p)
    for row in bepHistory:
        if isinstance(row, dict):
            p = str(row.get("period", ""))
            if p and p not in seen:
                periodSet.append(p)
                seen.add(p)
    if not periodSet:
        return {}
    # 과거 → 최신 (정통 분석 시각화 방향)
    periods = sorted(periodSet)
    dolLookup = {str(row.get("period", "")): _toFloat(row.get("dol")) for row in dolHistory if isinstance(row, dict)}
    safetyLookup = {
        str(row.get("period", "")): _toFloat(row.get("marginOfSafety")) for row in bepHistory if isinstance(row, dict)
    }
    return {
        "categories": periods,
        "series": [
            {
                "key": "dol",
                "label": "영업레버리지 (DOL)",
                "color": "var(--chart-2)",
                "intent": "accent",
                "unit": "배",
                "type": "bar",
                "data": [dolLookup.get(p) for p in periods],
            },
            {
                "key": "marginOfSafety",
                "label": "안전마진",
                "color": "var(--chart-5)",
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "axis": "right",
                "data": [safetyLookup.get(p) for p in periods],
            },
        ],
    }


def buildDistressEnsembleGauge(company: Any) -> dict[str, Any]:
    """calcDistressEnsemble → 5 모델 (Altman Z·Z''·Ohlson·Springate·Zmijewski) 다수결 gauge.

    agreement (다수파 일치도, %) 를 gauge value 로. ensemble label ("안전"|"주의"|"위험")
    + 모델별 verdict 카운트는 subtitle.
    """
    res = _safeCall("dartlab.analysis.financial._stabilityDistress", "calcDistressEnsemble", company)
    if not isinstance(res, dict):
        return {}
    agreement = _toFloat(res.get("agreement"))
    ensemble = res.get("ensemble") or ""
    safeCount = res.get("safeCount") or 0
    dangerCount = res.get("dangerCount") or 0
    total = res.get("total") or 0
    if agreement is None or not total:
        return {}
    # ensemble label 별 invert: "안전" 이면 agreement 높을수록 좋음, "위험" 이면 agreement 높을수록 나쁨.
    # gauge value = 안전 확신도 (safeCount/total × 100). 0~100 단순.
    safetyScore = safeCount / total * 100 if total > 0 else None
    if safetyScore is None:
        return {}
    return {
        "value": round(safetyScore, 1),
        "minValue": 0.0,
        "maxValue": 100.0,
        "bands": [
            {"fromValue": 0.0, "toValue": 30.0, "label": "위험", "intent": "negative"},
            {"fromValue": 30.0, "toValue": 60.0, "label": "주의", "intent": "accent"},
            {"fromValue": 60.0, "toValue": 100.0, "label": "안전", "intent": "positive"},
        ],
        "unit": "%",
        "subtitle": f"5 모델 다수결 — {ensemble} · 안전 {safeCount}/{total} · 위험 {dangerCount}/{total} · 일치도 {agreement:.0f}%",
    }


__all__ = [
    "LIFE_CYCLE_PHASES",
    "buildBeneishGauge",
    "buildCapitalAllocationBars",
    "buildCapitalAllocationWaterfall",
    "buildCashflowAllocationSankey",
    "buildDistressDecomp",
    "buildDistressEnsembleGauge",
    "buildDistressGauge",
    "buildDolBreakeven",
    "buildKpiTilesFromNorm",
    "buildLifeCyclePhase",
    "buildNarrativeBridge",
    "buildPeerComparison",
    "buildPeerScatter",
    "buildPenmanRoeBars",
    "buildRoicWaccGap",
    "buildScenarioSensitivity",
    "buildScoreBadge",
    "buildSegmentBreakdown",
    "buildSegmentConcentration",
    "buildSnowflakeAlert",
    "buildSnowflakeKpi",
    "buildSnowflakeRadar",
    "buildTopListFromFlags",
    # quant 탭 adapter 7 개 (가격·기술·모멘텀·변동성·베타·예측·placeholder).
    "buildQuantPriceTrend",
    "buildQuantVerdictKpi",
    "buildQuantMomentumKpi",
    "buildQuantVolatilityKpi",
    "buildQuantBetaKpi",
    "buildQuantForecastKpi",
    "buildQuantComingSoon",
]


# ─────────────────────────────────────────────────────────────
# quant 탭 어댑터 — dartlab.quant 엔진 axis 산출물 → KPI tile / trend.
# stockCode 직접 받음 (company.rawFinance 와 무관, 가격 데이터 자체 fetch).
# 실패 (network · 데이터 부족) 시 빈 spec → frontend 에서 "데이터 없음" 표시.
# ─────────────────────────────────────────────────────────────


def _safeQuantCall(modulePath: str, fnName: str, stockCode: str, **kwargs: Any) -> Any:
    """quant 모듈 함수 안전 호출. import / 실행 실패 → None."""
    try:
        mod = importlib.import_module(modulePath)
    except ImportError:
        return None
    fn = getattr(mod, fnName, None)
    if fn is None:
        return None
    try:
        return fn(stockCode, **kwargs)
    except Exception:  # noqa: BLE001
        return None


def buildQuantPriceTrend(stockCode: str) -> dict[str, Any]:
    """최근 1 년 종가 + 거래량 + SMA(20)/SMA(60) overlay trend spec.

    gather 자동 fetch (Naver/Yahoo). 데이터 부족 시 빈 series.
    """
    from datetime import date, timedelta

    start = (date.today() - timedelta(days=400)).isoformat()
    try:
        from dartlab.quant.signal.momentum import fetchOhlcv  # type: ignore[import-untyped]
    except ImportError:
        return {"categories": [], "series": []}
    try:
        ohlcv = fetchOhlcv(stockCode, start=start)
    except Exception:  # noqa: BLE001
        return {"categories": [], "series": []}

    if ohlcv is None:
        return {"categories": [], "series": []}
    try:
        rows = ohlcv.to_dicts() if hasattr(ohlcv, "to_dicts") else list(ohlcv)
    except Exception:  # noqa: BLE001
        return {"categories": [], "series": []}
    if not rows:
        return {"categories": [], "series": []}
    # 최근 252 거래일만 (1 년).
    rows = rows[-252:]
    categories: list[str] = []
    closes: list[float | None] = []
    volumes: list[float | None] = []
    for r in rows:
        d = r.get("date") or r.get("Date")
        c = r.get("close") or r.get("Close")
        v = r.get("volume") or r.get("Volume")
        categories.append(str(d) if d is not None else "")
        closes.append(_toFloat(c))
        volumes.append(_toFloat(v))
    # SMA overlay.
    def _sma(arr: list[float | None], window: int) -> list[float | None]:
        out: list[float | None] = []
        buf: list[float] = []
        for v in arr:
            if v is not None:
                buf.append(v)
                if len(buf) > window:
                    buf.pop(0)
                out.append(sum(buf) / len(buf) if len(buf) == window else None)
            else:
                out.append(None)
        return out

    sma20 = _sma(closes, 20)
    sma60 = _sma(closes, 60)
    return {
        "categories": categories,
        "series": [
            {
                "key": "close",
                "label": "종가",
                "color": "#2563eb",
                "intent": "primary",
                "unit": "원",
                "type": "line",
                "axis": "left",
                "data": closes,
            },
            {
                "key": "sma20",
                "label": "SMA(20)",
                "color": "#10b981",
                "intent": "accent",
                "unit": "원",
                "type": "line",
                "axis": "left",
                "data": sma20,
            },
            {
                "key": "sma60",
                "label": "SMA(60)",
                "color": "#f59e0b",
                "intent": "accent",
                "unit": "원",
                "type": "line",
                "axis": "left",
                "data": sma60,
            },
            {
                "key": "volume",
                "label": "거래량",
                "color": "#94a3b8",
                "intent": "neutral",
                "unit": "주",
                "type": "bar",
                "axis": "right",
                "data": volumes,
            },
        ],
    }


def _kpiTile(label: str, value: Any, *, unit: str = "", intent: str = "primary", subtitle: str = "") -> dict[str, Any]:
    """간이 KpiTile dict 생성."""
    return {
        "label": label,
        "value": _toFloat(value),
        "prev": None,
        "unit": unit,
        "intent": intent,
        "subtitle": subtitle,
    }


def buildQuantVerdictKpi(stockCode: str) -> dict[str, Any]:
    """quant.verdict → 6 tile KPI (점수·판정·RSI·ADX·BB위치·SMA 돌파)."""
    result = _safeQuantCall("dartlab.quant.screen.axTechnical", "calcVerdict", stockCode)
    if result is None or not isinstance(result, dict) or result.get("error"):
        return {"tiles": []}
    verdict = str(result.get("verdict", "—"))
    intentByVerdict = {
        "강세": "positive",
        "중립": "neutral",
        "약세": "negative",
    }
    score = result.get("score")
    rsi = result.get("rsi")
    adx = result.get("adx")
    bb = result.get("bbPosition")
    aboveSma20 = result.get("aboveSma20")
    aboveSma60 = result.get("aboveSma60")
    tiles = [
        _kpiTile("판단", score, unit="점", intent=intentByVerdict.get(verdict, "neutral"), subtitle=verdict),
        _kpiTile("RSI(14)", rsi, unit="%", intent="primary", subtitle="과매수 70+ / 과매도 30-"),
        _kpiTile("ADX", adx, unit="%", intent="primary", subtitle="추세 강도 25+ 강함"),
        _kpiTile("BB 위치", bb, unit="%", intent="neutral", subtitle="0=하단 100=상단"),
        _kpiTile(
            "SMA20 돌파",
            1.0 if aboveSma20 else 0.0,
            unit="",
            intent="positive" if aboveSma20 else "negative",
            subtitle="단기 추세",
        ),
        _kpiTile(
            "SMA60 돌파",
            1.0 if aboveSma60 else 0.0,
            unit="",
            intent="positive" if aboveSma60 else "negative",
            subtitle="중기 추세",
        ),
    ]
    return {"tiles": tiles}


def buildQuantMomentumKpi(stockCode: str) -> dict[str, Any]:
    """quant.momentum → 4 tile KPI (12-1m or 6-1m · TS 1m · 52w high · streak).

    데이터 252 일 미만일 때 momentum12_1=None → 6-1m fallback. crashRisk 는
    문자열 ("low"/"high") · streak/streakDirection 가 추가 정보.
    """
    result = _safeQuantCall("dartlab.quant.signal.momentum", "calcMomentum", stockCode)
    if result is None or not isinstance(result, dict) or result.get("error"):
        return {"tiles": []}
    mom12_1 = result.get("momentum12_1")
    mom6_1 = result.get("momentum6_1")
    # momentum12_1 우선, None 이면 6-1 fallback.
    momPrimary = mom12_1 if mom12_1 is not None else mom6_1
    momLabel = "12-1m 모멘텀" if mom12_1 is not None else "6-1m 모멘텀 (fallback)"
    ts1m = _drill(result, "tsMomentum.1m.return")
    ts1mSignal = str(_drill(result, "tsMomentum.1m.signal") or "—")
    high52 = result.get("highRatio52w")
    streak = result.get("streak")
    streakDir = str(result.get("streakDirection") or "")
    verdict = str(result.get("momentumVerdict") or "—")
    intentByVerdict = {
        "strong_bullish": "positive",
        "bullish": "positive",
        "neutral": "neutral",
        "bearish": "negative",
        "strong_bearish": "negative",
    }
    intentMom = intentByVerdict.get(verdict, "primary")
    tiles = [
        _kpiTile(
            momLabel,
            momPrimary * 100 if isinstance(momPrimary, (int, float)) else momPrimary,
            unit="%",
            intent=intentMom,
            subtitle=f"verdict={verdict}",
        ),
        _kpiTile(
            "1m 수익률 (TS)",
            ts1m * 100 if isinstance(ts1m, (int, float)) else ts1m,
            unit="%",
            intent="primary",
            subtitle=f"signal={ts1mSignal}",
        ),
        _kpiTile(
            "52주 신고가 비율",
            high52 * 100 if isinstance(high52, (int, float)) else high52,
            unit="%",
            intent="primary",
            subtitle="95%+ 강한 추세 (George-Hwang)",
        ),
        _kpiTile(
            f"연속 {streakDir or '추세'}",
            streak,
            unit="일",
            intent="positive" if streakDir == "상승" else ("negative" if streakDir == "하락" else "neutral"),
            subtitle="동일 방향 연속 일수",
        ),
    ]
    return {"tiles": tiles}


def buildQuantVolatilityKpi(stockCode: str) -> dict[str, Any]:
    """quant.volatility → 4 tile KPI (20일·60일 RV · HAR-RV · GARCH · 레짐)."""
    result = _safeQuantCall("dartlab.quant.risk.volatility", "calcVolatility", stockCode)
    if result is None or not isinstance(result, dict) or result.get("error"):
        return {"tiles": []}
    rv20 = result.get("realizedVol_20d")
    rv60 = result.get("realizedVol_60d")
    harRV = result.get("harRV")
    garch = result.get("garchVol")
    regime = str(result.get("volRegime") or "—")
    shape = str(result.get("volCurveShape") or "")
    intentByRegime = {"low": "positive", "normal": "neutral", "high": "negative", "extreme": "negative"}
    tiles = [
        _kpiTile(
            "RV 20일 (연환산)",
            rv20 * 100 if isinstance(rv20, (int, float)) and rv20 < 5 else rv20,
            unit="%",
            intent=intentByRegime.get(regime, "primary"),
            subtitle=f"regime={regime}",
        ),
        _kpiTile(
            "RV 60일",
            rv60 * 100 if isinstance(rv60, (int, float)) and rv60 < 5 else rv60,
            unit="%",
            intent="primary",
            subtitle=f"커브={shape or '—'}",
        ),
        _kpiTile(
            "HAR-RV",
            harRV * 100 if isinstance(harRV, (int, float)) and harRV < 5 else harRV,
            unit="%",
            intent="accent",
            subtitle="Heterogeneous AR (1d+5d+22d)",
        ),
        _kpiTile(
            "GARCH(1,1)",
            garch * 100 if isinstance(garch, (int, float)) and garch < 5 else garch,
            unit="%",
            intent="primary",
            subtitle="조건부 — 다음날 예측",
        ),
    ]
    return {"tiles": tiles}


def buildQuantBetaKpi(stockCode: str) -> dict[str, Any]:
    """quant.beta → 4 tile KPI (β · R² · CAPM 기대 · 상대강도)."""
    result = _safeQuantCall("dartlab.quant.screen.axTechnical", "calcBeta", stockCode)
    if result is None or not isinstance(result, dict) or result.get("error"):
        return {"tiles": []}
    beta = result.get("value")
    r2 = result.get("r2")
    capm = result.get("capmExpected")
    rs = result.get("relativeStrength")
    interp = str(result.get("interpretation", ""))
    tiles = [
        _kpiTile("β", beta, unit="배", intent="primary", subtitle=interp[:30] if interp else "시장 민감도"),
        _kpiTile("R²", r2, unit="%", intent="neutral", subtitle="시장 설명력"),
        _kpiTile("CAPM 기대", capm, unit="%", intent="accent", subtitle="rf + β × 시장프리미엄"),
        _kpiTile("상대강도", rs, unit="배", intent="primary", subtitle="벤치마크 대비"),
    ]
    return {"tiles": tiles}


def buildQuantForecastKpi(stockCode: str) -> dict[str, Any]:
    """quant.forecast → 4 tile KPI (point · CI 폭 · model · 정상성).

    horizon=5 일 일별 수익률 예측. forecastTable: [{date, point, lower, upper, ...}].
    누적은 합성. 90% Conformal interval (predictive coverage 보장).
    """
    result = _safeQuantCall(
        "dartlab.quant.benchmark.forecast", "forecastReturns", stockCode, horizon=5
    )
    if result is None or not isinstance(result, dict) or result.get("error"):
        return {"tiles": []}
    table = result.get("forecastTable") or []
    halfWidth = result.get("conformalHalfWidth")
    model = str(result.get("modelChosen", "auto"))
    pAdf = result.get("pAdfStationary")
    summary = result.get("summary") or {}
    # 누적 수익률 — table 의 일별 point 합산 (log-return 가정이면 합, simple 이면 곱-1).
    # summary 에 있으면 우선 사용.
    cumPoint = summary.get("cumulativeReturn") if isinstance(summary, dict) else None
    if cumPoint is None and isinstance(table, list):
        try:
            pts = [_toFloat(row.get("point") if isinstance(row, dict) else None) for row in table]
            valid = [p for p in pts if p is not None]
            cumPoint = sum(valid) if valid else None
        except Exception:  # noqa: BLE001
            cumPoint = None
    pointFloat = _toFloat(cumPoint)
    intent = (
        "positive" if pointFloat is not None and pointFloat > 0
        else "negative" if pointFloat is not None and pointFloat < 0
        else "neutral"
    )
    tiles = [
        _kpiTile(
            "5일 누적 예측",
            cumPoint * 100 if isinstance(cumPoint, (int, float)) and abs(cumPoint) < 1 else cumPoint,
            unit="%",
            intent=intent,
            subtitle=f"model={model}",
        ),
        _kpiTile(
            "90% CI 반폭",
            halfWidth * 100 if isinstance(halfWidth, (int, float)) and halfWidth < 1 else halfWidth,
            unit="%",
            intent="accent",
            subtitle="Conformal predictive coverage 90%",
        ),
        _kpiTile(
            "정상성 p-value",
            pAdf,
            unit="",
            intent="primary",
            subtitle="ADF — 0.05 미만이면 정상",
        ),
        _kpiTile(
            "예측 모델",
            len(result.get("modelsConsidered") or []),
            unit="개",
            intent="neutral",
            subtitle=f"선택={model}",
        ),
    ]
    return {"tiles": tiles}


def buildQuantComingSoon(label: str = "준비 중") -> dict[str, Any]:
    """placeholder KPI 1 tile — 미구현 카드 graceful 빈 표시."""
    return {
        "tiles": [
            {
                "label": label,
                "value": None,
                "prev": None,
                "unit": "",
                "intent": "neutral",
                "subtitle": "엔진 wiring 진행 중 — 다음 commit 에서 실값",
            }
        ]
    }
