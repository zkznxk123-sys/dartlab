"""기업 유형 판별 — 스토리 템플릿 자동 감지 (L0).

story/analysis 양쪽에서 사용하는 기업 분류 로직.
Phase 9 A1: story/templates.py 에서 L0 으로 이동.
"""

from __future__ import annotations


def _extractCommon(company):
    """공통 데이터 추출 (체크 함수 공용)."""
    try:
        ratios = company._finance.ratios
    except (AttributeError, ValueError):
        return None

    def _g(name, default=None):
        return getattr(ratios, name, default)

    try:
        rs = company._finance.ratioSeries
        if rs:
            data, _ = rs
            opMargins = data.get("RATIO", {}).get("operatingMargin", [])
        else:
            opMargins = []
    except (AttributeError, ValueError):
        opMargins = []

    return {
        "ratios": ratios,
        "opMargin": _g("operatingMargin"),
        "netDebt": _g("netDebt"),
        "cash": _g("cash"),
        "totalAssets": _g("totalAssets"),
        "ppe": _g("ppe") or _g("tangibleAssets"),
        "opMargins": opMargins,
    }


def _cv(values: list, min_count: int = 4) -> float | None:
    valid = [m for m in values if m is not None]
    if len(valid) < min_count:
        return None
    avg = sum(valid) / len(valid)
    if avg == 0:
        return None
    std = (sum((m - avg) ** 2 for m in valid) / len(valid)) ** 0.5
    return std / abs(avg)


def _checkTurnaround(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    opMargins = ctx["opMargins"]
    if len(opMargins) < 3:
        return False
    recent3 = opMargins[-3:]
    hasNeg = any(m is not None and m < 0 for m in recent3[:-1])
    lastPos = recent3[-1] is not None and recent3[-1] > 0
    return hasNeg and lastPos


def _checkHolding(company) -> bool:
    from dartlab.analysis.financial.earningsQuality import calcNonOperatingBreakdown

    nob = calcNonOperatingBreakdown(company)
    if not nob:
        return False
    latest = nob["history"][0] if nob.get("history") else None
    if not latest:
        return False
    opInc = abs(latest.get("opIncome") or 1)
    assocInc = abs(latest.get("associateIncome") or 0)
    if opInc > 0 and assocInc / opInc > 0.30:
        return True
    finCost = abs(latest.get("finCost") or 0)
    finIncome = abs(latest.get("finIncome") or 0)
    nonOpTotal = abs(latest.get("nonOpTotal") or 0)
    nonOpExFinance = nonOpTotal - finCost - finIncome
    return opInc > 0 and nonOpExFinance > 0 and nonOpExFinance / opInc > 0.80


def _checkGrowth(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    from dartlab.analysis.financial.growthAnalysis import calcCagrComparison

    cc = calcCagrComparison(company)
    if not cc:
        return False
    for comp in cc.get("comparisons", []):
        if comp.get("label") == "마진 방향" and comp.get("cagr1") is not None:
            if comp["cagr1"] > 15:
                cv = _cv(ctx["opMargins"])
                if cv is not None and cv > 0.5:
                    return False
                return True
    return False


def _checkCashRich(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    nd, ta, cash = ctx["netDebt"], ctx["totalAssets"], ctx["cash"]
    return nd is not None and ta and cash and nd < 0 and cash / ta > 0.20


def _checkCyclical(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    cv = _cv(ctx["opMargins"])
    return cv is not None and cv > 0.4


def _checkCapitalIntensive(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    ppe, ta = ctx["ppe"], ctx["totalAssets"]
    return ppe is not None and ta and ppe / ta > 0.40


def _checkFranchise(company) -> bool:
    ctx = _extractCommon(company)
    if not ctx:
        return False
    opMargin = ctx["opMargin"]
    if opMargin is None or opMargin <= 10:
        return False
    cv = _cv(ctx["opMargins"])
    return cv is not None and cv < 0.15


_TEMPLATE_CHECKS: list[tuple[str, object]] = [
    ("턴어라운드", _checkTurnaround),
    ("지주", _checkHolding),
    ("성장", _checkGrowth),
    ("현금부자", _checkCashRich),
    ("사이클", _checkCyclical),
    ("자본집약", _checkCapitalIntensive),
    ("프랜차이즈", _checkFranchise),
]


def detectTemplates(company) -> list[str]:
    """기업 재무 데이터에서 해당하는 스토리 템플릿 전부 반환."""
    results: list[str] = []
    for name, check in _TEMPLATE_CHECKS:
        try:
            if check(company):
                results.append(name)
        except (AttributeError, ValueError, TypeError, KeyError, IndexError):
            continue
    return results


def detectTemplate(company) -> str | None:
    """기업 재무 데이터에서 스토리 템플릿 자동 판별. 첫 매칭 반환."""
    results = detectTemplates(company)
    return results[0] if results else None
