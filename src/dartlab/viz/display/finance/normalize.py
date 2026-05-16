"""rawFinance → 표준 long-form.

K-IFRS DART OpenAPI 의 sj_div = BS / CIS (포괄손익) / CF / SCE.
- thstrm_amount (str, 콤마 포함) → Float64
- sj_div = CIS → IS (관습) 매핑
- bsns_year + reprt_code → period (annual: YYYY-FY, quarterly: YYYY-Q1/HY/Q3)
- fs_div = CFS (연결) / OFS (별도) 보존
"""

from __future__ import annotations

import polars as pl

_REPRT_CODE = {
    "11011": "FY",
    "11013": "Q1",
    "11012": "HY",
    "11014": "Q3",
}

_REPRT_KIND = {
    "11011": "annual",
    "11013": "quarterly",
    "11012": "quarterly",
    "11014": "quarterly",
}


def _toNum(col: str) -> pl.Expr:
    """str → Float64. 빈/'-' → null, 콤마 제거."""
    return (
        pl.col(col)
        .cast(pl.Utf8, strict=False)
        .str.strip_chars()
        .str.replace_all(",", "")
        .str.replace_all(r"^[-‒–—]$", "")
        .str.replace_all(r"^$", "")
        .cast(pl.Float64, strict=False)
    )


def normalize(rawFinance: pl.DataFrame) -> pl.DataFrame:
    """rawFinance → 표준 long-form.

    Returns:
        DataFrame[stockCode, corpName, fsDiv, sjDiv, accountId, accountNm,
                  bsnsYear, reprtCode, periodKind, period, ord,
                  amount, prevAmount, prevPrevAmount]
        - sjDiv: BS | IS | CF | SCE (CIS → IS 통일)
        - periodKind: annual | quarterly
        - period: 2024-FY | 2024-Q1 | 2024-HY | 2024-Q3
    """
    if rawFinance is None or rawFinance.height == 0:
        return pl.DataFrame({})

    df = rawFinance.lazy().with_columns(
        [
            pl.when(pl.col("sj_div") == "CIS").then(pl.lit("IS")).otherwise(pl.col("sj_div")).alias("sjDiv"),
            _toNum("thstrm_amount").alias("amount"),
            _toNum("frmtrm_amount").alias("prevAmount"),
            _toNum("bfefrmtrm_amount").alias("prevPrevAmount"),
        ]
    )
    df = df.with_columns(
        [
            pl.col("reprt_code").replace_strict(_REPRT_CODE, default="FY").alias("periodTag"),
            pl.col("reprt_code").replace_strict(_REPRT_KIND, default="annual").alias("periodKind"),
        ]
    )
    df = df.with_columns((pl.col("bsns_year").cast(pl.Utf8) + pl.lit("-") + pl.col("periodTag")).alias("period"))
    df = df.rename(
        {
            "stock_code": "stockCode",
            "corp_name": "corpName",
            "fs_div": "fsDiv",
            "account_id": "accountId",
            "account_nm": "accountNm",
            "bsns_year": "bsnsYear",
            "reprt_code": "reprtCode",
        }
    )
    df = df.with_columns(pl.col("ord").cast(pl.Int64, strict=False).alias("ord"))
    cols = [
        "stockCode",
        "corpName",
        "fsDiv",
        "sjDiv",
        "accountId",
        "accountNm",
        "bsnsYear",
        "reprtCode",
        "periodKind",
        "periodTag",
        "period",
        "ord",
        "amount",
        "prevAmount",
        "prevPrevAmount",
    ]
    return df.select([pl.col(c) for c in cols]).collect()
