"""rawFinance(14557×27) → 표준 long-form.

K-IFRS DART OpenAPI 의 sj_div = BS / CIS (포괄손익) / CF / SCE. 이 모듈은:
- thstrm_amount (str, 콤마 포함) → Float64
- sj_div = CIS → IS (관습) 매핑
- bsns_year + reprt_code → period (Y/Q1/Q2/Q3/Q4)
- fs_div = CFS (연결) / OFS (별도) 보존
"""

from __future__ import annotations

import polars as pl

_AMT_COLS = (
    "thstrm_amount",
    "frmtrm_amount",
    "bfefrmtrm_amount",
    "thstrm_add_amount",
    "frmtrm_q_amount",
    "frmtrm_add_amount",
)


def _toNum(col: str) -> pl.Expr:
    """str → Float64. 빈 문자열 / '-' → null, 콤마 제거."""
    return (
        pl.col(col)
        .cast(pl.Utf8, strict=False)
        .str.strip_chars()
        .str.replace_all(",", "")
        .str.replace_all(r"^[-‒–—]$", "")
        .str.replace_all(r"^$", "")
        .cast(pl.Float64, strict=False)
    )


_PERIOD_MAP = {
    "11011": ("FY", "Y"),
    "11013": ("Q1", "Q"),
    "11012": ("HY", "Q"),
    "11014": ("Q3", "Q"),
}


def normalize(rawFinance: pl.DataFrame) -> pl.DataFrame:
    """rawFinance → 표준 long-form.

    Returns:
        DataFrame[stockCode, corpName, fsDiv, sjDiv, accountId, accountNm,
                  bsnsYear, reprtCode, periodKind, period,
                  amount, prevAmount, prevPrevAmount]
        - sjDiv: BS | IS | CF | SCE (CIS → IS 통일)
        - periodKind: Y | Q
        - period: 2024-FY | 2024-Q1 ...
    """
    if rawFinance is None or rawFinance.height == 0:
        return pl.DataFrame({})

    df = rawFinance.lazy()
    df = df.with_columns(
        [
            pl.when(pl.col("sj_div") == "CIS").then(pl.lit("IS")).otherwise(pl.col("sj_div")).alias("sjDiv"),
            _toNum("thstrm_amount").alias("amount"),
            _toNum("frmtrm_amount").alias("prevAmount"),
            _toNum("bfefrmtrm_amount").alias("prevPrevAmount"),
        ]
    )
    df = df.with_columns(
        [
            pl.col("reprt_code")
            .replace_strict({k: v[0] for k, v in _PERIOD_MAP.items()}, default="FY")
            .alias("periodTag"),
            pl.col("reprt_code")
            .replace_strict({k: v[1] for k, v in _PERIOD_MAP.items()}, default="Y")
            .alias("periodKind"),
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
