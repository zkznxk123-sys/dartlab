"""FRED/ECOS HF 데이터셋 액세스 — gather macro 기본 경로.

KRX 벌크와 같은 패턴:
    - 운영자 cron 이 API 키로 전체 카탈로그를 HF 에 publish
    - 사용자는 API 키 없이 HF snapshot 을 소비
    - 직접 API 호출은 gather("macro", ..., apiKey="...") 로만 선택
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime

import polars as pl

_SOURCE_TO_CATEGORY = {
    "fred": "macroFred",
    "ecos": "macroEcos",
}


def _toDate(value: str | _date) -> _date:
    """YYYY-MM-DD / YYYYMMDD / date → date."""
    if isinstance(value, _date):
        return value
    s = str(value).replace("-", "").strip()
    if len(s) >= 8:
        return _date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    if len(s) == 4:
        return _date(int(s), 1, 1)
    raise ValueError(f"날짜 포맷 오류: {value!r}")


def _category(source: str) -> str:
    key = source.lower()
    if key not in _SOURCE_TO_CATEGORY:
        raise ValueError("source 는 'fred' 또는 'ecos' 여야 합니다.")
    return _SOURCE_TO_CATEGORY[key]


def loadManifest(source: str) -> pl.DataFrame:
    """HF macro manifest 로드.

    Parameters
    ----------
    source : str
        "fred" 또는 "ecos".

    Returns
    -------
    pl.DataFrame
        seriesId : str — 시리즈 ID
        label : str — 한글 라벨
        group : str — 카탈로그 그룹
        frequency : str — 원본 주기
        unit : str — 단위
        status : str — ok/stale/error
    """
    from dartlab.core.dataLoader import loadData

    return loadData("manifest", category=_category(source))


def loadObservations(source: str) -> pl.DataFrame:
    """HF macro observations 로드."""
    from dartlab.core.dataLoader import loadData

    df = loadData("observations", category=_category(source))
    if "date" in df.columns:
        df = df.with_columns(pl.col("date").cast(pl.Date))
    return df


def availableSeries(source: str) -> set[str]:
    """HF manifest 기준 사용 가능한 시리즈 ID 집합."""
    manifest = loadManifest(source)
    if manifest.is_empty() or "seriesId" not in manifest.columns:
        return set()
    return set(manifest.get_column("seriesId").drop_nulls().to_list())


def fetchSeries(
    source: str,
    seriesId: str,
    *,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> pl.DataFrame:
    """HF macro 단일 시리즈 조회 → ``(date, value)``.

    Parameters
    ----------
    limit : int | None
        반환 행수 상한 (가장 최근 N). None이면 전체.

    Raises
    ------
    ValueError
        HF 카탈로그에 없는 시리즈일 때. 직접 API가 필요하면 ``apiKey=``를 명시해야 한다.
    """
    sourceKey = source.lower()
    supported = availableSeries(sourceKey)
    if seriesId not in supported:
        envKey = "FRED_API_KEY" if sourceKey == "fred" else "ECOS_API_KEY"
        raise ValueError(
            f"{sourceKey.upper()} HF 카탈로그에 없는 지표입니다: {seriesId}. "
            f"직접 API 조회가 필요하면 gather('macro', '{seriesId}', apiKey=...) "
            f"또는 {envKey} 값을 apiKey 인자로 전달하세요."
        )

    df = loadObservations(sourceKey)
    if df.is_empty():
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})
    df = df.filter(pl.col("seriesId") == seriesId)
    if start:
        df = df.filter(pl.col("date") >= _toDate(start))
    if end:
        df = df.filter(pl.col("date") <= _toDate(end))
    if df.is_empty():
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})
    out = df.select("date", "value").sort("date")
    if limit is not None and limit > 0:
        return out.tail(limit)
    return out


def fetchMulti(
    source: str,
    seriesIds: list[str],
    *,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> pl.DataFrame:
    """HF macro 복수 시리즈 조회 → wide DataFrame.

    Parameters
    ----------
    limit : int | None
        반환 행수 상한 (가장 최근 N). None이면 전체.
    """
    if not seriesIds:
        return pl.DataFrame()

    frames: list[pl.DataFrame] = []
    for sid in seriesIds:
        df = fetchSeries(source, sid, start=start, end=end)
        if df.is_empty():
            df = pl.DataFrame(schema={"date": pl.Date, sid: pl.Float64})
        else:
            df = df.rename({"value": sid})
        frames.append(df)

    result = frames[0]
    for df in frames[1:]:
        result = result.join(df, on="date", how="full", coalesce=True)

    fillCols = [c for c in result.columns if c != "date"]
    if fillCols:
        result = result.sort("date").with_columns([pl.col(c).forward_fill() for c in fillCols])
    out = result.sort("date")
    if limit is not None and limit > 0:
        return out.tail(limit)
    return out


def latestUpdatedAt(source: str) -> datetime | None:
    """manifest 의 최신 갱신 시각 반환."""
    manifest = loadManifest(source)
    if manifest.is_empty() or "updatedAtUtc" not in manifest.columns:
        return None
    vals = manifest.get_column("updatedAtUtc").drop_nulls().to_list()
    if not vals:
        return None
    try:
        return datetime.fromisoformat(str(max(vals)).replace("Z", "+00:00"))
    except ValueError:
        return None
