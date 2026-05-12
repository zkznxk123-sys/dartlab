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

# 단위 오류 sanity guard — 한 종목 매출이 500조 KRW (5e14) 초과하면 단위 mix 의심
# (삼성전자 연결 매출 ~300조 미만이라 정상값은 절대 hit 안 함). DART 원본 또는 빌드
# 단계에서 단위 혼동 (원/백만원 mix) 으로 7.34e16 같은 값이 들어오면 산업 집계 왜곡.
_REVENUE_SANITY_LIMIT = 5.0e14
_OPINCOME_SANITY_LIMIT = 1.0e14
_ASSET_SANITY_LIMIT = 5.0e15


def _finPath() -> Path:
    from dartlab.frame.dataConfig import DATA_RELEASES
    from dartlab.frame.dataLoader import _getDataRoot

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
        .filter(pl.col("sj_div").is_in(["IS", "CIS", "BS"]))
        .select(["stockCode", "fs_div", "account_id_std", "thstrm_amount"])
        .collect(engine="streaming")
    )

    if df.height == 0:
        return pl.DataFrame()

    # 금액 변환
    df = df.with_columns(
        pl.col("thstrm_amount").str.replace_all(",", "").cast(pl.Float64, strict=False).alias("amount")
    )

    # 계정별로 CFS 우선, OFS fallback
    allCodes = df["stockCode"].unique().sort()
    result = pl.DataFrame({"stockCode": allCodes})

    for snakeId, alias in _ACCOUNTS.items():
        subset = df.filter(pl.col("account_id_std") == snakeId)
        cfs = subset.filter(pl.col("fs_div") == "CFS").group_by("stockCode").agg(pl.col("amount").first().alias(alias))
        ofsCodes = cfs.select("stockCode")
        ofs = (
            subset.filter(pl.col("fs_div") == "OFS")
            .join(ofsCodes, on="stockCode", how="anti")
            .group_by("stockCode")
            .agg(pl.col("amount").first().alias(alias))
        )
        acct = pl.concat([cfs, ofs])
        result = result.join(acct, on="stockCode", how="left")

    return _applySanityGuard(result, year=year)


def _applySanityGuard(result: pl.DataFrame, *, year: str) -> pl.DataFrame:
    """단위 오류 outlier 제거 + 경고 로깅.

    한 종목 매출 > 500조 / 영업이익 > 100조 / 총자산 > 5,000조 면 단위 mix 의심
    (예: 032680 소프트센 2022 sales = 7.34e16 = 73,373조 — 한국 GDP 30 배).
    해당 종목의 해당 계정 값을 None 으로 대체해 산업 집계 왜곡 차단.
    """
    if result.height == 0:
        return result

    checks = (
        ("revenue", _REVENUE_SANITY_LIMIT),
        ("opIncome", _OPINCOME_SANITY_LIMIT),
        ("totalAssets", _ASSET_SANITY_LIMIT),
    )
    for col, limit in checks:
        if col not in result.columns:
            continue
        # null dtype (모든 값 None) 컬럼은 skip — abs 연산 불가
        if not result.schema[col].is_numeric():
            continue
        outliers = result.filter(pl.col(col).abs() > limit)
        if outliers.height == 0:
            continue
        for row in outliers.iter_rows(named=True):
            logger.warning(
                "%s %s outlier (단위 오류 의심): %s = %.2e (> %.2e), 산업 집계에서 제외",
                year,
                col,
                row["stockCode"],
                row[col],
                limit,
            )
        result = result.with_columns(pl.when(pl.col(col).abs() > limit).then(None).otherwise(pl.col(col)).alias(col))

    return result


def attachFinancials(
    nodes: list[IndustryNode],
    *,
    years: list[str] | None = None,
) -> list[IndustryNode]:
    """nodes에 재무 데이터를 붙인다.

    최신 연도부터 시도하여 데이터가 있는 연도를 사용한다.

    Parameters
    ----------
    nodes : list[IndustryNode]
        기존 노드 리스트.
    years : list[str] | None
        시도할 연도 목록 (내림차순). None이면 2025→2024→2023.

    Returns
    -------
    list[IndustryNode]
        revenue 필드가 채워진 노드 리스트.
    """
    if years is None:
        years = ["2025", "2024", "2023"]

    # 최신 연도부터 merge

    allFin: dict[str, dict] = {}
    for year in years:
        fin = _extractYearly(year)
        if fin.height == 0:
            continue
        for row in fin.iter_rows(named=True):
            code = row["stockCode"]
            if code not in allFin:  # 최신 연도 우선
                allFin[code] = row

    if not allFin:
        return nodes

    finMap = allFin

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
    filtered = joined.filter((pl.col("industry") == industryId) & (pl.col("stage") != ""))

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
        pl.col("stage").replace_strict(stageLabels, default=None, return_dtype=pl.Utf8).alias("공정명")
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

    return (
        pl.concat(frames)
        .select(["연도", "stage", "공정명", "매출(조)", "영업이익(조)", "기업수"])
        .sort(["stage", "연도"])
    )
