"""TTM (trailing twelve months / 연환산) 변환 — norm long-form → TTM 화 norm.

DART OpenAPI 의 분기 amount 는 *cumulative-from-Jan* 이다.
- Q1 (reprt_code 11013) → Jan-Mar
- HY (11012)            → Jan-Jun
- Q3 (11014)            → Jan-Sep
- FY (11011)            → Jan-Dec (= 12 개월)

따라서 분기 row 에 단순 rolling_sum 4 를 적용하면 누적치를 다시 더하는 *오류*.
정확한 TTM 공식:

    TTM(Y, tag) = FY(Y-1) - Cumulative(Y-1, tag) + Cumulative(Y, tag)

예: TTM(2024-Q3) = FY(2023) - Cum(2023-Q3) + Cum(2024-Q3)
    = (Jan-Dec 2023) - (Jan-Sep 2023) + (Jan-Sep 2024)
    = (Oct-Dec 2023) + (Jan-Sep 2024)
    = 직전 12 개월.

전년도 데이터 부재 (신규 상장 / FY 누락) → annualize fallback:
    TTM ≈ Cum(Y, tag) × 12 / months(tag)
    months: Q1=3, HY=6, Q3=9.

대상:
- sjDiv ∈ {"IS","CF"} (flow) 분기 row 만 변환.
- BS (stock) row: pass-through (point-in-time, TTM 의미 없음).
- IS/CF annual row: pass-through (FY 자체가 TTM).
"""

from __future__ import annotations

import polars as pl

_FLOW_SJ = ("IS", "CF")
_TAG_MONTHS: dict[str, int] = {"Q1": 3, "HY": 6, "Q3": 9}


def toTtmNorm(norm: pl.DataFrame) -> pl.DataFrame:
    """norm long-form → TTM 화 norm. schema 동일.

    Args:
        norm: normalize.normalize() 출력.

    Returns:
        같은 schema 의 DataFrame. IS/CF quarterly row 만 amount 가 TTM 으로 치환.
        BS row, IS/CF annual row 는 그대로.
    """
    if norm is None or norm.height == 0:
        return norm

    cols = norm.columns
    bs = norm.filter(~pl.col("sjDiv").is_in(_FLOW_SJ))
    flow = norm.filter(pl.col("sjDiv").is_in(_FLOW_SJ))
    if flow.height == 0:
        return norm

    annualFlow = flow.filter(pl.col("periodKind") == "annual")
    quarterlyFlow = flow.filter(pl.col("periodKind") == "quarterly")

    if quarterlyFlow.height == 0:
        return norm

    keyCols = ["stockCode", "fsDiv", "sjDiv", "accountId"]
    quarterlyFlow = quarterlyFlow.with_columns((pl.col("bsnsYear").cast(pl.Int64) - 1).cast(pl.Utf8).alias("_prevYear"))

    prevFyLookup = annualFlow.select([*keyCols, "bsnsYear", "amount"]).rename(
        {"bsnsYear": "_prevYear", "amount": "_prevFy"}
    )
    prevTagLookup = quarterlyFlow.select([*keyCols, "bsnsYear", "periodTag", "amount"]).rename(
        {"bsnsYear": "_prevYear", "amount": "_prevTag"}
    )

    quarterlyFlow = quarterlyFlow.join(prevFyLookup, on=[*keyCols, "_prevYear"], how="left").join(
        prevTagLookup, on=[*keyCols, "_prevYear", "periodTag"], how="left"
    )

    monthsExpr = pl.col("periodTag").replace_strict(_TAG_MONTHS, default=12).cast(pl.Float64)
    fullTtm = pl.col("_prevFy") - pl.col("_prevTag") + pl.col("amount")
    annualized = pl.col("amount") * 12.0 / monthsExpr

    quarterlyFlow = quarterlyFlow.with_columns(
        pl.when(pl.col("_prevFy").is_not_null() & pl.col("_prevTag").is_not_null())
        .then(fullTtm)
        .otherwise(annualized)
        .alias("_ttm")
    )
    quarterlyFlow = (
        quarterlyFlow.drop(["amount", "_prevYear", "_prevFy", "_prevTag"]).rename({"_ttm": "amount"}).select(cols)
    )

    return pl.concat(
        [bs.select(cols), annualFlow.select(cols), quarterlyFlow.select(cols)],
        how="vertical",
    )


__all__ = ["toTtmNorm"]
