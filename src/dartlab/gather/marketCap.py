"""시가총액 합성 — 일별 종가 × 분기별 발행주식수.

데이터 소스:
- KR: data/dart/scan/sharesOutstanding.parquet (DART docs `4. 주식의 총수 등` 파싱)
- US: data/edgar/scan/sharesOutstanding.parquet (XBRL dei `EntityCommonStockSharesOutstanding`)
- 종가: gather("price", stockCode) — 시장별 fallback 체인

합성 방식: as-of backward join으로 가장 최근 보고서의 outstanding 을
다음 보고서가 나올 때까지 forward-fill 한다. 분기 사이 무상/유상증자는
다음 분기 보고서까지 stale 하다 (capitalChange 보강은 후속 트랙).

반환 컬럼:
    date, close, volume, commonOutstanding, preferredOutstanding,
    marketCap, marketCapTotal

    - marketCap = close × commonOutstanding (보통주 시총)
    - marketCapTotal = close × (commonOutstanding + preferredOutstanding)

호출 패턴:
    >>> from dartlab.gather.marketCap import marketCap
    >>> df = marketCap("005930")          # 일별 시계열
    >>> snap = marketCapSnapshot("005930") # 최신 한 점

ops/gather.md 4축 외 보조 모듈. analysis(L2) import 금지.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.quant._helpers import fetch_ohlcv, load_shares_outstanding, resolve_market

log = logging.getLogger(__name__)


def _stockSharesSeries(stockCode: str, market: str) -> pl.DataFrame | None:
    """단일 종목의 발행주식수 분기 시계열."""
    lf = load_shares_outstanding(market)
    if lf is None:
        return None
    try:
        if market == "KR":
            df = (
                lf.filter(pl.col("stock_code") == stockCode)
                .select(
                    [
                        "rcept_date",
                        "outstandingShares",
                        "preferredOutstanding",
                    ]
                )
                .collect()
            )
        else:
            df = (
                lf.filter(pl.col("ticker") == stockCode.upper())
                .select(["end", "val"])
                .rename({"end": "rcept_date", "val": "outstandingShares"})
                .with_columns(pl.lit(0.0).alias("preferredOutstanding"))
                .collect()
            )
    except (pl.exceptions.PolarsError, pl.exceptions.ColumnNotFoundError):
        return None
    if df.is_empty():
        return None
    # rcept_date 를 Date 로 정규화
    if df.schema["rcept_date"] == pl.Utf8:
        df = df.with_columns(pl.col("rcept_date").str.to_date(format="%Y%m%d", strict=False))
    return df.drop_nulls("rcept_date").sort("rcept_date")


def marketCap(stockCode: str, *, market: str = "auto") -> pl.DataFrame | None:
    """시가총액 일별 시계열.

    Args:
        stockCode: 종목코드/티커
        market: KR | US | auto

    Returns:
        Polars DataFrame (date, close, volume, commonOutstanding,
        preferredOutstanding, marketCap, marketCapTotal) 또는 None.
    """
    market = resolve_market(stockCode, market)

    px = fetch_ohlcv(stockCode)
    if px is None or not isinstance(px, pl.DataFrame) or px.is_empty():
        log.warning("marketCap: 주가 없음 %s", stockCode)
        return None

    shares = _stockSharesSeries(stockCode, market)
    if shares is None:
        log.warning("marketCap: 발행주식수 없음 %s", stockCode)
        return None

    if px.schema["date"] != pl.Date:
        px = px.with_columns(pl.col("date").cast(pl.Date, strict=False))

    px = px.sort("date").select(["date", "close", "volume"])

    merged = px.join_asof(
        shares,
        left_on="date",
        right_on="rcept_date",
        strategy="backward",
    )
    merged = merged.rename({"outstandingShares": "commonOutstanding"})
    merged = merged.with_columns(
        [
            pl.col("preferredOutstanding").fill_null(0.0),
            (pl.col("close") * pl.col("commonOutstanding")).alias("marketCap"),
            (
                pl.col("close")
                * (pl.col("commonOutstanding") + pl.col("preferredOutstanding").fill_null(0.0))
            ).alias("marketCapTotal"),
        ]
    )
    return merged.drop("rcept_date") if "rcept_date" in merged.columns else merged


def marketCapSnapshot(stockCode: str, *, market: str = "auto") -> dict | None:
    """최신 시가총액 한 점."""
    df = marketCap(stockCode, market=market)
    if df is None or df.is_empty():
        return None
    df = df.drop_nulls("marketCap")
    if df.is_empty():
        return None
    last = df.sort("date").row(-1, named=True)
    return {
        "stockCode": stockCode,
        "market": resolve_market(stockCode, market),
        "date": last["date"],
        "close": last["close"],
        "commonOutstanding": last["commonOutstanding"],
        "preferredOutstanding": last["preferredOutstanding"],
        "marketCap": last["marketCap"],
        "marketCapTotal": last["marketCapTotal"],
    }


def marketCapAll(market: str = "KR") -> pl.LazyFrame | None:
    """전 종목 최신 시가총액 횡단면 (factor/value 빌더용).

    분기별 시계열에서 종목당 가장 최근 rcept_date 한 행만 추출. 종가는
    별도로 일별 종가가 필요하므로 여기서는 outstanding 만 반환 (factor
    빌더가 자체 종가와 곱한다).

    Returns:
        LazyFrame (stock_code, rcept_date, outstandingShares, preferredOutstanding)
        또는 None.
    """
    lf = load_shares_outstanding(market)
    if lf is None:
        return None
    if market == "KR":
        latest = (
            lf.sort(["stock_code", "rcept_date"], descending=[False, True])
            .group_by("stock_code")
            .agg(
                [
                    pl.col("rcept_date").first(),
                    pl.col("outstandingShares").first(),
                    pl.col("preferredOutstanding").first(),
                ]
            )
        )
    else:
        latest = (
            lf.sort(["ticker", "end"], descending=[False, True])
            .group_by("ticker")
            .agg([pl.col("end").first().alias("rcept_date"), pl.col("val").first().alias("outstandingShares")])
            .with_columns(pl.lit(0.0).alias("preferredOutstanding"))
            .rename({"ticker": "stock_code"})
        )
    return latest
