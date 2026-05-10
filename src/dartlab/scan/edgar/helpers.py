"""EDGAR scan 공용 헬퍼 — scanAccount 기반 전종목 재무 지표 계산.

DART scan은 프리빌드 parquet에서 읽지만, EDGAR scan은
providers/edgar/finance/scanAccount.py를 활용하여 전종목 XBRL 데이터를 읽는다.
"""

from __future__ import annotations

import polars as pl


def scanEdgarAccounts(snakeIds: list[str], *, annual: bool = True) -> pl.DataFrame:
    """여러 EDGAR 계정을 한번에 스캔하여 wide DataFrame으로 반환.

    Parameters
    ----------
    snake_ids : list[str]
        스캔할 계정 snakeId 목록 (예: ["sales", "operating_profit"]).
    annual : bool
        연간(10-K) 데이터 사용 여부.

    Returns
    -------
    pl.DataFrame
        stockCode : str — CIK 또는 종목코드
        corpName : str — 회사명
        {snakeId} : float — 해당 계정의 최신 기간 값
        {snakeId}_prev : float — 해당 계정의 전기 값 (YoY 계산용)
    """
    from dartlab.providers.edgar.finance.scanAccount import scanAccount

    base: pl.DataFrame | None = None
    for sid in snakeIds:
        df = scanAccount(sid, annual=annual)
        if df.is_empty():
            continue
        # 가장 데이터가 많은 기간을 선택 (non-null 최다)
        period_cols = [c for c in df.columns if c not in ("stockCode", "corpName")]
        if len(period_cols) < 1:
            continue
        best_col = max(period_cols, key=lambda c: df[c].drop_nulls().len())
        prev_idx = period_cols.index(best_col) + 1
        prev_col = period_cols[prev_idx] if prev_idx < len(period_cols) else None
        select_cols = ["stockCode", "corpName", pl.col(best_col).alias(f"{sid}")]
        if prev_col:
            select_cols.append(pl.col(prev_col).alias(f"{sid}_prev"))
        narrow = df.select(select_cols)
        if base is None:
            base = narrow
        else:
            base = base.join(narrow, on="stockCode", how="outer", suffix=f"_{sid}")
            if f"corpName_{sid}" in base.columns:
                base = base.with_columns(
                    pl.coalesce(pl.col("corpName"), pl.col(f"corpName_{sid}")).alias("corpName")
                ).drop(f"corpName_{sid}")
    return base if base is not None else pl.DataFrame({"stockCode": []})


def safeDiv(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    """안전한 나눗셈 — 분모 0이면 None.

    Returns
    -------
    pl.Expr
        num / den. 분모가 0이면 None.
    """
    return pl.when(den != 0).then(num / den).otherwise(None)


def pct(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    """백분율 계산 — (num/den)*100, 소수점 2자리.

    Returns
    -------
    pl.Expr
        비율 (%). 분모 0이면 None.
    """
    return (safeDiv(num, den) * 100).round(2)


def scanEdgarRawTags(tags: list[str], *, annual: bool = True) -> pl.DataFrame:
    """XBRL 태그명으로 직접 전종목 스캔 (snakeId 매핑 없이).

    Parameters
    ----------
    tags : list[str]
        XBRL 태그명 목록 (예: ["AuditFees", "NonAuditServicesFees"]).
    annual : bool
        연간(10-K/20-F) 데이터만 필터.

    Returns
    -------
    pl.DataFrame
        stockCode : str — CIK
        corpName : str — 회사명
        {tag} : float — 각 태그의 최신 연도 값 (USD)
    """
    from dartlab.core.dataLoader import _getDataRoot

    edgarDir = _getDataRoot() / "edgar" / "finance"
    if not edgarDir.exists():
        return pl.DataFrame()

    records = []
    for fp in edgarDir.glob("*.parquet"):
        cik = fp.stem
        try:
            df = (
                pl.scan_parquet(fp)
                .filter(pl.col("tag").is_in(tags) & pl.col("form").is_in(["10-K", "20-F"]))
                .select("tag", "val", "fy", "entityName")
                .collect()
            )

            if df.is_empty():
                continue

            # 최신 연도
            latestFy = df["fy"].max()
            latest = df.filter(pl.col("fy") == latestFy)

            record = {
                "stockCode": cik,
                "corpName": latest["entityName"][0] if latest.height > 0 else "",
            }
            for tag in tags:
                tagRows = latest.filter(pl.col("tag") == tag)
                record[tag] = tagRows["val"][0] if tagRows.height > 0 else None

            records.append(record)
        except (pl.exceptions.ComputeError, OSError):
            continue

    return pl.DataFrame(records) if records else pl.DataFrame()


def gradeByValue(val: pl.Expr, thresholds: list[tuple[float, str]], default: str = "해당없음") -> pl.Expr:
    """값 기반 등급 분류.

    Parameters
    ----------
    val : pl.Expr
        등급 판정 대상 Polars 표현식.
    thresholds : list[tuple[float, str]]
        (하한, 등급) 리스트 (내림차순). 예: [(20, "우수"), (10, "양호")].
    default : str
        어떤 threshold에도 해당 안 되면 반환할 등급.

    Returns
    -------
    pl.Expr
        등급 문자열 (예: "우수", "양호", ..., default).
    """
    expr = val
    for i, (threshold, label) in enumerate(thresholds):
        if i == 0:
            expr = pl.when(val >= threshold).then(pl.lit(label))
        else:
            expr = expr.when(val >= threshold).then(pl.lit(label))
    return expr.otherwise(pl.lit(default))
