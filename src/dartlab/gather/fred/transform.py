"""FRED 시계열 변환 — YoY, MoM, diff, MA, normalize, correlation, lead-lag.

모든 함수는 Polars DataFrame을 받아 Polars DataFrame을 반환.
입력 형식:
- 단일: (date, value)
- 복수: (date, col1, col2, ...)
"""

from __future__ import annotations

import polars as pl


def yoy(df: pl.DataFrame, col: str = "value") -> pl.DataFrame:
    """전년 동기 대비 변화율 (%).

    12개월 전 값 대비 퍼센트 변화. 월별 데이터 기준.
    분기별 데이터는 4행 전, 연간은 1행 전.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    col : str
        변화율 계산 대상 컬럼명.

    Returns
    -------
    pl.DataFrame
        원본 컬럼 + ``{col}_yoy`` (Float64) — 전년 동기 대비 변화율 (%).

    Raises
    ------
    없음.

    Example
    -------
    >>> df_yoy = yoy(df)
    """
    period = _inferPeriod(df)
    return df.with_columns(((pl.col(col) / pl.col(col).shift(period) - 1) * 100).alias(f"{col}_yoy"))


def mom(df: pl.DataFrame, col: str = "value") -> pl.DataFrame:
    """전월 대비 변화율 (%). 일별 데이터는 전일 대비.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    col : str
        변화율 계산 대상 컬럼명.

    Returns
    -------
    pl.DataFrame
        원본 컬럼 + ``{col}_mom`` (Float64) — 전월(전기) 대비 변화율 (%).

    Raises
    ------
    없음.

    Example
    -------
    >>> df_mom = mom(df)
    """
    return df.with_columns(((pl.col(col) / pl.col(col).shift(1) - 1) * 100).alias(f"{col}_mom"))


def diff(df: pl.DataFrame, col: str = "value", periods: int = 1) -> pl.DataFrame:
    """차분 (현재 값 - N기간 전 값).

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    col : str
        차분 대상 컬럼명.
    periods : int
        차분 기간 (행 수).

    Returns
    -------
    pl.DataFrame
        원본 컬럼 + ``{col}_diff{periods}`` (Float64) — 차분값.

    Raises
    ------
    없음.

    Example
    -------
    >>> df_diff = diff(df, periods=4)
    """
    return df.with_columns((pl.col(col) - pl.col(col).shift(periods)).alias(f"{col}_diff{periods}"))


def movingAverage(df: pl.DataFrame, col: str = "value", window: int = 12) -> pl.DataFrame:
    """이동평균.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    col : str
        이동평균 대상 컬럼명.
    window : int
        이동평균 윈도우 크기 (기).

    Returns
    -------
    pl.DataFrame
        원본 컬럼 + ``{col}_ma{window}`` (Float64) — 이동평균값.

    Raises
    ------
    없음.

    Example
    -------
    >>> df_ma = movingAverage(df, window=6)
    """
    return df.with_columns(pl.col(col).rolling_mean(window_size=window).alias(f"{col}_ma{window}"))


def normalize(df: pl.DataFrame, col: str = "value", baseDate: str | None = None) -> pl.DataFrame:
    """기준일 = 100 정규화.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    col : str
        정규화 대상 컬럼명.
    base_date : str | None
        기준일 (YYYY-MM-DD). None이면 첫 번째 유효값.

    Returns
    -------
    pl.DataFrame
        원본 컬럼 + ``{col}_norm`` (Float64) — 기준일 = 100 정규화 값.
        기준값이 0 또는 None이면 ``{col}_norm`` = None.

    Raises
    ------
    ValueError
        baseDate 가 YYYY-MM-DD 포맷이 아닐 때.

    Example
    -------
    >>> df_norm = normalize(df, baseDate="2020-01-01")
    """
    if baseDate is not None:
        from datetime import datetime

        target = datetime.strptime(baseDate, "%Y-%m-%d").date()
        base_row = df.filter(pl.col("date") == target)
        if base_row.is_empty():
            # 가장 가까운 날짜
            base_row = df.filter(pl.col("date") <= target).tail(1)
        if base_row.is_empty():
            base_row = df.head(1)
        baseVal = base_row[col][0]
    else:
        non_null = df.filter(pl.col(col).is_not_null())
        if non_null.is_empty():
            return df.with_columns(pl.lit(None).alias(f"{col}_norm"))
        baseVal = non_null[col][0]

    if baseVal is None or baseVal == 0:
        return df.with_columns(pl.lit(None).alias(f"{col}_norm"))

    return df.with_columns((pl.col(col) / baseVal * 100).alias(f"{col}_norm"))


