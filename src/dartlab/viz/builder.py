"""buildView — catalog 의 cardKey → 완성된 View dict.

설계 사상 (SSOT):
- catalog 의 SeriesPlan 이 series 모양 + 색상 + **데이터 정의** 까지 한 곳에 선언.
- builder 는 norm DataFrame 을 한 번 만들고 SeriesPlan 의 데이터 정의 보고
  자동으로 추출 + 합성 + 비율 + YoY 계산.
- statements/ratios 함수 신설 0 — accounts.py 의 표준 28 항목만 활용.

SeriesPlan 데이터 정의 우선순위 (한 series 마다 하나):
1. ratio    — {num, den, scale?}     비율 = sum(num) / sum(den) * scale
2. yoy      — account 문자열          YoY % = (cur-prev)/prev * 100
3. compose  — {accountKey: sign}     가산 합성
4. account  — 단일 표준 항목         extractSeries 단일 호출

위 4 가지 다 없으면 catalog 의 `statementsCall` 호출 fallback (legacy
호환 — analysis.* topic / 기존 ratios.profitability 등).
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Any

from dartlab.viz.catalog import CATALOG
from dartlab.viz.data import _cache, normalize, ratios, statements
from dartlab.viz.display.finance.accounts import extractSeries
from dartlab.viz.display.finance.periods import lastNPeriods
from dartlab.viz.schema import (
    CatalogEntry,
    PeriodKind,
    Series,
    SeriesPlan,
    View,
    makeBinding,
    makeMeta,
)

_ANALYSIS_PREFIX = "analysis."


def _sumWeighted(norm: Any, terms: dict[str, int], periods: list[str]) -> list[float | None]:
    """compose 또는 ratio 의 분자/분모 가산.

    terms = {accountKey: sign} 형태. 각 항목 extractSeries 후 sign 곱해 합산.
    한 기간이라도 None 이면 그 기간 결과 None (보수적).
    """
    n = len(periods)
    if not terms:
        return [None] * n
    series_by_key = {k: extractSeries(norm, k, periods) for k in terms}
    out: list[float | None] = []
    for i in range(n):
        total: float = 0.0
        valid = False
        for k, sign in terms.items():
            v = series_by_key[k][i]
            if v is None:
                continue
            total += sign * float(v)
            valid = True
        out.append(total if valid else None)
    return out


def _ratioSeries(norm: Any, ratio: dict[str, Any], periods: list[str]) -> list[float | None]:
    """ratio = {num: {key:sign}, den: {key:sign}, scale?: int} → 시계열."""
    num_terms: dict[str, int] = ratio.get("num") or ratio.get("numerator") or {}
    den_terms: dict[str, int] = ratio.get("den") or ratio.get("denominator") or {}
    scale = float(ratio.get("scale", 100))
    num = _sumWeighted(norm, num_terms, periods)
    den = _sumWeighted(norm, den_terms, periods)
    out: list[float | None] = []
    for i in range(len(periods)):
        n, d = num[i], den[i]
        if n is None or d is None or d == 0:
            out.append(None)
        else:
            out.append(n / d * scale)
    return out


def _yoySeries(norm: Any, account: str, periods: list[str]) -> list[float | None]:
    """단일 account 의 YoY (%). periods 가 시간 순 정렬이라고 가정."""
    base = extractSeries(norm, account, periods)
    out: list[float | None] = [None]
    for i in range(1, len(periods)):
        prev, curr = base[i - 1], base[i]
        if prev is None or curr is None or prev == 0:
            out.append(None)
        else:
            out.append((curr - prev) / abs(prev) * 100)
    return out


def _analysisCallSeries(spec: dict[str, Any], stockCode: str, periods: list[str]) -> list[float | None] | None:
    """analysisCall = {module, fn, outputKey, [outputType]} → 시계열.

    module: "valuation.dFV" 처럼 dartlab.analysis.* 하위 경로.
    fn: 호출 함수명. 인자는 Company 객체 (자동 주입).
    outputKey: 반환 dict 의 어떤 키를 시리즈로 쓸지. dot-path 지원 (예: "history.roic").
    outputType: "timeseries" (기본, period 매칭) 또는 "scalar" (모든 period 같은 값).
    """
    moduleName = spec.get("module")
    fnName = spec.get("fn")
    outputKey = spec.get("outputKey", "")
    outputType = spec.get("outputType", "timeseries")
    if not moduleName or not fnName:
        return None
    try:
        mod = importlib.import_module(f"dartlab.analysis.{moduleName}")
    except ImportError:
        return None
    fn = getattr(mod, fnName, None)
    if fn is None:
        return None
    company = _cache.getCompany(stockCode)
    try:
        result = fn(company)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(result, dict):
        return None

    def _drill(d: Any, path: str) -> Any:
        cur = d
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    val = _drill(result, outputKey) if outputKey else result

    if outputType == "scalar":
        try:
            num = float(val) if val is not None else None
            return [num] * len(periods)
        except (TypeError, ValueError):
            return None

    # timeseries: list[dict] 인 경우 period 기준 매칭. period 키 이름은 자유 ("period"/"yr"/"quarter").
    if isinstance(val, list):
        lookup: dict[str, float] = {}
        for row in val:
            if not isinstance(row, dict):
                continue
            row_period = row.get("period") or row.get("yr") or row.get("quarter") or row.get("date")
            row_value = row.get("value") or row.get(outputKey.split(".")[-1])
            if row_period is not None and row_value is not None:
                try:
                    lookup[str(row_period)] = float(row_value)
                except (TypeError, ValueError):
                    continue
        return [lookup.get(p) for p in periods]
    return None


def _seriesDataFromPlan(
    plan: SeriesPlan, norm: Any, periods: list[str], stockCode: str = ""
) -> list[float | None] | None:
    """SeriesPlan 의 데이터 정의 → 시계열. None 반환 시 fallback (raw lookup)."""
    if "ratio" in plan:
        return _ratioSeries(norm, plan["ratio"], periods)
    if "yoy" in plan:
        return _yoySeries(norm, plan["yoy"], periods)
    if "compose" in plan:
        return _sumWeighted(norm, plan["compose"], periods)
    if "account" in plan:
        return extractSeries(norm, plan["account"], periods)
    if "analysisCall" in plan and stockCode:
        return _analysisCallSeries(plan["analysisCall"], stockCode, periods)
    return None


def _resolveLegacyCall(topic: str, stockCode: str) -> tuple[str, Any, Any]:
    """statementsCall fallback 용 — topic → (kind, context, module)."""
    company = _cache.getCompany(stockCode)
    if topic.startswith(_ANALYSIS_PREFIX):
        moduleName = topic[len(_ANALYSIS_PREFIX) :]
        mod = importlib.import_module(f"dartlab.analysis.financial.{moduleName}")
        return "analysis", company, mod
    if topic == "ratios":
        norm = normalize.normalize(company.rawFinance)
        return "data", norm, ratios
    if topic in ("IS", "BS", "CF"):
        norm = normalize.normalize(company.rawFinance)
        return "data", norm, statements
    raise ValueError(f"viz.builder: unknown topic '{topic}'")


def _callLegacy(
    kind: str, context: Any, mod: Any, callName: str, nPeriods: int, periodKind: PeriodKind
) -> dict[str, Any]:
    fn = getattr(mod, callName, None)
    if fn is None:
        raise ValueError(f"viz.builder: 모듈 '{mod.__name__}' 에 '{callName}' 없음")
    if kind == "analysis":
        result = fn(context)
        return result if isinstance(result, dict) else {}
    return fn(context, nPeriods, periodKind)


def _extractFromRaw(raw: dict[str, Any], key: str, nPeriods: int) -> list[float | None]:
    """legacy raw dict 에서 key 시계열 추출. 3 패턴 지원."""
    if key in raw:
        v = raw[key]
        if isinstance(v, list):
            return v
    rows = raw.get("rows")
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict) and r.get("key") == key:
                return list(r.get("values") or [])
    history = raw.get("history")
    if isinstance(history, list) and history:
        return [h.get(key) if isinstance(h, dict) else None for h in history]
    return [None] * nPeriods


def _periodsFromRaw(raw: dict[str, Any]) -> list[str]:
    p = raw.get("periods")
    if isinstance(p, list):
        return [str(x) for x in p]
    history = raw.get("history")
    if isinstance(history, list):
        return [str(h.get("period", "")) for h in history if isinstance(h, dict)]
    return []


def _materializeSeries(plan: SeriesPlan, data: list[float | None]) -> Series:
    series: Series = {}
    for field in ("key", "label", "color", "intent", "unit", "type", "axis", "stack"):
        if field in plan:
            series[field] = plan[field]  # type: ignore[literal-required]
    series["data"] = data
    return series


_NON_TREND_KINDS = frozenset(
    {
        "kpiTile",
        "diffView",
        "topList",
        "comparisonTable",
        "gauge",
        "phaseIndicator",
        "sankey",
        "scatter",
        "matrix",
        "radar",
        "waterfall",
    }
)


def _buildKindSpecView(
    entry: CatalogEntry, company: Any, stockCode: str, periodKind: PeriodKind, nPeriods: int
) -> View | None:
    """kpiTile/diffView/topList/comparisonTable/gauge/phaseIndicator/sankey/scatter dispatch.

    entry.dataSpec 의 `adapter` 키로 어댑터 선택. None 반환 시 호출자가 trend fallback.
    """
    from dartlab.viz.display import adapters

    kind = entry.get("kind")
    spec = entry.get("dataSpec") or {}
    adapter_name = spec.get("adapter", "")
    # _NON_TREND_KINDS 외에도 trend kind 가 adapter 명시한 경우 처리.
    # (P-DASH-V1 D6: capitalAllocationBars 는 kind=trend 지만 adapter dispatch 필요.)
    if kind not in _NON_TREND_KINDS and not adapter_name:
        return None

    # 공통: norm + periods (필요한 어댑터만 사용).
    needsNorm = adapter_name in (
        "kpiFromNorm",
        "diffFromNorm",
        "cashflowSankey",
        "capitalAllocationBars",
        "capitalAllocationWaterfall",
        "duPontRadar",
    )
    norm = None
    periods: list[str] = []
    if needsNorm:
        norm = normalize.normalize(company.rawFinance)
        periods = lastNPeriods(norm, nPeriods, periodKind)

    base_view: dict[str, Any] = {
        "kind": kind,
        "title": entry.get("title", ""),
        "categories": periods,
        "series": [],
        "options": dict(entry.get("options") or {}),
    }

    if adapter_name == "kpiFromNorm":
        tilePlans = spec.get("tilePlans", [])
        tiles = adapters.buildKpiTilesFromNorm(norm, periods, tilePlans)
        base_view["tiles"] = tiles
    elif adapter_name == "diffFromNorm":
        tilePlans = spec.get("tilePlans", [])
        tiles = adapters.buildKpiTilesFromNorm(norm, periods, tilePlans)
        base_view["tiles"] = tiles
        base_view["periodLabel"] = spec.get("periodLabel", "YoY")
    elif adapter_name == "flagsTopList":
        modPath = spec.get("module", "")
        fnName = spec.get("fn", "")
        flags = adapters._safeCall(modPath, fnName, company)
        items = adapters.buildTopListFromFlags(flags)
        # analysis 함수 결과 비면 norm 기반 fallback.
        if not items:
            items = adapters.buildAnomalyTopList(company)
        base_view["items"] = items
        base_view["direction"] = spec.get("direction", "desc")
    elif adapter_name == "peerComparison":
        base_view.update(adapters.buildPeerComparison(company))
    elif adapter_name == "distressGauge":
        base_view.update(adapters.buildDistressGauge(company))
    elif adapter_name == "beneishGauge":
        base_view.update(adapters.buildBeneishGauge(company))
    elif adapter_name == "lifeCyclePhase":
        base_view.update(adapters.buildLifeCyclePhase(company))
    elif adapter_name == "cashflowSankey":
        base_view.update(adapters.buildCashflowAllocationSankey(norm, periods))
    elif adapter_name == "capitalAllocationBars":
        result = adapters.buildCapitalAllocationBars(norm, periods)
        if "series" in result:
            base_view["series"] = result["series"]
    elif adapter_name == "capitalAllocationWaterfall":
        result = adapters.buildCapitalAllocationWaterfall(norm, periods)
        if "categories" in result:
            base_view["categories"] = result["categories"]
        if "series" in result:
            base_view["series"] = result["series"]
    elif adapter_name == "distressDecomp":
        base_view.update(adapters.buildDistressDecomp(company))
    elif adapter_name == "scenarioSensitivity":
        base_view.update(adapters.buildScenarioSensitivity(company))
    elif adapter_name == "peerScatter":
        base_view.update(adapters.buildPeerScatter(company))
    elif adapter_name == "duPontRadar":
        result = adapters.buildDuPontRadar(norm, periods)
        base_view["categories"] = result.get("categories", [])
        base_view["series"] = result.get("series", [])
    else:
        # adapter 미지정 — 빈 spec 으로라도 kind 보존.
        pass

    corpName = getattr(company, "corpName", None)
    base_view["evidenceBinding"] = makeBinding(stockCode, entry.get("topic", "BS"), periodKind, periods or [])
    base_view["meta"] = makeMeta(
        stockCode,
        corpName=corpName,
        periodKind=periodKind,
        periods=periods,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
    if "layout" in entry:
        base_view["layout"] = dict(entry["layout"])
    return base_view  # type: ignore[return-value]


def buildView(
    cardKey: str,
    stockCode: str,
    *,
    periodKind: PeriodKind = "annual",
    nPeriods: int = 8,
) -> View:
    """cardKey + stockCode → 완성된 View JSON.

    SeriesPlan 의 데이터 정의 (ratio/yoy/compose/account) 가 우선. 모든 series 가
    데이터 정의 보유 시 statementsCall 호출 없이 norm 만으로 처리. 일부라도
    데이터 정의 없는 series 가 있으면 fallback 으로 statementsCall 결과 lookup.

    kpiTile/diffView/topList/comparisonTable/gauge/phaseIndicator/sankey/scatter 는
    별도 어댑터 dispatch — 시계열 series 가 아닌 kind-별 spec 필드 채움.
    """
    if cardKey not in CATALOG:
        raise KeyError(f"viz.buildView: cardKey '{cardKey}' not in CATALOG")
    entry: CatalogEntry = CATALOG[cardKey]
    topic: str = entry.get("topic", "BS")  # type: ignore[assignment]

    company = _cache.getCompany(stockCode)
    corpName = getattr(company, "corpName", None)

    # 비-시계열 kind 는 별도 어댑터.
    kind_view = _buildKindSpecView(entry, company, stockCode, periodKind, nPeriods)
    if kind_view is not None:
        return kind_view  # type: ignore[return-value]

    plans = entry["seriesPlan"]
    allHaveDataDef = all(
        ("ratio" in p) or ("yoy" in p) or ("compose" in p) or ("account" in p) or ("analysisCall" in p) for p in plans
    )

    if allHaveDataDef and not topic.startswith(_ANALYSIS_PREFIX):
        # 모든 series 가 catalog 정의 → norm 한 번 + 자동 추출
        norm = normalize.normalize(company.rawFinance)
        periods = lastNPeriods(norm, nPeriods, periodKind)
        series: list[Series] = []
        for plan in plans:
            data = _seriesDataFromPlan(plan, norm, periods, stockCode)
            if data is None:
                data = [None] * len(periods)
            series.append(_materializeSeries(plan, data))
        bindingTopic = topic
    else:
        # legacy: statementsCall 호출 → raw dict → key lookup
        kind, context, mod = _resolveLegacyCall(topic, stockCode)
        callName = entry.get("statementsCall")
        if not callName:
            raise ValueError(f"viz.builder: '{cardKey}' 의 seriesPlan 일부에 데이터 정의 누락 + statementsCall 없음")
        raw = _callLegacy(kind, context, mod, callName, nPeriods, periodKind)
        periods = _periodsFromRaw(raw)
        # 일부 series 는 catalog 정의, 일부는 raw lookup — 혼합 처리
        if not topic.startswith(_ANALYSIS_PREFIX) and topic in ("IS", "BS", "CF", "ratios"):
            norm = normalize.normalize(company.rawFinance)
        else:
            norm = None
        series = []
        for plan in plans:
            data = _seriesDataFromPlan(plan, norm, periods, stockCode) if norm is not None else None
            if data is None:
                data = _extractFromRaw(raw, plan["key"], len(periods))
            series.append(_materializeSeries(plan, data))
        bindingTopic = topic.split(".", 1)[1].upper() if topic.startswith(_ANALYSIS_PREFIX) else topic

    view: View = {
        "kind": entry["kind"],
        "title": entry["title"],
        "categories": periods,
        "series": series,
        "evidenceBinding": makeBinding(stockCode, bindingTopic, periodKind, periods),
        "meta": makeMeta(
            stockCode,
            corpName=corpName,
            periodKind=periodKind,
            periods=periods,
            generatedAt=datetime.now(timezone.utc).isoformat(),
        ),
        "options": dict(entry.get("options") or {}),
    }
    if "layout" in entry:
        view["layout"] = dict(entry["layout"])
    return view


__all__ = ["buildView"]
