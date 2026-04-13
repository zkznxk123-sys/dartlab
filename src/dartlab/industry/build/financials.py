"""재무 데이터 join — finance.parquet → nodes에 매출/이익/자산 붙이기.

account_id_std(정규화 snakeId)를 사용하여 전종목 재무 데이터를 추출한다.
CFS(연결) 우선, OFS(개별) fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from dartlab.industry.types import IndustryNode

logger = logging.getLogger(__name__)

# 추출할 계정
_ACCOUNTS = {
    "sales": "revenue",
    "operating_profit": "opIncome",
    "net_profit": "netIncome",
    "total_assets": "totalAssets",
}


def _finPath() -> Path:
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / DATA_RELEASES["scan"]["dir"] / "finance.parquet"


def _extractYearly(year: str) -> pl.DataFrame:
    """특정 연도의 전종목 재무 데이터를 추출.

    Returns
    -------
    pl.DataFrame
        columns: stockCode, revenue, opIncome, netIncome, totalAssets
    """
    path = _finPath()
    if not path.exists():
        return pl.DataFrame()

    snakeIds = list(_ACCOUNTS.keys())

    df = (
        pl.scan_parquet(str(path))
        .filter(pl.col("account_id_std").is_in(snakeIds))
        .filter(pl.col("bsns_year") == year)
        .filter(pl.col("reprt_nm") == "4분기")  # 연간 누적만
        .filter(pl.col("sj_div").is_in(["IS", "BS"]))
        .select(["stockCode", "fs_div", "account_id_std", "thstrm_amount"])
        .collect()
    )

    if df.height == 0:
        return pl.DataFrame()

    # 금액 변환
    df = df.with_columns(
        pl.col("thstrm_amount")
        .str.replace_all(",", "")
        .cast(pl.Float64, strict=False)
        .alias("amount")
    )

    # CFS 우선, OFS fallback
    cfsCodes = df.filter(pl.col("fs_div") == "CFS").select("stockCode").unique()
    cfs = df.filter(pl.col("fs_div") == "CFS")
    ofs = df.filter(pl.col("fs_div") == "OFS").join(cfsCodes, on="stockCode", how="anti")
    merged = pl.concat([cfs, ofs])

    # pivot: stockCode × account
    result = pl.DataFrame({"stockCode": merged["stockCode"].unique().sort()})

    for snakeId, alias in _ACCOUNTS.items():
        acct = (
            merged.filter(pl.col("account_id_std") == snakeId)
            .group_by("stockCode")
            .agg(pl.col("amount").first().alias(alias))
        )
        result = result.join(acct, on="stockCode", how="left")

    return result


def attachFinancials(
    nodes: list[IndustryNode],
    *,
    year: str = "2024",
) -> list[IndustryNode]:
    """nodes에 재무 데이터를 붙인다.

    Parameters
    ----------
    nodes : list[IndustryNode]
        기존 노드 리스트.
    year : str
        재무 데이터 연도.

    Returns
    -------
    list[IndustryNode]
        revenue 필드가 채워진 노드 리스트.
    """
    fin = _extractYearly(year)
    if fin.height == 0:
        return nodes

    finMap: dict[str, dict] = {}
    for row in fin.iter_rows(named=True):
        finMap[row["stockCode"]] = row

    for node in nodes:
        data = finMap.get(node.stockCode)
        if data:
            node.revenue = data.get("revenue")

    logger.info("재무 데이터 %d사 join (year=%s)", len(finMap), year)
    return nodes


def buildIndustrySummary(
    nodes: list[IndustryNode],
    industryId: str,
    *,
    year: str = "2024",
) -> pl.DataFrame:
    """산업별/공정별 재무 집계.

    Returns
    -------
    pl.DataFrame
        columns: 공정, 공정명, 매출(조), 영업이익(조), 기업수
    """
    fin = _extractYearly(year)
    if fin.height == 0:
        return pl.DataFrame()

    # nodes → DataFrame
    nodesDf = pl.DataFrame(
        {
            "stockCode": [n.stockCode for n in nodes],
            "industry": [n.industry for n in nodes],
            "stage": [n.stage for n in nodes],
        }
    )

    joined = fin.join(nodesDf, on="stockCode", how="inner")
    filtered = joined.filter(
        (pl.col("industry") == industryId) & (pl.col("stage") != "")
    )

    if filtered.height == 0:
        return pl.DataFrame()

    # stage label 매핑
    from dartlab.industry.taxonomy import getIndustry

    ind = getIndustry(industryId)
    stageLabels = {s.key: s.name for s in ind.stages} if ind else {}

    result = (
        filtered.group_by("stage")
        .agg(
            [
                (pl.col("revenue").sum() / 1e12).round(1).alias("매출(조)"),
                (pl.col("opIncome").sum() / 1e12).round(1).alias("영업이익(조)"),
                pl.len().alias("기업수"),
            ]
        )
        .sort("매출(조)", descending=True)
    )

    # 공정명 추가
    result = result.with_columns(
        pl.col("stage")
        .replace_strict(stageLabels, default=None, return_dtype=pl.Utf8)
        .alias("공정명")
    )

    return result.select(["stage", "공정명", "매출(조)", "영업이익(조)", "기업수"])


def buildTimelineSummary(
    nodes: list[IndustryNode],
    industryId: str,
    *,
    years: list[str] | None = None,
) -> pl.DataFrame:
    """연도별 공정 매출 추이.

    Returns
    -------
    pl.DataFrame
        columns: 연도, 공정, 공정명, 매출(조), 영업이익(조), 기업수
    """
    if years is None:
        years = ["2021", "2022", "2023", "2024", "2025"]

    frames: list[pl.DataFrame] = []
    for year in years:
        df = buildIndustrySummary(nodes, industryId, year=year)
        if df.height > 0:
            df = df.with_columns(pl.lit(year).alias("연도"))
            frames.append(df)

    if not frames:
        return pl.DataFrame()

    return pl.concat(frames).select(
        ["연도", "stage", "공정명", "매출(조)", "영업이익(조)", "기업수"]
    ).sort(["stage", "연도"])