def normalizeMulti(df: pl.DataFrame, baseDate: str | None = None) -> pl.DataFrame:
    """wide DataFrame의 모든 값 컬럼을 기준일=100 정규화.

    date 컬럼 제외한 모든 수치 컬럼을 정규화.

    Parameters
    ----------
    df : pl.DataFrame
        wide 형태 DataFrame (date, col1, col2, ...).
    base_date : str | None
        기준일 (YYYY-MM-DD). None이면 각 컬럼의 첫 번째 유효값.

    Returns
    -------
    pl.DataFrame
        동일 컬럼 구조에 각 수치 컬럼이 기준일=100으로 정규화된 DataFrame.

    Raises
    ------
    ValueError
        baseDate 가 YYYY-MM-DD 포맷이 아닐 때 (normalize 위임).

    Example
    -------
    >>> df_n = normalizeMulti(wide_df, baseDate="2020-01-01")
    """
    result = df.clone()
    for col in df.columns:
        if col == "date":
            continue
        if df[col].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32):
            temp = df.select("date", col)
            normed = normalize(temp, col=col, baseDate=baseDate)
            norm_col = f"{col}_norm"
            if norm_col in normed.columns:
                result = result.with_columns(normed[norm_col].alias(col))
    return result


def correlation(df: pl.DataFrame, method: str = "pearson") -> pl.DataFrame:
    """복수 시계열 간 상관행렬.

    Args:
        df: wide DataFrame (date, col1, col2, ...).
        method: "pearson" (기본). Polars 기본 지원.

    Returns:
        상관행렬 DataFrame (column, col1, col2, ...).

    Raises:
        없음 — 컬럼 2개 미만이면 빈 DataFrame.

    Example:
        >>> corr = correlation(wide_df)
    """
    value_cols = [c for c in df.columns if c != "date"]
    if len(value_cols) < 2:
        return pl.DataFrame()

    # null 제거 후 상관 계산
    clean = df.select(value_cols).drop_nulls()

    n = len(value_cols)
    rows: list[dict] = []
    for i in range(n):
        row: dict = {"column": value_cols[i]}
        for j in range(n):
            if i == j:
                row[value_cols[j]] = 1.0
            else:
                corr_val = clean.select(pl.corr(value_cols[i], value_cols[j])).item()
                row[value_cols[j]] = round(corr_val, 4) if corr_val is not None else None
        rows.append(row)

    return pl.DataFrame(rows)


def leadLag(
    df: pl.DataFrame,
    colA: str,
    colB: str,
    *,
    maxLag: int = 12,
) -> pl.DataFrame:
    """선행/후행 상관분석.

    col_a를 기준으로 col_b를 -max_lag ~ +max_lag 시프트하여 상관계수 측정.
    양수 lag = col_b가 col_a보다 후행, 음수 = col_b가 선행.

    Returns:
        DataFrame (lag, correlation).

    Raises:
        없음 — 데이터 3행 미만이면 lag 별 None.

    Example:
        >>> df_ll = leadLag(wide_df, "FEDFUNDS", "UNRATE", maxLag=6)
    """
    clean = df.select(colA, colB).drop_nulls()
    a = clean[colA]
    b = clean[colB]

    lags: list[int] = []
    corrs: list[float | None] = []

    for lag in range(-maxLag, maxLag + 1):
        if lag == 0:
            corr_val = clean.select(pl.corr(colA, colB)).item()
        elif lag > 0:
            shifted = pl.DataFrame({colA: a[lag:], colB: b[: len(b) - lag]})
            if shifted.height < 3:
                corr_val = None
            else:
                corr_val = shifted.select(pl.corr(colA, colB)).item()
        else:
            shift_abs = abs(lag)
            shifted = pl.DataFrame({colA: a[: len(a) - shift_abs], colB: b[shift_abs:]})
            if shifted.height < 3:
                corr_val = None
            else:
                corr_val = shifted.select(pl.corr(colA, colB)).item()

        lags.append(lag)
        corrs.append(round(corr_val, 4) if corr_val is not None else None)

    return pl.DataFrame({"lag": lags, "correlation": corrs})


# ── internal ──


def _inferPeriod(df: pl.DataFrame) -> int:
    """데이터 간격 추론 → YoY 기간 결정.

    date 컬럼의 중앙 간격(일)으로 주기를 판별한다.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.

    Returns
    -------
    int
        YoY 비교용 행 수 (개).
        일별 252, 주별 52, 월별 12, 분기별 4, 연간 1.
        데이터 3행 미만이면 1.
    """
    if df.height < 3:
        return 1

    dates = df["date"].drop_nulls()
    if dates.dtype == pl.Date:
        diffs = dates.diff().drop_nulls()
        median_days = diffs.cast(pl.Int64).median()
        if median_days is None:
            return 12
        if median_days <= 5:
            return 252  # daily → ~1 year
        if median_days <= 10:
            return 52  # weekly
        if median_days <= 45:
            return 12  # monthly
        if median_days <= 120:
            return 4  # quarterly
        return 1  # annual

    return 12  # default
