"""전종목 재무비율 시계열 — scanAccount.py 분할 (규칙 3 LoC).

`scanAccount.py` 1082 LoC 가 규칙 3 임계 (>800) 위반. scanRatio / scanRatioList /
`_calcSimpleRatio` / `_calcYoyRatio` 와 `_RATIO_DEFS` 카탈로그 (~480 줄) 를 본 모듈로
분리. 호출자 호환 — scanAccount.py 가 `_RATIO_DEFS` · scanRatio · scanRatioList 재내보내기.
"""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.finance.scanAccount import scanAccount

_RATIO_DEFS: dict[str, dict] = {
    "roe": {"numer": "net_income", "denom": "total_stockholders_equity", "pct": True, "label": "ROE"},
    "roa": {"numer": "net_income", "denom": "total_assets", "pct": True, "label": "ROA"},
    "operatingMargin": {
        "numer": "operating_profit",
        "denom": "sales",
        "pct": True,
        "label": "영업이익률",
    },
    "netMargin": {"numer": "net_income", "denom": "sales", "pct": True, "label": "순이익률"},
    "grossMargin": {"numer": "gross_profit", "denom": "sales", "pct": True, "label": "매출총이익률"},
    "debtRatio": {
        "numer": "total_liabilities",
        "denom": "total_stockholders_equity",
        "pct": True,
        "label": "부채비율",
    },
    "currentRatio": {
        "numer": "current_assets",
        "denom": "current_liabilities",
        "pct": True,
        "label": "유동비율",
    },
    "equityRatio": {
        "numer": "total_stockholders_equity",
        "denom": "total_assets",
        "pct": True,
        "label": "자기자본비율",
    },
    "revenueGrowth": {"base": "sales", "yoy": True, "pct": True, "label": "매출성장률"},
    "operatingProfitGrowth": {
        "base": "operating_profit",
        "yoy": True,
        "pct": True,
        "label": "영업이익성장률",
    },
    "netProfitGrowth": {
        "base": "net_income",
        "yoy": True,
        "pct": True,
        "label": "순이익성장률",
    },
    "totalAssetTurnover": {
        "numer": "sales",
        "denom": "total_assets",
        "pct": False,
        "label": "총자산회전율",
    },
    "operatingCfMargin": {
        "numer": "operating_cashflow",
        "denom": "sales",
        "pct": True,
        "label": "영업CF마진",
    },
}


def scanRatio(
    ratioName: str,
    *,
    fsPref: str = "CFS",
    freq: str = "Q",
) -> pl.DataFrame:
    """전종목 단일 재무비율 시계열. 본문 docstring 은 scanAccount.py 원본 보존."""
    if ratioName not in _RATIO_DEFS:
        available = ", ".join(sorted(_RATIO_DEFS))
        lower = ratioName.lower()
        hint = ""
        if lower in {"pbr", "per", "psr", "ev", "evEbitda".lower(), "ev_ebitda", "dividendyield", "dividend_yield"}:
            hint = (
                " — 시가총액 기반 밸류에이션 비율은 scanRatio 범위 밖이다. "
                "dartlab.scan('valuation') 을 사용하라 (네이버 시총 snapshot 경로)."
            )
        msg = f"지원하지 않는 비율: '{ratioName}'.{hint} 사용 가능: {available}"
        raise ValueError(msg)

    defn = _RATIO_DEFS[ratioName]

    if defn.get("yoy"):
        return _calcYoyRatio(defn, fsPref, freq=freq)
    return _calcSimpleRatio(defn, fsPref, freq=freq)


def scanRatioList() -> list[dict[str, str]]:
    """사용 가능한 scanRatio 비율 목록."""
    return [{"name": k, "label": v["label"], "unit": "%" if v.get("pct") else "배"} for k, v in _RATIO_DEFS.items()]


def _calcSimpleRatio(defn: dict, fsPref: str, *, freq: str = "Q") -> pl.DataFrame:
    """분자/분모 비율 계산."""
    numer = scanAccount(defn["numer"], fsPref=fsPref, freq=freq)
    denom = scanAccount(defn["denom"], fsPref=fsPref, freq=freq)

    numerYears = [c for c in numer.columns if c != "stockCode"]
    denomYears = [c for c in denom.columns if c != "stockCode"]
    commonYears = sorted(set(numerYears) & set(denomYears), reverse=True)

    if not commonYears:
        return pl.DataFrame({"stockCode": []})

    joined = numer.select(["stockCode"] + commonYears).join(
        denom.select(["stockCode"] + commonYears),
        on="stockCode",
        suffix="_d",
    )

    isPct = defn.get("pct", False)
    multiplier = 100.0 if isPct else 1.0

    resultExprs = [pl.col("stockCode")]
    for y in commonYears:
        expr = (
            pl.when((pl.col(f"{y}_d") != 0) & pl.col(f"{y}_d").is_not_null() & pl.col(y).is_not_null())
            .then((pl.col(y) / pl.col(f"{y}_d") * multiplier).round(2))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias(y)
        )
        resultExprs.append(expr)

    return joined.select(resultExprs)


def _calcYoyRatio(defn: dict, fsPref: str, *, freq: str = "Q") -> pl.DataFrame:
    """YoY 성장률 계산."""
    base = scanAccount(defn["base"], fsPref=fsPref, freq=freq)
    yearCols = sorted(c for c in base.columns if c != "stockCode")

    if len(yearCols) < 2:
        return pl.DataFrame({"stockCode": []})

    resultExprs = [pl.col("stockCode")]
    for i in range(1, len(yearCols)):
        cur = yearCols[i]
        prev = yearCols[i - 1]
        expr = (
            pl.when(
                (pl.col(prev) != 0) & pl.col(prev).is_not_null() & pl.col(cur).is_not_null() & (pl.col(prev).abs() > 0)
            )
            .then(((pl.col(cur) - pl.col(prev)) / pl.col(prev).abs() * 100).round(2))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias(cur)
        )
        resultExprs.append(expr)

    yoyCols = [yearCols[i] for i in range(1, len(yearCols))]
    return base.select(resultExprs).select(["stockCode"] + list(reversed(yoyCols)))
