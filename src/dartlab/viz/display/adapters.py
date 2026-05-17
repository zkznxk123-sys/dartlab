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
    """norm + tilePlans → KpiTile dict list.

    tilePlans 각 항목: {label, account?: str, ratio?: dict, unit, intent, subtitle?}.
    """
    tiles: list[dict[str, Any]] = []
    for plan in tilePlans:
        label = plan.get("label", "")
        unit = plan.get("unit", "")
        intent = plan.get("intent", "primary")
        subtitle = plan.get("subtitle", "")
        # 데이터 추출 — account/compose/ratio 중 하나.
        data: list[float | None] = []
        if "account" in plan:
            data = extractSeries(norm, plan["account"], periods)
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
        # 마지막 2 비 None 값.
        last, prev = _lastTwo(data)
        tiles.append(
            {
                "label": label,
                "value": last,
                "prev": prev,
                "unit": unit,
                "intent": intent,
                "subtitle": subtitle,
            }
        )
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
    """norm 의 마지막 기간에서 CFO 를 CapEx · 배당 · 부채상환 · 잉여 로 분해.

    값이 모두 0 또는 음수면 빈 dict.
    """
    if not periods:
        return {}
    last = periods[-1]
    cfo = extractSeries(norm, "cfOperating", [last])[0]
    capex_raw = extractSeries(norm, "capex", [last])[0]
    dividends_raw = extractSeries(norm, "dividendsPaid", [last])[0]
    # capex/배당은 음수일 수 있음 — 절대값으로.
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


__all__ = [
    "LIFE_CYCLE_PHASES",
    "buildBeneishGauge",
    "buildCashflowAllocationSankey",
    "buildDistressGauge",
    "buildKpiTilesFromNorm",
    "buildLifeCyclePhase",
    "buildPeerComparison",
    "buildPeerScatter",
    "buildTopListFromFlags",
]
