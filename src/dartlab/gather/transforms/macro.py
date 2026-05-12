"""거시지표 시계열 정제 유틸 — ECOS/FRED 공통.

변화율 계산, 분기/연간 리샘플링, Parquet 영구 캐시.
analysis 계층에서 재무-거시 회귀 시 시간축 맞추기에 사용.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

log = logging.getLogger(__name__)

# Parquet 영구 캐시 경로
_CACHE_DIR = Path.home() / ".dartlab" / "cache" / "macro"


# ── 변화율 계산 ──


def addChangeRate(df: pl.DataFrame, *, valueName: str = "value") -> pl.DataFrame:
    """시계열 DataFrame에 변화율 컬럼 추가.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    valueName : str
        값 컬럼명. 기본 ``"value"``.

    Returns
    -------
    pl.DataFrame
        date : date — 관측일
        {valueName} : float — 원본 지표값
        change : float — 전기대비 변화량
        changePct : float — 전기대비 변화율 (%)
        yoyChange : float — 전년동기대비 변화량 (8행 이상 시)
        yoyChangePct : float — 전년동기대비 변화율 (%) (8행 이상 시)
        빈 DataFrame 또는 valueName 컬럼 미존재 시 원본 그대로 반환.

    Raises
    ------
    없음
        빈 입력은 원본 그대로 반환.

    Example
    -------
    >>> out = addChangeRate(df)
    """
    if df.is_empty() or valueName not in df.columns:
        return df

    result = df.sort("date").with_columns(
        (pl.col(valueName) - pl.col(valueName).shift(1)).alias("change"),
        ((pl.col(valueName) - pl.col(valueName).shift(1)) / pl.col(valueName).shift(1).abs() * 100).alias("changePct"),
    )

    # YoY: 날짜 간격 추정으로 lag 결정
    if len(df) >= 8:
        dates = df.sort("date").get_column("date")
        avgGapDays = (dates[-1] - dates[0]).days / (len(dates) - 1)

        if avgGapDays < 45:
            # 월별 → 12기 lag
            yoyLag = 12
        elif avgGapDays < 120:
            # 분기별 → 4기 lag
            yoyLag = 4
        else:
            # 연간 → 1기 lag
            yoyLag = 1

        result = result.with_columns(
            (pl.col(valueName) - pl.col(valueName).shift(yoyLag)).alias("yoyChange"),
            ((pl.col(valueName) - pl.col(valueName).shift(yoyLag)) / pl.col(valueName).shift(yoyLag).abs() * 100).alias(
                "yoyChangePct"
            ),
        )

    return result


# ── 리샘플링 ──


def resampleToQuarterly(df: pl.DataFrame, *, valueName: str = "value", method: str = "last") -> pl.DataFrame:
    """시계열을 분기별로 리샘플링.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    valueName : str
        값 컬럼명. 기본 ``"value"``.
    method : str
        집계 방식. ``"last"`` (기말값), ``"mean"`` (평균), ``"sum"`` (합계).

    Returns
    -------
    pl.DataFrame
        date : date — 분기 시작일
        {valueName} : float — 집계된 지표값
        빈 DataFrame 또는 valueName 컬럼 미존재 시 원본 그대로 반환.

    Raises
    ------
    KeyError
        ``method`` 가 ``"last"``/``"mean"``/``"sum"`` 외일 때.

    Example
    -------
    >>> q = resampleToQuarterly(df)
    """
    if df.is_empty() or valueName not in df.columns:
        return df

    df = df.sort("date")

    agg_expr = {
        "last": pl.col(valueName).last(),
        "mean": pl.col(valueName).mean(),
        "sum": pl.col(valueName).sum(),
    }[method]

    return df.with_columns(pl.col("date").cast(pl.Date)).group_by_dynamic("date", every="1q").agg(agg_expr).sort("date")


def resampleToAnnual(df: pl.DataFrame, *, valueName: str = "value", method: str = "last") -> pl.DataFrame:
    """시계열을 연간으로 리샘플링.

    Parameters
    ----------
    df : pl.DataFrame
        ``(date, value)`` 형태 시계열 DataFrame.
    valueName : str
        값 컬럼명. 기본 ``"value"``.
    method : str
        집계 방식. ``"last"`` (기말값), ``"mean"`` (평균), ``"sum"`` (합계).

    Returns
    -------
    pl.DataFrame
        date : date — 연도 시작일
        {valueName} : float — 집계된 지표값
        빈 DataFrame 또는 valueName 컬럼 미존재 시 원본 그대로 반환.

    Raises
    ------
    KeyError
        ``method`` 가 ``"last"``/``"mean"``/``"sum"`` 외일 때.

    Example
    -------
    >>> a = resampleToAnnual(df)
    """
    if df.is_empty() or valueName not in df.columns:
        return df

    df = df.sort("date")

    agg_expr = {
        "last": pl.col(valueName).last(),
        "mean": pl.col(valueName).mean(),
        "sum": pl.col(valueName).sum(),
    }[method]

    return df.with_columns(pl.col("date").cast(pl.Date)).group_by_dynamic("date", every="1y").agg(agg_expr).sort("date")


# ── Parquet 영구 캐시 ──


def saveMacroParquet(indicatorId: str, df: pl.DataFrame, *, source: str = "ecos") -> Path:
    """거시지표 시계열을 Parquet으로 영구 저장.

    Parameters
    ----------
    indicatorId : str
        지표 ID (예: "GDP", "CPI").
    df : pl.DataFrame
        ``(date, value, ...)`` 형태 시계열 DataFrame.
    source : str
        데이터 출처. "ecos" 또는 "fred".

    Returns
    -------
    Path
        저장된 Parquet 파일 경로 (``~/.dartlab/cache/macro/{source}/{indicatorId}.parquet``).

    Raises
    ------
    OSError
        디렉터리 생성/파일 쓰기 실패.

    Example
    -------
    >>> p = saveMacroParquet("GDP", df, source="fred")
    """
    dirPath = _CACHE_DIR / source
    dirPath.mkdir(parents=True, exist_ok=True)
    path = dirPath / f"{indicatorId}.parquet"
    df.write_parquet(path)
    log.debug("Parquet 저장: %s (%d rows)", path, len(df))
    return path


def loadMacroParquet(indicatorId: str, *, source: str = "ecos") -> pl.DataFrame | None:
    """Parquet 영구 캐시에서 거시지표 로드.

    Parameters
    ----------
    indicatorId : str
        지표 ID (예: "GDP", "CPI").
    source : str
        데이터 출처. "ecos" 또는 "fred".

    Returns
    -------
    pl.DataFrame | None
        date : date — 관측일
        value : float — 지표값
        changePct : float — 전기대비 변화율 (%), enrichAndCache 사용 시
        yoyChangePct : float — 전년동기대비 변화율 (%), enrichAndCache 사용 시
        캐시 파일 없거나 읽기 실패 시 None.

    Raises
    ------
    없음
        파일 부재 또는 읽기 오류 (OSError/ValueError/ImportError) 는 None 반환 + warning.

    Example
    -------
    >>> df = loadMacroParquet("GDP", source="fred")
    """
    path = _CACHE_DIR / source / f"{indicatorId}.parquet"
    if not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except (OSError, ValueError, ImportError):
        log.warning("Parquet 읽기 실패: %s", path)
        return None


def enrichAndCache(
    indicatorId: str,
    df: pl.DataFrame,
    *,
    source: str = "ecos",
    valueName: str = "value",
) -> pl.DataFrame:
    """변화율 추가 + Parquet 저장을 한 번에 처리.

    ``addChangeRate`` 로 변화율 컬럼을 추가한 뒤
    ``saveMacroParquet`` 로 영구 캐시에 저장한다.

    Parameters
    ----------
    indicatorId : str
        지표 ID (예: "GDP", "CPI").
    df : pl.DataFrame
        raw ``(date, value)`` DataFrame.
    source : str
        데이터 출처. "ecos" 또는 "fred".
    valueName : str
        값 컬럼명.

    Returns
    -------
    pl.DataFrame
        date : date — 관측일
        value : float — 원본 지표값
        change : float — 전기대비 변화량
        changePct : float — 전기대비 변화율 (%)
        yoyChange : float — 전년동기대비 변화량 (8행 이상 시)
        yoyChangePct : float — 전년동기대비 변화율 (%) (8행 이상 시)

    Raises
    ------
    OSError
        saveMacroParquet 의 파일 쓰기 실패 시.

    Example
    -------
    >>> out = enrichAndCache("GDP", df, source="fred")
    """
    enriched = addChangeRate(df, valueName=valueName)
    saveMacroParquet(indicatorId, enriched, source=source)
    return enriched


# ── 복수 지표 정렬 (재무 시계열과 맞추기) ──


def alignToFinancialPeriods(
    macroDf: pl.DataFrame,
    periods: list[str],
    *,
    valueName: str = "value",
) -> pl.DataFrame:
    """거시지표 시계열을 재무 기간에 맞춰 정렬.

    재무 기간 "2024A" → 2024년 기말값으로 매핑.
    재무 기간 "2024Q3" → 해당 분기 기말값으로 매핑.
    해당 기간에 데이터 없으면 value=None.

    Parameters
    ----------
    macroDf : pl.DataFrame
        ``(date, value, ...)`` 거시지표 DataFrame.
    periods : list[str]
        재무 기간 목록 (예: ``["2024A", "2023A", "2024Q3"]``).
    valueName : str
        값 컬럼명.

    Returns
    -------
    pl.DataFrame
        period : str — 재무 기간 레이블
        value : float | None — 해당 기간 기말 지표값

    Raises
    ------
    ValueError
        ``period`` 가 4자리 연도로 시작하지 않을 때 (int 변환 실패).

    Example
    -------
    >>> aligned = alignToFinancialPeriods(macroDf, ["2024A", "2024Q3"])
    """
    if macroDf.is_empty():
        return pl.DataFrame({"period": periods, "value": [None] * len(periods)})

    rows: list[dict] = []
    df = macroDf.sort("date")

    for period in periods:
        year = int(period[:4])

        if "Q" in period:
            q = int(period[-1])
            startMonth = (q - 1) * 3 + 1
            endMonth = q * 3
            from datetime import date

            startDate = date(year, startMonth, 1)
            if endMonth == 12:
                endDate = date(year, 12, 31)
            else:
                endDate = date(year, endMonth + 1, 1)

            mask = (pl.col("date") >= startDate) & (pl.col("date") < endDate)
        else:
            # 연간 ("2024A" 또는 "2024")
            from datetime import date

            startDate = date(year, 1, 1)
            endDate = date(year + 1, 1, 1)
            mask = (pl.col("date") >= startDate) & (pl.col("date") < endDate)

        subset = df.filter(mask)
        if subset.is_empty():
            rows.append({"period": period, "value": None})
        else:
            val = subset.get_column(valueName)[-1]  # 기말값
            rows.append({"period": period, "value": val})

    return pl.DataFrame(rows)
